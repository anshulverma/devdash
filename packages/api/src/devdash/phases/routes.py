"""FastAPI routes for the phase tracker: phases list + manual sessions CRUD."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine

from . import repository as repo
from .taxonomy import PhaseTrackerConfig
from .tokens import ImportResult, TokenRow

EngineDep = Callable[..., AsyncEngine]


class PhaseOut(BaseModel):
    phase: str
    label: str | None = None
    status: str | None = None
    complexity: float | None = None
    display_order: int | None = None
    parent: str | None = None
    color: str | None = None


class SessionIn(BaseModel):
    dev_name: str
    started_at: str
    ended_at: str
    duration_sec: int
    phase: str | None = None
    source: str = "manual"
    notes: str | None = None


class SessionPatch(BaseModel):
    phase: str | None = None
    notes: str | None = None
    duration_sec: int | None = None


def build_phases_router(
    engine_dep: EngineDep, config: PhaseTrackerConfig, *, prefix: str = "/phases"
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["phases"])
    color_by_key = {p.key: p.color for p in config.phases}

    @router.get("/phases", response_model=list[PhaseOut])
    async def list_phases(engine: AsyncEngine = Depends(engine_dep)) -> list[PhaseOut]:
        rows = await repo.list_phases(engine)
        return [PhaseOut(**row, color=color_by_key.get(row["phase"])) for row in rows]

    @router.get("/sessions")
    async def list_sessions(
        dev: str | None = None,
        phase: str | None = None,
        engine: AsyncEngine = Depends(engine_dep),
    ) -> list[dict]:
        return await repo.list_sessions(engine, dev_name=dev, phase=phase)

    @router.post("/sessions", status_code=201)
    async def create_session(
        body: SessionIn, engine: AsyncEngine = Depends(engine_dep)
    ) -> dict:
        return await repo.create_session(engine, body.model_dump())

    @router.put("/sessions/{session_id}")
    async def update_session(
        session_id: int, body: SessionPatch, engine: AsyncEngine = Depends(engine_dep)
    ) -> dict:
        changes = body.model_dump(exclude_none=True)
        updated = await repo.update_session(engine, session_id, changes)
        if updated is None:
            raise HTTPException(status_code=404, detail="session not found")
        return updated

    @router.delete("/sessions/{session_id}", status_code=204)
    async def delete_session(
        session_id: int, engine: AsyncEngine = Depends(engine_dep)
    ) -> None:
        if not await repo.delete_session(engine, session_id):
            raise HTTPException(status_code=404, detail="session not found")

    @router.post("/tokens/import", response_model=ImportResult)
    async def import_tokens(
        rows: list[TokenRow], engine: AsyncEngine = Depends(engine_dep)
    ) -> ImportResult:
        # Provider-neutral; cost computed from the host price table; unknown
        # models -> cost 0 + reported (ADR-D08). Idempotent on message_uuid.
        return ImportResult(**await repo.import_token_rows(engine, rows, config.prices))

    @router.get("/tokens/stats")
    async def tokens_stats(engine: AsyncEngine = Depends(engine_dep)) -> dict:
        return await repo.token_stats(engine)

    @router.get("/projection")
    async def projection(engine: AsyncEngine = Depends(engine_dep)) -> dict:
        from dataclasses import asdict
        from datetime import date

        from .projection import compute_projection

        phases, cumulative, elapsed_days = await repo.projection_inputs(engine)
        result = compute_projection(
            phases, cumulative_sec=cumulative, elapsed_days=elapsed_days, today=date.today()
        )
        return asdict(result)

    return router
