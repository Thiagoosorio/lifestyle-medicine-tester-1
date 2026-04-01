"""Clinical Command Center.

Physician-style first page that summarizes:
- confirmed diagnoses
- confirmed interventions (meds/supplements/lifestyle/training)
- out-of-range labs
- key objective test highlights (DEXA + clinician-entered tests like CPET/Kinemo/Carotid US)
- evidence trace constrained to validated Q1/Q2 or guideline-organization sources
"""

from __future__ import annotations

import json
import streamlit as st

from components.custom_theme import render_hero_banner, render_section_header
from services.clinical_command_service import build_clinical_snapshot
from services.ai_cds_service import (
    build_ai_cds_rollout_plan,
    build_lifestyle_intervention_support,
    get_ai_cds_use_cases,
    get_github_lifestyle_patterns,
    get_institution_emr_benchmarks,
    get_lifestyle_evidence_base,
)
from models.clinical_registry import (
    delete_record,
    save_diagnosis,
    save_intervention,
    save_test_result,
    update_diagnosis_status,
    update_intervention_status,
)


def _fmt(v, fallback="N/A"):
    return fallback if v is None or v == "" else str(v)


def _iso_or_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _as_rows(items: list[dict], columns: list[str]) -> list[dict]:
    rows = []
    for item in items:
        row = {}
        for col in columns:
            row[col] = item.get(col)
        rows.append(row)
    return rows


def _lab_rows(labs: list[dict]) -> list[dict]:
    rows = []
    for row in labs:
        rows.append(
            {
                "Marker": row.get("name"),
                "Value": f"{row.get('value')} {row.get('unit') or ''}".strip(),
                "Classification": row.get("classification"),
                "Standard Range": row.get("standard_range"),
                "Date": row.get("lab_date"),
            }
        )
    return rows


def _critical_policy_rows(plan: dict) -> list[dict]:
    rows = []
    for row in plan.get("alerts", []):
        rows.append(
            {
                "Marker": row.get("name"),
                "Value": f"{row.get('value')} {row.get('unit') or ''}".strip(),
                "Classification": row.get("classification"),
                "Critical Threshold": row.get("critical_threshold"),
                "Notify <= (min)": row.get("notify_within_minutes"),
                "Escalate after (min)": row.get("escalate_after_minutes"),
                "Urgency": row.get("urgency_level"),
                "Recommended Action": row.get("recommended_action"),
            }
        )
    return rows


def _render_critical_policy_block(snapshot: dict) -> None:
    plan = snapshot.get("critical_lab_communication") or {}
    if not plan.get("has_critical"):
        return

    policy = plan.get("policy") or {}
    st.error(
        "Critical lab values detected. Follow urgent communication workflow and clinician escalation."
    )

    rows = _critical_policy_rows(plan)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander("Critical Communication Policy (Evidence-backed)", expanded=False):
        for step in policy.get("workflow_steps", []):
            st.markdown(f"- {step}")
        st.caption(
            f"Read-back required: {policy.get('read_back_required')} | "
            f"Documentation required: {policy.get('documentation_required')}"
        )
        sources = policy.get("evidence_sources", [])
        if sources:
            st.markdown("**Sources**")
            for src in sources:
                title = src.get("title", "Source")
                year = src.get("year", "n/a")
                st.markdown(f"- {title} ({year}) - {src.get('link')}")


def _render_kpi_detail_panel(snapshot: dict) -> None:
    focus = st.session_state.get("cc_focus", "diagnoses")
    render_section_header(
        "KPI Detail View",
        "Click any KPI card button above to open its details here.",
    )

    if focus == "diagnoses":
        rows = _as_rows(
            snapshot.get("diagnoses_active", []),
            ["diagnosis_name", "status", "confirmed_date", "confirming_clinician", "source"],
        )
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No active diagnoses.")
        return

    if focus == "interventions":
        rows = _as_rows(
            snapshot.get("interventions_active", []),
            ["intervention_type", "name", "dose", "schedule", "status", "start_date"],
        )
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No active interventions.")
        return

    if focus == "labs_flagged":
        rows = _lab_rows(snapshot.get("labs_attention", {}).get("all", []))
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.success("No flagged labs.")
        return

    if focus == "labs_critical":
        rows = _lab_rows(snapshot.get("labs_attention", {}).get("critical", []))
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
            _render_critical_policy_block(snapshot)
        else:
            st.success("No critical labs.")
        return

    rows = _as_rows(
        snapshot.get("organ_high_risk_scores", []),
        ["name", "organ_system", "value", "label", "severity", "lab_date"],
    )
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.success("No high-risk organ scores.")


