"""Provider-neutral token ingest contract.

The engine's contract is this row shape (ADR-D08); the Claude Code `~/.claude`
parser is one bundled-but-optional adapter that produces these rows. Cost is
computed server-side from the host PriceTable when not supplied; an unknown
model yields cost 0 and a warning (never a guessed rate).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TokenRow(BaseModel):
    message_uuid: str
    ts: str
    model: str
    dev_name: str
    provider: str = "unknown"
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    #: If None, computed server-side from the host PriceTable.
    cost_usd: float | None = None


class ImportResult(BaseModel):
    imported: int = 0
    skipped: int = 0  # already present (idempotent on message_uuid)
    unknown_models: list[str] = Field(default_factory=list)
