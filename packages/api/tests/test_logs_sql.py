"""M3 box 4 — SQL/Postgres LogSource adapter.

Parametrized over SQLite (always) and Postgres (when DEVDASH_TEST_PG_URL is set,
e.g. in CI), so the same suite verifies both backends.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from devdash import SqlLogSource
from devdash.db import dispose_engine, make_engine
from devdash.logs import LogEntry, LogFilters
from devdash.logs.sql import _TABLE

_PG = os.environ.get("DEVDASH_TEST_PG_URL")
_BACKENDS = ["sqlite"] + (["postgres"] if _PG else [])


def _entry(level: str, message: str, service: str = "api") -> LogEntry:
    return LogEntry(id="", ts="2026-06-08T00:00:00Z", level=level, message=message, service=service)


@pytest.fixture(params=_BACKENDS)
async def source(request, tmp_path):
    url = _PG if request.param == "postgres" else f"sqlite+aiosqlite:///{tmp_path / 'logs.db'}"
    engine = make_engine(url)
    src = SqlLogSource(poll_interval=0.02)
    await src.bind_engine(engine)
    if request.param == "postgres":  # start from a clean table on the shared PG
        async with engine.begin() as conn:
            await conn.execute(_TABLE.delete())
    yield src
    await dispose_engine(engine)


def test_capabilities_cursor_paginated():
    caps = SqlLogSource().capabilities()
    assert caps.can_search and caps.can_tail and caps.cursor_pagination


async def test_ingest_and_search(source):
    await source.ingest(
        [_entry("info", "service started", "api"), _entry("error", "connection refused", "worker")]
    )
    assert [e.message for e in (await source.search(LogFilters(levels=["error"]))).entries] == [
        "connection refused"
    ]
    by_text = await source.search(LogFilters(search="STARTED"))  # case-insensitive
    assert [e.message for e in by_text.entries] == ["service started"]
    assert len((await source.search(LogFilters(services=["worker"]))).entries) == 1


async def test_enumerate(source):
    await source.ingest([_entry("info", "a", "api"), _entry("warn", "b", "worker")])
    facets = await source.enumerate()
    assert facets.services == ["api", "worker"]
    assert facets.levels == ["info", "warn"]


async def test_ingest_assigns_distinct_increasing_ids(source):
    ids = await source.ingest([_entry("info", "x"), _entry("info", "y")])
    nums = [int(i) for i in ids]
    assert len(set(nums)) == 2 and nums[1] > nums[0]  # stable, monotonic (D04)


async def test_tail_delivers_new_rows(source):
    received: list[str] = []

    async def consume():
        async for e in source.tail(LogFilters(levels=["error"])):
            received.append(e.message)
            break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await source.ingest([_entry("info", "ignored")])
    await source.ingest([_entry("error", "boom")])
    await asyncio.wait_for(task, timeout=3)
    assert received == ["boom"]


async def test_tail_resumes_from_cursor(source):
    ids = await source.ingest(
        [_entry("info", "one"), _entry("info", "two"), _entry("info", "three")]
    )
    got: list[str] = []

    async def consume():
        async for e in source.tail(LogFilters(cursor=ids[0])):  # resume after the 1st id
            got.append(e.message)
            if len(got) == 2:
                break

    await asyncio.wait_for(asyncio.create_task(consume()), timeout=3)
    assert got == ["two", "three"]
