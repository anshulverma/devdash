"""SQL-backed LogSource — a `logs` table in devdash's OWNED database.

Postgres-primary but portable to SQLite (the owned DB in dev/tests), so it adds
ZERO infrastructure beyond the database devdash already owns. Substring search
via a portable case-insensitive LIKE; a cursor-poll tail on the autoincrement
id, which is the entry's stable id (ADR-D04) and gives real Last-Event-ID
resume (`cursor_pagination=True`).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable, Sequence

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    Integer,
    MetaData,
    String,
    Text,
    distinct,
    func,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import AsyncEngine

from .contract import LogCapabilities, LogEntry, LogFacets, LogFilters, LogPage

# Private metadata: the adapter creates its own table on bind (expand-only,
# checkfirst), so importing this module does NOT add a table to devdash's shared
# metadata for hosts that don't use the SQL adapter.
_metadata = MetaData()


def _build_table(meta: MetaData):
    from sqlalchemy import Table

    return Table(
        "devdash_logs",
        meta,
        Column(
            "id",
            BigInteger().with_variant(Integer, "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        Column("ts", String(64), nullable=False),
        Column("level", String(32), nullable=False),
        Column("message", Text, nullable=False),
        Column("service", String(255)),
        Column("container", String(255)),
        Column("stream", String(32)),
        Column("fields", JSON, nullable=False, default=dict),
    )


_TABLE = _build_table(_metadata)


def _row_to_entry(row) -> LogEntry:
    return LogEntry(
        id=str(row.id),
        ts=row.ts,
        level=row.level,
        message=row.message,
        service=row.service,
        container=row.container,
        stream=row.stream,
        fields=row.fields or {},
    )


class SqlLogSource:
    def __init__(self, *, poll_interval: float = 0.5) -> None:
        self._engine: AsyncEngine | None = None
        self._poll = poll_interval
        self._t = _TABLE

    # -- bind (called by the dashboard lifespan, on the running loop) ----------
    async def bind_engine(self, engine: AsyncEngine) -> None:
        self._engine = engine
        async with engine.begin() as conn:
            await conn.run_sync(_metadata.create_all)

    @property
    def _e(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("SqlLogSource not bound — wire dashboard_lifespan")
        return self._engine

    # -- ingest mixin (NOT on the LogSource protocol, ADR-D06) ----------------
    async def ingest(self, entries: Iterable[LogEntry]) -> list[str]:
        ids: list[str] = []
        async with self._e.begin() as conn:
            for e in entries:
                res = await conn.execute(
                    insert(self._t).values(
                        ts=e.ts,
                        level=e.level,
                        message=e.message,
                        service=e.service,
                        container=e.container,
                        stream=e.stream,
                        fields=e.fields or {},
                    )
                )
                ids.append(str(res.inserted_primary_key[0]))
        return ids

    # -- LogSource ------------------------------------------------------------
    def capabilities(self) -> LogCapabilities:
        return LogCapabilities(
            can_search=True,
            can_tail=True,
            can_enumerate=True,
            text_search="substring",
            time_range=True,
            cursor_pagination=True,
        )

    def _apply_filters(self, q, filters: LogFilters):
        t = self._t
        if filters.services:
            q = q.where(t.c.service.in_(filters.services))
        if filters.levels:
            q = q.where(t.c.level.in_(filters.levels))
        if filters.search:
            q = q.where(func.lower(t.c.message).like(f"%{filters.search.lower()}%"))
        if filters.start_ts:
            q = q.where(t.c.ts >= filters.start_ts)
        if filters.end_ts:
            q = q.where(t.c.ts <= filters.end_ts)
        return q

    async def search(self, filters: LogFilters) -> LogPage:
        t = self._t
        q = self._apply_filters(select(t), filters).order_by(t.c.id.desc()).limit(filters.limit)
        async with self._e.connect() as conn:
            rows: Sequence = (await conn.execute(q)).all()
        entries = [_row_to_entry(r) for r in reversed(rows)]
        return LogPage(entries=entries, total=len(entries))

    async def enumerate(self) -> LogFacets:
        t = self._t
        async with self._e.connect() as conn:
            services = [
                r[0]
                for r in (
                    await conn.execute(
                        select(distinct(t.c.service)).where(t.c.service.isnot(None)).order_by(
                            t.c.service
                        )
                    )
                ).all()
            ]
            levels = [
                r[0]
                for r in (
                    await conn.execute(select(distinct(t.c.level)).order_by(t.c.level))
                ).all()
            ]
        return LogFacets(services=services, levels=levels)

    async def tail(self, filters: LogFilters) -> AsyncIterator[LogEntry]:
        t = self._t
        # Resume from the Last-Event-ID cursor, else from the current head.
        if filters.cursor:
            last = int(filters.cursor)
        else:
            async with self._e.connect() as conn:
                last = (await conn.execute(select(func.max(t.c.id)))).scalar() or 0
        while True:
            await asyncio.sleep(self._poll)
            q = self._apply_filters(select(t).where(t.c.id > last), filters).order_by(t.c.id).limit(
                500
            )
            async with self._e.connect() as conn:
                rows: Sequence = (await conn.execute(q)).all()
            for r in rows:
                last = r.id
                yield _row_to_entry(r)
