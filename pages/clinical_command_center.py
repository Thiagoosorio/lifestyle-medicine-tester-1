"""Clinical Command Center.

Physician-style first page that summarizes:
- confirmed diagnoses
- confirmed interventions (meds/supplements/lifestyle/training)
- out-of-range labs
- key objective test highlights (DEXA + clinician-entered tests like CPET/Kinemo/Carotid US)
"""

from __future__ import annotations

import json
import streamlit as st

from components.custom_theme import render_hero_banner, render_section_header
from services.clinical_command_service import build_clinical_snapshot
from models.clinical_registry import (
    save_diagnosis,
    update_diagnosis_status,
    save_intervention,
    update_intervention_status,
    save_test_result,
    delete_record,
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

metric_cols = st.columns(5)
metric_cols[0].metric("Active Diagnoses", counts["diagnoses_active"])
metric_cols[1].metric("Active Interventions", counts["interventions_active"])
metric_cols[2].metric("Labs Flagged", counts["labs_flagged"])
metric_cols[3].metric("Labs Critical", counts["labs_critical"])
metric_cols[4].metric("High-Risk Organ Scores", counts["organ_scores_high_risk"])

tab_summary, tab_dx, tab_rx, tab_tests = st.tabs(
    ["Clinical Summary", "Diagnoses", "Interventions", "Tests & Imaging"]
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
            for d in diagnoses:
                st.markdown(
                    f"- **{d.get('diagnosis_name')}** "
                    f"({d.get('status')})"
                    f"{' - ' + d.get('confirmed_date') if d.get('confirmed_date') else ''}"
                )
        else:
            st.info("No active confirmed diagnoses yet.")

    with right:
        render_section_header("Confirmed Interventions", "Medication, supplements, lifestyle, training")
        interventions = snapshot["interventions_active"]
        if interventions:
            for iv in interventions[:12]:
                dose = f" | {iv.get('dose')}" if iv.get("dose") else ""
                sched = f" | {iv.get('schedule')}" if iv.get("schedule") else ""
                st.markdown(
                    f"- **{iv.get('name')}** ({iv.get('intervention_type')}){dose}{sched}"
                )
            if len(interventions) > 12:
                st.caption(f"+{len(interventions) - 12} more interventions")
        else:
            st.info("No active interventions confirmed yet.")

    st.divider()

    render_section_header("Labs Requiring Attention", "Outside normal/target range on latest panel")
    labs = snapshot["labs_attention"]["all"]
    if labs:
        rows = []
        for r in labs:
            rows.append(
                {
                    "Marker": r.get("name"),
                    "Value": f"{r.get('value')} {r.get('unit') or ''}".strip(),
                    "Classification": r.get("classification"),
                    "Standard Range": r.get("standard_range"),
                    "Optimal Range": r.get("optimal_range"),
                    "Date": r.get("lab_date"),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
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

    render_section_header("Key Objective Tests", "DEXA plus confirmed clinician-entered tests (CPET/Kinemo/Carotid)")
    key_tests = snapshot.get("key_tests", [])
    if key_tests:
        st.dataframe(
            _as_rows(key_tests, ["test_type", "test_date", "summary", "risk_flag", "source"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No key objective tests recorded yet.")

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

    all_iv = [x for x in snapshot["interventions_active"] if str(x.get("id", "")).isdigit()]
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
        options = {f"{t['test_type']} ({t.get('test_date') or 'no date'}) [{t.get('status')}]": t["id"] for t in all_tests}
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
