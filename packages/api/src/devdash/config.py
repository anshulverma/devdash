"""Typed configuration for the devdash backend.

Precedence: explicit constructor args > ``DEVDASH_*`` environment variables >
defaults. Construct via ``DevDashConfig()`` (reads env) or pass overrides.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DevDashConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEVDASH_", extra="ignore")

    #: SQLAlchemy async URL for the devdash-OWNED database. Defaults to a local
    #: SQLite file for zero-config standalone/demo; production points this at a
    #: dedicated Postgres database that devdash owns end to end (ADR-D07).
    database_url: str = "sqlite+aiosqlite:///./devdash.db"

    #: Path the dashboard sub-app is mounted under.
    base_path: str = "/dev"

    #: Explicit CORS allow-list. NEVER defaults to "*".
    cors_origins: list[str] = Field(default_factory=list)

    #: Optional bearer token guarding mutating routes. When unset and no auth
    #: hook is supplied, the dashboard is open (and logs a loud warning).
    auth_token: str | None = None

    #: Expose Prometheus metrics. Off by default in mounted mode (the host
    #: likely already instruments); the standalone runner turns it on.
    enable_metrics: bool = False

    #: Run migrations automatically inside the lifespan. Hosts driving DDL from
    #: their own release pipeline set this False.
    auto_migrate: bool = True

    #: Built-in tabs to mount.
    enabled_tabs: set[str] = Field(default_factory=lambda: {"logs", "phases"})

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")
