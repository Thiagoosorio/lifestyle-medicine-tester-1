"""Organ health score display components for Streamlit UI."""

import streamlit as st
import plotly.graph_objects as go
from datetime import date
from models.clinical_profile import get_profile, get_age, get_bmi
from services.fracture_risk_service import build_frax_workflow_context

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


def _option_index(options, current) -> int:
    """Return a stable select index, treating unrecognised values as unknown."""
    return options.index(current) if current in options else 0


def _optional_boolean_input(label: str, value, **kwargs) -> int | None:
    """Render a tri-state clinical input so NULL is distinct from a negative."""
    options = [None, 0, 1]
    labels = {None: "Unknown", 0: "No", 1: "Yes"}
    return st.selectbox(
        label,
        options=options,
        format_func=labels.get,
        index=_option_index(options, value),
        **kwargs,
    )


def _first_sentence(text: str, max_len: int = 210) -> str:
    """Return a compact first sentence for inline card explanations."""
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return ""
    for sep in (". ", "; ", " — ", " - "):
        if sep in cleaned:
            cleaned = cleaned.split(sep, 1)[0]
            break
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 1].rstrip() + "…"
    return cleaned


def _scientific_explanation(score_def: dict) -> str:
    """Build a short scientific explanation shown on every score card."""
    description = _first_sentence(score_def.get("description", ""))
    citation_pmid = str(score_def.get("citation_pmid") or "").strip()
    tier = str(score_def.get("tier") or "validated").lower()

    if not description:
        score_name = score_def.get("name", "This score")
        description = f"{score_name} combines clinical inputs into a risk estimate."

    if citation_pmid:
        if tier == "validated":
            evidence = f"Validated in peer-reviewed studies (PMID: {citation_pmid})."
        else:
            evidence = f"Evidence is emerging and should be interpreted directionally (PMID: {citation_pmid})."
    else:
        evidence = "Evidence citation not linked in this card."

    return f"{description}. {evidence}"


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
                # Integer-valued ordinal scores (e.g. DXA risk class 0/1/2/3)
                # render without trailing ".00" so clinicians don't misread the
                # value as a decimal measurement.
                if value == int(value) and abs(value) < 100:
                    display_val = str(int(value))
                elif value < 100:
                    display_val = f"{value:.2f}"
                else:
                    display_val = f"{value:.1f}"
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
            st.caption(f"Scientific explanation: {_scientific_explanation(score_def)}")

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
        st.caption(f"Scientific explanation: {_scientific_explanation(score_def)}")

        missing_items = []
        if missing_biomarkers:
            biomarker_labels = {
                "dexa_t_score": "DEXA T-score",
                "dexa_z_score": "DEXA Z-score",
                "dexa_alm_kg": "DEXA appendicular lean mass (kg)",
                "dexa_alm_h2": "DEXA ALM / height² (kg/m²)",
                "dexa_ffmi": "DEXA fat-free mass index",
                "dexa_bmd_g_cm2": "DEXA BMD (g/cm²)",
            }
            named_biomarkers = [biomarker_labels.get(code, code) for code in missing_biomarkers]
            missing_items.append(f"**Inputs needed:** {', '.join(named_biomarkers)}")
        if missing_clinical:
            labels = {
                "age": "Date of Birth", "sex": "Sex", "bmi": "Height & Weight",
                "systolic_bp": "Blood Pressure", "smoking_status": "Smoking Status",
                "diabetes_status": "Diabetes Status", "on_bp_medication": "BP Medication",
                "education_years": "Education Years", "physical_activity_level": "Physical Activity Level",
                "height_cm": "Height", "weight_kg": "Weight",
                "grip_strength_kg": "Grip Strength", "chair_stand_time_s": "Chair Stand Time",
                "gait_speed_m_per_s": "Gait Speed", "waist_cm": "Waist Circumference",
                "daily_activity_30min": "Daily Physical Activity", "daily_fruit_veg": "Daily Fruit / Vegetable Intake",
                "history_high_glucose": "History of High Glucose", "family_history_diabetes": "Family History of Diabetes",
                "neck_circumference_cm": "Neck Circumference", "loud_snoring": "Loud Snoring",
                "ethnicity": "Ethnicity", "cigarettes_per_day": "Cigarettes per Day",
                "alcohol_intake_level": "Alcohol Intake Level", "antidepressant_use": "Antidepressant Use",
                "cancer": "Cancer History", "asthma_copd": "Asthma / COPD",
                "care_home": "Care Home Status", "prior_stroke_tia": "Prior Stroke / TIA",
                "vascular_disease": "Vascular Disease", "dementia": "Dementia",
                "endocrine_bone_disorder": "Endocrine Bone Disorder", "epilepsy": "Epilepsy",
                "falls_last_year": "Falls in Last Year", "prior_fragility_fracture": "Prior Fragility Fracture",
                "hrt_estrogen_only": "Estrogen-only HRT", "chronic_liver_disease": "Chronic Liver Disease",
                "malabsorption": "Malabsorption", "parkinsons": "Parkinson's Disease",
                "advanced_ckd_stage45": "Advanced CKD (Stage 4-5)",
                "family_history_osteoporosis": "Family History of Osteoporosis / Hip Fracture",
                "diabetes_type": "Diabetes Type",
                "parent_hip_fracture": "Parent Hip Fracture",
            }
            named = [labels.get(c, c) for c in missing_clinical]
            missing_items.append(f"**Clinical data needed:** {', '.join(named)}")

        for item in missing_items:
            st.markdown(item)

        # Surface the same Details & Citation context shown on computed cards
        # so the clinician can review clinical provenance before any data is on
        # file (useful for Reveal Day prep, patient-facing explanations, etc.).
        citation_pmid = score_def.get("citation_pmid", "")
        citation_text = score_def.get("citation_text", "")
        if score_def.get("description") or citation_text or citation_pmid:
            with st.expander("Details & Citation"):
                if score_def.get("description"):
                    st.markdown(score_def["description"])
                if citation_text:
                    st.markdown(f"**Citation:** {citation_text}")
                elif citation_pmid:
                    st.markdown(f"**PMID:** {citation_pmid}")


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
            sex_options = [None, "male", "female"]
            sex_labels = {None: "Unknown", "male": "Male", "female": "Female"}
            current_sex = profile.get("sex")
            sex = st.selectbox(
                "Biological Sex",
                options=sex_options,
                format_func=sex_labels.get,
                index=_option_index(sex_options, current_sex),
                help="Required for: eGFR, ASCVD, PREVENT, QRISK3",
            )

        with col3:
            ethnicity_options = [None, "white", "indian", "pakistani", "bangladeshi", "other_asian", "black_caribbean", "black_african", "chinese", "other"]
            ethnicity_labels = {
                None: "Unknown", "white": "White", "indian": "Indian",
                "pakistani": "Pakistani", "bangladeshi": "Bangladeshi",
                "other_asian": "Other Asian", "black_caribbean": "Black Caribbean",
                "black_african": "Black African", "chinese": "Chinese", "other": "Other",
            }
            current_eth = profile.get("ethnicity")
            ethnicity = st.selectbox(
                "Ethnicity",
                options=ethnicity_options,
                format_func=ethnicity_labels.get,
                index=_option_index(ethnicity_options, current_eth),
                help="Used by QRISK3 for ethnicity-calibrated risk",
            )

        st.markdown("#### Body Measurements")
        col3a, col4a = st.columns(2)
        with col3a:
            height_cm = st.number_input(
                "Height (cm)",
                min_value=50.0, max_value=250.0,
                value=profile.get("height_cm"),
                step=0.5,
                placeholder="Unknown",
                help="Required for BMI calculation (NAFLD-FS, PREVENT, QRISK3)",
            )
        with col4a:
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=20.0, max_value=300.0,
                value=profile.get("weight_kg"),
                step=0.5,
                placeholder="Unknown",
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
                value=profile.get("systolic_bp"),
                step=1.0,
                placeholder="Unknown",
                help="Required for: ASCVD, PREVENT, Framingham, QRISK3",
            )
        with col6:
            diastolic = st.number_input(
                "Diastolic BP (mmHg)",
                min_value=30.0, max_value=150.0,
                value=profile.get("diastolic_bp"),
                step=1.0,
                placeholder="Unknown",
            )
        with col7:
            on_bp_med = _optional_boolean_input(
                "On BP medication",
                profile.get("on_bp_medication"),
                help="Taking antihypertensive medication",
            )
        with col7b:
            sbp_var = st.number_input(
                "SBP variability (SD)",
                min_value=0.0, max_value=40.0,
                value=profile.get("sbp_variability"),
                step=0.5,
                placeholder="Unknown",
                help="Standard deviation of repeated SBP readings. Used by QRISK3.",
            )

        st.markdown("#### Smoking")
        col8a, col8b = st.columns(2)
        with col8a:
            smoke_options = [None, "never", "former", "current"]
            smoke_labels = {None: "Unknown", "never": "Never smoker", "former": "Former smoker", "current": "Current smoker"}
            current_smoke = profile.get("smoking_status")
            smoking = st.selectbox(
                "Smoking Status",
                options=smoke_options,
                format_func=smoke_labels.get,
                index=_option_index(smoke_options, current_smoke),
                help="Required for: ASCVD, PREVENT, Framingham, QRISK3",
            )
        with col8b:
            cigs = st.number_input(
                "Cigarettes per day (if current smoker)",
                min_value=0, max_value=60,
                value=profile.get("cigarettes_per_day"),
                step=1,
                placeholder="Unknown",
                disabled=smoking != "current",
                help="QRISK3 uses: light (1-9), moderate (10-19), heavy (20+)",
            )

        st.markdown("#### Diabetes")
        col_dt1, col_dt2 = st.columns(2)
        with col_dt1:
            dm_type_options = [None, "none", "type2", "type1"]
            dm_type_labels = {None: "Unknown", "none": "No diabetes", "type2": "Type 2 diabetes", "type1": "Type 1 diabetes"}
            current_dm_type = profile.get("diabetes_type")
            diabetes_type = st.selectbox(
                "Diabetes Type",
                options=dm_type_options,
                format_func=dm_type_labels.get,
                index=_option_index(dm_type_options, current_dm_type),
                help="QRISK3 distinguishes Type 1 vs Type 2. Other scores use any diabetes.",
            )
        with col_dt2:
            on_statin = _optional_boolean_input(
                "On statin therapy",
                profile.get("on_statin"),
            )

        st.markdown("#### Medical History (for QRISK3)")
        st.caption("Check all conditions that apply. These enable more accurate QRISK3 cardiovascular risk prediction.")
        col_mh1, col_mh2, col_mh3 = st.columns(3)
        with col_mh1:
            fh_chd = _optional_boolean_input(
                "Family history of CHD (<60)",
                profile.get("family_history_chd"),
                help="First-degree relative with coronary heart disease under age 60",
            )
            af = _optional_boolean_input(
                "Atrial fibrillation",
                profile.get("atrial_fibrillation"),
            )
            ra = _optional_boolean_input(
                "Rheumatoid arthritis",
                profile.get("rheumatoid_arthritis"),
            )
            ckd = _optional_boolean_input(
                "Chronic kidney disease (stage 3-5)",
                profile.get("chronic_kidney_disease"),
            )
        with col_mh2:
            migraine = _optional_boolean_input(
                "Migraine",
                profile.get("migraine"),
            )
            sle_val = _optional_boolean_input(
                "Systemic lupus (SLE)",
                profile.get("sle"),
            )
            smi = _optional_boolean_input(
                "Severe mental illness",
                profile.get("severe_mental_illness"),
                help="Schizophrenia, bipolar disorder, or severe depression",
            )
            ed = _optional_boolean_input(
                "Erectile dysfunction",
                profile.get("erectile_dysfunction"),
                help="Males only — used in QRISK3 male model",
            )
        with col_mh3:
            antipsych = _optional_boolean_input(
                "Atypical antipsychotic use",
                profile.get("atypical_antipsychotic"),
            )
            cortico = _optional_boolean_input(
                "Oral corticosteroid use",
                profile.get("corticosteroid_use"),
                help="Regular use of oral steroid tablets",
            )

        st.markdown("#### Cardiovascular / Stroke History (for CHA\u2082DS\u2082-VASc)")
        st.caption("Check all conditions that apply. These enable stroke risk scoring in atrial fibrillation.")
        col_cv1, col_cv2, col_cv3 = st.columns(3)
        with col_cv1:
            chf = _optional_boolean_input(
                "Congestive heart failure",
                profile.get("congestive_heart_failure"),
                help="History of heart failure / reduced ejection fraction",
            )
        with col_cv2:
            stroke_tia = _optional_boolean_input(
                "Prior stroke / TIA",
                profile.get("prior_stroke_tia"),
                help="History of stroke, TIA, or thromboembolism — adds 2 points",
            )
        with col_cv3:
            vasc = _optional_boolean_input(
                "Vascular disease",
                profile.get("vascular_disease"),
                help="Prior MI, peripheral artery disease, or aortic plaque",
            )

        st.markdown("#### Dementia Risk Factors (for CAIDE)")
        st.caption("Education and physical activity level used in the CAIDE Dementia Risk Score.")
        col_dem1, col_dem2 = st.columns(2)
        with col_dem1:
            edu_years = st.number_input(
                "Education (total years)",
                min_value=0, max_value=30,
                value=profile.get("education_years"),
                step=1,
                placeholder="Unknown",
                help="CAIDE: >=10 yrs (0 pts), 7-9 yrs (2 pts), 0-6 yrs (3 pts)",
            )
        with col_dem2:
            activity_options = [None, "active", "inactive"]
            activity_labels = {None: "Unknown", "active": "Active (regular exercise)", "inactive": "Inactive (sedentary)"}
            current_activity = profile.get("physical_activity_level")
            phys_activity = st.selectbox(
                "Physical activity level",
                options=activity_options,
                format_func=activity_labels.get,
                index=_option_index(activity_options, current_activity),
                help="CAIDE: active (0 pts), inactive (1 pt)",
            )

        st.markdown("#### Musculoskeletal Function (for FNIH / EWGSOP2)")
        st.caption("Use dynamometer grip strength, five-repetition chair stand time, and usual gait speed alongside DXA lean-mass data.")
        col_ms1, col_ms2, col_ms3 = st.columns(3)
        with col_ms1:
            grip_strength = st.number_input(
                "Grip strength (kg)",
                min_value=0.0, max_value=120.0,
                value=profile.get("grip_strength_kg"),
                step=0.5,
                placeholder="Unknown",
                help="EWGSOP2 low strength cutpoints: <27 kg men, <16 kg women.",
            )
        with col_ms2:
            chair_stand_time = st.number_input(
                "Chair stand time (s)",
                min_value=0.0, max_value=60.0,
                value=profile.get("chair_stand_time_s"),
                step=0.1,
                placeholder="Unknown",
                help="Time for 5 chair rises. EWGSOP2 low-strength threshold: >15 seconds.",
            )
        with col_ms3:
            gait_speed = st.number_input(
                "Gait speed (m/s)",
                min_value=0.0, max_value=3.0,
                value=profile.get("gait_speed_m_per_s"),
                step=0.05,
                placeholder="Unknown",
                help="Usual gait speed. EWGSOP2 severe-stage threshold: <=0.8 m/s.",
            )

        st.markdown("#### Diabetes Risk Inputs (for FINDRISC)")
        col_dr1, col_dr2 = st.columns(2)
        with col_dr1:
            family_diabetes_options = [None, "none", "second_degree", "first_degree"]
            family_diabetes_labels = {
                None: "Unknown",
                "none": "No family history",
                "second_degree": "Second-degree relative (grandparent, aunt/uncle, cousin)",
                "first_degree": "First-degree relative (parent, sibling, child)",
            }
            current_family_dm = profile.get("family_history_diabetes")
            family_history_diabetes = st.selectbox(
                "Family history of diabetes",
                options=family_diabetes_options,
                format_func=family_diabetes_labels.get,
                index=_option_index(family_diabetes_options, current_family_dm),
            )
            history_high_glucose = _optional_boolean_input(
                "History of high blood glucose",
                profile.get("history_high_glucose"),
                help="Includes prior impaired fasting glucose, gestational diabetes, or any previous elevated glucose test.",
            )
        with col_dr2:
            daily_activity_30min = _optional_boolean_input(
                "At least 30 min physical activity daily",
                profile.get("daily_activity_30min"),
                help="Specific FINDRISC activity item.",
            )
            daily_fruit_veg = _optional_boolean_input(
                "Eat fruit / vegetables every day",
                profile.get("daily_fruit_veg"),
                help="Specific FINDRISC diet item.",
            )

        with st.expander("Advanced Bone & Sleep Risk Inputs (QFracture / NoSAS)", expanded=False):
            st.markdown("##### Sleep / Recovery")
            col_sl1, col_sl2 = st.columns(2)
            with col_sl1:
                neck_circumference = st.number_input(
                    "Neck circumference (cm)",
                    min_value=0.0, max_value=80.0,
                    value=profile.get("neck_circumference_cm"),
                    step=0.5,
                    placeholder="Unknown",
                    help="NoSAS awards 4 points if neck circumference is >40 cm.",
                )
            with col_sl2:
                loud_snoring = _optional_boolean_input(
                    "Loud / habitual snoring",
                    profile.get("loud_snoring"),
                )

            st.markdown("##### Fracture & Bone-Risk History")
            alcohol_options = [None, "none", "trivial", "light", "moderate", "heavy", "very_heavy"]
            alcohol_labels = {
                None: "Unknown", "none": "None", "trivial": "Trivial / occasional",
                "light": "Light", "moderate": "Moderate", "heavy": "Heavy",
                "very_heavy": "Very heavy",
            }
            current_alcohol = profile.get("alcohol_intake_level")
            alcohol_intake_level = st.selectbox(
                "Alcohol intake level",
                options=alcohol_options,
                format_func=alcohol_labels.get,
                index=_option_index(alcohol_options, current_alcohol),
                help="Six-level category used by QFracture.",
            )

            col_fx1, col_fx2, col_fx3, col_fx4 = st.columns(4)
            with col_fx1:
                prior_fragility_fracture = _optional_boolean_input(
                    "Prior fragility fracture",
                    profile.get("prior_fragility_fracture"),
                )
                parent_hip_fracture = _optional_boolean_input(
                    "Parent fractured hip",
                    profile.get("parent_hip_fracture"),
                    help="FRAX uses parent hip-fracture history specifically, not general family osteoporosis history.",
                )
                family_history_osteoporosis = _optional_boolean_input(
                    "Family history of osteoporosis / hip fracture",
                    profile.get("family_history_osteoporosis"),
                )
                falls_last_year = _optional_boolean_input(
                    "Falls in last year",
                    profile.get("falls_last_year"),
                )
                care_home = _optional_boolean_input(
                    "Care home / institutional living",
                    profile.get("care_home"),
                )
            with col_fx2:
                dementia = _optional_boolean_input(
                    "Dementia",
                    profile.get("dementia"),
                )
                cancer = _optional_boolean_input(
                    "Cancer history",
                    profile.get("cancer"),
                )
                asthma_copd = _optional_boolean_input(
                    "Asthma / COPD",
                    profile.get("asthma_copd"),
                )
                chronic_liver_disease = _optional_boolean_input(
                    "Chronic liver disease",
                    profile.get("chronic_liver_disease"),
                )
            with col_fx3:
                advanced_ckd_stage45 = _optional_boolean_input(
                    "Advanced CKD (stage 4-5)",
                    profile.get("advanced_ckd_stage45"),
                )
                epilepsy = _optional_boolean_input(
                    "Epilepsy",
                    profile.get("epilepsy"),
                )
                parkinsons = _optional_boolean_input(
                    "Parkinson's disease",
                    profile.get("parkinsons"),
                )
                malabsorption = _optional_boolean_input(
                    "Malabsorption syndrome",
                    profile.get("malabsorption"),
                )
            with col_fx4:
                endocrine_bone_disorder = _optional_boolean_input(
                    "Endocrine bone disorder",
                    profile.get("endocrine_bone_disorder"),
                    help="For example untreated hyperthyroidism, hyperparathyroidism, or related endocrine bone disease.",
                )
                antidepressant_use = _optional_boolean_input(
                    "Antidepressant use",
                    profile.get("antidepressant_use"),
                )
                hrt_estrogen_only = _optional_boolean_input(
                    "Estrogen-only HRT",
                    profile.get("hrt_estrogen_only"),
                    help="Relevant to the female QFracture model.",
                )

        submitted = st.form_submit_button("Save Clinical Profile", use_container_width=True)
        if submitted and smoking == "current" and cigs is None:
            st.error("Enter cigarettes per day for a current smoker.")
        elif submitted:
            from models.clinical_profile import save_profile
            # Derive diabetes_status from diabetes_type for backward compat
            dm_status = None if diabetes_type is None else int(diabetes_type != "none")
            data = {
                "date_of_birth": str(dob) if dob else None,
                "sex": sex,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "smoking_status": smoking,
                "diabetes_status": dm_status,
                "systolic_bp": systolic,
                "diastolic_bp": diastolic,
                "on_bp_medication": on_bp_med,
                "on_statin": on_statin,
                "ethnicity": ethnicity,
                "diabetes_type": diabetes_type,
                "family_history_chd": fh_chd,
                "atrial_fibrillation": af,
                "rheumatoid_arthritis": ra,
                "chronic_kidney_disease": ckd,
                "migraine": migraine,
                "sle": sle_val,
                "severe_mental_illness": smi,
                "erectile_dysfunction": ed,
                "atypical_antipsychotic": antipsych,
                "corticosteroid_use": cortico,
                "sbp_variability": sbp_var,
                "cigarettes_per_day": cigs if smoking == "current" else None,
                "congestive_heart_failure": chf,
                "prior_stroke_tia": stroke_tia,
                "vascular_disease": vasc,
                "education_years": edu_years,
                "physical_activity_level": phys_activity,
                "family_history_diabetes": family_history_diabetes,
                "history_high_glucose": history_high_glucose,
                "daily_fruit_veg": daily_fruit_veg,
                "daily_activity_30min": daily_activity_30min,
                "neck_circumference_cm": neck_circumference,
                "loud_snoring": loud_snoring,
                "grip_strength_kg": grip_strength,
                "chair_stand_time_s": chair_stand_time,
                "gait_speed_m_per_s": gait_speed,
                "prior_fragility_fracture": prior_fragility_fracture,
                "parent_hip_fracture": parent_hip_fracture,
                "family_history_osteoporosis": family_history_osteoporosis,
                "falls_last_year": falls_last_year,
                "alcohol_intake_level": alcohol_intake_level,
                "care_home": care_home,
                "dementia": dementia,
                "cancer": cancer,
                "asthma_copd": asthma_copd,
                "chronic_liver_disease": chronic_liver_disease,
                "advanced_ckd_stage45": advanced_ckd_stage45,
                "epilepsy": epilepsy,
                "parkinsons": parkinsons,
                "malabsorption": malabsorption,
                "endocrine_bone_disorder": endocrine_bone_disorder,
                "antidepressant_use": antidepressant_use,
                "hrt_estrogen_only": hrt_estrogen_only,
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

    advanced_parts = []
    if profile.get("grip_strength_kg"):
        advanced_parts.append(f"Grip {profile['grip_strength_kg']} kg")
    if profile.get("chair_stand_time_s"):
        advanced_parts.append(f"Chair stand {profile['chair_stand_time_s']} s")
    if profile.get("gait_speed_m_per_s"):
        advanced_parts.append(f"Gait {profile['gait_speed_m_per_s']} m/s")
    if profile.get("neck_circumference_cm"):
        advanced_parts.append(f"Neck {profile['neck_circumference_cm']} cm")
    if advanced_parts:
        st.caption("Advanced inputs: " + " | ".join(advanced_parts))


def render_frax_workflow_panel(user_id: int, *, show_body_metrics_link: bool = False):
    """Render a UAE-oriented FRAX workflow panel."""
    context = build_frax_workflow_context(user_id)

    with st.container(border=True):
        st.markdown("### Official FRAX Workflow")
        st.caption(
            "For UAE use, the recommended FRAX model is Abu Dhabi. This app prepares the inputs "
            "and links to the official FRAX calculator; it does not calculate FRAX locally."
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Recommended Model", context["model_label"])
        m2.metric("Status", context["status_label"])
        m3.metric("Age Rule", context["age_status"])

        if context["missing_core"]:
            st.warning("Missing core FRAX inputs: " + ", ".join(context["missing_core"]))

        if context["generic_dexa_without_femoral_neck"]:
            st.info(
                "A generic DXA T-score/BMD is on file, but FRAX should use a femoral-neck BMD "
                "or femoral-neck T-score if you want the BMD-enhanced calculation."
            )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Prepared clinical inputs**")
            for label, value in context["prepared_inputs"]:
                st.markdown(f"- {label}: {value}")
        with col2:
            st.markdown("**Bone-specific inputs**")
            for label, value in context["bone_inputs"]:
                st.markdown(f"- {label}: {value}")
            if context["secondary_reasons"]:
                st.caption(
                    "Secondary osteoporosis inferred from: "
                    + ", ".join(context["secondary_reasons"])
                )

        if show_body_metrics_link:
            btn1, btn2 = st.columns(2)
            with btn1:
                st.link_button(
                    "Open Official FRAX Calculator",
                    context["calculator_url"],
                    use_container_width=True,
                )
            with btn2:
                st.page_link(
                    "pages/body_metrics.py",
                    label="Add Femoral-Neck DXA",
                    icon=":material/monitor_weight:",
                )
        else:
            st.link_button(
                "Open Official FRAX Calculator",
                context["calculator_url"],
                use_container_width=True,
            )
