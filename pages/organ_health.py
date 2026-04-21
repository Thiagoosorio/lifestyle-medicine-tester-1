"""Organ Health Scores page — Computed clinical indices from lab results."""

import streamlit as st
from config.organ_scores_data import ORGAN_SYSTEMS, OPTIONAL_ADVANCED_SCORE_CODES
from components.custom_theme import render_hero_banner, render_section_header
from services.organ_score_service import (
    compute_all_scores, get_computable_scores, get_latest_computed_scores,
)
try:
    # Backward-compatible fallback for environments that have not yet loaded
    # the latest organ_score_service symbol set.
    from services.organ_score_service import compute_overall_organ_score
except ImportError:  # pragma: no cover - deploy compatibility guard
    def compute_overall_organ_score(_user_id: int):
        return None

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
    missing_biomarkers = [
        b
        for m in missing_items
        for b in m.get("missing_biomarkers", [])
    ]
    missing_dexa = [b for b in missing_biomarkers if str(b).startswith("dexa_")]
    missing_labs = [b for b in missing_biomarkers if not str(b).startswith("dexa_")]
    missing_clinical = sum(len(m.get("missing_clinical", [])) for m in missing_items)
    if missing_labs:
        actions.append("Log missing lab biomarkers to unlock additional validated scores.")
    if missing_dexa:
        actions.append("Add a DEXA scan with T-score to unlock validated bone-health scoring.")
    if missing_clinical:
        actions.append("Complete your Clinical Profile to improve score completeness and confidence.")

    if not actions:
        actions.append("Maintain current progress and re-check scores with your next lab panel.")
    return actions[:3]


