"""devdash — pluggable operator/developer dashboard backend."""

from .config import DevDashConfig
from .dashboard import (
    Dashboard,
    dashboard_lifespan,
    make_dashboard_app,
    mount_dashboard,
)
from .logs import InMemoryLogSource, LogSource, SqlLogSource, build_logs_router
from .metadata import metadata
from .migrations import create_database, migrate
from .phases import PhaseSpec, PhaseTrackerConfig, PriceTable
from .version import CONTRACT_VERSION, __version__

__all__ = [
    "__version__",
    "CONTRACT_VERSION",
    "DevDashConfig",
    "Dashboard",
    "make_dashboard_app",
    "mount_dashboard",
    "dashboard_lifespan",
    "migrate",
    "create_database",
    "metadata",
    "LogSource",
    "InMemoryLogSource",
    "build_logs_router",
    "SqlLogSource",
    "PhaseTrackerConfig",
    "PhaseSpec",
    "PriceTable",
]
