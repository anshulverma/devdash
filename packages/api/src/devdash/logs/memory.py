"""In-memory LogSource — the default adapter and the test/demo fixture.

Zero infrastructure: holds entries in a ring and fans live appends out to tail
subscribers. ``append`` is an adapter-specific ingest mixin, deliberately NOT on
the LogSource protocol (ADR-D06).
"""

from __future__ import annotations

import asyncio
import itertools
from collections.abc import AsyncIterator, Iterable

from .contract import LogCapabilities, LogEntry, LogFacets, LogFilters, LogPage


def _matches(entry: LogEntry, filters: LogFilters) -> bool:
    if filters.services and entry.service not in filters.services:
        return False
    if filters.levels and entry.level not in filters.levels:
        return False
    if filters.search and filters.search.lower() not in entry.message.lower():
        return False
    if filters.start_ts and entry.ts < filters.start_ts:
        return False
    if filters.end_ts and entry.ts > filters.end_ts:
        return False
    return True


class InMemoryLogSource:
    def __init__(self, entries: Iterable[LogEntry] | None = None, *, ring: int = 50_000) -> None:
        self._entries: list[LogEntry] = list(entries or [])
        self._ring = ring
        self._ids = itertools.count(1)
        self._subscribers: set[asyncio.Queue[LogEntry]] = set()

    # -- ingest mixin (NOT part of the LogSource protocol) --------------------
    def append(self, entry: LogEntry) -> LogEntry:
        if not entry.id:
            entry = entry.model_copy(update={"id": f"m{next(self._ids)}"})
        self._entries.append(entry)
        if len(self._entries) > self._ring:
            self._entries = self._entries[-self._ring :]
        for q in list(self._subscribers):
            q.put_nowait(entry)
        return entry

    # -- LogSource ------------------------------------------------------------
    def capabilities(self) -> LogCapabilities:
        return LogCapabilities(
            can_search=True,
            can_tail=True,
            can_enumerate=True,
            text_search="substring",
            time_range=True,
            cursor_pagination=False,
        )

    async def search(self, filters: LogFilters) -> LogPage:
        matched = [e for e in self._entries if _matches(e, filters)]
        page = matched[-filters.limit :]
        return LogPage(entries=page, total=len(matched))

    async def enumerate(self) -> LogFacets:
        services = sorted({e.service for e in self._entries if e.service})
        levels = sorted({e.level for e in self._entries})
        return LogFacets(services=services, levels=levels)

    async def tail(self, filters: LogFilters) -> AsyncIterator[LogEntry]:
        q: asyncio.Queue[LogEntry] = asyncio.Queue()
        self._subscribers.add(q)
        try:
            while True:
                entry = await q.get()
                if _matches(entry, filters):
                    yield entry
        finally:
            self._subscribers.discard(q)
