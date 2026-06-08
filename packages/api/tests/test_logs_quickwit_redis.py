"""M3 box 3 — Quickwit (search) + Redis Streams (tail) composite LogSource.

Degradation + query-builder need no services. The Redis tail and Quickwit
search run only when DEVDASH_TEST_REDIS_URL / DEVDASH_TEST_QUICKWIT_URL are set
(docker locally + CI services).
"""

from __future__ import annotations

import asyncio
import os

import pytest

from devdash.logs import QuickwitRedisLogSource, QuickwitSearch, RedisStreamTail
from devdash.logs.contract import LogEntry, LogFilters

_REDIS = os.environ.get("DEVDASH_TEST_REDIS_URL")
_QUICKWIT = os.environ.get("DEVDASH_TEST_QUICKWIT_URL")


def _composite(qw="http://127.0.0.1:1", rd="redis://127.0.0.1:6390"):
    return QuickwitRedisLogSource(quickwit_url=qw, redis_url=rd)


def test_capabilities_declare_fulltext_and_cursor():
    caps = _composite().capabilities()
    assert caps.text_search == "fulltext"  # Quickwit (D05)
    assert caps.can_tail and caps.cursor_pagination


def test_query_builder():
    qs = QuickwitSearch("http://x", "logs")
    assert qs._query(LogFilters()) == "*"
    q = qs._query(LogFilters(services=["api"], levels=["error", "warn"], search="boom"))
    assert "service:api" in q and "(level:error OR level:warn)" in q and "message:boom" in q


async def test_degrades_to_tail_only_when_quickwit_unreachable():
    src = _composite(qw="http://127.0.0.1:1")  # nothing listening
    assert src.capabilities().can_search is True  # optimistic until checked
    await src.refresh_health()
    assert src.capabilities().can_search is False  # degraded to tail-only
    assert src.capabilities().can_tail is True


@pytest.mark.skipif(not _REDIS, reason="set DEVDASH_TEST_REDIS_URL")
async def test_redis_tail_ingest_and_resume():
    stream = "devdash:test:logs"
    tail = RedisStreamTail(_REDIS, stream=stream)
    # clean slate
    import redis.asyncio as aioredis

    r = aioredis.from_url(_REDIS, decode_responses=True)
    await r.delete(stream)
    await r.aclose()

    await tail.ingest([_e("info", "ignored"), _e("error", "boom")])
    got: list[str] = []

    async def consume():
        async for e in tail.tail(LogFilters(levels=["error"], cursor="0")):  # replay from start
            got.append(e.message)
            break

    await asyncio.wait_for(asyncio.create_task(consume()), timeout=5)
    assert got == ["boom"]


@pytest.mark.skipif(not _QUICKWIT, reason="set DEVDASH_TEST_QUICKWIT_URL")
async def test_quickwit_search_real():
    import httpx

    index = "devdash_test_logs"
    base = _QUICKWIT.rstrip("/")
    mapping = {
        "version": "0.8",
        "index_id": index,
        "doc_mapping": {
            "field_mappings": [
                {"name": "ts", "type": "text", "tokenizer": "raw"},
                {"name": "service", "type": "text", "tokenizer": "raw"},
                {"name": "level", "type": "text", "tokenizer": "raw"},
                {"name": "message", "type": "text", "tokenizer": "default"},
            ]
        },
        "search_settings": {"default_search_fields": ["message"]},
    }
    async with httpx.AsyncClient(timeout=20) as c:
        await c.delete(f"{base}/api/v1/indexes/{index}")
        r = await c.post(f"{base}/api/v1/indexes", json=mapping)
        assert r.status_code in (200, 201), r.text
        rows = [
            {"ts": "2026-06-08T00:00:01Z", "service": "api", "level": "info",
             "message": "service started"},
            {"ts": "2026-06-08T00:00:02Z", "service": "worker", "level": "error",
             "message": "connection refused"},
        ]
        import json as _json

        ndjson = "".join(_json.dumps(r) + "\n" for r in rows)
        ing = await c.post(
            f"{base}/api/v1/{index}/ingest?commit=force", content=ndjson
        )
        assert ing.status_code == 200, ing.text

    src = QuickwitSearch(base, index)
    page = await src.search(LogFilters(search="refused", limit=10))
    assert [e.message for e in page.entries] == ["connection refused"]
    page2 = await src.search(LogFilters(levels=["info"], limit=10))
    assert [e.message for e in page2.entries] == ["service started"]


def _e(level: str, message: str) -> LogEntry:
    return LogEntry(id="", ts="2026-06-08T00:00:00Z", level=level, message=message, service="svc")
