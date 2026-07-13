import pytest

import components.privacy_notice as privacy_notice
from components.privacy_notice import (
    ai_coach_cloud_consent,
    ai_coach_cloud_processing_copy,
    cloud_ai_provider_name,
)


@pytest.mark.parametrize(
    ("configured", "display_name"),
    [
        ("anthropic", "Anthropic"),
        (" ANTHROPIC ", "Anthropic"),
        ("openai", "OpenAI"),
    ],
)
def test_cloud_ai_provider_name(configured, display_name):
    assert cloud_ai_provider_name(configured) == display_name


def test_unknown_provider_is_not_treated_as_cloud_enabled():
    assert cloud_ai_provider_name("local") is None


@pytest.mark.parametrize("provider_name", ["Anthropic", "OpenAI"])
def test_ai_coach_consent_copy_is_provider_specific_and_informed(provider_name):
    notice, checkbox_label, session_note = ai_coach_cloud_processing_copy(provider_name)

    assert f"configured cloud AI provider is **{provider_name}**" in notice
    assert "assembled health context" in notice
    assert "biomarkers and organ scores" in notice
    assert "exercise, and wearable metrics" in notice
    assert "locally stored chat history" in notice
    assert f"to {provider_name}" in checkbox_label
    assert "not saved to your account" in session_note
    assert "cannot recall data already sent" in session_note


def test_ai_coach_consent_copy_rejects_unsupported_provider():
    with pytest.raises(ValueError, match="Unsupported AI Coach cloud provider"):
        ai_coach_cloud_processing_copy("local")


def test_ai_coach_cloud_consent_is_opt_in(monkeypatch):
    rendered = {}

    monkeypatch.setattr(
        privacy_notice.st,
        "warning",
        lambda message: rendered.update(warning=message),
    )
    monkeypatch.setattr(
        privacy_notice.st,
        "caption",
        lambda message: rendered.update(caption=message),
    )

    def fake_checkbox(label, *, value, key):
        rendered.update(label=label, value=value, key=key)
        return value

    monkeypatch.setattr(privacy_notice.st, "checkbox", fake_checkbox)

    consented = ai_coach_cloud_consent(key="coach-consent", provider="openai")

    assert consented is False
    assert rendered["value"] is False
    assert rendered["key"] == "coach-consent"
    assert "OpenAI" in rendered["warning"]
    assert "OpenAI" in rendered["label"]
