import streamlit as st
from config.settings import STAGES_OF_CHANGE


STAGE_COLORS = {
    "precontemplation": "#9E9E9E",
    "contemplation": "#FF9800",
    "preparation": "#FFC107",
    "action": "#4CAF50",
    "maintenance": "#2196F3",
}


def render_stage_badge(stage: str):
    """Render a colored badge for a stage of change."""
    info = STAGES_OF_CHANGE.get(stage, {})
    color = STAGE_COLORS.get(stage, "#9E9E9E")
    label = info.get("label", stage.title())
    st.markdown(
        f'<span style="background-color:{color}; color:white; padding:2px 8px; '
        f'border-radius:12px; font-size:0.8em; font-weight:bold">{label}</span>',
        unsafe_allow_html=True,
    )


def render_stage_timeline(stages_history: list):
    """Render a horizontal timeline of stage changes.
    stages_history = [{stage, assessed_at}]
    """
    if not stages_history:
        st.caption("No stage history available.")
        return

    cols = st.columns(len(stages_history))
    for i, entry in enumerate(stages_history):
        with cols[i]:
            color = STAGE_COLORS.get(entry["stage"], "#9E9E9E")
            label = STAGES_OF_CHANGE.get(entry["stage"], {}).get("label", entry["stage"])
            st.markdown(
                f'<div style="text-align:center">'
                f'<div style="background-color:{color}; color:white; padding:4px 8px; '
                f'border-radius:8px; font-size:0.75em; font-weight:bold">{label}</div>'
                f'<div style="font-size:0.7em; color:rgba(235,235,245,0.72); margin-top:2px">{entry["assessed_at"][:10]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
