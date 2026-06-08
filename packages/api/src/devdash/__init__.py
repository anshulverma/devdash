"""devdash — pluggable operator/developer dashboard backend."""

__version__ = "0.0.0"

# Wire-contract version negotiated with the UI (ADR-D12). Kept in lockstep with
# @devdash/ui's DEVDASH_CONTRACT_VERSION.
CONTRACT_VERSION = 1

__all__ = ["__version__", "CONTRACT_VERSION"]
