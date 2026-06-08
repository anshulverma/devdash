"""M3 — LogSource abstraction + in-memory adapter + routes."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from devdash import DevDashConfig, InMemoryLogSource, make_dashboard_app
from devdash.logs import LogEntry, LogFilters, LogSource


def _entry(i: int, level: str, message: str, service: str = "api") -> LogEntry:
    return LogEntry(
        id=str(i),
        ts=f"2026-06-08T00:00:0{i}Z",
        level=level,
        message=message,
        service=service,
    )


def _source() -> InMemoryLogSource:
    return InMemoryLogSource(
        [
            _entry(1, "info", "service started", "api"),
            _entry(2, "warn", "cache miss", "api"),
            _entry(3, "error", "connection refused", "worker"),
        ]
    )


def test_inmemory_is_a_logsource():
    assert isinstance(InMemoryLogSource(), LogSource)


def test_capabilities_declared():
    caps = InMemoryLogSource().capabilities()
    assert caps.can_search and caps.can_tail and caps.can_enumerate
    assert caps.text_search == "substring"  # declared, never emulated (D05)


async def test_search_filters():
    src = _source()
    assert [e.id for e in (await src.search(LogFilters(levels=["error"]))).entries] == ["3"]
    assert [e.id for e in (await src.search(LogFilters(services=["api"]))).entries] == ["1", "2"]
    by_text = await src.search(LogFilters(search="refused"))
    assert [e.id for e in by_text.entries] == ["3"]


async def test_enumerate_facets():
    facets = await _source().enumerate()
    assert facets.services == ["api", "worker"]
    assert facets.levels == ["error", "info", "warn"]


async def test_tail_delivers_live_appends():
    src = InMemoryLogSource()
    received: list[str] = []

    async def consume():
        async for entry in src.tail(LogFilters(levels=["error"])):
            received.append(entry.id)
            break  # one is enough for the test

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    src.append(_entry(9, "info", "ignored"))  # filtered out
    src.append(_entry(7, "error", "boom"))  # matches
    await asyncio.wait_for(task, timeout=1)
    assert received == ["7"]


def test_append_assigns_stable_id():
    src = InMemoryLogSource()
    e = src.append(LogEntry(id="", ts="2026-06-08T00:00:00Z", level="info", message="x"))
    assert e.id  # adapter-supplied stable id (D04)


def test_logs_routes_mounted():
    config = DevDashConfig(database_url="sqlite+aiosqlite:///:memory:")
    app = make_dashboard_app(config, log_source=_source())
    with TestClient(app) as client:
        caps = client.get("/dev/logs/capabilities")
        assert caps.status_code == 200
        assert caps.json()["text_search"] == "substring"

        facets = client.get("/dev/logs/facets")
        assert facets.json()["levels"] == ["error", "info", "warn"]

        page = client.get("/dev/logs/search", params={"levels": ["error"]})
        assert page.status_code == 200
        assert [e["id"] for e in page.json()["entries"]] == ["3"]


def test_logs_routes_absent_when_tab_disabled():
    config = DevDashConfig(database_url="sqlite+aiosqlite:///:memory:", enabled_tabs={"phases"})
    app = make_dashboard_app(config, log_source=_source())
    with TestClient(app) as client:
        assert client.get("/dev/logs/capabilities").status_code == 404
