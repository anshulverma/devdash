"""Alembic-driven, advisory-locked, expand-only migrations for devdash's DB.

``migrate()`` runs ``alembic upgrade head`` against devdash's OWNED database
using the async run_sync pattern. On Postgres a session-level advisory lock is
held (on a separate connection) so concurrent blue/green replicas booting
together cannot double-apply. Migrations must be expand-only (ADR-D07).
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from .config import DevDashConfig

logger = logging.getLogger("devdash.migrations")

# Stable arbitrary key for the devdash migration advisory lock.
_ADVISORY_LOCK_KEY = 0x44455644  # "DEVD"


def _alembic_config():
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "_alembic"))
    return cfg


def _run_upgrade(connection: Connection, cfg) -> None:
    from alembic import command

    cfg.attributes["connection"] = connection
    command.upgrade(cfg, "head")


async def migrate(engine: AsyncEngine, config: DevDashConfig) -> None:
    """Run ``alembic upgrade head`` against devdash's owned database."""
    cfg = _alembic_config()

    if config.is_sqlite:
        async with engine.connect() as conn:
            await conn.run_sync(_run_upgrade, cfg)
            await conn.commit()
        logger.info("devdash migrate complete (sqlite)")
        return

    # Postgres: hold a session-level advisory lock on a dedicated connection so
    # it spans alembic's own transaction; migrate on a second connection.
    async with engine.connect() as lock_conn:
        await lock_conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _ADVISORY_LOCK_KEY})
        try:
            async with engine.connect() as conn:
                await conn.run_sync(_run_upgrade, cfg)
                await conn.commit()
        finally:
            await lock_conn.execute(
                text("SELECT pg_advisory_unlock(:k)"), {"k": _ADVISORY_LOCK_KEY}
            )
    logger.info("devdash migrate complete (postgres, advisory-locked)")


async def create_database(database_url: str) -> bool:
    """Provision the devdash-owned database if absent (`devdash db create`).

    Returns True if it created the database, False if it already existed or the
    driver creates it lazily (SQLite). For Postgres this connects to the
    server's maintenance DB with asyncpg and issues CREATE DATABASE.
    """
    if database_url.startswith("sqlite"):
        return False

    import asyncpg
    from sqlalchemy.engine import make_url

    url = make_url(database_url)
    target_db = url.database
    if not target_db:
        raise ValueError("database_url has no database name to create")
    admin = url.set(database="postgres", drivername="postgresql")
    dsn = admin.render_as_string(hide_password=False).replace("postgresql+asyncpg", "postgresql")

    conn = await asyncpg.connect(dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", target_db)
        if exists:
            return False
        await conn.execute(f'CREATE DATABASE "{target_db}"')
        return True
    finally:
        await conn.close()
