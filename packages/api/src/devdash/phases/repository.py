"""Async DB access for the phase tracker (devdash's owned tables)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from . import models as m
from .taxonomy import PhaseSpec


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def seed_phases(engine: AsyncEngine, specs: list[PhaseSpec]) -> int:
    """Insert phase_config rows for phases not yet present. Seed values only —
    existing rows (with the dashboard's edits) are left untouched. Returns the
    number of rows inserted."""
    if not specs:
        return 0
    async with engine.begin() as conn:
        existing = {r[0] for r in (await conn.execute(select(m.phase_config.c.phase))).all()}
        now = _now()
        inserted = 0
        for s in specs:
            if s.key in existing:
                continue
            await conn.execute(
                insert(m.phase_config).values(
                    phase=s.key,
                    label=s.label,
                    status=s.status,
                    complexity=s.complexity,
                    display_order=s.display_order,
                    parent=s.parent,
                    updated_at=now,
                )
            )
            inserted += 1
    return inserted


async def list_phases(engine: AsyncEngine) -> list[dict]:
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                select(m.phase_config).order_by(
                    m.phase_config.c.display_order, m.phase_config.c.phase
                )
            )
        ).all()
    return [dict(r._mapping) for r in rows]


async def create_session(engine: AsyncEngine, data: dict) -> dict:
    now = _now()
    values = {**data, "created_at": now, "updated_at": now}
    async with engine.begin() as conn:
        res = await conn.execute(insert(m.sessions).values(**values))
        sid = res.inserted_primary_key[0]
    got = await get_session(engine, sid)
    assert got is not None
    return got


async def get_session(engine: AsyncEngine, session_id: int) -> dict | None:
    async with engine.connect() as conn:
        row = (
            await conn.execute(select(m.sessions).where(m.sessions.c.id == session_id))
        ).first()
    return dict(row._mapping) if row else None


async def list_sessions(
    engine: AsyncEngine, *, dev_name: str | None = None, phase: str | None = None
) -> list[dict]:
    q = select(m.sessions).order_by(m.sessions.c.started_at.desc())
    if dev_name:
        q = q.where(m.sessions.c.dev_name == dev_name)
    if phase:
        q = q.where(m.sessions.c.phase == phase)
    async with engine.connect() as conn:
        rows = (await conn.execute(q)).all()
    return [dict(r._mapping) for r in rows]


async def update_session(engine: AsyncEngine, session_id: int, changes: dict) -> dict | None:
    async with engine.begin() as conn:
        await conn.execute(
            update(m.sessions)
            .where(m.sessions.c.id == session_id)
            .values(**changes, updated_at=_now())
        )
    return await get_session(engine, session_id)


async def delete_session(engine: AsyncEngine, session_id: int) -> bool:
    async with engine.begin() as conn:
        res = await conn.execute(delete(m.sessions).where(m.sessions.c.id == session_id))
    return res.rowcount > 0
