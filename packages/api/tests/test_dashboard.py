"""M2 — backend mount model, engine lifecycle, config, auth, migrations."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import devdash
from devdash import (
    CONTRACT_VERSION,
    DevDashConfig,
    make_dashboard_app,
    mount_dashboard,
)
from devdash.db import dispose_engine, make_engine
from devdash.migrations import create_database, migrate


def _config(tmp_path, **over) -> DevDashConfig:
    db = tmp_path / "devdash.db"
    return DevDashConfig(database_url=f"sqlite+aiosqlite:///{db}", **over)


def test_standalone_app_meta_and_health(tmp_path):
    app = make_dashboard_app(_config(tmp_path))
    with TestClient(app) as client:  # `with` runs the lifespan -> builds engine
        meta = client.get("/dev/__devdash/meta")
        assert meta.status_code == 200
        body = meta.json()
        assert body["contract_version"] == CONTRACT_VERSION
        assert body["version"] == devdash.__version__
        assert body["base_path"] == "/dev"

        health = client.get("/dev/healthz")
        assert health.status_code == 200
        assert health.json() == {"status": "ok", "db": "ok"}


def test_mount_into_host_no_cross_loop(tmp_path):
    """Regression for ADR-D10: the engine is built inside the lifespan on the
    running loop, so a request that touches it must not raise a cross-loop
    error. The host composes the returned lifespan into its own."""
    holder: dict[str, object] = {}

    @asynccontextmanager
    async def host_lifespan(_app: FastAPI):
        async with holder["dash"]():  # type: ignore[operator]
            yield

    host = FastAPI(lifespan=host_lifespan)
    holder["dash"] = mount_dashboard(host, _config(tmp_path), "/dev")

    @host.get("/")
    def root():
        return {"host": "ok"}

    with TestClient(host) as client:
        assert client.get("/").json() == {"host": "ok"}
        # Hits the devdash engine through the mounted sub-app — proves the
        # engine works on the request loop.
        assert client.get("/dev/healthz").json() == {"status": "ok", "db": "ok"}


def test_health_503_when_lifespan_not_wired(tmp_path):
    # Mounted but lifespan NOT composed -> engine never built -> honest failure.
    host = FastAPI()
    mount_dashboard(host, _config(tmp_path), "/dev")
    with TestClient(host) as client:
        assert client.get("/dev/healthz").status_code == 503  # honest 'not started'


def test_auth_open_by_default(tmp_path):
    app = make_dashboard_app(_config(tmp_path))
    with TestClient(app) as client:
        assert client.post("/dev/__devdash/echo", json={"x": 1}).status_code == 200


def test_auth_bearer_enforced(tmp_path):
    app = make_dashboard_app(_config(tmp_path, auth_token="s3cret"))
    with TestClient(app) as client:
        assert client.post("/dev/__devdash/echo", json={"x": 1}).status_code == 401
        ok = client.post(
            "/dev/__devdash/echo",
            json={"x": 1},
            headers={"Authorization": "Bearer s3cret"},
        )
        assert ok.status_code == 200
        assert ok.json() == {"echo": {"x": 1}}


def test_config_reads_env(monkeypatch):
    monkeypatch.setenv("DEVDASH_BASE_PATH", "/ops")
    monkeypatch.setenv("DEVDASH_AUTH_TOKEN", "abc")
    monkeypatch.setenv("DEVDASH_ENABLE_METRICS", "true")
    config = DevDashConfig()
    assert config.base_path == "/ops"
    assert config.auth_token == "abc"
    assert config.enable_metrics is True
    assert config.cors_origins == []  # never defaults to "*"


async def test_migrate_is_idempotent(tmp_path):
    config = _config(tmp_path)
    engine = make_engine(config.database_url)
    try:
        await migrate(engine, config)
        await migrate(engine, config)  # expand-only: running twice is a no-op
    finally:
        await dispose_engine(engine)


async def test_create_database_sqlite_is_noop(tmp_path):
    config = _config(tmp_path)
    assert await create_database(config.database_url) is False


def test_metrics_opt_in(tmp_path):
    app = make_dashboard_app(_config(tmp_path, enable_metrics=True))
    with TestClient(app) as client:
        assert client.get("/dev/metrics").status_code == 200


@pytest.mark.parametrize("url", ["sqlite+aiosqlite:///x.db"])
def test_is_sqlite(url):
    assert DevDashConfig(database_url=url).is_sqlite is True


def test_standalone_serves_ui_bundle(tmp_path):
    app = make_dashboard_app(_config(tmp_path))
    with TestClient(app) as client:
        resp = client.get("/dev/")
        assert resp.status_code == 200
        assert "devdash" in resp.text.lower()