def _render_five_domain_cards(snapshot: dict) -> None:
    render_section_header(
        "5-Domain Organ Representation",
        "Heart & Metabolism, Muscle & Bones, Gut & Digestion, Brain Health, and System Wide.",
    )
    rows = snapshot.get("organ_domain_categories", [])
    if not rows:
        st.info("No domain-level organ representation available yet.")
        return

    for offset in range(0, len(rows), 3):
        cols = st.columns(3)
        chunk = rows[offset : offset + 3]
        for idx, row in enumerate(chunk):
            with cols[idx]:
                with st.container(border=True):
                    value = f"{row.get('score_10')}/10" if row.get("score_10") is not None else "N/A"
                    st.metric(row.get("domain_name"), value)
                    st.caption(
                        f"Coverage: {row.get('coverage_pct', 0)}% | "
                        f"Confidence: {row.get('confidence_pct', 0)}% | "
                        f"Elevated+: {row.get('elevated_or_worse', 0)}"
                    )
                    covered = row.get("systems_covered") or []
                    if covered:
                        st.caption("Covered systems: " + ", ".join(covered))
                    if row.get("note"):
                        st.caption(row["note"])


def _render_ai_cds_tab(snapshot: dict) -> None:
    render_section_header(
        "Lifestyle Intervention Support (AI + Evidence)",
        "Lifestyle-medicine focused support only: no emergency workflows.",
    )
    rollout = build_ai_cds_rollout_plan(snapshot)
    readiness = rollout.get("readiness_score_100", 0)
    m1, m2, m3 = st.columns(3)
    m1.metric("AI CDS Readiness", f"{readiness}/100")
    m2.metric("Readiness Label", rollout.get("readiness_label", "N/A"))
    m3.metric("Modules Planned", len(rollout.get("modules", [])))

    st.caption(
        "Design principle: prevention-first and evidence-first. AI supports decisions, but clinician review remains mandatory."
    )

    st.divider()
    render_section_header(
        "Next-Best Lifestyle Interventions",
        "Domain-based recommendations generated from current profile, labs, organ scores, and wearables.",
    )
    support_cards = build_lifestyle_intervention_support(snapshot)
    evidence_by_topic = {row.get("topic"): row for row in get_lifestyle_evidence_base()}

    for card in support_cards:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{card.get('domain')}**")
            c2.caption(f"Priority: {card.get('priority')}")
            st.caption(f"Trigger: {card.get('trigger')}")
            st.markdown(f"**Recommendation:** {card.get('recommendation')}")
            st.caption(f"Success metric: {card.get('success_metric')}")

            topics = card.get("evidence_topics") or []
            if topics:
                st.markdown("**Evidence links**")
                for topic in topics:
                    ev = evidence_by_topic.get(topic)
                    if not ev:
                        st.markdown(f"- {topic} - source pending")
                        continue
                    label = (
                        f"{ev.get('evidence')} ({ev.get('source_type')}, {ev.get('year')})"
                    )
                    st.markdown(f"- {label}")
                    st.link_button(
                        f"Open source: {ev.get('topic')}",
                        ev.get("link"),
                        use_container_width=True,
                    )

    st.divider()
    for module in rollout.get("modules", []):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 2])
            c1.markdown(f"**{module.get('module')}**")
            c2.caption(f"Priority: {module.get('priority')}")
            c3.caption(f"Status: {module.get('status')}")
            st.caption(f"Why now: {module.get('why_now')}")
            st.caption(f"Safety model: {module.get('safety_model')}")
            st.caption(f"Evidence anchor: {module.get('evidence_anchor')}")

    st.divider()
    render_section_header("Institution EMR Benchmarks", "Harvard-affiliated and peer institutions")
    benchmark_rows = get_institution_emr_benchmarks()
    if benchmark_rows:
        for row in benchmark_rows:
            with st.container(border=True):
                st.markdown(f"**{row.get('institution')}**")
                st.caption(f"EMR platform: {row.get('emr_platform')}")
                st.caption(row.get("what_they_built"))
                st.caption(f"Source: {row.get('source_title')} ({row.get('source_type')}, {row.get('year')})")
                st.link_button("Open source", row.get("link"), use_container_width=False)
    else:
        st.info("No institution benchmarks available yet.")

    st.divider()
    render_section_header("Validated AI CDS Use Cases", "Only evidence-backed patterns are listed")
    use_cases = get_ai_cds_use_cases()
    if use_cases:
        for item in use_cases:
            with st.expander(f"{item.get('use_case')} ({item.get('evidence_level')})", expanded=False):
                st.markdown(f"**Institution examples:** {item.get('institution_examples')}")
                st.markdown(f"**Impact:** {item.get('impact_summary')}")
                st.markdown(f"**Study type:** {item.get('study_type')} ({item.get('year')})")
                st.markdown(f"**Citation:** {item.get('citation')}")
                if item.get("pmid"):
                    st.markdown(f"**PMID:** {item.get('pmid')}")
                if item.get("doi"):
                    st.markdown(f"**DOI:** {item.get('doi')}")
                st.link_button("Open source", item.get("link"), use_container_width=True)
                st.markdown(f"**How to use in this app:** {item.get('app_pattern')}")
                st.markdown(f"**Current app status:** {item.get('status_in_app')}")
    else:
        st.info("No AI CDS use cases available yet.")

    st.divider()
    render_section_header("GitHub Patterns We Can Reuse", "Open-source building blocks for lifestyle CDS")
    patterns = get_github_lifestyle_patterns()
    if patterns:
        for row in patterns:
            with st.container(border=True):
                st.markdown(f"**{row.get('name')}**")
                st.caption(row.get("why_relevant"))
                st.caption(f"Adopt next: {row.get('adopt_next')}")
                st.link_button("Open GitHub repo", row.get("repo"), use_container_width=False)
    else:
        st.info("No GitHub patterns configured yet.")

    with st.expander("Safety & Governance Rules", expanded=False):
        for rule in rollout.get("governance_rules", []):
            st.markdown(f"- {rule}")
        for phase in rollout.get("phases", []):
            st.markdown(f"- {phase}")


