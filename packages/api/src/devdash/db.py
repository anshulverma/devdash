"""Async engine lifecycle for devdash.

The engine is NEVER created at import time. asyncpg/aiosqlite engines are bound
to the event loop they are created on; building a module-global engine flakes
across the host loop, the standalone loop, and the pytest loop. The engine is
built inside the lifespan (on the running loop) and disposed on shutdown
(ADR-D10).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def make_engine(database_url: str) -> AsyncEngine:
    """Create the async engine on the CURRENTLY running event loop."""
    is_sqlite = database_url.startswith("sqlite")
    kwargs: dict[str, object] = {"future": True}
    if not is_sqlite:
        # Pool tuning only applies to real DB drivers; SQLite uses a
        # SingletonThreadPool / StaticPool path.
        kwargs.update(pool_size=5, max_overflow=5, pool_pre_ping=True)
    return create_async_engine(database_url, **kwargs)


async def dispose_engine(engine: AsyncEngine) -> None:
    await engine.dispose()
