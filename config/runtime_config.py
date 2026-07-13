"""Runtime configuration loaded from environment variables or Streamlit Secrets."""

from __future__ import annotations

from dataclasses import dataclass, field
import os


class RuntimeConfigError(ValueError):
    """Raised when deployment bootstrap settings are incomplete."""


def get_runtime_setting(name: str, default: str | None = None) -> str | None:
    """Read a setting without requiring a local Streamlit secrets file."""
    environment_value = os.getenv(name)
    if environment_value is not None:
        value = str(environment_value).strip()
        return value if value else default

    try:
        import streamlit as st

        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None

    if secret_value is None:
        return default
    value = str(secret_value).strip()
    return value if value else default


@dataclass(frozen=True)
class AdminBootstrapConfig:
    username: str
    password: str = field(repr=False)
    display_name: str
    bootstrap_revision: str | None = None
    account_reset_revision: str | None = None


def load_admin_bootstrap_config() -> AdminBootstrapConfig | None:
    """Load an optional admin bootstrap without exposing its password in code."""
    username = get_runtime_setting("BOOTSTRAP_ADMIN_USERNAME")
    password = get_runtime_setting("BOOTSTRAP_ADMIN_PASSWORD")
    if username is None and password is None:
        return None
    if not username or not password:
        raise RuntimeConfigError(
            "BOOTSTRAP_ADMIN_USERNAME and BOOTSTRAP_ADMIN_PASSWORD must be set together"
        )

    return AdminBootstrapConfig(
        username=username,
        password=password,
        display_name=get_runtime_setting("BOOTSTRAP_ADMIN_DISPLAY_NAME", username)
        or username,
        bootstrap_revision=get_runtime_setting("BOOTSTRAP_ADMIN_REVISION"),
        account_reset_revision=get_runtime_setting("ACCOUNT_RESET_REVISION"),
    )
