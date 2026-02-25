"""Organ health score display components for Streamlit UI."""

import streamlit as st
import plotly.graph_objects as go
from datetime import date
from models.clinical_profile import get_profile, get_age, get_bmi

SEVERITY_COLORS = {
    "optimal": "#30D158",
    "normal": "#64D2FF",
    "elevated": "#FFD60A",
    "high": "#FF9F0A",
    "critical": "#FF453A",
}

TIER_BADGES = {
    "validated": ("Clinically Validated", "#30D158", "#30D15830"),
    "derived": ("Derived / Experimental", "#FFD60A", "#FFD60A30"),
}


def render_organ_score_card(score_result: dict, score_def: dict):
    """Render a single organ health score card."""
    tier = score_def.get("tier", "validated")
    badge_label, badge_color, badge_bg = TIER_BADGES.get(tier, TIER_BADGES["validated"])
    severity = score_result.get("severity", "normal")
    sev_color = SEVERITY_COLORS.get(severity, "#AEAEB2")

    value = score_result.get("value", 0)
    label = score_result.get("label", "")
    lab_date = score_result.get("lab_date", "")

    with st.container(border=True):
        col_name, col_badge = st.columns([3, 1])
        with col_name:
            st.markdown(f"**{score_def.get('name', '')}**")
        with col_badge:
            st.markdown(
                f'<span style="background:{badge_bg};color:{badge_color};'
                f'padding:2px 8px;border-radius:12px;font-size:0.7em;font-weight:600;">'
                f'{badge_label}</span>',
                unsafe_allow_html=True,
            )

        col_val, col_interp = st.columns([1, 2])
        with col_val:
            if isinstance(value, float):
                display_val = f"{value:.2f}" if value < 100 else f"{value:.1f}"
            else:
                display_val = str(value)
            st.markdown(
                f'<div style="font-size:2em;font-weight:700;color:{sev_color};line-height:1.2;">'
                f'{display_val}</div>',
                unsafe_allow_html=True,
            )
        with col_interp:
            st.markdown(
                f'<div style="color:{sev_color};font-weight:600;margin-top:8px;">'
                f'{label}</div>',
                unsafe_allow_html=True,
            )

        _render_severity_bar(severity)

        snapshot = score_result.get("input_snapshot", {})
        if snapshot:
            inputs_text = " | ".join(
                f"{k}: {v}" for k, v in snapshot.items()
                if not k.startswith("_") and v is not None
            )
            st.caption(f"Inputs: {inputs_text}")

        citation_pmid = score_def.get("citation_pmid", "")
        citation_text = score_def.get("citation_text", "")
        footer_parts = []
        if citation_pmid:
            footer_parts.append(f"PMID: {citation_pmid}")
        if lab_date and lab_date != "unknown":
            footer_parts.append(f"Labs from {lab_date}")
        if footer_parts:
            st.caption(" | ".join(footer_parts))

        if score_def.get("description") or citation_text:
            with st.expander("Details & Citation"):
                if score_def.get("description"):
                    st.markdown(score_def["description"])
                if citation_text:
                    st.markdown(f"**Citation:** {citation_text}")


def _render_severity_bar(severity: str):
    """Render a thin horizontal bar indicating severity level."""
    levels = ["optimal", "normal", "elevated", "high", "critical"]
    active_idx = levels.index(severity) if severity in levels else 1

    cols = st.columns(len(levels))
    for i, (col, level) in enumerate(zip(cols, levels)):
        color = SEVERITY_COLORS.get(level, "#AEAEB2")
        opacity = "1.0" if i == active_idx else "0.2"
        col.markdown(
            f'<div style="height:4px;background:{color};opacity:{opacity};'
            f'border-radius:2px;"></div>',
            unsafe_allow_html=True,
        )


def render_missing_score_card(score_def: dict, missing_biomarkers: list,
                              missing_clinical: list):
    """Render a disabled card for a score that can't be computed."""
    tier = score_def.get("tier", "validated")
    badge_label, badge_color, badge_bg = TIER_BADGES.get(tier, TIER_BADGES["validated"])

    with st.container(border=True):
        col_name, col_badge = st.columns([3, 1])
        with col_name:
            st.markdown(
                f'<span style="color:#AEAEB2;">**{score_def.get("name", "")}**</span>',
                unsafe_allow_html=True,
            )
        with col_badge:
            st.markdown(
                f'<span style="background:{badge_bg};color:{badge_color};'
                f'padding:2px 8px;border-radius:12px;font-size:0.7em;font-weight:600;">'
                f'{badge_label}</span>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="color:#AEAEB2;font-size:1.5em;text-align:center;padding:8px 0;">\u2014</div>',
            unsafe_allow_html=True,
        )

        missing_items = []
        if missing_biomarkers:
            missing_items.append(f"**Lab results needed:** {', '.join(missing_biomarkers)}")
        if missing_clinical:
            labels = {
                "age": "Date of Birth", "sex": "Sex", "bmi": "Height & Weight",
                "systolic_bp": "Blood Pressure", "smoking_status": "Smoking Status",
                "diabetes_status": "Diabetes Status", "on_bp_medication": "BP Medication",
            }
            named = [labels.get(c, c) for c in missing_clinical]
            missing_items.append(f"**Clinical data needed:** {', '.join(named)}")

        for item in missing_items:
            st.markdown(item)


