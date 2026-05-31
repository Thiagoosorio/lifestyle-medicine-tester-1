"""Coach-facing InBody report upload and interpretation page."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.custom_theme import APPLE, render_hero_banner, render_section_header
from services.inbody_service import (
    INBODY_METRIC_SPECS,
    SEGMENT_LABELS,
    build_inbody_coach_summary,
    delete_inbody_report,
    extract_inbody_from_pdf,
    extract_inbody_from_text,
    get_inbody_reports,
    save_inbody_report,
)


A = APPLE
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in first.")
    st.stop()


FIELD_LAYOUT = [
    ("height_cm", "Height (cm)", 80.0, 230.0, 0.1, "%.1f"),
    ("weight_kg", "Weight (kg)", 25.0, 350.0, 0.1, "%.1f"),
    ("bmi", "BMI", 10.0, 80.0, 0.1, "%.1f"),
    ("total_body_water_l", "Total Body Water (L)", 10.0, 100.0, 0.1, "%.1f"),
    ("intracellular_water_l", "ICW (L)", 5.0, 70.0, 0.1, "%.1f"),
    ("extracellular_water_l", "ECW (L)", 3.0, 40.0, 0.1, "%.1f"),
    ("ecw_tbw_ratio", "ECW/TBW Ratio", 0.25, 0.55, 0.001, "%.3f"),
    ("phase_angle_deg", "Phase Angle (deg)", 1.0, 15.0, 0.1, "%.1f"),
    ("skeletal_muscle_mass_kg", "Skeletal Muscle Mass (kg)", 5.0, 80.0, 0.1, "%.1f"),
    ("soft_lean_mass_kg", "Soft Lean Mass (kg)", 10.0, 160.0, 0.1, "%.1f"),
    ("fat_free_mass_kg", "Fat-Free Mass (kg)", 10.0, 180.0, 0.1, "%.1f"),
    ("body_fat_mass_kg", "Body Fat Mass (kg)", 1.0, 150.0, 0.1, "%.1f"),
    ("body_fat_pct", "Percent Body Fat (%)", 2.0, 75.0, 0.1, "%.1f"),
    ("bmr_kcal", "BMR (kcal/day)", 500.0, 4000.0, 1.0, "%.0f"),
    ("visceral_fat_area_cm2", "Visceral Fat Area (cm2)", 1.0, 400.0, 1.0, "%.0f"),
    ("visceral_fat_level", "Visceral Fat Level", 1.0, 40.0, 1.0, "%.0f"),
    ("waist_hip_ratio", "Waist-Hip Ratio", 0.5, 1.5, 0.01, "%.2f"),
    ("inbody_score", "InBody Score", 1.0, 120.0, 1.0, "%.0f"),
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
    unit = INBODY_METRIC_SPECS.get(field, {}).get("unit", "")
    if field == "ecw_tbw_ratio":
        return f"{numeric:.3f}"
    if field == "inbody_score":
        return f"{numeric:.0f}"
    if unit == "%":
        return f"{numeric:.1f}%"
    if unit:
        return f"{numeric:.1f} {unit}"
    return f"{numeric:.1f}"


def _collect_report_form(initial: dict, prefix: str) -> tuple[date, str, dict, str]:
    metrics = initial.get("metrics", {})
    default_date = _date_from_state(initial.get("scan_date"))

    scan_date = st.date_input("Scan date", value=default_date, key=f"{prefix}_date")
    device_model = st.text_input(
        "Device model",
        value=initial.get("device_model") or "",
        placeholder="e.g. InBody 770",
        key=f"{prefix}_device",
    )

    entered: dict[str, float | dict] = {}
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

    with st.expander("Segmental ECW/TBW ratios", expanded=bool(metrics.get("segmental_ecw_ratio"))):
        st.caption("Optional but powerful for injury, swelling, and side-to-side recovery review.")
        segmental_initial = metrics.get("segmental_ecw_ratio") or {}
        seg_cols = st.columns(5)
        segmental: dict[str, float] = {}
        for idx, (key, label) in enumerate(SEGMENT_LABELS.items()):
            with seg_cols[idx]:
                value = st.number_input(
                    label,
                    min_value=0.25,
                    max_value=0.55,
                    value=_as_number(segmental_initial.get(key)),
                    step=0.001,
                    format="%.3f",
                    key=f"{prefix}_seg_{key}",
                )
                if value is not None:
                    segmental[key] = value
        if segmental:
            entered["segmental_ecw_ratio"] = segmental

    notes = st.text_area(
        "Coach notes",
        value=initial.get("notes") or "",
        placeholder="Testing conditions, injury context, hydration, training block, client questions...",
        height=90,
        key=f"{prefix}_notes",
    )
    return scan_date, device_model, entered, notes


def _render_summary(metrics: dict, previous_metrics: dict | None = None) -> None:
    summary = build_inbody_coach_summary(metrics, previous_metrics=previous_metrics)

    trust_rows = summary["trust_rows"]
    if trust_rows:
        st.markdown("**Trust hierarchy from this report**")
        st.dataframe(pd.DataFrame(trust_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No metrics entered yet. Upload a readable PDF or enter the key report values manually.")

    flags = summary["coach_flags"]
    if flags:
        st.markdown("**Coach review flags**")
        st.dataframe(pd.DataFrame(flags), use_container_width=True, hide_index=True)

    if summary["trend_notes"]:
        st.markdown("**Trend notes versus prior scan**")
        for note in summary["trend_notes"]:
            st.markdown(f"- {note}")

    st.markdown("**Coach talking points**")
    for item in summary["talking_points"]:
        st.markdown(f"- {item}")


def _render_metric_strip(metrics: dict) -> None:
    cols = st.columns(6)
    items = [
        ("weight_kg", "Weight"),
        ("skeletal_muscle_mass_kg", "SMM"),
        ("body_fat_pct", "Body Fat"),
        ("ecw_tbw_ratio", "ECW/TBW"),
        ("phase_angle_deg", "Phase Angle"),
        ("visceral_fat_area_cm2", "VFA"),
    ]
    for col, (field, label) in zip(cols, items):
        with col:
            st.metric(label, _format_value(field, metrics.get(field)))


def _render_history_chart(reports: list[dict]) -> None:
    rows = []
    for report in reports:
        metrics = report["metrics"]
        rows.append(
            {
                "scan_date": report["scan_date"],
                "Weight": metrics.get("weight_kg"),
                "SMM": metrics.get("skeletal_muscle_mass_kg"),
                "Body Fat %": metrics.get("body_fat_pct"),
                "ECW/TBW": metrics.get("ecw_tbw_ratio"),
                "Phase Angle": metrics.get("phase_angle_deg"),
            }
        )
    df = pd.DataFrame(rows)
    if len(df) < 2:
        return
    df["scan_date"] = pd.to_datetime(df["scan_date"])
    df = df.sort_values("scan_date")

    fig = go.Figure()
    for column in ["Weight", "SMM", "Body Fat %", "ECW/TBW", "Phase Angle"]:
        if df[column].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=df["scan_date"],
                    y=df[column],
                    mode="lines+markers",
                    name=column,
                )
            )
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
    title = f"{report['scan_date']} - {report.get('device_model') or 'InBody report'}"
    with st.expander(title, expanded=False):
        _render_metric_strip(metrics)
        st.divider()
        _render_summary(metrics, previous_metrics=previous["metrics"] if previous else None)
        if report.get("notes"):
            st.markdown("**Coach notes**")
            st.write(report["notes"])
        if st.button("Delete report", key=f"delete_inbody_{report['id']}", type="secondary"):
            delete_inbody_report(user_id, report["id"])
            st.toast("InBody report deleted.")
            st.rerun()


render_hero_banner(
    "InBody Coach",
    "Upload an InBody report, extract the useful signals, and turn the scan into a coach-friendly explanation.",
)

st.info(
    "Educational coaching support only. InBody is bioelectrical impedance analysis: hydration, recent exercise, "
    "food, alcohol, illness, and edema can all shift the result. Use trends and clinical context."
)

reports = get_inbody_reports(user_id)
latest = reports[0] if reports else None
previous = reports[1] if len(reports) > 1 else None

if latest:
    _render_metric_strip(latest["metrics"])

tab_upload, tab_saved, tab_guide = st.tabs(["Upload & Explain", "Saved Reports", "Coach Guide"])

with tab_upload:
    render_section_header("Upload InBody Report", "PDF extraction first, then coach review and save")
    uploaded = st.file_uploader("Upload an InBody PDF or text export", type=["pdf", "txt"], key="inbody_upload")

    if uploaded and st.button("Extract Report", type="primary", use_container_width=True):
        with st.spinner("Reading InBody report..."):
            try:
                payload = uploaded.getvalue()
                if uploaded.name.lower().endswith(".pdf"):
                    extracted = extract_inbody_from_pdf(payload)
                else:
                    raw_text = payload.decode("utf-8", errors="ignore")
                    extracted = extract_inbody_from_text(raw_text)
                    extracted["raw_text"] = raw_text
                extracted["source_filename"] = uploaded.name
                st.session_state["inbody_extracted"] = extracted
                st.rerun()
            except Exception as exc:
                st.error(f"InBody extraction failed: {exc}")

    if "inbody_extracted" in st.session_state:
        extracted = st.session_state["inbody_extracted"]
        warnings = extracted.get("extraction_warnings") or []
        if warnings:
            for warning in warnings:
                st.warning(warning)

        st.markdown("### Review extracted values")
        _render_summary(extracted.get("metrics", {}), previous_metrics=latest["metrics"] if latest else None)

        with st.form("inbody_extracted_form"):
            scan_date, device_model, metrics, notes = _collect_report_form(extracted, "inbody_extracted")
            submitted = st.form_submit_button("Save InBody Report", type="primary", use_container_width=True)
            if submitted:
                if not metrics:
                    st.error("Add at least one InBody metric before saving.")
                else:
                    save_inbody_report(
                        user_id=user_id,
                        scan_date=scan_date.isoformat(),
                        metrics=metrics,
                        source_filename=extracted.get("source_filename"),
                        device_model=device_model or extracted.get("device_model"),
                        raw_text=extracted.get("raw_text"),
                        notes=notes or None,
                    )
                    del st.session_state["inbody_extracted"]
                    st.toast("InBody report saved.")
                    st.rerun()

        if st.button("Cancel extraction", use_container_width=True):
            del st.session_state["inbody_extracted"]
            st.rerun()

    st.divider()
    with st.expander("Manual InBody entry", expanded=not reports and "inbody_extracted" not in st.session_state):
        st.caption("Use this when the PDF is scanned, locked, or the client brings a paper report.")
        with st.form("inbody_manual_form"):
            scan_date, device_model, metrics, notes = _collect_report_form({"metrics": {}}, "inbody_manual")
            submitted = st.form_submit_button("Save Manual InBody Report", type="primary", use_container_width=True)
            if submitted:
                if not metrics:
                    st.error("Add at least one InBody metric before saving.")
                else:
                    save_inbody_report(
                        user_id=user_id,
                        scan_date=scan_date.isoformat(),
                        metrics=metrics,
                        source_filename="manual_entry",
                        device_model=device_model or None,
                        notes=notes or None,
                    )
                    st.toast("Manual InBody report saved.")
                    st.rerun()

with tab_saved:
    render_section_header("Saved InBody Reports", "Track trend direction and review each scan in coach language")
    if not reports:
        st.info("No InBody reports saved yet.")
    else:
        _render_history_chart(reports)
        sorted_reports = sorted(reports, key=lambda item: item["scan_date"], reverse=True)
        for idx, report in enumerate(sorted_reports):
            older = sorted_reports[idx + 1] if idx + 1 < len(sorted_reports) else None
            _render_saved_report(report, previous=older)

with tab_guide:
    render_section_header("Coach Guide", "A practical reading hierarchy adapted from the InBody reading guide")
    st.markdown("**Trust the report in this order**")
    guide_rows = [
        {
            "Tier": "Tier 1",
            "Metrics": "Phase angle, total body water, ICW, ECW, ECW/TBW",
            "Coach meaning": "Closest to the raw impedance signal; best for hydration, cell-health, swelling, and recovery context.",
        },
        {
            "Tier": "Tier 2",
            "Metrics": "Skeletal muscle mass, soft lean mass, fat-free mass",
            "Coach meaning": "Good trend markers, but they depend on the assumption that lean tissue hydration is stable.",
        },
        {
            "Tier": "Tier 3",
            "Metrics": "Body fat %, body fat mass, BMR, visceral fat, InBody score",
            "Coach meaning": "Useful context and motivation, but more assumption-dependent. Use trend and confirm with other data.",
        },
    ]
    st.dataframe(pd.DataFrame(guide_rows), use_container_width=True, hide_index=True)

    st.markdown("**ECW/TBW interpretation**")
    ecw_rows = [
        {"Range or pattern": "~0.360-0.390", "Meaning": "Typical balanced water distribution in many healthy adults."},
        {"Range or pattern": "Rising toward or above ~0.390", "Meaning": "Review fluid retention, inflammation, edema, recent hard training, or injury context."},
        {"Range or pattern": "One limb higher than partner", "Meaning": "Can support a swelling or recovery story; verify with symptoms, girth, and function."},
        {"Range or pattern": "Falls back toward partner limb", "Meaning": "Objective sign that local fluid imbalance may be resolving."},
    ]
    st.dataframe(pd.DataFrame(ecw_rows), use_container_width=True, hide_index=True)

    st.markdown("**Standardize before comparing scans**")
    for item in build_inbody_coach_summary({})["standardization_checks"]:
        st.markdown(f"- {item}")

    st.markdown("**Patient-friendly explanation**")
    st.markdown(
        "InBody sends a tiny electrical current through the body. Water-rich tissue conducts that current better "
        "than fat, so the strongest readings are the water and phase-angle numbers. Muscle and fat values are "
        "calculated from those signals, so they are best used as trends on the same device, under the same conditions."
    )
