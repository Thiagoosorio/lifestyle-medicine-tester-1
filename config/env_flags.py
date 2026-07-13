"""Environment flag helpers."""

from config.runtime_config import get_runtime_setting


_TRUTHY = {"1", "true", "yes", "on"}


def is_demo_mode() -> bool:
    """Return True when demo-only features are explicitly enabled."""
    return (get_runtime_setting("DEMO_MODE", "false") or "false").lower() in _TRUTHY
