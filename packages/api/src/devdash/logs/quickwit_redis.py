"""Quickwit (search) + Redis Streams (tail) composite LogSource.

One LogSource whose search/enumerate are served by Quickwit and whose live tail
is served by a Redis Stream. Reports `can_search ∧ can_tail`, and DEGRADES to
tail-only when Quickwit is unreachable (call `refresh_health()` to update the
advertised capability). The two sub-backends stay independently swappable.

Optional deps: install `devdash[quickwit-redis]` (httpx + redis).
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator, Iterable

from .contract import LogCapabilities, LogEntry, LogFacets, LogFilters, LogPage


def _matches(entry: LogEntry, f: LogFilters) -> bool:
    if f.services and entry.service not in f.services:
        return False
    if f.levels and entry.level not in f.levels:
        return False
    if f.search and f.search.lower() not in entry.message.lower():
        return False
    return True


def _content_id(ts: str, service: str | None, message: str) -> str:
    # Quickwit docs carry no native id; content-hash fallback (ADR-D04).
    h = hashlib.sha1(f"{ts}|{service or ''}|{message}".encode()).hexdigest()
    return f"qw_{h[:16]}"


class QuickwitSearch:
    """Search/enumerate backend over the Quickwit REST API."""

    def __init__(self, url: str, index: str, *, timeout: float = 5.0) -> None:
        self._url = url.rstrip("/")
        self._index = index
        self._timeout = timeout

    def _client(self):
        import httpx

        return httpx.AsyncClient(timeout=self._timeout)

    async def health(self) -> bool:
        import httpx

        try:
            async with self._client() as c:
                r = await c.get(f"{self._url}/health/livez")
                return r.status_code == 200
        except httpx.HTTPError:
            return False

    def _query(self, f: LogFilters) -> str:
        clauses: list[str] = []
        if f.services:
            clauses.append("(" + " OR ".join(f"service:{s}" for s in f.services) + ")")
        if f.levels:
            clauses.append("(" + " OR ".join(f"level:{lv}" for lv in f.levels) + ")")
        if f.search:
            clauses.append(f"message:{f.search}")
        return " AND ".join(clauses) if clauses else "*"

    async def search(self, f: LogFilters) -> LogPage:
        body = {"query": self._query(f), "max_hits": f.limit}
        async with self._client() as c:
            r = await c.post(f"{self._url}/api/v1/{self._index}/search", json=body)
            r.raise_for_status()
            data = r.json()
        hits = data.get("hits", [])
        entries = [self._hit_to_entry(h) for h in hits]
        entries.sort(key=lambda e: e.ts)  # client-side chronological (no fast-field needed)
        return LogPage(entries=entries, total=data.get("num_hits"))

    def _hit_to_entry(self, h: dict) -> LogEntry:
        ts = str(h.get("ts", ""))
        service = h.get("service")
        message = str(h.get("message", ""))
        return LogEntry(
            id=_content_id(ts, service, message),
            ts=ts,
            level=str(h.get("level", "")),
            message=message,
            service=service,
            container=h.get("container"),
            stream=h.get("stream"),
        )

    async def enumerate(self) -> LogFacets:
        # Best-effort: derive facets from a recent sample (no fast-field config
        # required). A host that indexes service/level as fast fields can swap in
        # a terms-aggregation implementation.
        page = await self.search(LogFilters(limit=500))
        services = sorted({e.service for e in page.entries if e.service})
        levels = sorted({e.level for e in page.entries if e.level})
        return LogFacets(services=services, levels=levels)


class RedisStreamTail:
    """Live tail + ingest over a Redis Stream. The stream id is the entry's
    stable id (ADR-D04), enabling Last-Event-ID resume (cursor_pagination)."""

    def __init__(self, url: str, stream: str = "devdash:logs", *, maxlen: int = 50_000) -> None:
        self._url = url
        self._stream = stream
        self._maxlen = maxlen
        self._redis = None

    def _client(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._url, decode_responses=True)
        return self._redis

    async def ingest(self, entries: Iterable[LogEntry]) -> list[str]:
        r = self._client()
        ids: list[str] = []
        for e in entries:
            fields = {
                "ts": e.ts,
                "level": e.level,
                "message": e.message,
                "service": e.service or "",
                "container": e.container or "",
                "stream": e.stream or "",
            }
            sid = await r.xadd(self._stream, fields, maxlen=self._maxlen, approximate=True)
            ids.append(sid)
        return ids

    def _to_entry(self, sid: str, fields: dict) -> LogEntry:
        return LogEntry(
            id=sid,
            ts=fields.get("ts", ""),
            level=fields.get("level", ""),
            message=fields.get("message", ""),
            service=fields.get("service") or None,
            container=fields.get("container") or None,
            stream=fields.get("stream") or None,
        )

    async def tail(self, f: LogFilters) -> AsyncIterator[LogEntry]:
        r = self._client()
        last = f.cursor or "$"  # resume from Last-Event-ID, else only new entries
        while True:
            resp = await r.xread({self._stream: last}, block=30_000, count=100)
            if not resp:
                continue
            for _stream, messages in resp:
                for sid, fields in messages:
                    last = sid
                    entry = self._to_entry(sid, fields)
                    if _matches(entry, f):
                        yield entry


class QuickwitRedisLogSource:
    def __init__(
        self,
        *,
        quickwit_url: str,
        redis_url: str,
        index: str = "logs",
        stream: str = "devdash:logs",
    ) -> None:
        self._search = QuickwitSearch(quickwit_url, index)
        self._tail = RedisStreamTail(redis_url, stream)
        self._can_search = True

    async def refresh_health(self) -> None:
        """Update the advertised search capability from Quickwit's health."""
        self._can_search = await self._search.health()

    def capabilities(self) -> LogCapabilities:
        return LogCapabilities(
            can_search=self._can_search,
            can_tail=True,
            can_enumerate=self._can_search,
            text_search="fulltext",  # Quickwit/Tantivy (declared, never emulated — D05)
            time_range=True,
            cursor_pagination=True,
        )

    async def search(self, filters: LogFilters) -> LogPage:
        return await self._search.search(filters)

    async def enumerate(self) -> LogFacets:
        return await self._search.enumerate()

    async def tail(self, filters: LogFilters) -> AsyncIterator[LogEntry]:
        async for entry in self._tail.tail(filters):
            yield entry

    # ingest mixin (NOT on the LogSource protocol, ADR-D06) — feeds the tail.
    async def ingest(self, entries: Iterable[LogEntry]) -> list[str]:
        return await self._tail.ingest(entries)
