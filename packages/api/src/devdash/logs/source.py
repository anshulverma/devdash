"""The LogSource protocol — the day-one abstraction behind the log viewer.

Adapters implement read + tail + enumerate + capabilities. INGEST IS NOT PART OF
THIS INTERFACE (ADR-D06): it is an optional per-adapter mixin, so read-only
adapters (files, object storage, a hosted log service) never stub a write path.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .contract import LogCapabilities, LogEntry, LogFacets, LogFilters, LogPage


@runtime_checkable
class LogSource(Protocol):
    def capabilities(self) -> LogCapabilities: ...

    async def search(self, filters: LogFilters) -> LogPage: ...

    async def enumerate(self) -> LogFacets: ...

    def tail(self, filters: LogFilters) -> AsyncIterator[LogEntry]:
        """Return an async iterator of live entries matching ``filters``."""
        ...
