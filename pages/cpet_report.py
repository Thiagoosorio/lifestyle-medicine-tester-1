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
from services.cpet_vision_service import (
    VisionUnavailableError,
    analyze_cpet_plots,
    extract_cpet_from_pdf_via_vision,
    render_pdf_pages_to_images,
    vision_model,
)


A = APPLE
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in first.")
    st.stop()


FIELD_LAYOUT = [
    ("age_years", "Age (years)", 10.0, 100.0, 1.0, "%.0f"),
    ("weight_kg", "Weight (kg)", 25.0, 250.0, 0.1, "%.1f"),
    ("height_cm", "Height (cm)", 120.0, 220.0, 0.5, "%.1f"),
    ("test_duration_min", "Incremental duration (min)", 2.0, 40.0, 0.1, "%.1f"),
    ("peak_vo2_ml_kg_min", "Peak VO2 (mL/kg/min)", 5.0, 100.0, 0.1, "%.1f"),
    ("peak_vo2_l_min", "Peak VO2 absolute (L/min)", 0.5, 9.0, 0.01, "%.2f"),
    ("peak_vo2_pct_pred", "Peak VO2 % predicted", 10.0, 250.0, 1.0, "%.0f"),
    ("peak_power_w", "Peak work rate (W)", 20.0, 800.0, 1.0, "%.0f"),
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
    ("fatmax_hr_bpm", "FatMax HR (bpm)", 50.0, 190.0, 1.0, "%.0f"),
]


