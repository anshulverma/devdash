"""Host-supplied phase taxonomy + git-inference rules + token price table.

The word "phase" is devdash's vocabulary; the *content* here is host config. A
host passes a PhaseTrackerConfig to the dashboard; devdash seeds `phase_config`
from it (seed values only — the dashboard's edits win) and uses the inference
rules + price table when attributing commits and pricing tokens.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Two common tag forms: "[key] subject" and "key: subject".
DEFAULT_TAG_REGEX = r"^\s*(?:\[([^\]]+)\]|([A-Za-z0-9][\w-]*):)"


class PhaseSpec(BaseModel):
    key: str
    label: str | None = None
    status: str = "pending"  # done | in_progress | pending
    complexity: float | None = None
    display_order: int = 0
    parent: str | None = None  # optional grouping slug
    color: str | None = None  # UI hint; surfaced to CategoryColorProvider


class InferenceRules(BaseModel):
    """How commits map to phases. Engine is generic; content is host config."""

    tag_regex: str = DEFAULT_TAG_REGEX
    path_patterns: dict[str, list[str]] = Field(default_factory=dict)  # phase -> substrings
    subject_keywords: dict[str, list[str]] = Field(default_factory=dict)


class ModelRate(BaseModel):
    """USD per 1M tokens, per token kind."""

    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_creation: float = 0.0


class PriceTable(BaseModel):
    rates: dict[str, ModelRate] = Field(default_factory=dict)

    def cost(
        self,
        model: str,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> float | None:
        """Return the USD cost, or None when the model is not in the table."""
        rate = self.rates.get(model)
        if rate is None:
            return None
        return (
            input_tokens * rate.input
            + output_tokens * rate.output
            + cache_read_tokens * rate.cache_read
            + cache_creation_tokens * rate.cache_creation
        ) / 1_000_000


class PhaseTrackerConfig(BaseModel):
    phases: list[PhaseSpec] = Field(default_factory=list)
    inference: InferenceRules = Field(default_factory=InferenceRules)
    prices: PriceTable = Field(default_factory=PriceTable)

    @classmethod
    def from_dict(cls, data: dict) -> PhaseTrackerConfig:
        return cls.model_validate(data)
