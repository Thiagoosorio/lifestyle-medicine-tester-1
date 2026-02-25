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
                "education_years": "Education Years", "physical_activity_level": "Physical Activity Level",
                "height_cm": "Height", "weight_kg": "Weight",
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

    with st.form(key="clinical_profile_form"):
        st.markdown("#### Demographics")
        col1, col2, col3 = st.columns(3)
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
                help="Required for: eGFR, FIB-4, ASCVD, PREVENT, Framingham, QRISK3",
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
                help="Required for: eGFR, ASCVD, PREVENT, QRISK3",
            )

        with col3:
            ethnicity_options = ["white", "indian", "pakistani", "bangladeshi", "other_asian", "black_caribbean", "black_african", "chinese", "other"]
            ethnicity_labels = ["White / Not stated", "Indian", "Pakistani", "Bangladeshi", "Other Asian", "Black Caribbean", "Black African", "Chinese", "Other"]
            current_eth = profile.get("ethnicity", "white") or "white"
            eth_idx = ethnicity_options.index(current_eth) if current_eth in ethnicity_options else 0
            ethnicity = st.selectbox(
                "Ethnicity",
                options=ethnicity_options,
                format_func=lambda x: ethnicity_labels[ethnicity_options.index(x)],
                index=eth_idx,
                help="Used by QRISK3 for ethnicity-calibrated risk",
            )

        st.markdown("#### Body Measurements")
        col3a, col4a = st.columns(2)
        with col3a:
            height_cm = st.number_input(
                "Height (cm)",
                min_value=50.0, max_value=250.0,
                value=profile.get("height_cm") or 170.0,
                step=0.5,
                help="Required for BMI calculation (NAFLD-FS, PREVENT, QRISK3)",
            )
        with col4a:
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=20.0, max_value=300.0,
                value=profile.get("weight_kg") or 70.0,
                step=0.5,
                help="Required for BMI calculation (NAFLD-FS, PREVENT, QRISK3)",
            )

        if height_cm and weight_kg and height_cm > 0:
            computed_bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
            st.caption(f"Computed BMI: **{computed_bmi}** kg/m\u00b2")

        st.markdown("#### Blood Pressure")
        col5, col6, col7, col7b = st.columns(4)
        with col5:
            systolic = st.number_input(
                "Systolic BP (mmHg)",
                min_value=60.0, max_value=250.0,
                value=profile.get("systolic_bp") or 120.0,
                step=1.0,
                help="Required for: ASCVD, PREVENT, Framingham, QRISK3",
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
        with col7b:
            sbp_var = st.number_input(
                "SBP variability (SD)",
                min_value=0.0, max_value=40.0,
                value=profile.get("sbp_variability") or 0.0,
                step=0.5,
                help="Standard deviation of repeated SBP readings. Used by QRISK3. Leave 0 if unknown.",
            )

        st.markdown("#### Smoking")
        col8a, col8b = st.columns(2)
        with col8a:
            smoke_options = ["", "never", "former", "current"]
            smoke_labels = ["Select...", "Never smoker", "Former smoker", "Current smoker"]
            current_smoke = profile.get("smoking_status", "")
            smoke_idx = smoke_options.index(current_smoke) if current_smoke in smoke_options else 0
            smoking = st.selectbox(
                "Smoking Status",
                options=smoke_options,
                format_func=lambda x: smoke_labels[smoke_options.index(x)],
                index=smoke_idx,
                help="Required for: ASCVD, PREVENT, Framingham, QRISK3",
            )
        with col8b:
            cigs = st.number_input(
                "Cigarettes per day (if current smoker)",
                min_value=0, max_value=60,
                value=int(profile.get("cigarettes_per_day", 0) or 0),
                step=1,
                help="QRISK3 uses: light (1-9), moderate (10-19), heavy (20+)",
            )

        st.markdown("#### Diabetes")
        col_dt1, col_dt2 = st.columns(2)
        with col_dt1:
            dm_type_options = ["none", "type2", "type1"]
            dm_type_labels = ["No diabetes", "Type 2 diabetes", "Type 1 diabetes"]
            current_dm_type = profile.get("diabetes_type", "none") or "none"
            dm_idx = dm_type_options.index(current_dm_type) if current_dm_type in dm_type_options else 0
            diabetes_type = st.selectbox(
                "Diabetes Type",
                options=dm_type_options,
                format_func=lambda x: dm_type_labels[dm_type_options.index(x)],
                index=dm_idx,
                help="QRISK3 distinguishes Type 1 vs Type 2. Other scores use any diabetes.",
            )
        with col_dt2:
            on_statin = st.checkbox(
                "On statin therapy",
                value=bool(profile.get("on_statin", 0)),
            )

        st.markdown("#### Medical History (for QRISK3)")
        st.caption("Check all conditions that apply. These enable more accurate QRISK3 cardiovascular risk prediction.")
        col_mh1, col_mh2, col_mh3 = st.columns(3)
        with col_mh1:
            fh_chd = st.checkbox(
                "Family history of CHD (<60)",
                value=bool(profile.get("family_history_chd", 0)),
                help="First-degree relative with coronary heart disease under age 60",
            )
            af = st.checkbox(
                "Atrial fibrillation",
                value=bool(profile.get("atrial_fibrillation", 0)),
            )
            ra = st.checkbox(
                "Rheumatoid arthritis",
                value=bool(profile.get("rheumatoid_arthritis", 0)),
            )
            ckd = st.checkbox(
                "Chronic kidney disease (stage 3-5)",
                value=bool(profile.get("chronic_kidney_disease", 0)),
            )
        with col_mh2:
            migraine = st.checkbox(
                "Migraine",
                value=bool(profile.get("migraine", 0)),
            )
            sle_val = st.checkbox(
                "Systemic lupus (SLE)",
                value=bool(profile.get("sle", 0)),
            )
            smi = st.checkbox(
                "Severe mental illness",
                value=bool(profile.get("severe_mental_illness", 0)),
                help="Schizophrenia, bipolar disorder, or severe depression",
            )
            ed = st.checkbox(
                "Erectile dysfunction",
                value=bool(profile.get("erectile_dysfunction", 0)),
                help="Males only — used in QRISK3 male model",
            )
        with col_mh3:
            antipsych = st.checkbox(
                "Atypical antipsychotic use",
                value=bool(profile.get("atypical_antipsychotic", 0)),
            )
            cortico = st.checkbox(
                "Oral corticosteroid use",
                value=bool(profile.get("corticosteroid_use", 0)),
                help="Regular use of oral steroid tablets",
            )

        st.markdown("#### Cardiovascular / Stroke History (for CHA\u2082DS\u2082-VASc)")
        st.caption("Check all conditions that apply. These enable stroke risk scoring in atrial fibrillation.")
        col_cv1, col_cv2, col_cv3 = st.columns(3)
        with col_cv1:
            chf = st.checkbox(
                "Congestive heart failure",
                value=bool(profile.get("congestive_heart_failure", 0)),
                help="History of heart failure / reduced ejection fraction",
            )
        with col_cv2:
            stroke_tia = st.checkbox(
                "Prior stroke / TIA",
                value=bool(profile.get("prior_stroke_tia", 0)),
                help="History of stroke, TIA, or thromboembolism — adds 2 points",
            )
        with col_cv3:
            vasc = st.checkbox(
                "Vascular disease",
                value=bool(profile.get("vascular_disease", 0)),
                help="Prior MI, peripheral artery disease, or aortic plaque",
            )

        st.markdown("#### Dementia Risk Factors (for CAIDE)")
        st.caption("Education and physical activity level used in the CAIDE Dementia Risk Score.")
        col_dem1, col_dem2 = st.columns(2)
        with col_dem1:
            edu_years = st.number_input(
                "Education (total years)",
                min_value=0, max_value=30,
                value=int(profile.get("education_years") or 12),
                step=1,
                help="CAIDE: >=10 yrs (0 pts), 7-9 yrs (2 pts), 0-6 yrs (3 pts)",
            )
        with col_dem2:
            activity_options = ["active", "inactive"]
            activity_labels = ["Active (regular exercise)", "Inactive (sedentary)"]
            current_activity = profile.get("physical_activity_level", "active") or "active"
            act_idx = activity_options.index(current_activity) if current_activity in activity_options else 0
            phys_activity = st.selectbox(
                "Physical activity level",
                options=activity_options,
                format_func=lambda x: activity_labels[activity_options.index(x)],
                index=act_idx,
                help="CAIDE: active (0 pts), inactive (1 pt)",
            )

        submitted = st.form_submit_button("Save Clinical Profile", use_container_width=True)
        if submitted:
            from models.clinical_profile import save_profile
            # Derive diabetes_status from diabetes_type for backward compat
            dm_status = 1 if diabetes_type in ("type1", "type2") else 0
            data = {
                "date_of_birth": str(dob) if dob else None,
                "sex": sex if sex else None,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "smoking_status": smoking if smoking else None,
                "diabetes_status": dm_status,
                "systolic_bp": systolic,
                "diastolic_bp": diastolic,
                "on_bp_medication": 1 if on_bp_med else 0,
                "on_statin": 1 if on_statin else 0,
                "ethnicity": ethnicity,
                "diabetes_type": diabetes_type,
                "family_history_chd": 1 if fh_chd else 0,
                "atrial_fibrillation": 1 if af else 0,
                "rheumatoid_arthritis": 1 if ra else 0,
                "chronic_kidney_disease": 1 if ckd else 0,
                "migraine": 1 if migraine else 0,
                "sle": 1 if sle_val else 0,
                "severe_mental_illness": 1 if smi else 0,
                "erectile_dysfunction": 1 if ed else 0,
                "atypical_antipsychotic": 1 if antipsych else 0,
                "corticosteroid_use": 1 if cortico else 0,
                "sbp_variability": sbp_var if sbp_var > 0 else None,
                "cigarettes_per_day": cigs,
                "congestive_heart_failure": 1 if chf else 0,
                "prior_stroke_tia": 1 if stroke_tia else 0,
                "vascular_disease": 1 if vasc else 0,
                "education_years": edu_years,
                "physical_activity_level": phys_activity,
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
