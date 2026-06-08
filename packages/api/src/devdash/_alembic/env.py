"""Alembic environment for devdash's owned database.

Driven programmatically by ``devdash.migrations.migrate`` (async, via run_sync):
the live async connection is passed through ``config.attributes['connection']``.
"""

from __future__ import annotations

from alembic import context

# Import models so every devdash table is registered on the target metadata.
from devdash import phases as _phases  # noqa: F401
from devdash.metadata import metadata

target_metadata = metadata


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is None:  # pragma: no cover - offline/standalone path
        from sqlalchemy import engine_from_config

        url = context.config.get_main_option("sqlalchemy.url")
        engine = engine_from_config({"sqlalchemy.url": url}, prefix="sqlalchemy.")
        with engine.connect() as conn:
            context.configure(connection=conn, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
        return

    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


run_migrations_online()
