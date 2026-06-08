"""devdash baseline — create the phase-tracker tables.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-08
"""

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Register all phase tables on the shared metadata, then create them. A
    # create_all baseline is expand-only; later revisions use explicit ops.
    import devdash.phases.models  # noqa: F401
    from devdash.metadata import metadata

    metadata.create_all(op.get_bind())


def downgrade() -> None:
    from devdash.metadata import metadata

    metadata.drop_all(op.get_bind())
