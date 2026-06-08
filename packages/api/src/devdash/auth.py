"""Access control for the operator dashboard.

Two layers (ADR / DESIGN §7.5):
  1. a default bearer-token mode (``DEVDASH_AUTH_TOKEN``) guarding mutating routes;
  2. a host-supplied auth dependency that fully owns access.

When neither is configured the dashboard is open but logs a loud warning — it
never silently assumes a private network.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Header, HTTPException, status

from .config import DevDashConfig

logger = logging.getLogger("devdash.auth")

AuthDependency = Callable[..., Coroutine[Any, Any, None] | None]


def build_auth_dependency(
    config: DevDashConfig,
    hook: AuthDependency | None = None,
) -> AuthDependency:
    """Resolve the FastAPI dependency guarding mutating routes."""
    if hook is not None:
        return hook

    if config.auth_token is None:
        logger.warning(
            "devdash is running WITHOUT authentication (no DEVDASH_AUTH_TOKEN and "
            "no auth hook). Expose it only behind a trusted boundary."
        )

        async def _open() -> None:
            return None

        return _open

    expected = f"Bearer {config.auth_token}"

    async def _bearer(authorization: str | None = Header(default=None)) -> None:
        if authorization != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing token",
            )

    return _bearer
