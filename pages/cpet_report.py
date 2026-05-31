"""Coach-facing CPET upload and interpretation page."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.custom_theme import APPLE, render_hero_banner, render_section_header
from services.cpet_service import (
    CPET_CONTEXTS,
    CPET_METRIC_SPECS,
    NINE_PANEL_ROWS,
    build_cpet_coach_summary,
    delete_cpet_report,
    extract_cpet_from_pdf,
    extract_cpet_from_text,
    get_cpet_reports,
    save_cpet_report,
)


A = APPLE
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in first.")
    st.stop()


FIELD_LAYOUT = [
    ("age_years", "Age (years)", 10.0, 100.0, 1.0, "%.0f"),
    ("weight_kg", "Weight (kg)", 25.0, 250.0, 0.1, "%.1f"),
    ("test_duration_min", "Incremental duration (min)", 2.0, 40.0, 0.1, "%.1f"),
    ("peak_vo2_ml_kg_min", "Peak VO2 (mL/kg/min)", 5.0, 100.0, 0.1, "%.1f"),
    ("peak_vo2_l_min", "Peak VO2 absolute (L/min)", 0.5, 9.0, 0.01, "%.2f"),
    ("peak_vo2_pct_pred", "Peak VO2 % predicted", 10.0, 250.0, 1.0, "%.0f"),
    ("peak_rer", "Peak RER", 0.6, 1.6, 0.01, "%.2f"),
    ("rest_hr_bpm", "Resting HR (bpm)", 25.0, 140.0, 1.0, "%.0f"),
    ("peak_hr_bpm", "Peak HR (bpm)", 60.0, 230.0, 1.0, "%.0f"),
    ("predicted_hr_bpm", "Predicted HR (bpm)", 80.0, 230.0, 1.0, "%.0f"),
    ("hr_pct_pred", "Peak HR % predicted", 30.0, 130.0, 1.0, "%.0f"),
    ("vt1_vo2_ml_kg_min", "VT1 VO2 (mL/kg/min)", 3.0, 90.0, 0.1, "%.1f"),
    ("vt1_hr_bpm", "VT1 HR (bpm)", 50.0, 220.0, 1.0, "%.0f"),
    ("vt1_power_w", "VT1 power (W)", 20.0, 700.0, 1.0, "%.0f"),
    ("vt1_speed_kmh", "VT1 speed (km/h)", 3.0, 30.0, 0.1, "%.1f"),
    ("vt2_vo2_ml_kg_min", "VT2 VO2 (mL/kg/min)", 5.0, 95.0, 0.1, "%.1f"),
    ("vt2_hr_bpm", "VT2 HR (bpm)", 60.0, 230.0, 1.0, "%.0f"),
    ("vt2_power_w", "VT2 power (W)", 30.0, 800.0, 1.0, "%.0f"),
    ("vt2_speed_kmh", "VT2 speed (km/h)", 4.0, 35.0, 0.1, "%.1f"),
    ("ve_vco2_slope", "VE/VCO2 slope", 10.0, 80.0, 0.1, "%.1f"),
    ("ve_vco2_nadir", "VE/VCO2 nadir", 10.0, 80.0, 0.1, "%.1f"),
    ("breathing_reserve_pct", "Breathing reserve (%)", -20.0, 80.0, 1.0, "%.0f"),
    ("peak_ve_l_min", "Peak VE (L/min)", 10.0, 300.0, 1.0, "%.0f"),
    ("mvv_l_min", "MVV (L/min)", 20.0, 300.0, 1.0, "%.0f"),
    ("o2_pulse_ml_beat", "O2 pulse (mL/beat)", 2.0, 40.0, 0.1, "%.1f"),
    ("o2_pulse_pct_pred", "O2 pulse % predicted", 20.0, 200.0, 1.0, "%.0f"),
    ("vo2_wr_slope_ml_min_w", "VO2/WR slope (mL/min/W)", 3.0, 20.0, 0.1, "%.1f"),
    ("petco2_at_mmhg", "PETCO2 at AT (mmHg)", 10.0, 60.0, 1.0, "%.0f"),
    ("petco2_peak_mmhg", "Peak PETCO2 (mmHg)", 10.0, 60.0, 1.0, "%.0f"),
    ("spo2_nadir_pct", "SpO2 nadir (%)", 50.0, 100.0, 1.0, "%.0f"),
    ("oues", "OUES", 0.2, 8.0, 0.1, "%.1f"),
    ("peak_lactate_mmol_l", "Peak lactate (mmol/L)", 0.5, 25.0, 0.1, "%.1f"),
    ("fatmax_g_min", "Max fat oxidation (g/min)", 0.01, 2.5, 0.01, "%.2f"),
    ("fatmax_vo2_pct", "FatMax intensity (% VO2max)", 20.0, 90.0, 1.0, "%.0f"),
]


def _as_number(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date_from_state(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _format_value(field: str, value) -> str:
    numeric = _as_number(value)
    if numeric is None:
        return "--"
    unit = CPET_METRIC_SPECS.get(field, {}).get("unit", "")
    if field == "peak_rer":
        return f"{numeric:.2f}"
    if unit == "%":
        return f"{numeric:.0f}%"
    if unit:
        return f"{numeric:g} {unit}"
    return f"{numeric:g}"


def _collect_report_form(initial: dict, prefix: str) -> tuple[date, str, str, str, dict, str]:
    metrics = initial.get("metrics", {})
    default_date = _date_from_state(initial.get("test_date"))

    top_cols = st.columns(4)
    with top_cols[0]:
        test_date = st.date_input("Test date", value=default_date, key=f"{prefix}_date")
    with top_cols[1]:
        context_keys = list(CPET_CONTEXTS.keys())
        current_context = initial.get("client_context") or "general"
        if current_context not in context_keys:
            current_context = "general"
        client_context = st.selectbox(
            "Interpretation context",
            context_keys,
            index=context_keys.index(current_context),
            format_func=lambda key: CPET_CONTEXTS[key],
            key=f"{prefix}_context",
        )
    with top_cols[2]:
        test_modality = st.text_input(
            "Modality",
            value=initial.get("test_modality") or "",
            placeholder="treadmill, cycle ergometer...",
            key=f"{prefix}_modality",
        )
    with top_cols[3]:
        protocol = st.text_input(
            "Protocol",
            value=initial.get("protocol") or "",
            placeholder="ramp, Bruce, bike ramp...",
            key=f"{prefix}_protocol",
        )

    entered: dict[str, float] = {}
    for row_start in range(0, len(FIELD_LAYOUT), 3):
        cols = st.columns(3)
        for idx, spec in enumerate(FIELD_LAYOUT[row_start:row_start + 3]):
            field, label, min_value, max_value, step, fmt = spec
            with cols[idx]:
                value = st.number_input(
                    label,
                    min_value=min_value,
                    max_value=max_value,
                    value=_as_number(metrics.get(field)),
                    step=step,
                    format=fmt,
                    key=f"{prefix}_{field}",
                )
                if value is not None:
                    entered[field] = value

    notes = st.text_area(
        "Coach notes",
        value=initial.get("notes") or "",
        placeholder="Symptoms, medications, beta-blocker timing, test quality, training block, athlete goal...",
        height=90,
        key=f"{prefix}_notes",
    )
    return test_date, client_context, test_modality, protocol, entered, notes


def _render_metric_strip(metrics: dict) -> None:
    cols = st.columns(7)
    items = [
        ("peak_vo2_ml_kg_min", "Peak VO2"),
        ("peak_vo2_pct_pred", "% Pred"),
        ("peak_rer", "RER"),
        ("vt1_hr_bpm", "VT1 HR"),
        ("vt2_hr_bpm", "VT2 HR"),
        ("ve_vco2_slope", "VE/VCO2"),
        ("breathing_reserve_pct", "BR"),
    ]
    for col, (field, label) in zip(cols, items):
        with col:
            st.metric(label, _format_value(field, metrics.get(field)))


def _render_summary(metrics: dict, context: str, previous_metrics: dict | None = None) -> None:
    summary = build_cpet_coach_summary(metrics, client_context=context, previous_metrics=previous_metrics)

    validity = summary["validity_gate"]
    if validity:
        st.markdown("**Validity gate**")
        st.dataframe(pd.DataFrame(validity), use_container_width=True, hide_index=True)

    if summary["zone_rows"]:
        st.markdown("**Measured threshold zones**")
        st.dataframe(pd.DataFrame(summary["zone_rows"]), use_container_width=True, hide_index=True)
    else:
        st.warning("Threshold anchors are incomplete. Avoid building zones only from fixed %HRmax.")

    if summary["trust_rows"]:
        st.markdown("**Measurement hierarchy**")
        st.dataframe(pd.DataFrame(summary["trust_rows"]), use_container_width=True, hide_index=True)
    else:
        st.info("No CPET metrics entered yet. Upload a readable report or enter the key values manually.")

    if summary["coach_flags"]:
        st.markdown("**Coach review flags**")
        st.dataframe(pd.DataFrame(summary["coach_flags"]), use_container_width=True, hide_index=True)

    if summary["trend_notes"]:
        st.markdown("**Trend notes versus prior CPET**")
        for note in summary["trend_notes"]:
            st.markdown(f"- {note}")

    st.markdown("**Coach talking points**")
    for point in summary["talking_points"]:
        st.markdown(f"- {point}")


def _render_history_chart(reports: list[dict]) -> None:
    rows = []
    for report in reports:
        metrics = report["metrics"]
        rows.append(
            {
                "test_date": report["test_date"],
                "Peak VO2": metrics.get("peak_vo2_ml_kg_min"),
                "VT1 HR": metrics.get("vt1_hr_bpm"),
                "VT2 HR": metrics.get("vt2_hr_bpm"),
                "VE/VCO2": metrics.get("ve_vco2_slope"),
                "RER": metrics.get("peak_rer"),
            }
        )
    df = pd.DataFrame(rows)
    if len(df) < 2:
        return
    df["test_date"] = pd.to_datetime(df["test_date"])
    df = df.sort_values("test_date")
    fig = go.Figure()
    for column in ["Peak VO2", "VT1 HR", "VT2 HR", "VE/VCO2", "RER"]:
        if df[column].notna().any():
            fig.add_trace(go.Scatter(x=df["test_date"], y=df[column], mode="lines+markers", name=column))
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor=A["chart_bg"],
        plot_bgcolor=A["chart_bg"],
        font=dict(color=A["chart_text"]),
        hovermode="x unified",
        yaxis=dict(showgrid=True, gridcolor=A["chart_grid"]),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_saved_report(report: dict, previous: dict | None = None) -> None:
    metrics = report["metrics"]
    context = report.get("client_context") or "general"
    title = f"{report['test_date']} - {CPET_CONTEXTS.get(context, context)}"
    with st.expander(title, expanded=False):
        _render_metric_strip(metrics)
        st.caption(
            "Modality: "
            + (report.get("test_modality") or "not recorded")
            + " | Protocol: "
            + (report.get("protocol") or "not recorded")
        )
        st.divider()
        _render_summary(metrics, context, previous_metrics=previous["metrics"] if previous else None)
        if report.get("notes"):
            st.markdown("**Coach notes**")
            st.write(report["notes"])
        if st.button("Delete CPET report", key=f"delete_cpet_{report['id']}", type="secondary"):
            delete_cpet_report(user_id, report["id"])
            st.toast("CPET report deleted.")
            st.rerun()


render_hero_banner(
    "CPET Coach",
    "Upload a cardiopulmonary exercise test, extract the key numbers, and turn the result into coach-friendly action.",
)

st.warning(
    "CPET interpretation can reveal cardiac, pulmonary, vascular, or metabolic limitation. This page supports coaching "
    "and education only; diagnosis, clearance, and abnormal-pattern interpretation belong with the supervising clinician."
)

reports = get_cpet_reports(user_id)
latest = reports[0] if reports else None

if latest:
    _render_metric_strip(latest["metrics"])

tab_upload, tab_saved, tab_guide, tab_panels = st.tabs(
    ["Upload & Explain", "Saved Reports", "Coach Guide", "Nine-Panel Guide"]
)

with tab_upload:
    render_section_header("Upload CPET Report", "PDF extraction first, then coach review and save")
    uploaded = st.file_uploader("Upload a CPET PDF or text export", type=["pdf", "txt"], key="cpet_upload")

    if uploaded and st.button("Extract CPET Report", type="primary", use_container_width=True):
        with st.spinner("Reading CPET report..."):
            try:
                payload = uploaded.getvalue()
                if uploaded.name.lower().endswith(".pdf"):
                    extracted = extract_cpet_from_pdf(payload)
                else:
                    raw_text = payload.decode("utf-8", errors="ignore")
                    extracted = extract_cpet_from_text(raw_text)
                    extracted["raw_text"] = raw_text
                extracted["source_filename"] = uploaded.name
                st.session_state["cpet_extracted"] = extracted
                st.rerun()
            except Exception as exc:
                st.error(f"CPET extraction failed: {exc}")

    if "cpet_extracted" in st.session_state:
        extracted = st.session_state["cpet_extracted"]
        warnings = extracted.get("extraction_warnings") or []
        if warnings:
            for warning in warnings:
                st.warning(warning)

        st.markdown("### Review extracted values")
        _render_summary(extracted.get("metrics", {}), "general", previous_metrics=latest["metrics"] if latest else None)

        with st.form("cpet_extracted_form"):
            test_date, context, modality, protocol, metrics, notes = _collect_report_form(extracted, "cpet_extracted")
            submitted = st.form_submit_button("Save CPET Report", type="primary", use_container_width=True)
            if submitted:
                if not metrics:
                    st.error("Add at least one CPET metric before saving.")
                else:
                    save_cpet_report(
                        user_id=user_id,
                        test_date=test_date.isoformat(),
                        client_context=context,
                        metrics=metrics,
                        source_filename=extracted.get("source_filename"),
                        test_modality=modality or extracted.get("test_modality"),
                        protocol=protocol or extracted.get("protocol"),
                        raw_text=extracted.get("raw_text"),
                        notes=notes or None,
                    )
                    del st.session_state["cpet_extracted"]
                    st.toast("CPET report saved.")
                    st.rerun()

        if st.button("Cancel extraction", use_container_width=True):
            del st.session_state["cpet_extracted"]
            st.rerun()

    st.divider()
    with st.expander("Manual CPET entry", expanded=not reports and "cpet_extracted" not in st.session_state):
        st.caption("Use this when the report is scanned, locked, or the client brings a paper result.")
        with st.form("cpet_manual_form"):
            test_date, context, modality, protocol, metrics, notes = _collect_report_form({"metrics": {}}, "cpet_manual")
            submitted = st.form_submit_button("Save Manual CPET Report", type="primary", use_container_width=True)
            if submitted:
                if not metrics:
                    st.error("Add at least one CPET metric before saving.")
                else:
                    save_cpet_report(
                        user_id=user_id,
                        test_date=test_date.isoformat(),
                        client_context=context,
                        metrics=metrics,
                        source_filename="manual_entry",
                        test_modality=modality or None,
                        protocol=protocol or None,
                        notes=notes or None,
                    )
                    st.toast("Manual CPET report saved.")
                    st.rerun()

with tab_saved:
    render_section_header("Saved CPET Reports", "Track serial changes and keep the coaching explanation attached")
    if not reports:
        st.info("No CPET reports saved yet.")
    else:
        _render_history_chart(reports)
        sorted_reports = sorted(reports, key=lambda item: item["test_date"], reverse=True)
        for idx, report in enumerate(sorted_reports):
            older = sorted_reports[idx + 1] if idx + 1 < len(sorted_reports) else None
            _render_saved_report(report, previous=older)

with tab_guide:
    render_section_header("Coach Guide", "The CPET explanation hierarchy for client conversations")
    hierarchy_rows = [
        {
            "Layer": "Measured",
            "Examples": "VO2, VCO2, VE, HR, work rate, PETCO2, SpO2",
            "How to use": "Highest confidence when calibration, mask seal, and protocol are good.",
        },
        {
            "Layer": "Derived",
            "Examples": "RER, O2 pulse, VE/VCO2 slope, breathing reserve, VO2/WR slope, OUES",
            "How to use": "Useful patterns, but still depend on measured signals and equations.",
        },
        {
            "Layer": "Interpreted",
            "Examples": "VT1/VT2, % predicted, phenotype, risk class, training zones",
            "How to use": "Requires reader judgment, population context, effort quality, and serial comparison.",
        },
    ]
    st.dataframe(pd.DataFrame(hierarchy_rows), use_container_width=True, hide_index=True)

    st.markdown("**The client explanation**")
    st.markdown(
        "CPET measures how the heart, lungs, blood, and muscles work together under load. Peak VO2 is the engine size, "
        "VT1 and VT2 are the gears for training zones, and VE/VCO2, breathing reserve, O2 pulse, PETCO2, and SpO2 help "
        "the clinician see where the system may be running out of room."
    )

    st.markdown("**Standardize before comparing tests**")
    for item in build_cpet_coach_summary({})["standardization_checks"]:
        st.markdown(f"- {item}")

    st.markdown("**Athlete and hybrid-sport caveats**")
    athlete_rows = [
        {
            "Topic": "Athlete norms",
            "Coach note": "General-population predicted normal may be underperforming for endurance athletes. Compare to sport, prior tests, and training phase.",
        },
        {
            "Topic": "Thresholds over shortcuts",
            "Coach note": "Training zones should be anchored to measured VT1/LT1 and VT2/LT2 whenever available, not fixed %HRmax alone.",
        },
        {
            "Topic": "Hybrid athletes",
            "Coach note": "Ramp CPET captures aerobic ceiling, but HYROX/CrossFit also need repeated-effort, loaded, and pre-fatigued sport-specific checks.",
        },
        {
            "Topic": "Substrate data",
            "Coach note": "FatMax and fat oxidation are protocol and nutrition dependent; RER above 1.0 invalidates fat oxidation estimates.",
        },
    ]
    st.dataframe(pd.DataFrame(athlete_rows), use_container_width=True, hide_index=True)

with tab_panels:
    render_section_header("Nine-Panel Reading Workflow", "A coach-safe map of what the CPET clinician is looking at")
    st.dataframe(pd.DataFrame(NINE_PANEL_ROWS), use_container_width=True, hide_index=True)

    st.markdown("**Clinical escalation reminders**")
    escalation_rows = [
        {
            "Pattern": "Low peak VO2 with low RER",
            "Meaning": "Peak capacity may be underestimated; lean on thresholds and VE/VCO2 until clinician confirms effort.",
        },
        {
            "Pattern": "High VE/VCO2 slope, low PETCO2, or desaturation",
            "Meaning": "Can fit pulmonary vascular, HF, V/Q, or hyperventilation patterns; not a coaching diagnosis.",
        },
        {
            "Pattern": "Low O2 pulse or VO2/work flattening",
            "Meaning": "Can suggest oxygen-delivery limitation or ischemic pattern; clinician review required.",
        },
        {
            "Pattern": "Breathing reserve <15%",
            "Meaning": "Possible ventilatory limitation; avoid unsupervised intensity progression until reviewed.",
        },
    ]
    st.dataframe(pd.DataFrame(escalation_rows), use_container_width=True, hide_index=True)
