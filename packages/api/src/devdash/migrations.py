"""Expand-only, advisory-locked schema management for devdash's owned database.

`migrate()` is expand-only: it only ever CREATEs missing tables (never drops),
so it is safe under blue/green rollout. On Postgres it takes a transaction-level
advisory lock so two replicas booting together cannot double-apply.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .config import DevDashConfig
from .metadata import metadata

logger = logging.getLogger("devdash.migrations")

# Stable arbitrary key for the devdash migration advisory lock.
_ADVISORY_LOCK_KEY = 0x44455644  # "DEVD"


async def migrate(engine: AsyncEngine, config: DevDashConfig) -> None:
    """Create any missing devdash tables (expand-only), advisory-locked on PG."""
    async with engine.begin() as conn:
        if not config.is_sqlite:
            await conn.execute(
                text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ADVISORY_LOCK_KEY}
            )
        await conn.run_sync(metadata.create_all)
    logger.info("devdash migrate complete (%d tables known)", len(metadata.tables))


async def create_database(database_url: str) -> bool:
    """Provision the devdash-owned database if absent (`devdash db create`).

    Returns True if it created the database, False if it already existed or the
    driver creates it lazily (SQLite). For Postgres this connects to the
    server's maintenance DB with asyncpg and issues CREATE DATABASE.
    """
    if database_url.startswith("sqlite"):
        # SQLite creates the file on first connect; nothing to provision.
        return False

    import asyncpg  # local import; only needed for the PG path

    # Normalize the SQLAlchemy URL to an asyncpg DSN and split off the db name.
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
        # CREATE DATABASE cannot run inside a transaction block.
        await conn.execute(f'CREATE DATABASE "{target_db}"')
        return True
    finally:
        await conn.close()
