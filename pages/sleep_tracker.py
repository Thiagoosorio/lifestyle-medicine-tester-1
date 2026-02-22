"""Sleep Tracker — Log sleep, view scores, discover your chronotype."""

import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from components.sleep_display import (
    render_sleep_score_circle,
    render_chronotype_card,
    render_sleep_stat_cards,
    render_sleep_hygiene_tips,
)
from config.sleep_data import MEQ_QUESTIONS, CHRONOTYPES
from services.sleep_service import (
    log_sleep,
    get_sleep_history,
    get_all_sleep_history,
    get_sleep_averages,
    get_latest_sleep_score,
    assess_chronotype,
    get_chronotype,
    analyze_sleep_hygiene,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Sleep Tracker",
    "Quality sleep is the foundation of recovery. Track your patterns, discover your chronotype, and optimize your rest."
)

tab_dashboard, tab_log, tab_chronotype, tab_trends, tab_hygiene = st.tabs([
    "Dashboard", "Log Sleep", "Chronotype", "Trends", "Sleep Hygiene"
])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Dashboard
# ══════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    score = get_latest_sleep_score(user_id)
    averages = get_sleep_averages(user_id, days=30)

    if not averages or not averages.get("log_count"):
        st.info("No sleep data yet. Go to the **Log Sleep** tab to record your first night.")
    else:
        col_score, col_stats = st.columns([1, 2])
        with col_score:
            render_sleep_score_circle(score)
        with col_stats:
            render_sleep_stat_cards(averages)

            # Chronotype badge
            chrono = get_chronotype(user_id)
            if chrono:
                cdata = chrono.get("data", {})
                badge_html = (
                    f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                    f'border-radius:{A["radius_md"]};padding:10px 14px;display:inline-flex;'
                    f'align-items:center;gap:8px">'
                    f'<span style="font-size:18px">{cdata.get("icon", "")}</span>'
                    f'<span style="font-size:13px;font-weight:600;color:{cdata.get("color", A["blue"])}">'
                    f'{cdata.get("name", "")} Chronotype</span>'
                    f'</div>'
                )
                st.markdown(badge_html, unsafe_allow_html=True)

        # Recent sleep log
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        render_section_header("Recent Sleep", "Last 7 nights")

        recent = get_sleep_history(user_id, days=7)
        if recent:
            for s in recent:
                hours = s["total_sleep_min"] // 60 if s.get("total_sleep_min") else 0
                mins = s["total_sleep_min"] % 60 if s.get("total_sleep_min") else 0
                sc = s.get("sleep_score", 0)
                if sc >= 85:
                    sc_color = "#30D158"
                elif sc >= 70:
                    sc_color = "#64D2FF"
                elif sc >= 50:
                    sc_color = "#FFD60A"
                else:
                    sc_color = "#FF453A"

                eff = s.get("sleep_efficiency", 0)
                row_html = (
                    f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                    f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:6px;'
                    f'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">'
                    f'<div style="font-size:13px;color:{A["label_secondary"]};min-width:90px">'
                    f'{s["sleep_date"]}</div>'
                    f'<div style="font-size:13px;color:{A["label_primary"]};font-weight:600">'
                    f'{hours}h {mins}m</div>'
                    f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
                    f'{s.get("bedtime", "")} &#8594; {s.get("wake_time", "")}</div>'
                    f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
                    f'Eff: {eff:.0f}%</div>'
                    f'<div style="font-size:14px;font-weight:700;color:{sc_color};'
                    f'min-width:40px;text-align:right">{sc}</div>'
                    f'</div>'
                )
                st.markdown(row_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Log Sleep
# ══════════════════════════════════════════════════════════════════════════
with tab_log:
    render_section_header("Log Last Night's Sleep")

    with st.form("sleep_log_form"):
        sleep_date = st.date_input("Date", value=date.today())

        col1, col2 = st.columns(2)
        with col1:
            bedtime = st.time_input("Bedtime", value=None)
        with col2:
            wake_time = st.time_input("Wake Time", value=None)

        col3, col4 = st.columns(2)
        with col3:
            latency = st.number_input("Time to fall asleep (min)", min_value=0, max_value=180, value=15)
        with col4:
            awakenings = st.number_input("Night awakenings", min_value=0, max_value=20, value=1)

        wake_dur = st.number_input("Total time awake during night (min)", min_value=0, max_value=180, value=0)
        quality = st.slider("Subjective sleep quality", min_value=1, max_value=5, value=3,
                            help="1=Very Poor, 2=Poor, 3=Fair, 4=Good, 5=Excellent")
        naps = st.number_input("Nap time today (min)", min_value=0, max_value=180, value=0)

        st.markdown("**Sleep Hygiene Factors**")
        col5, col6 = st.columns(2)
        with col5:
            caffeine = st.time_input("Last caffeine", value=None, help="Leave empty if no caffeine")
        with col6:
            screens = st.time_input("Last screen time", value=None, help="Leave empty if unknown")

        col7, col8 = st.columns(2)
        with col7:
            alcohol = st.checkbox("Alcohol before bed")
        with col8:
            exercise = st.checkbox("Exercised today")

        notes = st.text_area("Notes (optional)", placeholder="How did you feel? Any factors affecting sleep?")

        submitted = st.form_submit_button("Save Sleep Log", use_container_width=True)
        if submitted:
            if bedtime is None or wake_time is None:
                st.warning("Please enter both bedtime and wake time.")
            else:
                result = log_sleep(
                    user_id=user_id,
                    sleep_date=sleep_date.isoformat(),
                    bedtime=bedtime.strftime("%H:%M"),
                    wake_time=wake_time.strftime("%H:%M"),
                    sleep_latency_min=latency,
                    awakenings=awakenings,
                    wake_duration_min=wake_dur,
                    sleep_quality=quality,
                    naps_min=naps,
                    caffeine_cutoff=caffeine.strftime("%H:%M") if caffeine else None,
                    screen_cutoff=screens.strftime("%H:%M") if screens else None,
                    alcohol=1 if alcohol else 0,
                    exercise_today=1 if exercise else 0,
                    notes=notes if notes else None,
                )
                st.toast(f"Sleep logged! Score: {result['score']}/100")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: Chronotype
# ══════════════════════════════════════════════════════════════════════════
with tab_chronotype:
    render_section_header("Your Chronotype", "Based on the Horne-Ostberg MEQ (PMID: 1027738)")

    existing = get_chronotype(user_id)
    if existing:
        render_chronotype_card(existing)

        if st.button("Retake Quiz"):
            st.session_state["retake_chrono"] = True
            st.rerun()

    if not existing or st.session_state.get("retake_chrono"):
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        render_section_header("Chronotype Quiz", "5 quick questions to find your sleep type")

        with st.form("chronotype_quiz"):
            answers = []
            for q in MEQ_QUESTIONS:
                option_labels = [opt["label"] for opt in q["options"]]
                choice = st.radio(q["question"], option_labels, key=f"meq_{q['id']}")
                score = next(opt["score"] for opt in q["options"] if opt["label"] == choice)
                answers.append(score)

            if st.form_submit_button("Find My Chronotype", use_container_width=True):
                result = assess_chronotype(user_id, answers)
                st.session_state.pop("retake_chrono", None)
                st.toast(f"You're a {result['data']['name']}! ({result['data']['subtitle']})")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# Tab 4: Trends
# ══════════════════════════════════════════════════════════════════════════
with tab_trends:
    render_section_header("Sleep Trends", "Your sleep patterns over time")

    history = get_all_sleep_history(user_id)
    if not history:
        st.caption("Not enough data for trends yet. Keep logging!")
    else:
        dates = [h["sleep_date"] for h in history]
        scores = [h.get("sleep_score", 0) for h in history]
        durations = [h.get("total_sleep_min", 0) / 60 for h in history]
        efficiencies = [h.get("sleep_efficiency", 0) for h in history]

        metric = st.selectbox("Metric", ["Sleep Score", "Duration (hours)", "Efficiency (%)"])

        if metric == "Sleep Score":
            y_data = scores
            y_title = "Score"
            color = "#BF5AF2"
        elif metric == "Duration (hours)":
            y_data = durations
            y_title = "Hours"
            color = "#0A84FF"
        else:
            y_data = efficiencies
            y_title = "Efficiency %"
            color = "#30D158"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=y_data,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=5, color=color),
            hovertemplate="%{y:.1f}<br>%{x}<extra></extra>",
        ))

        # Add reference lines for duration
        if metric == "Duration (hours)":
            fig.add_hline(y=7, line_dash="dash", line_color="#30D158", opacity=0.5,
                          annotation_text="7h min", annotation_position="bottom left")
            fig.add_hline(y=9, line_dash="dash", line_color="#30D158", opacity=0.5,
                          annotation_text="9h max", annotation_position="top left")

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#1C1C1E",
            font=dict(family=A["font_text"]),
            margin=dict(l=40, r=20, t=30, b=40),
            height=320,
            xaxis=dict(gridcolor="rgba(84,84,88,0.3)"),
            yaxis=dict(title=y_title, gridcolor="rgba(84,84,88,0.3)"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 5: Sleep Hygiene
# ══════════════════════════════════════════════════════════════════════════
with tab_hygiene:
    render_section_header("Sleep Hygiene Analysis", "Personalized tips based on your data")

    tips = analyze_sleep_hygiene(user_id, days=14)
    if tips:
        render_sleep_hygiene_tips(tips)
    else:
        st.caption("Log at least a few nights of sleep to get personalized recommendations.")

    # General tips always shown
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_section_header("Evidence-Based Sleep Tips")

    from config.sleep_data import SLEEP_HYGIENE_TIPS
    for key, tip in SLEEP_HYGIENE_TIPS.items():
        tip_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:12px;margin-bottom:8px">'
            f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]};'
            f'margin-bottom:4px">{tip["tip"]}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
            f'{tip["evidence"]}</div>'
            f'</div>'
        )
        st.markdown(tip_html, unsafe_allow_html=True)
