"""Phase-tracker tables, registered on devdash's owned MetaData.

devdash owns the whole database (ADR-D07), so these live in the default schema
with no host-collision risk. The alembic baseline creates them.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    Float,
    Integer,
    String,
    Table,
    Text,
)

from ..metadata import metadata

_BigId = BigInteger().with_variant(Integer, "sqlite")


def _id() -> Column:
    return Column("id", _BigId, primary_key=True, autoincrement=True)


# A work session (git-derived or manual). `phases_json` carries multi-phase
# weights; `phase` is the dominant phase for back-compat queries.
sessions = Table(
    "devdash_sessions",
    metadata,
    _id(),
    Column("dev_name", String(255), nullable=False, index=True),
    Column("started_at", String(64), nullable=False, index=True),
    Column("ended_at", String(64), nullable=False),
    Column("duration_sec", Integer, nullable=False),
    Column("phase", String(64), index=True),
    Column("phases_json", JSON),
    Column("source", String(16), nullable=False, index=True),  # 'git' | 'manual'
    Column("commit_shas", JSON),
    Column("notes", Text),
    Column("created_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
)

# Provider-neutral token usage (one row per message).
token_usage = Table(
    "devdash_token_usage",
    metadata,
    _id(),
    Column("dev_name", String(255), nullable=False, index=True),
    Column("message_uuid", String(128), nullable=False, unique=True),
    Column("ts", String(64), nullable=False, index=True),
    Column("provider", String(64), nullable=False, default="unknown"),
    Column("model", String(128), nullable=False),
    Column("input_tokens", Integer, nullable=False, default=0),
    Column("output_tokens", Integer, nullable=False, default=0),
    Column("cache_read_tokens", Integer, nullable=False, default=0),
    Column("cache_creation_tokens", Integer, nullable=False, default=0),
    Column("cost_usd", Float, nullable=False, default=0.0),
    Column("session_id", BigInteger, index=True),
    Column("created_at", String(64), nullable=False),
)

# The host phase taxonomy, seeded from the host's config and editable in the UI.
phase_config = Table(
    "devdash_phase_config",
    metadata,
    Column("phase", String(64), primary_key=True),
    Column("label", String(255)),
    Column("status", String(16)),  # 'done' | 'in_progress' | 'pending'
    Column("complexity", Float),
    Column("display_order", Integer),
    Column("parent", String(64)),  # optional grouping slug
    Column("actual_seconds_override", Integer),
    Column("updated_at", String(64), nullable=False),
)

phase_transitions = Table(
    "devdash_phase_transitions",
    metadata,
    _id(),
    Column("phase", String(64), nullable=False, index=True),
    Column("from_status", String(16)),
    Column("to_status", String(16), nullable=False),
    Column("transitioned_at", String(64), nullable=False),
)

developers = Table(
    "devdash_developers",
    metadata,
    Column("dev_name", String(255), primary_key=True),
    Column("display_name", String(255), nullable=False),
    Column("email", String(255)),
    Column("aliases", JSON),
    Column("first_seen_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
)

dev_settings = Table(
    "devdash_dev_settings",
    metadata,
    Column("dev_name", String(255), primary_key=True),
    Column("monthly_budget_usd", Float),
    Column("plan", String(64)),
    Column("updated_at", String(64), nullable=False),
)

projection_snapshots = Table(
    "devdash_projection_snapshots",
    metadata,
    _id(),
    Column("captured_at", String(64), nullable=False, index=True),
    Column("projected_finish_date", String(64)),
    Column("cumulative_sec", Integer, nullable=False),
    Column("remaining_sec", Integer, nullable=False),
    Column("target_sec", Integer, nullable=False),
    Column("burn_per_day_sec", Float),
    Column("method", String(16), nullable=False),  # 'calibrated' | 'naive' | 'none'
    Column("trigger", String(32), nullable=False),
)

ALL_TABLES = [
    sessions,
    token_usage,
    phase_config,
    phase_transitions,
    developers,
    dev_settings,
    projection_snapshots,
]
