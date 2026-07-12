"""Small helpers for HTML rendered through Streamlit markdown."""

from __future__ import annotations

from html import escape
from typing import Any


def escape_html(value: Any) -> str:
    """Return a safe string for interpolation into unsafe_allow_html markup."""
    return escape("" if value is None else str(value), quote=True)