def render_organ_section_header(organ_system: str, name: str, icon: str, color: str):
    """Render a section header for an organ system group."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin:16px 0 8px 0;">'
        f'<span style="color:{color};font-size:1.3em;">{icon}</span>'
        f'<span style="font-size:1.2em;font-weight:700;color:{color};">{name}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_score_trend_chart(history: list, definition: dict, height: int = 300):
    """Render a Plotly line chart showing score history with interpretation zones."""
    if not history:
        st.info("No history available for this score yet.")
        return

    dates = [h["lab_date"] for h in history]
    values = [h["value"] for h in history]

    fig = go.Figure()

    interp = definition.get("interpretation", {})
    ranges = interp.get("ranges", [])
    zone_colors = {
        "optimal": "rgba(48,209,88,0.1)",
        "normal": "rgba(100,210,255,0.1)",
        "elevated": "rgba(255,214,10,0.1)",
        "high": "rgba(255,159,10,0.1)",
        "critical": "rgba(255,69,58,0.1)",
    }
    for r in ranges:
        r_min = r.get("min", min(values) - 10 if values else 0)
        r_max = r.get("max", max(values) + 10 if values else 100)
        fig.add_hrect(
            y0=r_min, y1=r_max,
            fillcolor=zone_colors.get(r.get("severity", "normal"), "rgba(0,0,0,0.05)"),
            line_width=0,
            annotation_text=r.get("label", ""),
            annotation_position="top left",
            annotation_font_size=9,
            annotation_font_color="#AEAEB2",
        )

    fig.add_trace(go.Scatter(
        x=dates, y=values,
        mode="lines+markers",
        name=definition.get("name", "Score"),
        line=dict(color="#007AFF", width=2),
        marker=dict(size=8),
    ))

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title=None,
        yaxis_title=definition.get("name", "Score"),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_clinical_profile_form(user_id: int):
    """Render the clinical profile form for non-lab inputs."""
    profile = get_profile(user_id) or {}

    st.markdown("### Clinical & Demographic Profile")
    st.markdown(
        "These inputs are required for certain organ health scores that "
        "need data beyond blood labs (e.g., cardiovascular risk calculators)."
    )

    CLINICAL_INPUT_SCORES = {
        "date_of_birth": ["CKD-EPI eGFR", "FIB-4", "NAFLD Fibrosis Score", "ASCVD Risk", "AHA PREVENT"],
        "sex": ["CKD-EPI eGFR", "ASCVD Risk", "AHA PREVENT"],
        "height_cm": ["NAFLD Fibrosis Score (BMI)", "AHA PREVENT (BMI)"],
        "weight_kg": ["NAFLD Fibrosis Score (BMI)", "AHA PREVENT (BMI)"],
        "systolic_bp": ["ASCVD Risk", "AHA PREVENT"],
        "smoking_status": ["ASCVD Risk", "AHA PREVENT"],
        "diabetes_status": ["ASCVD Risk", "AHA PREVENT", "NAFLD Fibrosis Score"],
        "on_bp_medication": ["ASCVD Risk", "AHA PREVENT"],
    }

    with st.form(key="clinical_profile_form"):
        st.markdown("#### Demographics")
        col1, col2 = st.columns(2)
        with col1:
            dob_val = None
            if profile.get("date_of_birth"):
                try:
                    parts = profile["date_of_birth"].split("-")
                    dob_val = date(int(parts[0]), int(parts[1]), int(parts[2]))
                except (ValueError, IndexError):
                    dob_val = None
            dob = st.date_input(
                "Date of Birth",
                value=dob_val,
                min_value=date(1920, 1, 1),
                max_value=date.today(),
                help="Required for: " + ", ".join(CLINICAL_INPUT_SCORES["date_of_birth"]),
            )

        with col2:
            sex_options = ["", "male", "female"]
            sex_labels = ["Select...", "Male", "Female"]
            current_sex = profile.get("sex", "")
            sex_idx = sex_options.index(current_sex) if current_sex in sex_options else 0
            sex = st.selectbox(
                "Biological Sex",
                options=sex_options,
                format_func=lambda x: sex_labels[sex_options.index(x)],
                index=sex_idx,
                help="Required for: " + ", ".join(CLINICAL_INPUT_SCORES["sex"]),
            )

        st.markdown("#### Body Measurements")
        col3, col4 = st.columns(2)
        with col3:
            height_cm = st.number_input(
                "Height (cm)",
                min_value=50.0, max_value=250.0,
                value=profile.get("height_cm") or 170.0,
                step=0.5,
                help="Required for BMI calculation (NAFLD-FS, PREVENT)",
            )
        with col4:
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=20.0, max_value=300.0,
                value=profile.get("weight_kg") or 70.0,
                step=0.5,
                help="Required for BMI calculation (NAFLD-FS, PREVENT)",
            )

        if height_cm and weight_kg and height_cm > 0:
            computed_bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
            st.caption(f"Computed BMI: **{computed_bmi}** kg/m\u00b2")

        st.markdown("#### Blood Pressure")
        col5, col6, col7 = st.columns(3)
        with col5:
            systolic = st.number_input(
                "Systolic BP (mmHg)",
                min_value=60.0, max_value=250.0,
                value=profile.get("systolic_bp") or 120.0,
                step=1.0,
                help="Required for: ASCVD Risk, AHA PREVENT",
            )
        with col6:
            diastolic = st.number_input(
                "Diastolic BP (mmHg)",
                min_value=30.0, max_value=150.0,
                value=profile.get("diastolic_bp") or 80.0,
                step=1.0,
            )
        with col7:
            on_bp_med = st.checkbox(
                "On BP medication",
                value=bool(profile.get("on_bp_medication", 0)),
                help="Taking antihypertensive medication",
            )

        st.markdown("#### Risk Factors")
        col8, col9 = st.columns(2)
        with col8:
            smoke_options = ["", "never", "former", "current"]
            smoke_labels = ["Select...", "Never smoker", "Former smoker", "Current smoker"]
            current_smoke = profile.get("smoking_status", "")
            smoke_idx = smoke_options.index(current_smoke) if current_smoke in smoke_options else 0
            smoking = st.selectbox(
                "Smoking Status",
                options=smoke_options,
                format_func=lambda x: smoke_labels[smoke_options.index(x)],
                index=smoke_idx,
                help="Required for: ASCVD Risk, AHA PREVENT",
            )
        with col9:
            diabetes = st.checkbox(
                "Diabetes / Impaired Fasting Glucose",
                value=bool(profile.get("diabetes_status", 0)),
                help="Required for: ASCVD Risk, AHA PREVENT, NAFLD Fibrosis Score",
            )

        col10, _ = st.columns(2)
        with col10:
            on_statin = st.checkbox(
                "On statin therapy",
                value=bool(profile.get("on_statin", 0)),
            )

        submitted = st.form_submit_button("Save Clinical Profile", use_container_width=True)
        if submitted:
            from models.clinical_profile import save_profile
            data = {
                "date_of_birth": str(dob) if dob else None,
                "sex": sex if sex else None,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "smoking_status": smoking if smoking else None,
                "diabetes_status": 1 if diabetes else 0,
                "systolic_bp": systolic,
                "diastolic_bp": diastolic,
                "on_bp_medication": 1 if on_bp_med else 0,
                "on_statin": 1 if on_statin else 0,
            }
            save_profile(user_id, data)
            st.success("Clinical profile saved.")
            st.rerun()


def render_clinical_profile_summary(user_id: int):
    """Render a compact summary of the user's clinical profile."""
    profile = get_profile(user_id)
    if not profile:
        st.info("No clinical profile set. Fill in the Clinical Profile tab to enable cardiovascular and other scores.")
        return

    age = get_age(user_id)
    bmi = get_bmi(user_id)

    cols = st.columns(4)
    with cols[0]:
        st.metric("Age", f"{int(age)} yrs" if age else "Not set")
    with cols[1]:
        st.metric("Sex", (profile.get("sex") or "Not set").capitalize())
    with cols[2]:
        st.metric("BMI", f"{bmi} kg/m\u00b2" if bmi else "Not set")
    with cols[3]:
        bp_text = "Not set"
        if profile.get("systolic_bp") and profile.get("diastolic_bp"):
            bp_text = f"{int(profile['systolic_bp'])}/{int(profile['diastolic_bp'])}"
            if profile.get("on_bp_medication"):
                bp_text += " (Rx)"
        st.metric("Blood Pressure", bp_text)