user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in first.")
    st.stop()

render_hero_banner(
    "Clinical Command Center",
    "Confirmed diagnostics, interventions, key tests, and risk flags in one medical summary view.",
)

snapshot = build_clinical_snapshot(user_id)
counts = snapshot["counts"]

if "cc_focus" not in st.session_state:
    st.session_state["cc_focus"] = "diagnoses"

metric_defs = [
    ("Active Diagnoses", counts["diagnoses_active"], "diagnoses"),
    ("Active Interventions", counts["interventions_active"], "interventions"),
    ("Labs Flagged", counts["labs_flagged"], "labs_flagged"),
    ("Labs Critical", counts["labs_critical"], "labs_critical"),
    ("High-Risk Organ Scores", counts["organ_scores_high_risk"], "high_risk_scores"),
]

metric_cols = st.columns(5)
for idx, (label, value, focus_key) in enumerate(metric_defs):
    with metric_cols[idx]:
        st.metric(label, value)
        if st.button("Open details", key=f"cc_focus_{focus_key}", use_container_width=True):
            st.session_state["cc_focus"] = focus_key

_render_kpi_detail_panel(snapshot)
st.divider()

(
    tab_summary,
    tab_priority,
    tab_timeline,
    tab_evidence,
    tab_lifestyle_ai,
    tab_dx,
    tab_rx,
    tab_tests,
) = st.tabs(
    [
        "Clinical Summary",
        "Priority List",
        "Timeline",
        "Evidence Trace",
        "Lifestyle AI Support",
        "Diagnoses",
        "Interventions",
        "Tests & Imaging",
    ]
)

