"""Diet Pattern Assessment — Identify your dietary pattern and HEI-2020 score."""

import streamlit as st
import plotly.graph_objects as go
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from services.diet_service import (
    assess_diet_pattern,
    get_latest_assessment,
    get_assessment_history,
    get_hei_score_zone,
)
from components.diet_display import (
    render_hei_score_circle,
    render_diet_pattern_card,
    render_hei_component_bars,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Diet Pattern Assessment",
    "Identify your dietary pattern and score your diet quality using HEI-2020 methodology. "
    "Based on Dr. David Katz's Diet ID research (PMID: 25015212) and USDA Healthy Eating Index."
)

tab_quiz, tab_results, tab_history = st.tabs(["Take Assessment", "My Results", "History"])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Take Assessment (12-question quiz)
# ══════════════════════════════════════════════════════════════════════════
with tab_quiz:
    render_section_header("Diet Pattern Quiz", "12 questions about your typical eating habits")

    from config.diet_data import DIET_QUIZ_QUESTIONS

    with st.form("diet_quiz_form"):
        answers = []
        for i, q in enumerate(DIET_QUIZ_QUESTIONS):
            option_labels = [opt["label"] for opt in q["options"]]
            selected = st.radio(
                f"**{i + 1}. {q['question']}**",
                options=list(range(len(option_labels))),
                format_func=lambda x, labels=option_labels: labels[x],
                key=f"diet_q_{i}",
                horizontal=False,
            )
            answers.append(selected)

        submitted = st.form_submit_button("Submit Assessment", use_container_width=True)
        if submitted:
            result = assess_diet_pattern(user_id, answers)
            st.session_state["diet_result"] = result
            st.toast(f"Assessment complete! Your pattern: {result['data']['name']}")
            st.rerun()

    # Show result inline if just completed
    if "diet_result" in st.session_state:
        result = st.session_state.pop("diet_result")
        st.divider()
        render_section_header("Your Result")
        col_score, col_card = st.columns([1, 2])
        with col_score:
            render_hei_score_circle(result["hei_score"])
        with col_card:
            render_diet_pattern_card(result)
        render_hei_component_bars(result["component_scores"])

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: My Results (latest assessment)
# ══════════════════════════════════════════════════════════════════════════
with tab_results:
    latest = get_latest_assessment(user_id)

    if not latest:
        st.info("No assessment yet. Take the quiz to see your diet pattern and HEI score.")
    else:
        render_section_header("Latest Assessment", f"Taken on {latest['assessment_date']}")

        col_score, col_card = st.columns([1, 2])
        with col_score:
            render_hei_score_circle(latest["hei_score"])
        with col_card:
            render_diet_pattern_card(latest)

        render_hei_component_bars(latest.get("component_scores", {}))

        # Evidence badge
        evidence = latest.get("data", {}).get("evidence", "")
        if evidence:
            ev_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_md"]};padding:12px;margin-top:12px">'
                f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:4px">'
                f'Evidence Base</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]};font-style:italic">'
                f'{evidence}</div>'
                f'</div>'
            )
            st.markdown(ev_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: History
# ══════════════════════════════════════════════════════════════════════════
with tab_history:
    history = get_assessment_history(user_id)

    if not history:
        st.info("No assessment history yet. Take your first quiz!")
    elif len(history) == 1:
        st.caption("Take another assessment in a few weeks to see your trend.")
        a = history[0]
        zone = get_hei_score_zone(a["hei_score"])
        row_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-left:3px solid {zone["color"]};border-radius:{A["radius_md"]};'
            f'padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between;'
            f'align-items:center">'
            f'<div>'
            f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
            f'{a.get("data", {}).get("name", a["diet_type"])}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">{a["assessment_date"]}</div>'
            f'</div>'
            f'<div style="font-family:{A["font_display"]};font-size:20px;font-weight:700;'
            f'color:{zone["color"]}">{a["hei_score"]}</div>'
            f'</div>'
        )
        st.markdown(row_html, unsafe_allow_html=True)
    else:
        render_section_header("Assessment History", f"{len(history)} assessments")

        # Trend chart
        dates = [a["assessment_date"] for a in history]
        scores = [a["hei_score"] for a in history]
        patterns = [a.get("data", {}).get("name", a["diet_type"]) for a in history]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=scores, mode="lines+markers",
            line=dict(color="#30D158", width=2),
            marker=dict(size=10, color="#30D158"),
            text=patterns,
            hovertemplate="HEI: %{y}<br>Pattern: %{text}<br>%{x}<extra></extra>",
        ))
        fig.add_hline(y=80, line_dash="dash", line_color="#30D158", opacity=0.3,
                      annotation_text="Excellent (80+)")
        fig.add_hline(y=60, line_dash="dash", line_color="#FFD60A", opacity=0.3,
                      annotation_text="Good (60+)")
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=A["chart_bg"],
            font=dict(family=A["font_text"], color=A["chart_text"]),
            margin=dict(l=40, r=20, t=30, b=40),
            height=280,
            xaxis=dict(gridcolor=A["chart_grid"]),
            yaxis=dict(title="HEI Score", range=[0, 105], gridcolor=A["chart_grid"]),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        # History list
        for a in reversed(history):
            zone = get_hei_score_zone(a["hei_score"])
            row_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-left:3px solid {zone["color"]};border-radius:{A["radius_md"]};'
                f'padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between;'
                f'align-items:center">'
                f'<div>'
                f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
                f'{a.get("data", {}).get("name", a["diet_type"])}</div>'
                f'<div style="font-size:11px;color:{A["label_tertiary"]}">{a["assessment_date"]}</div>'
                f'</div>'
                f'<div style="font-family:{A["font_display"]};font-size:20px;font-weight:700;'
                f'color:{zone["color"]}">{a["hei_score"]}</div>'
                f'</div>'
            )
            st.markdown(row_html, unsafe_allow_html=True)