def _split_missing_scores(missing_items: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split missing items into core vs optional advanced scores."""
    core_missing: list[dict] = []
    optional_missing: list[dict] = []
    for item in missing_items:
        code = item.get("definition", {}).get("code")
        if code in OPTIONAL_ADVANCED_SCORE_CODES:
            optional_missing.append(item)
        else:
            core_missing.append(item)
    return core_missing, optional_missing


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
    comp_data = get_computable_scores(user_id)

    existing_codes = {s.get("code") for s in existing_scores}
    computable_codes = {defn["code"] for defn in comp_data.get("computable", [])}
    stale_or_missing = (
        not existing_scores
        or bool(computable_codes - existing_codes)
    )
    if stale_or_missing and not recalculate:
        compute_all_scores(user_id)
        existing_scores = get_latest_computed_scores(user_id)
        comp_data = get_computable_scores(user_id)
    core_missing, optional_missing = _split_missing_scores(comp_data.get("missing", []))
    core_comp_data = dict(comp_data)
    core_comp_data["missing"] = core_missing
    overall = compute_overall_organ_score(user_id)

    if existing_scores:
        high_count = sum(1 for s in existing_scores if s.get("severity") in {"high", "critical"})
        elevated_count = sum(1 for s in existing_scores if s.get("severity") == "elevated")
        missing_count = len(core_missing)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Computed Scores", len(existing_scores))
        m2.metric("High Risk", high_count)
        m3.metric("Elevated", elevated_count)
        m4.metric("Core Missing Inputs", missing_count)

    if overall:
        render_section_header(
            "Overall Organ Composite",
            "Balanced index across organ systems, weighted by evidence tier and data coverage",
        )
        o1, o2, o3, o4 = st.columns(4)
        o1.metric("Overall Organ Score", f"{overall['overall_score_10']}/10")
        o2.metric("Status", overall["overall_label"])
        o3.metric("Confidence", f"{overall['overall_confidence_pct']}%")
        o4.metric("Organs Covered", f"{overall['organs_covered']}/{overall['total_organs']}")

        coverage_value = float(overall.get("organ_coverage_0_1") or 0.0)
        st.progress(max(0.0, min(1.0, coverage_value)))
        st.caption(
            f"Formula coverage: {overall['computed_scores']}/{overall['total_definitions']} "
            f"({overall['score_coverage_pct']}%). "
            f"Validated share: {overall['validated_share_pct']}%. "
            f"Weighting: evidence-first (80%) + prevention emphasis (20%). "
            f"Optional advanced formulas used: {overall.get('optional_scores_used', 0)}. "
            f"Missing organ systems: "
            f"{', '.join(overall['missing_organs']) if overall['missing_organs'] else 'none'}."
        )

        with st.expander("Per-organ composite scores"):
            organ_rows = overall.get("organ_breakdown", [])
            if organ_rows:
                cols = st.columns(min(3, len(organ_rows)))
                for idx, organ_row in enumerate(organ_rows):
                    with cols[idx % len(cols)]:
                        with st.container(border=True):
                            st.markdown(f"**{organ_row['name']}**")
                            st.metric("Score", f"{organ_row['score_10']}/10")
                            st.caption(
                                f"{organ_row['label']} | "
                                f"Coverage {int(round(organ_row['coverage_0_1'] * 100))}% | "
                                f"{organ_row['confidence_label']} confidence"
                            )
            else:
                st.caption("No per-organ composite data available yet.")
        st.divider()

    render_section_header("Patient Action Plan", "Your next best steps from current scores and data completeness")
    for action in _build_organ_action_plan(existing_scores, core_comp_data):
        st.markdown(f"- {action}")
    q1, q2 = st.columns(2)
    with q1:
        if st.button("Open Biomarkers", use_container_width=True, key="organ_open_biomarkers"):
            st.switch_page("pages/biomarkers.py")
    with q2:
        st.caption("Need profile fields? Use the **Clinical Profile** tab above to complete them.")
    st.divider()

    # Complete score map — every definition, with computed value or missing-data flag.
    # Gives the clinician a bird's-eye inventory without having to hunt through organ sections.
    with st.expander("Complete score inventory (all formulas, computed or missing)", expanded=False):
        st.caption(
            "Every defined organ score with its current status. Missing scores are flagged as "
            "data-gaps and are NOT counted as zero in the composite — they only lower coverage."
        )
        inventory_rows = []
        scores_by_code = {s.get("code"): s for s in existing_scores}
        missing_by_code = {m["definition"]["code"]: m for m in comp_data.get("missing", [])}
        for defn in sorted(
            get_all_score_definitions(),
            key=lambda d: (
                ORGAN_SYSTEMS.get(d.get("organ_system"), {}).get("sort_order", 999),
                d.get("sort_order", 0),
            ),
        ):
            code = defn["code"]
            organ_meta = ORGAN_SYSTEMS.get(defn.get("organ_system"), {})
            if code in scores_by_code:
                s = scores_by_code[code]
                status = f"Computed ({s.get('label', '')})"
                value_str = str(s.get("value", ""))
                severity = s.get("severity", "")
            elif code in missing_by_code:
                m = missing_by_code[code]
                gaps = ", ".join(list(m.get("missing_biomarkers", [])) + list(m.get("missing_clinical", [])))
                status = f"Missing data: {gaps or 'required inputs'}"
                value_str = "—"
                severity = ""
            else:
                status = "Not applicable for this patient"
                value_str = "—"
                severity = ""
            inventory_rows.append({
                "Organ": organ_meta.get("name", defn.get("organ_system", "")),
                "Score": defn.get("name"),
                "Tier": defn.get("tier"),
                "Value": value_str,
                "Severity": severity,
                "Status": status,
            })
        st.dataframe(inventory_rows, use_container_width=True, hide_index=True)

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
        for m in core_missing:
            organ = m["definition"]["organ_system"]
            missing_by_organ.setdefault(organ, []).append(m)

        # Organs with at least one core definition get a section even if every
        # score for that organ is missing data, so the clinician always sees
        # (for example) the Musculoskeletal section with a DXA missing-card.
        core_def_organs = {
            d["organ_system"]
            for d in get_all_score_definitions()
            if d.get("code") not in OPTIONAL_ADVANCED_SCORE_CODES
        }

        for organ_code in sorted(
            ORGAN_SYSTEMS.keys(),
            key=lambda o: ORGAN_SYSTEMS[o]["sort_order"]
        ):
            organ_meta = ORGAN_SYSTEMS[organ_code]
            organ_scores = scores_by_organ.get(organ_code, [])
            organ_missing = missing_by_organ.get(organ_code, [])

            if not organ_scores and not organ_missing and organ_code not in core_def_organs:
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

        if optional_missing:
            with st.expander("Optional Advanced Markers (Not Required for Core Readiness)"):
                st.caption(
                    "These formulas can add detail if you track specialized markers "
                    "(e.g., ApoB, GGT, homocysteine), but they do not block core scoring."
                )
                for m in optional_missing:
                    render_missing_score_card(
                        m["definition"],
                        m["missing_biomarkers"],
                        m["missing_clinical"],
                    )

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
    all_definitions = get_all_score_definitions()
    core_definitions = [d for d in all_definitions if d.get("code") not in OPTIONAL_ADVANCED_SCORE_CODES]
    core_missing, optional_missing = _split_missing_scores(comp_data.get("missing", []))
    total_definitions = len(core_definitions)
    missing_count = len(core_missing)
    ready_count = max(0, total_definitions - missing_count)
    if total_definitions > 0:
        st.progress(ready_count / total_definitions)
        st.caption(
            f"Core readiness: {ready_count}/{total_definitions} formulas can be computed "
            f"(optional advanced missing: {len(optional_missing)})."
        )

    if not core_missing:
        st.success("All organ health scores can be computed with your current data!")
    else:
        st.markdown(
            f"**{len(core_missing)}** core score(s) cannot be computed due to missing inputs."
        )

        for m in core_missing:
            defn = m["definition"]
            with st.expander(f"{defn['name']} ({defn['organ_system'].title()})"):
                if m["missing_biomarkers"]:
                    missing_dexa = [b for b in m["missing_biomarkers"] if str(b).startswith("dexa_")]
                    missing_labs = [b for b in m["missing_biomarkers"] if not str(b).startswith("dexa_")]
                    st.markdown("**Missing inputs:**")
                    for b in m["missing_biomarkers"]:
                        st.markdown(f"- `{b}`")
                    if missing_labs:
                        st.page_link("pages/biomarkers.py", label="Go to Biomarkers", icon=":material/bloodtype:")
                    if missing_dexa:
                        st.page_link("pages/body_metrics.py", label="Go to Body Metrics (DEXA)", icon=":material/monitor_weight:")

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

    if optional_missing:
        with st.expander(f"Optional Advanced Missing ({len(optional_missing)})"):
            st.caption(
                "Optional formulas do not reduce core readiness. Add these markers only if clinically useful."
            )
            for m in optional_missing:
                defn = m["definition"]
                with st.expander(f"{defn['name']} ({defn['organ_system'].title()})", expanded=False):
                    if m["missing_biomarkers"]:
                        st.markdown("**Missing lab results:**")
                        for b in m["missing_biomarkers"]:
                            st.markdown(f"- `{b}`")
                    if m["missing_clinical"]:
                        st.markdown("**Missing clinical data:**")
                        for c in m["missing_clinical"]:
                            st.markdown(f"- `{c}`")
