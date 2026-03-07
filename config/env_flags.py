"""Environment flag helpers."""

import os


_TRUTHY = {"1", "true", "yes", "on"}


def is_demo_mode() -> bool:
    """Return True when demo-only features are explicitly enabled."""
    return os.getenv("DEMO_MODE", "false").strip().lower() in _TRUTHY