def _as_number(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_numeric_metric(metrics: dict) -> bool:
    """True if at least one non-context metric value was entered.

    Context-only fields like ``sex`` are strings and must not, on their own,
    satisfy the "enter at least one CPET metric" save guard.
    """
    return any(_as_number(value) is not None for key, value in metrics.items() if key != "sex")


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

    top_cols = st.columns(5)
    with top_cols[0]:
        test_date = st.date_input("Test date", value=default_date, key=f"{prefix}_date")
    with top_cols[1]:
        sex_options = ["", "female", "male"]
        current_sex = str(metrics.get("sex") or "").lower()
        if current_sex not in sex_options:
            current_sex = ""
        sex_value = st.selectbox(
            "Sex",
            sex_options,
            index=sex_options.index(current_sex),
            format_func=lambda key: "Not set" if key == "" else key.capitalize(),
            key=f"{prefix}_sex",
            help="Biological sex is required to place VO2peak on age/sex percentile norms.",
        )
    with top_cols[2]:
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
    with top_cols[3]:
        test_modality = st.text_input(
            "Modality",
            value=initial.get("test_modality") or "",
            placeholder="treadmill, cycle ergometer...",
            key=f"{prefix}_modality",
        )
    with top_cols[4]:
        protocol = st.text_input(
            "Protocol",
            value=initial.get("protocol") or "",
            placeholder="ramp, Bruce, bike ramp...",
            key=f"{prefix}_protocol",
        )

    entered: dict[str, float | str] = {}
    if sex_value:
        entered["sex"] = sex_value
    for row_start in range(0, len(FIELD_LAYOUT), 3):
        cols = st.columns(3)
        for idx, spec in enumerate(FIELD_LAYOUT[row_start:row_start + 3]):
            field, label, min_value, max_value, step, fmt = spec
            with cols[idx]:
                # Clamp the prefilled value into the widget's range. Extracted or
                # normalize-derived values can legitimately fall outside a field's
                # min/max, and st.number_input raises if value is out of bounds.
                initial_value = _as_number(metrics.get(field))
                if initial_value is not None:
                    initial_value = min(max(initial_value, min_value), max_value)
                value = st.number_input(
                    label,
                    min_value=min_value,
                    max_value=max_value,
                    value=initial_value,
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


def _render_fitness_banner(fitness: dict | None) -> None:
    if not fitness:
        return
    if fitness.get("insufficient_context"):
        st.info("Add age and biological sex to classify VO2peak against age/sex/modality percentile norms.")
        return
    percentile = fitness.get("percentile")
    if percentile is None:
        return
    category = fitness.get("category", "")
    label = fitness.get("percentile_label", "")
    ref = fitness.get("reference", "")
    group = fitness.get("reference_group", "")
    if percentile >= 60:
        render = st.success
    elif percentile >= 40:
        render = st.info
    else:
        render = st.warning
    render(
        f"**Aerobic fitness: {category}** — {label} for {group} ({fitness.get('modality_used', 'unknown')} norms). "
        f"Reference: {ref}. Classify against these age/sex/modality percentiles, not the cart's one-word label."
    )
    for caveat in fitness.get("caveats", []):
        st.caption(caveat)


def _render_training_zones(zones: dict | None, narrative: str | None) -> None:
    if not zones:
        return
    st.markdown("### Training zones")
    if not zones.get("has_zones"):
        st.warning(zones.get("incomplete_note", "Threshold anchors are incomplete — add VT1 and VT2."))
        return

    st.dataframe(pd.DataFrame(zones["zone_table"]), use_container_width=True, hide_index=True)

    z2 = zones.get("zone2") or {}
    z2_bits = [v for v in (z2.get("power"), z2.get("speed"), z2.get("hr")) if v]
    if z2_bits:
        bullseye = f" · fat-burning bullseye {z2['fatmax_bullseye']}" if z2.get("fatmax_bullseye") else ""
        st.success(
            f"**Endurance Zone 2 (the base you build on): {' / '.join(z2_bits)}**{bullseye}. "
            f"Prescribe on {zones.get('primary_anchor', 'the measured anchor')}; this band tops out at VT1, not VT2."
        )

    if narrative:
        st.markdown(narrative)

    if zones.get("polarized_rows"):
        with st.expander("Training-distribution monitor (3-zone polarized — monitoring only, not a prescription)"):
            st.caption(
                "Note: 'Grey' here is the between-thresholds zone you AVOID in polarized training — the opposite of the "
                "prescriptive Endurance Zone 2 above (which sits below VT1). Same idea, different use."
            )
            st.dataframe(pd.DataFrame(zones["polarized_rows"]), use_container_width=True, hide_index=True)
            st.caption(zones.get("polarized_target", ""))

    if zones.get("caveats"):
        with st.expander("How to use these zones (caveats)"):
            for caveat in zones["caveats"]:
                st.markdown(f"- {caveat}")


def _render_metabolic(profile: dict | None, narrative: str | None) -> None:
    if not profile:
        return
    st.markdown("### Metabolic / fat-oxidation profile")
    cols = st.columns(3)
    with cols[0]:
        st.metric("Max fat oxidation", f"{profile['mfo_g_min']:g} g/min" if profile.get("mfo_g_min") is not None else "--",
                  profile.get("mfo_class", ""))
    with cols[1]:
        st.metric("FatMax heart rate", f"{profile['fatmax_hr']} bpm" if profile.get("fatmax_hr") is not None else "--")
    with cols[2]:
        st.metric("FatMax intensity", f"{profile['fatmax_pct_vo2max']}% VO2max" if profile.get("fatmax_pct_vo2max") is not None else "--")
    if narrative:
        st.markdown(narrative)


def _render_summary(
    metrics: dict,
    context: str,
    previous_metrics: dict | None = None,
    modality: str | None = None,
) -> None:
    summary = build_cpet_coach_summary(
        metrics, client_context=context, previous_metrics=previous_metrics, modality=modality
    )

    _render_fitness_banner(summary.get("fitness_classification"))

    validity = summary["validity_gate"]
    if validity:
        st.markdown("**Validity gate**")
        st.dataframe(pd.DataFrame(validity), use_container_width=True, hide_index=True)

    if summary.get("consistency_rows"):
        st.markdown("**Data-consistency checks**")
        st.dataframe(pd.DataFrame(summary["consistency_rows"]), use_container_width=True, hide_index=True)

    _render_training_zones(summary.get("training_zones"), summary.get("training_narrative"))
    _render_metabolic(summary.get("metabolic_profile"), summary.get("metabolic_narrative"))

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
        _render_summary(
            metrics,
            context,
            previous_metrics=previous["metrics"] if previous else None,
            modality=report.get("test_modality"),
        )
        if report.get("notes"):
            st.markdown("**Coach notes**")
            st.write(report["notes"])
        if st.button("Delete CPET report", key=f"delete_cpet_{report['id']}", type="secondary"):
            delete_cpet_report(user_id, report["id"])
            st.toast("CPET report deleted.")
            st.rerun()


_QC_VERDICT_LABELS = {
    "consistent": ("Consistent with the curves", "✅"),
    "possibly_early": ("Marked line looks early", "⚠️"),
    "possibly_late": ("Marked line looks late", "⚠️"),
    "cannot_assess": ("Could not assess from the image", "❔"),
}
_QC_OVERALL_LABELS = {
    "thresholds_look_consistent": "Thresholds look consistent with the plots",
    "vt1_possibly_misplaced": "VT1 may be misplaced — review",
    "vt2_possibly_misplaced": "VT2 may be misplaced — review",
    "both_possibly_misplaced": "Both thresholds may be misplaced — review",
    "insufficient_image_quality": "Image quality was insufficient to judge",
}


def _render_qc_result(result: dict) -> None:
    overall = result.get("overall_assessment", "")
    headline = _QC_OVERALL_LABELS.get(overall, overall)
    confidence = result.get("confidence", "")
    if overall == "thresholds_look_consistent":
        st.success(f"**{headline}** (confidence: {confidence})")
    elif overall == "insufficient_image_quality":
        st.info(f"**{headline}** (confidence: {confidence})")
    else:
        st.warning(f"**{headline}** (confidence: {confidence})")

    for key, title in (("vt1", "VT1 (aerobic threshold / GET)"), ("vt2", "VT2 (RCP / second threshold)")):
        finding = result.get(key) or {}
        label, icon = _QC_VERDICT_LABELS.get(finding.get("verdict", ""), (finding.get("verdict", ""), "•"))
        st.markdown(f"**{title}** — {icon} {label}")
        if finding.get("rationale"):
            st.markdown(f"> {finding['rationale']}")
        if finding.get("criteria_checked"):
            st.caption("Criteria checked: " + ", ".join(finding["criteria_checked"]))

    if result.get("coach_summary"):
        st.markdown("**Coach summary**")
        st.markdown(result["coach_summary"])

    if result.get("clinician_flags"):
        st.markdown("**Escalate to the supervising clinician**")
        for flag in result["clinician_flags"]:
            st.markdown(f"- {flag}")

    legible = result.get("plots_legible") or []
    st.caption(
        "Panels used: " + (", ".join(legible) if legible else "none identified")
        + f" · Model: {result.get('model', '')} · Images sent: {result.get('image_count', '?')}"
    )


def _render_plot_qc_tab(latest_report: dict | None) -> None:
    render_section_header(
        "AI plot quality-control",
        "Second-opinion check of whether the cart placed VT1/VT2 where the curves say they belong",
    )
    st.info(
        "Carts auto-detect VT1/VT2 from the gas-exchange curves and sometimes place them wrong even when "
        "the numbers look plausible. Upload the plot images (V-slope, ventilatory equivalents, 9-panel, "
        "end-tidal gases) or the CPET PDF, and Claude checks the marked thresholds against the standard "
        "visual criteria. This is coach decision-support, not a diagnosis — the supervising clinician "
        "makes the final call on threshold placement."
    )

    images: list[bytes] = []

    pdf = st.file_uploader("Option A — upload the CPET PDF (pages are rendered for review)", type=["pdf"], key="cpet_qc_pdf")
    if pdf is not None:
        try:
            pages = render_pdf_pages_to_images(pdf.getvalue())
        except VisionUnavailableError as exc:
            st.warning(str(exc))
            pages = []
        if pages:
            labels = [f"Page {p['page']}" for p in pages]
            default = labels  # let the coach deselect the cover/summary pages
            chosen = st.multiselect(
                "Choose the plot pages to analyze (deselect cover / summary / medical-findings pages)",
                labels,
                default=default,
                key="cpet_qc_pages",
            )
            thumb_cols = st.columns(min(4, max(1, len(pages))))
            for i, page in enumerate(pages):
                with thumb_cols[i % len(thumb_cols)]:
                    st.image(page["png"], caption=f"Page {page['page']}", use_container_width=True)
            images += [p["png"] for p in pages if f"Page {p['page']}" in chosen]

    uploads = st.file_uploader(
        "Option B — upload plot screenshots (PNG/JPG, multiple allowed)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="cpet_qc_images",
    )
    if uploads:
        for upload in uploads:
            images.append(upload.getvalue())

    context = latest_report["metrics"] if latest_report else {}
    if latest_report:
        st.caption(
            "Using the most recent saved report as numeric context: "
            f"VT1 {context.get('vt1_vo2_ml_kg_min', '?')} mL/kg/min / HR {context.get('vt1_hr_bpm', '?')}, "
            f"VT2 {context.get('vt2_vo2_ml_kg_min', '?')} mL/kg/min / HR {context.get('vt2_hr_bpm', '?')}."
        )
    else:
        st.caption("No saved report found — the review will run on the images alone, without numeric context.")

    st.caption(f"{len(images)} image(s) selected · model: {vision_model()}")

    if st.button("Run AI plot QC", type="primary", use_container_width=True, disabled=not images):
        with st.spinner("Reviewing the plots..."):
            try:
                result = analyze_cpet_plots(images, context=context)
            except VisionUnavailableError as exc:
                st.error(str(exc))
                return
            except Exception as exc:  # surface API/other errors without crashing the page
                st.error(f"Plot QC failed: {exc}")
                return
        st.session_state["cpet_qc_result"] = result

    if "cpet_qc_result" in st.session_state:
        st.divider()
        _render_qc_result(st.session_state["cpet_qc_result"])


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

tab_upload, tab_saved, tab_qc, tab_guide, tab_panels = st.tabs(
    ["Upload & Explain", "Saved Reports", "Plot QC (AI)", "Coach Guide", "Nine-Panel Guide"]
)

with tab_upload:
    render_section_header("Upload CPET Report", "PDF extraction first, then coach review and save")
    uploaded = st.file_uploader("Upload a CPET PDF or text export", type=["pdf", "txt"], key="cpet_upload")

    st.caption(
        "Text-readable PDFs are parsed directly. Scanned or image-only PDFs (many Cortex exports) "
        "are read by AI — you review every value before saving."
    )
    if uploaded and st.button("Extract CPET Report", type="primary", use_container_width=True):
        with st.spinner("Reading CPET report..."):
            extracted = None
            payload = uploaded.getvalue()
            is_pdf = uploaded.name.lower().endswith(".pdf")
            if is_pdf:
                # 1) Try the fast text parser. 2) If the PDF has no text layer or the
                #    parser finds nothing, fall back to AI reading of the PDF image.
                text_error = None
                try:
                    extracted = extract_cpet_from_pdf(payload)
                    if not extracted.get("metrics"):
                        extracted = None  # nothing found -> try AI
                except Exception as exc:
                    text_error = exc
                if extracted is None:
                    try:
                        with st.spinner("No text layer found — reading the PDF with AI..."):
                            extracted = extract_cpet_from_pdf_via_vision(payload)
                    except VisionUnavailableError as exc:
                        st.error(
                            f"This PDF has no readable text and AI reading is unavailable ({exc}). "
                            "Enter the values manually below."
                        )
                    except Exception as exc:
                        st.error(f"AI reading failed: {exc}" + (f" (text parser: {text_error})" if text_error else ""))
            else:
                raw_text = payload.decode("utf-8", errors="ignore")
                try:
                    extracted = extract_cpet_from_text(raw_text)
                    extracted["raw_text"] = raw_text
                except Exception as exc:
                    st.error(f"CPET extraction failed: {exc}")

            if extracted is not None:
                extracted["source_filename"] = uploaded.name
                st.session_state["cpet_extracted"] = extracted
                st.rerun()

    if "cpet_extracted" in st.session_state:
        extracted = st.session_state["cpet_extracted"]
        warnings = extracted.get("extraction_warnings") or []
        if warnings:
            for warning in warnings:
                st.warning(warning)

        st.markdown("### Review extracted values")
        _render_summary(
            extracted.get("metrics", {}),
            "general",
            previous_metrics=latest["metrics"] if latest else None,
            modality=extracted.get("test_modality"),
        )

        with st.form("cpet_extracted_form"):
            test_date, context, modality, protocol, metrics, notes = _collect_report_form(extracted, "cpet_extracted")
            submitted = st.form_submit_button("Save CPET Report", type="primary", use_container_width=True)
            if submitted:
                if not _has_numeric_metric(metrics):
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
                if not _has_numeric_metric(metrics):
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

with tab_qc:
    _render_plot_qc_tab(latest)

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
            "Topic": "\"Zone 2\" means two things",
            "Coach note": "Prescriptive endurance Zone 2 tops out AT VT1/LT1 (near FatMax) — a narrow base band. The Seiler 3-zone 'Zone 2' is the between-thresholds grey zone you AVOID. Same words, opposite use; prescribe the former.",
        },
        {
            "Topic": "Power/pace over HR",
            "Coach note": "Where a power meter or GPS pace exists, prescribe zones on power/pace; HR lags and drifts, especially above VT2 and on long efforts.",
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
