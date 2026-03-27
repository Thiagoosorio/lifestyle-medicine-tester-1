"""Organ Health Scores page — Computed clinical indices from lab results."""

import streamlit as st
from config.organ_scores_data import ORGAN_SYSTEMS
from components.custom_theme import render_hero_banner, render_section_header
from services.organ_score_service import (
    compute_all_scores, get_computable_scores, get_latest_computed_scores,
)
from models.organ_score import get_all_score_definitions, get_score_history
from components.organ_health_display import (
    render_organ_score_card, render_missing_score_card,
    render_organ_section_header, render_score_trend_chart,
    render_clinical_profile_form, render_clinical_profile_summary,
)

def _build_organ_action_plan(existing_scores: list[dict], comp_data: dict) -> list[str]:
    actions: list[str] = []
    high_risk = [s for s in existing_scores if s.get("severity") in {"high", "critical"}]
    elevated = [s for s in existing_scores if s.get("severity") == "elevated"]

    if high_risk:
        score_names = [s.get("name") or s.get("code", "score") for s in high_risk[:3]]
        actions.append(
            "Priority review: discuss high-risk scores with your clinician (" + ", ".join(score_names) + ")."
        )
    elif elevated:
        score_names = [s.get("name") or s.get("code", "score") for s in elevated[:3]]
        actions.append(
            "Track elevated scores closely over time (" + ", ".join(score_names) + ")."
        )

    missing_items = comp_data.get("missing", [])
    missing_biomarkers = sum(len(m.get("missing_biomarkers", [])) for m in missing_items)
    missing_clinical = sum(len(m.get("missing_clinical", [])) for m in missing_items)
    if missing_biomarkers:
        actions.append("Log missing lab biomarkers to unlock additional validated scores.")
    if missing_clinical:
        actions.append("Complete your Clinical Profile to improve score completeness and confidence.")

    if not actions:
        actions.append("Maintain current progress and re-check scores with your next lab panel.")
    return actions[:3]


