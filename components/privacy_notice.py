"""Reusable privacy controls for cloud processing of health documents."""

import streamlit as st


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
