"""Generic log viewing: the LogSource abstraction + adapters + routes."""

from .contract import (
    LogCapabilities,
    LogEntry,
    LogFacets,
    LogFilters,
    LogPage,
)
from .memory import InMemoryLogSource
from .quickwit_redis import QuickwitRedisLogSource, QuickwitSearch, RedisStreamTail
from .routes import build_logs_router
from .source import LogSource
from .sql import SqlLogSource

__all__ = [
    "LogEntry",
    "LogFilters",
    "LogPage",
    "LogFacets",
    "LogCapabilities",
    "LogSource",
    "InMemoryLogSource",
    "build_logs_router",
    "SqlLogSource",
    "QuickwitRedisLogSource",
    "QuickwitSearch",
    "RedisStreamTail",
]
