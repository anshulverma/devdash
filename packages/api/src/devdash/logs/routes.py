"""FastAPI routes exposing a LogSource: capabilities, facets, search, SSE tail."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from .contract import LogCapabilities, LogFacets, LogFilters, LogPage
from .source import LogSource


def build_logs_router(source: LogSource, *, prefix: str = "/logs") -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["logs"])

    def _filters(
        services: list[str],
        levels: list[str],
        search: str | None,
        start_ts: str | None,
        end_ts: str | None,
        limit: int,
        cursor: str | None,
    ) -> LogFilters:
        return LogFilters(
            services=services,
            levels=levels,
            search=search,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
            cursor=cursor,
        )

    @router.get("/capabilities", response_model=LogCapabilities)
    def capabilities() -> LogCapabilities:
        return source.capabilities()

    @router.get("/facets", response_model=LogFacets)
    async def facets() -> LogFacets:
        if not source.capabilities().can_enumerate:
            raise HTTPException(status_code=501, detail="adapter does not support enumerate")
        return await source.enumerate()

    @router.get("/search", response_model=LogPage)
    async def search(
        services: list[str] = Query(default=[]),
        levels: list[str] = Query(default=[]),
        search: str | None = None,
        start_ts: str | None = None,
        end_ts: str | None = None,
        limit: int = 200,
        cursor: str | None = None,
    ) -> LogPage:
        if not source.capabilities().can_search:
            raise HTTPException(status_code=501, detail="adapter does not support search")
        return await source.search(
            _filters(services, levels, search, start_ts, end_ts, limit, cursor)
        )

    @router.get("/tail")
    async def tail(
        services: list[str] = Query(default=[]),
        levels: list[str] = Query(default=[]),
        search: str | None = None,
        prime: int = 100,
    ) -> StreamingResponse:
        caps = source.capabilities()
        if not caps.can_tail:
            raise HTTPException(status_code=501, detail="adapter does not support tail")
        filters = _filters(services, levels, search, None, None, prime, None)

        async def stream():
            try:
                page = await source.search(filters) if caps.can_search else LogPage(entries=[])
                data = "".join(f"data: {e.model_dump_json()}\n" for e in page.entries)
                yield f"event: prime\n{data}\n"
                async for entry in source.tail(filters):
                    # Emit per-event `id:` so the browser EventSource tracks
                    # lastEventId and auto-resumes via Last-Event-ID on reconnect.
                    yield (
                        f"event: entry\nid: {entry.id}\n"
                        f"data: {entry.model_dump_json()}\n\n"
                    )
            except Exception as exc:  # noqa: BLE001 - surface as a terminal SSE error
                yield f"event: error\ndata: {exc}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    return router
