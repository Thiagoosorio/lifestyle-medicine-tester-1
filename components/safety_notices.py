"""Shared safety notices for patient-facing exercise and coaching pages."""

from __future__ import annotations

import streamlit as st


def render_exercise_safety_notice(context: str = "training") -> None:
    st.warning(
        f"{context.title()} guidance is educational and should be individualized. "
        "Get clinician clearance before hard training or testing if you have known "
        "cardiovascular, metabolic, kidney, or lung disease; pregnancy; recent surgery; "
        "acute illness; uncontrolled blood pressure; or recent injury. Stop and seek "
        "urgent care for chest pressure, fainting, severe shortness of breath, new "
        "neurologic symptoms, sustained palpitations, or symptoms that feel unusual for you."
    )
