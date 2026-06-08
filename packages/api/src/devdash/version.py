"""Single source of truth for version + wire-contract constants.

Kept in its own module so feature modules can import these without creating an
import cycle through the package __init__.
"""

__version__ = "0.0.0"

# Wire-contract version negotiated with the UI (ADR-D12). In lockstep with
# @devdash/ui's DEVDASH_CONTRACT_VERSION.
CONTRACT_VERSION = 1
