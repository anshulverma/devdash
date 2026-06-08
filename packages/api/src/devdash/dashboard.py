"""The devdash backend: a mountable FastAPI sub-app + a standalone runner.

``make_dashboard_app(config)`` returns a self-contained app (own CORS, metrics,
exception handling) — the same object the standalone runner serves.
``mount_dashboard(host_app, config)`` mounts that sub-app into a host app and
returns the lifespan the host MUST compose into its own (Starlette does not run
a mounted sub-app's lifespan), so the in-loop engine + background tasks actually
start (ADR-D09, D10).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .auth import AuthDependency, build_auth_dependency
from .config import DevDashConfig
from .db import dispose_engine, make_engine
from .logs import InMemoryLogSource, LogSource, build_logs_router
from .phases import PhaseTrackerConfig, build_phases_router
from .version import CONTRACT_VERSION, __version__

logger = logging.getLogger("devdash")

LifespanFactory = Callable[[], AbstractAsyncContextManager[None]]


class Dashboard:
    """Owns the sub-app, the config, and the engine bound to the running loop."""

    def __init__(
        self,
        config: DevDashConfig,
        *,
        auth_hook: AuthDependency | None = None,
        log_source: LogSource | None = None,
        phases_config: PhaseTrackerConfig | None = None,
    ) -> None:
        self.config = config
        self._engine: AsyncEngine | None = None
        self._auth = build_auth_dependency(config, auth_hook)
        self._log_source: LogSource = log_source or InMemoryLogSource()
        self._phases_config = phases_config or PhaseTrackerConfig()
        self.app = self._build_app()

    # -- engine ---------------------------------------------------------------
    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError(
                "devdash engine not started — wire dashboard_lifespan into the host lifespan"
            )
        return self._engine

    def _require_engine(self) -> AsyncEngine:
        # FastAPI dependency: honest 503 (not a 500 crash) when the host forgot
        # to wire the lifespan, so the dashboard degrades gracefully.
        if self._engine is None:
            raise HTTPException(
                status_code=503,
                detail="devdash not started — compose dashboard_lifespan into the host lifespan",
            )
        return self._engine

    # -- lifespan -------------------------------------------------------------
    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        # Built HERE, on the running loop — never at import (ADR-D10).
        self._engine = make_engine(self.config.database_url)
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            if self.config.auto_migrate:
                from .migrations import migrate

                await migrate(self._engine, self.config)
            # Bind the engine to adapters that need it (e.g. the SQL log source),
            # on the running loop after migration.
            bind = getattr(self._log_source, "bind_engine", None)
            if bind is not None:
                await bind(self._engine)
            if "phases" in self.config.enabled_tabs and self._phases_config.phases:
                from .phases.repository import seed_phases

                await seed_phases(self._engine, self._phases_config.phases)
            yield
        finally:
            engine, self._engine = self._engine, None
            if engine is not None:
                await dispose_engine(engine)

    # -- app ------------------------------------------------------------------
    def _build_app(self) -> FastAPI:
        app = FastAPI(title="devdash", version=__version__)

        if self.config.cors_origins:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.cors_origins,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        if self.config.enable_metrics:
            from prometheus_fastapi_instrumentator import Instrumentator

            Instrumentator().instrument(app).expose(app, endpoint="/metrics")

        auth = self._auth

        @app.get("/__devdash/meta", tags=["meta"])
        async def meta() -> dict[str, object]:
            # Unauthenticated: the UI reads this before it has credentials, to
            # guard against UI/backend version skew (ADR-D12).
            return {
                "contract_version": CONTRACT_VERSION,
                "version": __version__,
                "base_path": self.config.base_path,
            }

        @app.get("/healthz", tags=["meta"])
        async def healthz(engine: AsyncEngine = Depends(self._require_engine)) -> dict[str, str]:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ok", "db": "ok"}

        @app.post("/__devdash/echo", tags=["meta"], dependencies=[Depends(auth)])
        async def echo(payload: dict[str, object]) -> dict[str, object]:
            # A trivial guarded (mutating) route, useful for auth wiring tests.
            return {"echo": payload}

        if "logs" in self.config.enabled_tabs:
            app.include_router(build_logs_router(self._log_source))

        if "phases" in self.config.enabled_tabs:
            app.include_router(build_phases_router(self._require_engine, self._phases_config))

        _mount_ui(app)
        return app


def dashboard_lifespan(
    config: DevDashConfig,
    *,
    auth_hook: AuthDependency | None = None,
    log_source: LogSource | None = None,
    phases_config: PhaseTrackerConfig | None = None,
) -> tuple[FastAPI, LifespanFactory]:
    """Build the dashboard sub-app and return ``(sub_app, lifespan)``.

    For hosts that mount the sub-app themselves and compose the returned
    lifespan into their own.
    """
    dash = Dashboard(
        config, auth_hook=auth_hook, log_source=log_source, phases_config=phases_config
    )
    return dash.app, dash.lifespan


def mount_dashboard(
    host_app: FastAPI,
    config: DevDashConfig,
    path: str | None = None,
    *,
    auth_hook: AuthDependency | None = None,
    log_source: LogSource | None = None,
    phases_config: PhaseTrackerConfig | None = None,
) -> LifespanFactory:
    """Mount the dashboard into ``host_app`` and return the lifespan to compose.

    The host MUST wire the returned lifespan into its own::

        dash_lifespan = mount_dashboard(app, config)

        @asynccontextmanager
        async def lifespan(app):
            async with dash_lifespan():
                yield
    """
    dash = Dashboard(
        config, auth_hook=auth_hook, log_source=log_source, phases_config=phases_config
    )
    host_app.mount(path or config.base_path, dash.app)
    return dash.lifespan


def make_dashboard_app(
    config: DevDashConfig,
    *,
    auth_hook: AuthDependency | None = None,
    log_source: LogSource | None = None,
    phases_config: PhaseTrackerConfig | None = None,
) -> FastAPI:
    """A self-contained app the standalone runner serves: a root app that mounts
    the dashboard sub-app at ``config.base_path`` with its lifespan wired."""
    dash = Dashboard(
        config, auth_hook=auth_hook, log_source=log_source, phases_config=phases_config
    )

    @asynccontextmanager
    async def root_lifespan(_app: FastAPI) -> AsyncIterator[None]:
        async with dash.lifespan():
            yield

    root = FastAPI(title="devdash (standalone)", version=__version__, lifespan=root_lifespan)
    root.mount(config.base_path, dash.app)
    return root


def _ui_dir() -> Path:
    """Directory of the bundled UI assets shipped in the wheel."""
    return Path(__file__).parent / "static"


def _mount_ui(app: FastAPI) -> None:
    """Serve the bundled UI shell as static assets (SPA), if packaged.

    The release pipeline (M5) builds @devdash/ui into this directory; until then
    a placeholder index.html is served. API routes are registered first, so this
    catch-all mount only handles UI/asset paths.
    """
    ui = _ui_dir()
    if (ui / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(ui), html=True), name="ui")
