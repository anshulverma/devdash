"""The single SQLAlchemy MetaData for devdash's OWNED database.

devdash owns the whole database (ADR-D07), so tables live in the default schema
with no host-collision risk and no schema prefix. Feature modules (phases, the
Postgres log adapter) register their tables on this MetaData; `migrate()` then
creates them expand-only.
"""

from __future__ import annotations

from sqlalchemy import MetaData

metadata = MetaData()
