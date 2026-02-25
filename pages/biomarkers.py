"""Biomarkers — Lab result tracking with standard vs optimal range analysis."""

import streamlit as st
import plotly.graph_objects as go
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
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Biomarker Dashboard",
    "Track lab results over time. See where you stand versus standard AND optimal ranges."
)

# ── Tabs ─────────────────────────────────────────────────────────────────
tab_dashboard, tab_log, tab_trends, tab_history = st.tabs([
    "Dashboard", "Log Results", "Trends", "Lab History"
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
