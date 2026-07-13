"""Central model configuration for external AI providers."""

import os


DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"


def anthropic_model() -> str:
    return os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL).strip() or DEFAULT_ANTHROPIC_MODEL