with tab_summary:
    render_section_header(
        "Patient Snapshot",
        "Auto-generated from confirmed structured records and latest measurements.",
    )
    patient = snapshot["patient"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Patient", _fmt(patient.get("display_name")))
    c2.metric("Age / Sex", f"{_fmt(patient.get('age'))} / {_fmt(patient.get('sex'))}")
    c3.metric("BMI", _fmt(patient.get("bmi")))
    c4.metric(
        "Blood Pressure",
        f"{_fmt(patient.get('systolic_bp'))}/{_fmt(patient.get('diastolic_bp'))} mmHg",
    )
    st.caption(
        f"Smoking: {_fmt(patient.get('smoking_status'))} | "
        f"Diabetes flag: {_fmt(patient.get('diabetes_status'))} | "
        f"Weight: {_fmt(patient.get('weight_kg'))} kg"
    )

    left, right = st.columns(2)
    with left:
        render_section_header("Confirmed Diagnoses", "Active problem list")
        diagnoses = snapshot["diagnoses_active"]
        if diagnoses:
            for diagnosis in diagnoses:
                st.markdown(
                    f"- **{diagnosis.get('diagnosis_name')}** "
                    f"({diagnosis.get('status')})"
                    f"{' - ' + diagnosis.get('confirmed_date') if diagnosis.get('confirmed_date') else ''}"
                )
        else:
            st.info("No active confirmed diagnoses yet.")

    with right:
        render_section_header("Confirmed Interventions", "Medication, supplements, lifestyle, training")
        interventions = snapshot["interventions_active"]
        if interventions:
            for intervention in interventions[:12]:
                dose = f" | {intervention.get('dose')}" if intervention.get("dose") else ""
                schedule = f" | {intervention.get('schedule')}" if intervention.get("schedule") else ""
                st.markdown(
                    f"- **{intervention.get('name')}** "
                    f"({intervention.get('intervention_type')}){dose}{schedule}"
                )
            if len(interventions) > 12:
                st.caption(f"+{len(interventions) - 12} more interventions")
        else:
            st.info("No active interventions confirmed yet.")

    st.divider()
    render_section_header("Labs Requiring Attention", "Outside lab reference interval on latest panel")
    labs = snapshot["labs_attention"]["all"]
    if labs:
        st.dataframe(_lab_rows(labs), use_container_width=True, hide_index=True)
        _render_critical_policy_block(snapshot)
    else:
        st.success("No out-of-range labs detected from latest results.")

    st.divider()
    organ_overall = snapshot.get("organ_overall")
    wearable = snapshot.get("wearable")
    col_o, col_w = st.columns(2)
    with col_o:
        render_section_header("Organ Composite", "Risk summary from validated organ formulas")
        if organ_overall:
            st.metric("Overall Organ Score", f"{organ_overall['overall_score_10']}/10")
            st.caption(
                f"Status: {organ_overall['overall_label']} | "
                f"Confidence: {organ_overall['overall_confidence_pct']}% | "
                f"Coverage: {organ_overall['score_coverage_pct']}%"
            )
        else:
            st.info("No organ composite available yet.")

    with col_w:
        render_section_header("Wearable Snapshot", "Readiness and resilience from wearable data")
        if wearable:
            st.metric("Overall Wearable Score", f"{wearable.get('overall_score_10', 0)}/10")
            st.caption(
                f"Readiness: {wearable.get('overall_readiness_10', 0)}/10 | "
                f"Resilience: {wearable.get('overall_resilience_10', 0)}/10"
            )
        else:
            st.info("No wearable summary available yet.")

    st.divider()
    _render_five_domain_cards(snapshot)

    st.divider()
    render_section_header(
        "Key Objective Tests",
        "DEXA plus confirmed clinician-entered tests (CPET/Kinemo/Carotid).",
    )
    key_tests = snapshot.get("key_tests", [])
    if key_tests:
        st.dataframe(
            _as_rows(key_tests, ["test_type", "test_date", "summary", "risk_flag", "source"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No key objective tests recorded yet.")

with tab_priority:
    render_section_header(
        "Priority Problem List",
        "Prevention-first ordering with recommended action windows.",
    )
    problems = snapshot.get("priority_problem_list", [])
    if problems:
        st.dataframe(
            _as_rows(
                problems,
                [
                    "priority_rank",
                    "problem_type",
                    "problem",
                    "severity",
                    "recommended_action",
                    "due_in_days",
                    "target_date",
                    "evidence_source",
                ],
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No active priority problems detected.")

with tab_timeline:
    render_section_header(
        "Clinical Timeline",
        "Chronological events from diagnoses, interventions, labs, tests, and score recomputations.",
    )
    timeline = snapshot.get("timeline", [])
    if timeline:
        types = sorted({row.get("event_type") for row in timeline if row.get("event_type")})
        selected_type = st.selectbox(
            "Filter event type",
            ["All"] + types,
            index=0,
            key="cc_timeline_filter",
        )
        limit = st.slider("Rows", min_value=10, max_value=120, value=40, step=5, key="cc_timeline_limit")
        filtered = timeline
        if selected_type != "All":
            filtered = [row for row in timeline if row.get("event_type") == selected_type]
        st.dataframe(
            _as_rows(
                filtered[:limit],
                ["date_time", "event_type", "title", "details", "severity", "source"],
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No timeline events yet.")

with tab_evidence:
    render_section_header(
        "Evidence Trace",
        "Only validated scores with PMID and Q1/Q2 tags or major-organization/guideline support are shown.",
    )
    trace = snapshot.get("evidence_trace", {})
    trace_counts = trace.get("counts", {})
    m1, m2, m3 = st.columns(3)
    m1.metric("Allowed Sources", trace_counts.get("allowed", 0))
    m2.metric("Excluded Sources", trace_counts.get("excluded", 0))
    m3.metric("Unique Scores Checked", trace_counts.get("total_unique_scores", 0))
    st.info(trace.get("policy", "Evidence policy unavailable."))

    allowed = trace.get("allowed_sources", [])
    if allowed:
        for row in allowed:
            st.markdown(
                f"- **{row.get('score_name')}** ({row.get('source_class')}) | "
                f"[PMID {row.get('pmid')}]({row.get('pubmed_url')})"
            )
    else:
        st.warning("No score sources passed the strict evidence gate yet.")

    excluded = trace.get("excluded_sources", [])
    if excluded:
        with st.expander("Excluded / Not Yet Eligible Sources", expanded=False):
            st.dataframe(
                _as_rows(excluded, ["score_name", "tier", "source_class", "reason"]),
                use_container_width=True,
                hide_index=True,
            )

with tab_lifestyle_ai:
    _render_ai_cds_tab(snapshot)

with tab_dx:
    render_section_header("Confirmed Diagnoses", "Maintain active/resolved diagnosis list")
    with st.form("dx_add_form", clear_on_submit=True):
        dx_name = st.text_input("Diagnosis name")
        dx_status = st.selectbox("Status", ["active", "resolved", "ruled_out"], index=0)
        dx_date = st.text_input("Confirmed date (YYYY-MM-DD)")
        dx_clinician = st.text_input("Confirming clinician")
        dx_source = st.text_input("Source")
        dx_notes = st.text_area("Notes", height=90)
        submitted_dx = st.form_submit_button("Add / Update Diagnosis", use_container_width=True, type="primary")
        if submitted_dx:
            save_diagnosis(
                user_id=user_id,
                diagnosis_name=dx_name,
                status=dx_status,
                confirmed_date=_iso_or_none(dx_date),
                confirming_clinician=dx_clinician,
                source=dx_source,
                notes=dx_notes,
            )
            st.success("Diagnosis saved.")
            st.rerun()

    dx_all = snapshot["diagnoses_all"]
    if dx_all:
        st.dataframe(
            _as_rows(dx_all, ["id", "diagnosis_name", "status", "confirmed_date", "confirming_clinician", "source"]),
            use_container_width=True,
            hide_index=True,
        )
        options = {f"{d['diagnosis_name']} [{d['status']}]": d["id"] for d in dx_all}
        pick = st.selectbox("Select diagnosis record", list(options.keys()), key="dx_pick")
        new_status = st.selectbox("Set status", ["active", "resolved", "ruled_out"], key="dx_new_status")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Update Status", use_container_width=True):
                update_diagnosis_status(user_id, options[pick], new_status)
                st.success("Diagnosis status updated.")
                st.rerun()
        with c2:
            if st.button("Delete Record", use_container_width=True):
                delete_record(user_id, "clinical_diagnoses", options[pick])
                st.success("Diagnosis deleted.")
                st.rerun()
    else:
        st.info("No diagnosis records yet.")

with tab_rx:
    render_section_header("Confirmed Interventions", "Medication, supplement, lifestyle, training, other")
    with st.form("iv_add_form", clear_on_submit=True):
        iv_type = st.selectbox("Intervention type", ["medication", "supplement", "lifestyle", "training", "other"])
        iv_name = st.text_input("Name")
        iv_dose = st.text_input("Dose / intensity")
        iv_schedule = st.text_input("Schedule")
        iv_start = st.text_input("Start date (YYYY-MM-DD)")
        iv_end = st.text_input("End date (YYYY-MM-DD)")
        iv_status = st.selectbox("Status", ["active", "paused", "completed", "stopped"], index=0)
        iv_prescriber = st.text_input("Prescriber")
        iv_notes = st.text_area("Notes", height=90)
        submitted_iv = st.form_submit_button("Add Intervention", use_container_width=True, type="primary")
        if submitted_iv:
            save_intervention(
                user_id=user_id,
                intervention_type=iv_type,
                name=iv_name,
                dose=iv_dose,
                schedule=iv_schedule,
                start_date=_iso_or_none(iv_start),
                end_date=_iso_or_none(iv_end),
                status=iv_status,
                prescriber=iv_prescriber,
                notes=iv_notes,
            )
            st.success("Intervention saved.")
            st.rerun()

    all_iv = [x for x in snapshot["interventions_all"] if str(x.get("id", "")).isdigit()]
    if all_iv:
        st.dataframe(
            _as_rows(all_iv, ["id", "intervention_type", "name", "dose", "schedule", "status", "start_date", "end_date"]),
            use_container_width=True,
            hide_index=True,
        )
        options = {f"{i['name']} ({i['intervention_type']}) [{i['status']}]": i["id"] for i in all_iv}
        pick = st.selectbox("Select intervention record", list(options.keys()), key="iv_pick")
        new_status = st.selectbox("Set status", ["active", "paused", "completed", "stopped"], key="iv_new_status")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Update Intervention Status", use_container_width=True):
                update_intervention_status(user_id, options[pick], new_status)
                st.success("Intervention status updated.")
                st.rerun()
        with c2:
            if st.button("Delete Intervention", use_container_width=True):
                delete_record(user_id, "clinical_interventions", options[pick])
                st.success("Intervention deleted.")
                st.rerun()
    else:
        st.info("No intervention records yet.")

with tab_tests:
    render_section_header("Tests & Imaging", "CPET, Kinemo, Carotid ultrasound, DEXA, and other results")
    with st.form("test_add_form", clear_on_submit=True):
        test_type = st.selectbox(
            "Test type",
            ["CPET", "Kinemo", "Carotid Ultrasound", "DEXA", "Lab Panel", "Other"],
        )
        test_date = st.text_input("Test date (YYYY-MM-DD)")
        test_status = st.selectbox("Status", ["confirmed", "pending", "excluded"], index=0)
        test_risk = st.selectbox("Risk flag", ["unknown", "low", "moderate", "high", "critical"], index=0)
        test_summary = st.text_area("Summary findings", height=120)
        test_metrics_text = st.text_area(
            "Key metrics (JSON, optional)",
            placeholder='{"vo2max_ml_kg_min": 38.2, "anaerobic_threshold_watts": 210}',
            height=90,
        )
        test_source = st.text_input("Source reference")
        submit_test = st.form_submit_button("Add Test Result", use_container_width=True, type="primary")
        if submit_test:
            key_metrics = {}
            if test_metrics_text.strip():
                try:
                    key_metrics = json.loads(test_metrics_text)
                    if not isinstance(key_metrics, dict):
                        raise ValueError("Metrics JSON must be an object.")
                except Exception as exc:
                    st.error(f"Invalid key metrics JSON: {exc}")
                    st.stop()

            save_test_result(
                user_id=user_id,
                test_type=test_type,
                test_date=_iso_or_none(test_date),
                status=test_status,
                summary=test_summary,
                key_metrics=key_metrics,
                source_ref=test_source,
                risk_flag=test_risk,
            )
            st.success("Test result saved.")
            st.rerun()

    all_tests = snapshot["test_results"]
    if all_tests:
        st.dataframe(
            _as_rows(all_tests, ["id", "test_type", "test_date", "status", "risk_flag", "summary", "source_ref"]),
            use_container_width=True,
            hide_index=True,
        )
        options = {
            f"{t['test_type']} ({t.get('test_date') or 'no date'}) [{t.get('status')}]": t["id"]
            for t in all_tests
        }
        pick = st.selectbox("Select test record", list(options.keys()), key="test_pick")
        if st.button("Delete Test Record", use_container_width=True):
            delete_record(user_id, "clinical_test_results", options[pick])
            st.success("Test record deleted.")
            st.rerun()
    else:
        st.info("No clinician-entered test records yet.")

st.caption(
    "Clinical Command Center summarizes structured records and computed screening scores. "
    "It supports clinical reasoning but does not replace physician diagnosis or treatment decisions."
)
