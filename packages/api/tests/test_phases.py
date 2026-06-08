"""M4 box 1 — phase-tracker tables created via alembic in devdash's owned DB."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect

from devdash.config import DevDashConfig
from devdash.db import dispose_engine, make_engine
from devdash.migrations import migrate

_PG = os.environ.get("DEVDASH_TEST_PG_URL")
_BACKENDS = ["sqlite"] + (["postgres"] if _PG else [])

PHASE_TABLES = {
    "devdash_sessions",
    "devdash_token_usage",
    "devdash_phase_config",
    "devdash_phase_transitions",
    "devdash_developers",
    "devdash_dev_settings",
    "devdash_projection_snapshots",
}


@pytest.fixture(params=_BACKENDS)
async def engine(request, tmp_path):
    url = _PG if request.param == "postgres" else f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite'}"
    eng = make_engine(url)
    if request.param == "postgres":  # clean slate on the shared PG
        from sqlalchemy import text

        async with eng.begin() as c:
            await c.execute(text("DROP SCHEMA public CASCADE"))
            await c.execute(text("CREATE SCHEMA public"))
    yield eng, DevDashConfig(database_url=url)
    await dispose_engine(eng)


async def test_migrate_creates_phase_tables(engine):
    eng, config = engine
    await migrate(eng, config)

    def _tables(sync_conn):
        return set(inspect(sync_conn).get_table_names())

    async with eng.connect() as conn:
        names = await conn.run_sync(_tables)
    assert PHASE_TABLES.issubset(names)
    assert "alembic_version" in names


async def test_migrate_is_idempotent(engine):
    eng, config = engine
    await migrate(eng, config)
    await migrate(eng, config)  # advisory-locked, expand-only — safe to repeat