render_hero_banner("Organ Health Scores", "Composite clinical indices from your lab results.")
st.markdown(
    "Composite clinical indices computed from your lab results. "
    "These are **screening tools**, not diagnoses — always discuss results with your healthcare provider."
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in first.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_dashboard, tab_profile, tab_trends, tab_missing = st.tabs([
    "Organ Dashboard", "Clinical Profile", "Score Trends", "Missing Data"
])

# ── Tab 1: Organ Dashboard ───────────────────────────────────────────────────
with tab_dashboard:
    render_clinical_profile_summary(user_id)
    st.divider()

    col_info, col_btn = st.columns([3, 1])
    with col_btn:
        recalculate = st.button(":material/refresh: Recalculate", use_container_width=True)

    if recalculate:
        with st.spinner("Computing organ health scores..."):
            computed = compute_all_scores(user_id)
        if computed:
            st.success(f"Computed {len(computed)} score(s).")
        else:
            st.warning("No scores could be computed. Check that you have lab results and a clinical profile.")

    existing_scores = get_latest_computed_scores(user_id)
    if not existing_scores and not recalculate:
        computed = compute_all_scores(user_id)
        existing_scores = get_latest_computed_scores(user_id)

    comp_data = get_computable_scores(user_id)

    if existing_scores:
        high_count = sum(1 for s in existing_scores if s.get("severity") in {"high", "critical"})
        elevated_count = sum(1 for s in existing_scores if s.get("severity") == "elevated")
        missing_count = len(comp_data.get("missing", []))
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Computed Scores", len(existing_scores))
        m2.metric("High Risk", high_count)
        m3.metric("Elevated", elevated_count)
        m4.metric("Missing Inputs", missing_count)

    render_section_header("Patient Action Plan", "Your next best steps from current scores and data completeness")
    for action in _build_organ_action_plan(existing_scores, comp_data):
        st.markdown(f"- {action}")
    q1, q2 = st.columns(2)
    with q1:
        if st.button("Open Biomarkers", use_container_width=True, key="organ_open_biomarkers"):
            st.switch_page("pages/biomarkers.py")
    with q2:
        st.caption("Need profile fields? Use the **Clinical Profile** tab above to complete them.")
    st.divider()

    if not existing_scores and not comp_data["computable"]:
        st.info(
            "No organ scores can be computed yet. Please:\n"
            "1. Log your lab results on the **Biomarkers** page\n"
            "2. Fill in your **Clinical Profile** (age, sex, BP, etc.)\n"
            "3. Return here to see your scores"
        )
    else:
        scores_by_organ = {}
        for s in existing_scores:
            organ = s.get("organ_system", "other")
            scores_by_organ.setdefault(organ, []).append(s)

        definitions = get_all_score_definitions()
        defs_by_code = {d["code"]: d for d in definitions}

        missing_by_organ = {}
        for m in comp_data["missing"]:
            organ = m["definition"]["organ_system"]
            missing_by_organ.setdefault(organ, []).append(m)

        for organ_code in sorted(
            ORGAN_SYSTEMS.keys(),
            key=lambda o: ORGAN_SYSTEMS[o]["sort_order"]
        ):
            organ_meta = ORGAN_SYSTEMS[organ_code]
            organ_scores = scores_by_organ.get(organ_code, [])
            organ_missing = missing_by_organ.get(organ_code, [])

            if not organ_scores and not organ_missing:
                continue

            render_organ_section_header(
                organ_code, organ_meta["name"],
                organ_meta.get("icon", ""), organ_meta["color"],
            )

            cols = st.columns(min(len(organ_scores), 2) if organ_scores else 1)
            for i, score in enumerate(organ_scores):
                with cols[i % 2]:
                    score_def = defs_by_code.get(score.get("code"), {})
                    render_organ_score_card(score, score_def)

            if organ_missing:
                miss_cols = st.columns(min(len(organ_missing), 2))
                for i, m in enumerate(organ_missing):
                    with miss_cols[i % 2]:
                        render_missing_score_card(
                            m["definition"],
                            m["missing_biomarkers"],
                            m["missing_clinical"],
                        )

            st.divider()

    st.caption(
        "**Disclaimer:** Organ health scores are screening tools derived from published clinical "
        "research. They are NOT diagnostic tests. Tier 1 (Clinically Validated) scores use "
        "peer-reviewed formulas with established cutoffs. Tier 2 (Derived/Experimental) scores "
        "use emerging formulas with limited population norms. Always consult your healthcare "
        "provider for clinical interpretation."
    )

# ── Tab 2: Clinical Profile ──────────────────────────────────────────────────
with tab_profile:
    render_clinical_profile_form(user_id)

# ── Tab 3: Score Trends ──────────────────────────────────────────────────────
with tab_trends:
    existing_scores = get_latest_computed_scores(user_id)
    if not existing_scores:
        st.info("No scores computed yet. Compute scores from the Organ Dashboard tab first.")
    else:
        definitions = get_all_score_definitions()
        defs_by_code = {d["code"]: d for d in definitions}

        score_names = {s["code"]: s["name"] for s in existing_scores}
        selected_code = st.selectbox(
            "Select Score",
            options=list(score_names.keys()),
            format_func=lambda x: score_names[x],
            key="trend_score",
        )

        if selected_code:
            history = get_score_history(user_id, selected_code, limit=50)
            defn = defs_by_code.get(selected_code, {})
            if len(history) < 2:
                st.info("Need at least 2 data points to show a trend. Compute scores over time as you log new labs.")
                if history:
                    st.metric(
                        defn.get("name", selected_code),
                        f"{history[0]['value']:.2f}",
                        help=f"From {history[0].get('lab_date', 'unknown')}",
                    )
            else:
                render_score_trend_chart(list(reversed(history)), defn)

# ── Tab 4: Missing Data ──────────────────────────────────────────────────────
with tab_missing:
    comp_data = get_computable_scores(user_id)
    total_definitions = len(get_all_score_definitions())
    missing_count = len(comp_data.get("missing", []))
    ready_count = max(0, total_definitions - missing_count)
    if total_definitions > 0:
        st.progress(ready_count / total_definitions)
        st.caption(f"Score readiness: {ready_count}/{total_definitions} formulas can be computed.")

    if not comp_data["missing"]:
        st.success("All organ health scores can be computed with your current data!")
    else:
        st.markdown(
            f"**{len(comp_data['missing'])}** score(s) cannot be computed due to missing inputs."
        )

        for m in comp_data["missing"]:
            defn = m["definition"]
            with st.expander(f"{defn['name']} ({defn['organ_system'].title()})"):
                if m["missing_biomarkers"]:
                    st.markdown("**Missing lab results:**")
                    for b in m["missing_biomarkers"]:
                        st.markdown(f"- `{b}`")
                    st.page_link("pages/biomarkers.py", label="Go to Biomarkers", icon=":material/bloodtype:")

                if m["missing_clinical"]:
                    labels = {
                        "age": "Date of Birth", "sex": "Biological Sex",
                        "bmi": "Height & Weight (for BMI)",
                        "systolic_bp": "Systolic Blood Pressure",
                        "smoking_status": "Smoking Status",
                        "diabetes_status": "Diabetes Status",
                        "on_bp_medication": "BP Medication Status",
                    }
                    st.markdown("**Missing clinical data:**")
                    for c in m["missing_clinical"]:
                        st.markdown(f"- {labels.get(c, c)}")
                    st.markdown("Fill in the **Clinical Profile** tab above.")

                if defn.get("description"):
                    st.caption(defn["description"])
