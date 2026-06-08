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


async def import_token_rows(engine: AsyncEngine, rows: list, price_table) -> dict:
    """Idempotent (on message_uuid) provider-neutral token ingest. Computes cost
    from the price table when a row omits it; unknown models yield cost 0 and a
    warning (ADR-D08). `rows` are TokenRow; `price_table` is a PriceTable."""
    from .tokens import ImportResult

    result = ImportResult()
    unknown: set[str] = set()
    if not rows:
        return result.model_dump()
    now = _now()
    async with engine.begin() as conn:
        uuids = [r.message_uuid for r in rows]
        existing = {
            r[0]
            for r in (
                await conn.execute(
                    select(m.token_usage.c.message_uuid).where(
                        m.token_usage.c.message_uuid.in_(uuids)
                    )
                )
            ).all()
        }
        for r in rows:
            if r.message_uuid in existing:
                result.skipped += 1
                continue
            cost = r.cost_usd
            if cost is None:
                cost = price_table.cost(
                    r.model,
                    input_tokens=r.input_tokens,
                    output_tokens=r.output_tokens,
                    cache_read_tokens=r.cache_read_tokens,
                    cache_creation_tokens=r.cache_creation_tokens,
                )
                if cost is None:
                    unknown.add(r.model)
                    cost = 0.0
            await conn.execute(
                insert(m.token_usage).values(
                    dev_name=r.dev_name,
                    message_uuid=r.message_uuid,
                    ts=r.ts,
                    provider=r.provider,
                    model=r.model,
                    input_tokens=r.input_tokens,
                    output_tokens=r.output_tokens,
                    cache_read_tokens=r.cache_read_tokens,
                    cache_creation_tokens=r.cache_creation_tokens,
                    cost_usd=cost,
                    created_at=now,
                )
            )
            result.imported += 1
            existing.add(r.message_uuid)  # dedup within the same batch
    result.unknown_models = sorted(unknown)
    return result.model_dump()


async def token_stats(engine: AsyncEngine) -> dict:
    from sqlalchemy import func

    async with engine.connect() as conn:
        totals = (
            await conn.execute(
                select(
                    func.count(m.token_usage.c.id),
                    func.coalesce(func.sum(m.token_usage.c.input_tokens), 0),
                    func.coalesce(func.sum(m.token_usage.c.output_tokens), 0),
                    func.coalesce(func.sum(m.token_usage.c.cost_usd), 0.0),
                )
            )
        ).one()
        by_model_rows = (
            await conn.execute(
                select(
                    m.token_usage.c.model,
                    func.coalesce(func.sum(m.token_usage.c.cost_usd), 0.0),
                ).group_by(m.token_usage.c.model)
            )
        ).all()
    return {
        "messages": totals[0],
        "input_tokens": int(totals[1]),
        "output_tokens": int(totals[2]),
        "cost_usd": float(totals[3]),
        "by_model": {r[0]: float(r[1]) for r in by_model_rows},
    }


async def projection_inputs(engine: AsyncEngine) -> tuple[list[dict], int, float]:
    """Gather (phases, cumulative_sec, elapsed_days) for a projection."""
    from datetime import datetime

    from sqlalchemy import func

    async with engine.connect() as conn:
        phases = [dict(r._mapping) for r in (await conn.execute(select(m.phase_config))).all()]
        agg = (
            await conn.execute(
                select(
                    func.coalesce(func.sum(m.sessions.c.duration_sec), 0),
                    func.min(m.sessions.c.started_at),
                    func.max(m.sessions.c.ended_at),
                )
            )
        ).one()
    cumulative = int(agg[0] or 0)
    elapsed_days = 0.0
    start, end = agg[1], agg[2]
    if start and end:
        try:
            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
            e = datetime.fromisoformat(end.replace("Z", "+00:00"))
            elapsed_days = max((e - s).total_seconds() / 86400.0, 0.0)
        except ValueError:
            pass
    return phases, cumulative, elapsed_days


async def snapshot_projection(engine: AsyncEngine, result, trigger: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            insert(m.projection_snapshots).values(
                captured_at=_now(),
                projected_finish_date=result.projected_finish_date,
                cumulative_sec=result.cumulative_sec,
                remaining_sec=result.remaining_sec,
                target_sec=result.target_sec,
                burn_per_day_sec=result.burn_per_day_sec,
                method=result.method,
                trigger=trigger,
            )
        )
