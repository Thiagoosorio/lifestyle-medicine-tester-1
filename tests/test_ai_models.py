from config.ai_models import DEFAULT_ANTHROPIC_MODEL, anthropic_model


def test_default_anthropic_model_is_current(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    assert DEFAULT_ANTHROPIC_MODEL == "claude-sonnet-4-6"
    assert anthropic_model() == "claude-sonnet-4-6"


def test_anthropic_model_can_be_overridden(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-8")
    assert anthropic_model() == "claude-opus-4-8"
