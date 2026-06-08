"""The log-viewing wire contract — the currency of every LogSource adapter."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TextSearchMode = Literal["fulltext", "substring", "none"]


class LogEntry(BaseModel):
    #: Adapter-supplied STABLE id, used for dedup / cursor / SSE-resume (ADR-D04).
    id: str
    ts: str  # ISO-8601
    level: str  # open string; known set is debug|info|warn|error|fatal
    message: str
    service: str | None = None  # optional — some sources have no service concept
    container: str | None = None
    stream: str | None = None
    #: Open map for adapter-specific columns (status, duration_ms, request_*).
    fields: dict[str, str] = Field(default_factory=dict)


class LogFilters(BaseModel):
    services: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)
    search: str | None = None
    start_ts: str | None = None
    end_ts: str | None = None
    limit: int = 200
    cursor: str | None = None


class LogPage(BaseModel):
    entries: list[LogEntry]
    cursor: str | None = None
    total: int | None = None


class LogFacets(BaseModel):
    services: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)


class LogCapabilities(BaseModel):
    """Static negotiation descriptor the UI reads once to enable/disable controls.

    A method an adapter does not implement fails loudly (501) — never a silent
    empty result.
    """

    can_search: bool
    can_tail: bool
    can_enumerate: bool
    #: Declared, never emulated (ADR-D05): the UI labels the active mode.
    text_search: TextSearchMode
    time_range: bool
    cursor_pagination: bool
