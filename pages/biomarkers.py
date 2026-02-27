"""Biomarkers — Lab result tracking with standard vs optimal range analysis."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, datetime
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from components.biomarker_display import (
    render_biomarker_range_bar,
    render_biomarker_score_gauge,
    render_biomarker_summary_strip,
    render_category_header,
)
from config.biomarkers_data import BIOMARKER_CATEGORIES
from services.biomarker_service import (
    get_all_definitions,
    get_definitions_by_category,
    get_latest_results,
    get_results_for_biomarker,
    log_biomarker_result,
    calculate_biomarker_score,
    get_biomarker_summary,
    classify_result,
    get_classification_display,
    get_lab_dates,
    get_results_by_date,
    get_cached_analysis,
    save_blood_analysis,
    extract_biomarkers_from_pdf,
)
from services.coaching_service import get_blood_ai_analysis

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Biomarker Dashboard",
    "Track lab results over time. See where you stand versus standard AND optimal ranges."
)

# ── Tabs ─────────────────────────────────────────────────────────────────
tab_dashboard, tab_log, tab_trends, tab_history, tab_ai, tab_upload = st.tabs([
    "Dashboard", "Log Results", "Trends", "Lab History", "AI Analysis", "Upload Lab PDF"
])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Dashboard
# ══════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    score = calculate_biomarker_score(user_id)
    summary = get_biomarker_summary(user_id)

    if summary["total"] == 0:
        st.info("No lab results yet. Go to the **Log Results** tab to enter your first blood panel.")
    else:
        col_score, col_summary = st.columns([1, 2])
        with col_score:
            render_biomarker_score_gauge(score)
        with col_summary:
            render_biomarker_summary_strip(summary)
            total = summary["total"]
            in_range = summary["optimal"] + summary["normal"]
            pct = round(in_range / total * 100) if total else 0
            info_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_md"]};padding:14px;margin-top:8px">'
                f'<div style="font-size:13px;color:{A["label_secondary"]}">'
                f'<span style="font-weight:600;color:{A["label_primary"]}">{in_range}/{total}</span>'
                f' markers in range ({pct}%)'
                f'</div>'
                f'</div>'
            )
            st.markdown(info_html, unsafe_allow_html=True)

        # Show results grouped by category
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        render_section_header("Latest Results by Category")

        results = get_latest_results(user_id)
        # Group by category
        grouped = {}
        for r in results:
            cat = r.get("category", "other")
            grouped.setdefault(cat, []).append(r)

        sorted_cats = sorted(
            BIOMARKER_CATEGORIES.keys(),
            key=lambda k: BIOMARKER_CATEGORIES[k]["sort_order"]
        )
        for cat_key in sorted_cats:
            if cat_key not in grouped:
                continue
            cat_info = BIOMARKER_CATEGORIES[cat_key]
            render_category_header(cat_key, cat_info)
            for r in grouped[cat_key]:
                render_biomarker_range_bar(r)

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Log Results
# ══════════════════════════════════════════════════════════════════════════
with tab_log:
    render_section_header("Log Lab Results", "Enter values from your blood work")

    all_defs = get_all_definitions()

    with st.form("log_biomarker_form"):
        lab_date = st.date_input("Lab Date", value=date.today())
        lab_name = st.text_input("Lab Name (optional)", placeholder="e.g., Quest Diagnostics")

        # Category selector
        cat_options = ["All Categories"] + [
            BIOMARKER_CATEGORIES[k]["label"]
            for k in sorted(BIOMARKER_CATEGORIES.keys(), key=lambda k: BIOMARKER_CATEGORIES[k]["sort_order"])
        ]
        selected_cat = st.selectbox("Category", cat_options)

        if selected_cat == "All Categories":
            display_defs = all_defs
        else:
            cat_key = next(k for k, v in BIOMARKER_CATEGORIES.items() if v["label"] == selected_cat)
            display_defs = [d for d in all_defs if d["category"] == cat_key]

        st.caption("Leave blank for markers you didn't test. Only filled values will be saved.")

        values = {}
        for defn in display_defs:
            unit = defn["unit"]
            std_range = ""
            if defn.get("standard_low") is not None and defn.get("standard_high") is not None:
                std_range = f" (standard: {defn['standard_low']}-{defn['standard_high']})"
            elif defn.get("standard_high") is not None:
                std_range = f" (standard: <{defn['standard_high']})"
            elif defn.get("standard_low") is not None:
                std_range = f" (standard: >{defn['standard_low']})"

            val = st.number_input(
                f"{defn['name']} ({unit}){std_range}",
                min_value=0.0,
                max_value=99999.0,
                value=None,
                step=0.1,
                key=f"bm_{defn['id']}",
                help=defn.get("clinical_note", ""),
            )
            values[defn["id"]] = val

        submitted = st.form_submit_button("Save Results", use_container_width=True)
        if submitted:
            saved_count = 0
            for bm_id, val in values.items():
                if val is not None and val > 0:
                    log_biomarker_result(user_id, bm_id, val, lab_date.isoformat(), lab_name)
                    saved_count += 1
            if saved_count > 0:
                st.toast(f"Saved {saved_count} biomarker results!")
                st.rerun()
            else:
                st.warning("No values entered. Fill in at least one marker to save.")

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: Trends
# ══════════════════════════════════════════════════════════════════════════
with tab_trends:
    render_section_header("Biomarker Trends", "Track changes over time")

    all_defs = get_all_definitions()
    if not all_defs:
        st.caption("No biomarker definitions loaded.")
    else:
        marker_options = {f"{d['name']} ({d['unit']})": d["id"] for d in all_defs}
        selected_marker_label = st.selectbox("Select Biomarker", list(marker_options.keys()))
        selected_marker_id = marker_options[selected_marker_label]

        history = get_results_for_biomarker(user_id, selected_marker_id)
        if not history:
            st.caption("No data for this biomarker yet.")
        else:
            defn = history[0]  # has definition fields joined
            dates = [h["lab_date"] for h in history]
            values = [h["value"] for h in history]

            fig = go.Figure()

            # Optimal zone shading
            if defn.get("optimal_low") is not None and defn.get("optimal_high") is not None:
                fig.add_hrect(
                    y0=defn["optimal_low"], y1=defn["optimal_high"],
                    fillcolor="#30D158", opacity=0.1,
                    line_width=0, annotation_text="Optimal",
                    annotation_position="top left",
                    annotation=dict(font_color="#30D158", font_size=10),
                )

            # Standard zone shading
            if defn.get("standard_low") is not None and defn.get("standard_high") is not None:
                fig.add_hrect(
                    y0=defn["standard_low"], y1=defn["standard_high"],
                    fillcolor="#64D2FF", opacity=0.05,
                    line_width=0,
                )

            # Value line
            fig.add_trace(go.Scatter(
                x=dates, y=values,
                mode="lines+markers",
                line=dict(color="#0A84FF", width=2),
                marker=dict(size=8, color="#0A84FF"),
                name=defn["name"],
                hovertemplate="%{y:.1f} " + defn["unit"] + "<br>%{x}<extra></extra>",
            ))

            fig.update_layout(
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor=A["chart_bg"],
                font=dict(family=A["font_text"], color=A["chart_text"]),
                margin=dict(l=40, r=20, t=30, b=40),
                height=320,
                xaxis=dict(gridcolor=A["chart_grid"]),
                yaxis=dict(
                    title=defn["unit"],
                    gridcolor=A["chart_grid"],
                ),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Show clinical note
            if defn.get("clinical_note"):
                note_html = (
                    f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                    f'border-radius:{A["radius_md"]};padding:12px;margin-top:8px">'
                    f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                    f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:4px">'
                    f'Clinical Note</div>'
                    f'<div style="font-size:13px;color:{A["label_secondary"]}">'
                    f'{defn["clinical_note"]}</div>'
                    f'</div>'
                )
                st.markdown(note_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 4: Lab History
# ══════════════════════════════════════════════════════════════════════════
with tab_history:
    render_section_header("Lab History", "View results by lab date")

    lab_dates = get_lab_dates(user_id)
    if not lab_dates:
        st.caption("No lab results recorded yet.")
    else:
        selected_date = st.selectbox("Select Lab Date", lab_dates)
        date_results = get_results_by_date(user_id, selected_date)

        if date_results:
            st.caption(f"Showing {len(date_results)} markers from {selected_date}")
            for r in date_results:
                render_biomarker_range_bar(r)

# ══════════════════════════════════════════════════════════════════════════
# Tab 5: AI Analysis (BloodGPT)
# ══════════════════════════════════════════════════════════════════════════
with tab_ai:
    render_section_header(
        "AI Blood Analysis",
        "BloodGPT-powered holistic analysis with scientific rigor",
    )

    ai_lab_dates = get_lab_dates(user_id)

    if not ai_lab_dates:
        st.info(
            "No lab results found. Log your first blood panel in 'Log Results' "
            "to enable AI analysis."
        )
    else:
        col_date_ai, col_btn_ai = st.columns([3, 1])
        with col_date_ai:
            ai_selected_date = st.selectbox(
                "Select Lab Date", ai_lab_dates, key="ai_lab_date_sel"
            )
        with col_btn_ai:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            ai_generate = st.button(
                "Generate Analysis",
                type="primary",
                use_container_width=True,
                key="ai_generate_btn",
            )

        # Load cached analysis
        cached = get_cached_analysis(user_id, ai_selected_date)

        # Generate (or regenerate) if requested or no cache exists
        if ai_generate:
            with st.spinner("Analysing your blood panel with BloodGPT… (15-20 seconds)"):
                analysis_text = get_blood_ai_analysis(user_id, ai_selected_date)
                save_blood_analysis(user_id, ai_selected_date, analysis_text)
            cached = get_cached_analysis(user_id, ai_selected_date)
            st.rerun()

        if cached:
            # Meta card — lab date + generation timestamp
            meta_html = (
                f'<div style="background:{A["bg_secondary"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_md"]};padding:10px 14px;margin-bottom:10px;'
                f'display:flex;justify-content:space-between;align-items:center">'
                f'<div style="font-size:13px;font-weight:700;color:{A["label_primary"]}">'
                f'Analysis for {ai_selected_date}</div>'
                f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
                f'Generated {cached["created_at"][:16]}</div>'
                f'</div>'
            )
            st.markdown(meta_html, unsafe_allow_html=True)

            # Medical disclaimer banner
            disclaimer_html = (
                f'<div style="background:#FF9F0A18;border:1px solid #FF9F0A55;'
                f'border-radius:{A["radius_md"]};padding:10px 14px;margin-bottom:14px">'
                f'<div style="font-size:11px;color:{A["label_secondary"]};line-height:16px">'
                f'<strong>Medical Disclaimer:</strong> This AI analysis is for educational '
                f'and informational purposes only. It does not constitute medical advice, '
                f'diagnosis, or treatment. Always discuss your results with a qualified '
                f'healthcare provider before making health decisions.'
                f'</div></div>'
            )
            st.markdown(disclaimer_html, unsafe_allow_html=True)

            # Render AI markdown — use st.container so headers/bullets/bold render correctly
            with st.container(border=True):
                st.markdown(cached["analysis_text"])

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.caption(
                f"Model: {cached.get('model_used', 'claude-sonnet')}  "
                f"·  Generated: {cached['created_at'][:16]}"
            )
            if st.button("Regenerate Analysis", key="ai_regen_btn"):
                # Clear cache by saving empty string, then rerun
                save_blood_analysis(user_id, ai_selected_date, "")
                st.rerun()

        else:
            # No cache yet — show prompt card
            prompt_html = (
                f'<div style="background:{A["bg_elevated"]};border:2px dashed {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:32px;text-align:center;margin-top:16px">'
                f'<div style="font-size:32px;margin-bottom:8px">🔬</div>'
                f'<div style="font-size:15px;font-weight:700;color:{A["label_primary"]};'
                f'margin-bottom:6px">Run BloodGPT Analysis</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]};max-width:380px;'
                f'margin:0 auto;line-height:18px">AI will analyse your complete blood panel '
                f'for clinical patterns, compare to previous results, rank lifestyle '
                f'interventions by evidence grade, and suggest next steps.</div>'
                f'</div>'
            )
            st.markdown(prompt_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 6: Upload Lab PDF
# ══════════════════════════════════════════════════════════════════════════
with tab_upload:
    render_section_header(
        "Upload Lab PDF",
        "AI reads your blood test report and extracts all values automatically",
    )

    info_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:16px">'
        f'<div style="font-size:13px;color:{A["label_secondary"]};line-height:19px">'
        f'<strong>How it works:</strong> Upload a PDF blood test from any lab (Quest, LabCorp, '
        f'NHS, etc.). Claude AI reads the report, matches each result to our biomarker database, '
        f'and shows you the values for review before saving. No manual entry needed.'
        f'</div></div>'
    )
    st.markdown(info_html, unsafe_allow_html=True)

    if "pdf_extracted" not in st.session_state:
        # ── Step 1: Upload ────────────────────────────────────────────────
        # Full-width uploader so drag-and-drop zone is large
        uploaded_pdfs = st.file_uploader(
            "Drop PDF(s) here or click Browse",
            type=["pdf"],
            accept_multiple_files=True,
            key="pdf_uploader",
            help="Select one or more PDF lab reports — all will be merged into one panel.",
        )
        col_date, col_lab = st.columns(2)
        with col_date:
            pdf_date_val = st.date_input("Lab Date", value=date.today(), key="pdf_date_input")
        with col_lab:
            pdf_lab_val = st.text_input(
                "Lab Name (optional)",
                placeholder="e.g. Cleveland Clinic, Quest",
                key="pdf_lab_input",
            )

        if uploaded_pdfs:
            n = len(uploaded_pdfs)
            names_preview = ", ".join(f.name for f in uploaded_pdfs[:3])
            if n > 3:
                names_preview += f" +{n - 3} more"
            st.caption(f"{n} file{'s' if n > 1 else ''} selected: {names_preview}")

            if st.button(
                f"Extract Values from {n} PDF{'s' if n > 1 else ''} with AI",
                type="primary",
                use_container_width=True,
                key="pdf_extract_btn",
            ):
                with st.spinner(
                    f"Reading {n} lab report{'s' if n > 1 else ''} with AI… "
                    f"({10 * n}–{20 * n} seconds)"
                ):
                    try:
                        all_defs = get_all_definitions()
                        merged: list[dict] = []
                        seen_ids: set[int] = set()
                        errors: list[str] = []

                        for pdf_file in uploaded_pdfs:
                            try:
                                pdf_bytes = pdf_file.read()
                                batch = extract_biomarkers_from_pdf(pdf_bytes, all_defs)
                                for item in batch:
                                    if item["biomarker_id"] not in seen_ids:
                                        seen_ids.add(item["biomarker_id"])
                                        merged.append(item)
                            except Exception as _fe:
                                errors.append(f"{pdf_file.name}: {_fe}")

                        st.session_state["pdf_extracted"] = merged
                        st.session_state["pdf_date_str"]  = pdf_date_val.isoformat()
                        st.session_state["pdf_lab_str"]   = pdf_lab_val
                        st.session_state["pdf_file_count"] = n
                        if errors:
                            st.session_state["pdf_errors"] = errors
                        st.rerun()
                    except Exception as _exc:
                        st.error(f"Extraction failed: {_exc}")
    else:
        # ── Step 2: Review & confirm ──────────────────────────────────────
        extracted = st.session_state["pdf_extracted"]
        ext_date  = st.session_state.get("pdf_date_str", date.today().isoformat())
        ext_lab   = st.session_state.get("pdf_lab_str", "")

        if not extracted:
            st.warning(
                "No biomarkers could be matched from this PDF. The report may use "
                "non-standard terminology or the file may be a scanned image. "
                "Try entering values manually in the **Log Results** tab."
            )
            if st.button("Try Another PDF", key="pdf_retry_empty_btn"):
                for _k in ("pdf_extracted", "pdf_date_str", "pdf_lab_str", "pdf_file_count"):
                    st.session_state.pop(_k, None)
                st.rerun()
        else:
            # Show any per-file errors as a warning
            pdf_errors = st.session_state.pop("pdf_errors", [])
            if pdf_errors:
                st.warning("Some files could not be read: " + " | ".join(pdf_errors))

            # Meta header card
            n_files = st.session_state.get("pdf_file_count", 1)
            file_label = f"{n_files} PDF{'s' if n_files > 1 else ''}"
            meta_html = (
                f'<div style="background:{A["bg_secondary"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_md"]};padding:10px 14px;margin-bottom:12px;'
                f'display:flex;justify-content:space-between;align-items:center">'
                f'<div style="font-size:13px;font-weight:700;color:{A["label_primary"]}">'
                f'{len(extracted)} markers extracted from {file_label} — {ext_date}</div>'
                f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
                f'{ext_lab if ext_lab else "Lab not specified"}</div>'
                f'</div>'
            )
            st.markdown(meta_html, unsafe_allow_html=True)
            st.caption(
                "Review values below. Edit incorrect numbers, uncheck markers to skip, "
                "then click **Save to Biomarkers**."
            )

            # Editable review table
            review_df = pd.DataFrame([
                {"Save": True, "Biomarker": r["name"], "Value": r["value"], "Unit": r["unit"]}
                for r in extracted
            ])
            edited_df = st.data_editor(
                review_df,
                column_config={
                    "Save": st.column_config.CheckboxColumn("Save?", default=True, width="small"),
                    "Biomarker": st.column_config.TextColumn("Biomarker", disabled=True),
                    "Value": st.column_config.NumberColumn("Value", min_value=0.0, format="%.2f"),
                    "Unit": st.column_config.TextColumn("Unit", disabled=True, width="small"),
                },
                use_container_width=True,
                hide_index=True,
                key="pdf_review_editor",
            )

            col_save, col_cancel = st.columns([3, 1])
            with col_save:
                if st.button(
                    "Save to Biomarkers",
                    type="primary",
                    use_container_width=True,
                    key="pdf_save_btn",
                ):
                    saved_n = 0
                    for i, row in edited_df.iterrows():
                        if row["Save"] and float(row["Value"]) > 0:
                            bm = extracted[i]
                            log_biomarker_result(
                                user_id,
                                bm["biomarker_id"],
                                float(row["Value"]),
                                ext_date,
                                ext_lab or None,
                            )
                            saved_n += 1
                    for _k in ("pdf_extracted", "pdf_date_str", "pdf_lab_str", "pdf_file_count"):
                        st.session_state.pop(_k, None)
                    st.toast(f"Saved {saved_n} biomarker results!")
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", use_container_width=True, key="pdf_cancel_btn"):
                    for _k in ("pdf_extracted", "pdf_date_str", "pdf_lab_str", "pdf_file_count"):
                        st.session_state.pop(_k, None)
                    st.rerun()
