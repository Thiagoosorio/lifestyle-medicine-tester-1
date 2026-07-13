"""Reusable privacy controls for cloud processing of health data."""

import streamlit as st


CLOUD_AI_PROVIDER_NAMES = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
}


def cloud_ai_provider_name(provider: str) -> str | None:
    """Return the user-facing name for an AI Coach cloud provider."""
    return CLOUD_AI_PROVIDER_NAMES.get((provider or "").strip().lower())


def ai_coach_cloud_processing_copy(provider: str) -> tuple[str, str, str]:
    """Build provider-specific informed-consent copy for AI Coach requests."""
    provider_name = cloud_ai_provider_name(provider)
    if provider_name is None:
        raise ValueError(f"Unsupported AI Coach cloud provider: {provider!r}")

    notice = (
        f"Cloud AI processing is optional. The configured cloud AI provider is **{provider_name}**. "
        "To generate a response, the app sends your message, up to 20 recent AI Coach messages, "
        "and an assembled health context to that provider. The context can include Wheel and stage "
        "scores, goals, habits, check-ins, mood and energy, sleep and recovery, biomarkers and organ "
        "scores, nutrition, fasting, calorie and diet data, meditation, digestive symptoms, exercise, "
        "and wearable metrics. This may reveal sensitive health information. The provider processes "
        "these data outside this app under its own terms and privacy practices. Leaving consent "
        "unchecked prevents AI Coach cloud requests; you can still view or clear locally stored chat history."
    )
    checkbox_label = (
        f"I understand and consent to send my AI Coach messages, recent chat, and assembled health "
        f"context to {provider_name}."
    )
    session_note = (
        "This opt-in lasts only for the current app session and is not saved to your account. "
        "You can uncheck it to stop future requests, but that cannot recall data already sent."
    )
    return notice, checkbox_label, session_note


def ai_coach_cloud_consent(*, key: str, provider: str) -> bool:
    """Render an opt-in, session-only consent control for AI Coach cloud calls."""
    notice, checkbox_label, session_note = ai_coach_cloud_processing_copy(provider)
    st.warning(notice)
    consented = st.checkbox(checkbox_label, value=False, key=key)
    st.caption(session_note)
    return consented


def cloud_health_data_consent(*, key: str, sends_full_document: bool = False) -> bool:
    if sends_full_document:
        detail = (
            "The full selected document or images may include identifying information. "
            "Remove pages you do not want processed."
        )
    else:
        detail = (
            "Common direct identifiers are removed locally first, but automated redaction "
            "may not catch every identifier."
        )
    st.caption(
        "Cloud processing: this sends health-report content to Anthropic to extract or review values. "
        + detail
    )
    return st.checkbox(
        "I have permission to process this health data with Anthropic.",
        key=key,
    )
