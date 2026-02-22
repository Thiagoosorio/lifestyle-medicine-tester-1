"""Recovery Dashboard — Composite recovery score from sleep, stress, activity, habits, mood."""

import streamlit as st
import plotly.graph_objects as go
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from services.recovery_service import (
    calculate_recovery_score,
    get_recovery_history,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Recovery Dashboard",
    "Your daily readiness score. Based on sleep, stress, activity, habits, and mood."
)

recovery = calculate_recovery_score(user_id)

if not recovery:
    st.info(
        "Not enough data to calculate recovery. "
        "Log sleep, complete daily check-ins, and track habits to see your recovery score."
    )
else:
    score = recovery["score"]
    zone = recovery["zone"]
    components = recovery["components"]

    # ── Score Gauge + Zone ────────────────────────────────────────────────
    col_gauge, col_info = st.columns([1, 2])

    with col_gauge:
        radius = 58
        circumference = 2 * 3.14159 * radius
        offset = circumference * (1 - score / 100)

        gauge_html = (
            f'<div style="text-align:center;padding:20px">'
            f'<svg width="150" height="150" viewBox="0 0 150 150">'
            f'<circle cx="75" cy="75" r="{radius}" fill="none" stroke="{A["bg_tertiary"]}" stroke-width="10"/>'
            f'<circle cx="75" cy="75" r="{radius}" fill="none" stroke="{zone["color"]}" stroke-width="10" '
            f'stroke-linecap="round" stroke-dasharray="{circumference}" '
            f'stroke-dashoffset="{offset}" transform="rotate(-90 75 75)"/>'
            f'<text x="75" y="68" text-anchor="middle" fill="{A["label_primary"]}" '
            f'font-family="{A["font_display"]}" font-size="32" font-weight="700">{score}</text>'
            f'<text x="75" y="90" text-anchor="middle" fill="{zone["color"]}" '
            f'font-family="{A["font_text"]}" font-size="12" font-weight="600">'
            f'{zone["icon"]} {zone["label"]}</text>'
            f'</svg>'
            f'<div style="font-size:12px;font-weight:600;color:{A["label_secondary"]};'
            f'text-transform:uppercase;letter-spacing:0.06em;margin-top:4px">Recovery Score</div>'
            f'</div>'
        )
        st.markdown(gauge_html, unsafe_allow_html=True)

    with col_info:
        # Zone message
        msg_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-left:3px solid {zone["color"]};border-radius:{A["radius_lg"]};'
            f'padding:16px;margin-bottom:12px">'
            f'<div style="font-size:14px;font-weight:600;color:{zone["color"]};margin-bottom:4px">'
            f'{zone["message"]}</div>'
            f'<div style="font-size:13px;color:{A["label_secondary"]}">'
            f'{zone["recommendation"]}</div>'
            f'</div>'
        )
        st.markdown(msg_html, unsafe_allow_html=True)

        # Component breakdown
        comp_cards = ""
        for key, comp in components.items():
            raw_display = f"{comp['raw']}" if comp["raw"] is not None else "No data"
            comp_score = comp["score"]
            if comp_score >= 80:
                comp_color = "#30D158"
            elif comp_score >= 60:
                comp_color = "#FFD60A"
            else:
                comp_color = "#FF453A"

            comp_cards += (
                f'<div style="display:flex;align-items:center;gap:8px;'
                f'padding:8px 0;border-bottom:1px solid {A["separator"]}">'
                f'<span style="font-size:16px;min-width:24px">{comp["icon"]}</span>'
                f'<span style="font-size:13px;color:{A["label_secondary"]};flex:1">'
                f'{comp["label"]}</span>'
                f'<span style="font-size:13px;color:{A["label_tertiary"]};min-width:60px">'
                f'{raw_display}</span>'
                f'<span style="font-family:{A["font_display"]};font-size:15px;'
                f'font-weight:700;color:{comp_color};min-width:30px;text-align:right">'
                f'{comp_score}</span>'
                f'</div>'
            )

        breakdown_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_lg"]};padding:16px">'
            f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:8px">'
            f'Component Breakdown</div>'
            f'{comp_cards}'
            f'</div>'
        )
        st.markdown(breakdown_html, unsafe_allow_html=True)

    # ── Weight Explanation ────────────────────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    weights_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px">'
        f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
        f'Score = Sleep (35%) + Stress (25%) + Activity (20%) + Habits (10%) + Mood (10%)'
        f'</div>'
        f'</div>'
    )
    st.markdown(weights_html, unsafe_allow_html=True)

    # ── Recovery Trend ────────────────────────────────────────────────────
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    render_section_header("Recovery Trend", "Last 30 days")

    history = get_recovery_history(user_id, days=30)
    if history and len(history) >= 2:
        dates = [h["date"] for h in history]
        scores = [h["score"] for h in history]
        colors = ["#30D158" if s >= 80 else "#FFD60A" if s >= 60 else "#FF453A" for s in scores]

        fig = go.Figure()

        # Zone backgrounds
        fig.add_hrect(y0=80, y1=100, fillcolor="#30D158", opacity=0.08, line_width=0)
        fig.add_hrect(y0=60, y1=80, fillcolor="#FFD60A", opacity=0.06, line_width=0)
        fig.add_hrect(y0=0, y1=60, fillcolor="#FF453A", opacity=0.05, line_width=0)

        fig.add_trace(go.Scatter(
            x=dates, y=scores,
            mode="lines+markers",
            line=dict(color="#BF5AF2", width=2),
            marker=dict(size=6, color=colors),
            hovertemplate="Score: %{y}<br>%{x}<extra></extra>",
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#1C1C1E",
            font=dict(family=A["font_text"]),
            margin=dict(l=40, r=20, t=20, b=40),
            height=300,
            xaxis=dict(gridcolor="rgba(84,84,88,0.3)"),
            yaxis=dict(title="Recovery Score", range=[0, 105], gridcolor="rgba(84,84,88,0.3)"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Not enough historical data for trend chart. Keep logging daily!")
