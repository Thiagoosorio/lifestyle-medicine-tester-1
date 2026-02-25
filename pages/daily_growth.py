"""Daily Growth: Meditation, Quotes & Mindfulness — a moment of stillness in your day."""

import streamlit as st
from datetime import date
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from components.growth_display import (
    render_quote_card,
    render_nudge_card,
    render_meditation_streak,
    render_meditation_log_summary,
    render_session_row,
    render_mini_quote,
)
from services.growth_service import (
    get_daily_nudge,
    acknowledge_nudge,
    is_nudge_acknowledged,
    get_daily_quote,
    get_extra_quotes,
    save_quote_reflection,
    toggle_favorite_quote,
    get_quote_favorite_status,
    get_existing_reflection,
    get_favorite_quotes,
    log_meditation,
    get_meditation_streak,
    get_meditation_history,
    get_meditation_stats,
)
from config.growth_data import MEDITATION_TYPES, MOOD_LABELS

A = APPLE
user_id = st.session_state.user_id
today_str = date.today().isoformat()

render_hero_banner("Daily Growth", "A moment of stillness in your day")

# ══════════════════════════════════════════════════════════════════════════════
# Section 1: Mindfulness Nudge
# ══════════════════════════════════════════════════════════════════════════════
render_section_header("Mindfulness Moment")

nudge = get_daily_nudge(user_id)
render_nudge_card(nudge["text"])

nudge_acked = is_nudge_acknowledged(user_id, nudge["index"], today_str)
if nudge_acked:
    st.caption("Noted for today.")
else:
    if st.button("Noted", key="ack_nudge"):
        acknowledge_nudge(user_id, nudge["index"], today_str)
        st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# Section 2: Daily Quote + Reflection
# ══════════════════════════════════════════════════════════════════════════════
render_section_header("Today's Reflection")

quote = get_daily_quote(user_id)
render_quote_card(quote, reflection_prompt=quote["reflection_prompt"])

# Favorite button
is_fav = get_quote_favorite_status(user_id, quote["index"], today_str)
fav_label = "Saved" if is_fav else "Save to favorites"
col_fav, col_spacer = st.columns([1, 3])
with col_fav:
    if st.button(fav_label, key="toggle_fav"):
        toggle_favorite_quote(user_id, quote["index"], today_str)
        st.rerun()

# Reflection text area
existing_reflection = get_existing_reflection(user_id, quote["index"], today_str)
with st.form("reflection_form"):
    reflection_text = st.text_area(
        "Your reflection",
        value=existing_reflection or "",
        height=100,
        placeholder="What does this bring to mind? There is no wrong answer.",
        label_visibility="collapsed",
    )
    if st.form_submit_button("Save Reflection", use_container_width=True):
        if reflection_text.strip():
            save_quote_reflection(user_id, quote["index"], today_str, reflection_text.strip())
            st.toast("Reflection saved.")
            st.rerun()

# More quotes expander
with st.expander("More quotes"):
    extras = get_extra_quotes(user_id, count=4)
    for eq in extras:
        render_mini_quote(eq)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# Section 3: Log Meditation Session
# ══════════════════════════════════════════════════════════════════════════════
render_section_header("Log Meditation")

streak = get_meditation_streak(user_id)
stats = get_meditation_stats(user_id, days=30)

col_form, col_streak = st.columns([3, 1])

with col_streak:
    render_meditation_streak(streak, total_sessions=stats["total_sessions"])

with col_form:
    with st.form("meditation_form"):
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=180, value=10, step=1)
            med_type_labels = {k: v["label"] for k, v in MEDITATION_TYPES.items()}
            med_type = st.selectbox(
                "Type",
                options=list(med_type_labels.keys()),
                format_func=lambda x: med_type_labels[x],
            )
        with m_col2:
            mood_options = list(MOOD_LABELS.keys())
            mood_labels_list = [MOOD_LABELS[k] for k in mood_options]
            mood_before = st.select_slider(
                "Mood before",
                options=mood_options,
                format_func=lambda x: MOOD_LABELS[x],
                value=3,
            )
            mood_after = st.select_slider(
                "Mood after",
                options=mood_options,
                format_func=lambda x: MOOD_LABELS[x],
                value=4,
            )
        notes = st.text_input("Notes (optional)", placeholder="How was the session?")

        if st.form_submit_button("Log Session", use_container_width=True):
            log_meditation(
                user_id, today_str, duration, med_type,
                mood_before=mood_before, mood_after=mood_after,
                notes=notes if notes.strip() else None,
            )
            st.toast("Meditation session logged.")
            st.rerun()

# Recent sessions (last 7 days)
history = get_meditation_history(user_id, days=7)
if history:
    st.caption("Recent sessions")
    for session in history[:7]:
        render_session_row(session)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# Section 4: Your Journey (collapsed)
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("Your Journey"):
    # Stats
    all_stats = get_meditation_stats(user_id, days=30)
    render_meditation_log_summary(all_stats)

    # Type breakdown
    if all_stats and all_stats.get("type_breakdown"):
        breakdown_parts = []
        for t, cnt in all_stats["type_breakdown"].items():
            label = MEDITATION_TYPES.get(t, {}).get("label", t)
            breakdown_parts.append(f"{label}: {cnt}")
        if breakdown_parts:
            breakdown_html = (
                f'<div style="font-size:12px;color:{A["label_tertiary"]};'
                f'margin-bottom:12px">{" &middot; ".join(breakdown_parts)}</div>'
            )
            st.markdown(breakdown_html, unsafe_allow_html=True)

    # Mood trend
    full_history = get_meditation_history(user_id, days=30)
    mood_data = [(s["session_date"], s["mood_after"]) for s in full_history if s.get("mood_after")]
    if len(mood_data) >= 3:
        import plotly.graph_objects as go
        dates = [d[0] for d in reversed(mood_data)]
        moods = [d[1] for d in reversed(mood_data)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=moods, mode="lines+markers",
            line=dict(color=A["teal"], width=2),
            marker=dict(size=6, color=A["teal"]),
            hovertemplate="Mood: %{y}<br>%{x}<extra></extra>",
        ))
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=A["chart_bg"],
            font=dict(family=A["font_text"], color=A["chart_text"]),
            margin=dict(l=30, r=10, t=10, b=30),
            height=180,
            xaxis=dict(gridcolor=A["chart_grid"]),
            yaxis=dict(title="Mood", range=[0.5, 5.5], gridcolor=A["chart_grid"],
                       tickvals=[1, 2, 3, 4, 5], ticktext=["Agitated", "Restless", "Neutral", "Calm", "Very calm"]),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Favorite quotes
    favs = get_favorite_quotes(user_id)
    if favs:
        fav_header_html = (
            f'<div style="font-size:13px;font-weight:600;color:{A["label_secondary"]};'
            f'margin-top:12px;margin-bottom:8px">Saved Quotes</div>'
        )
        st.markdown(fav_header_html, unsafe_allow_html=True)
        for fq in favs:
            render_mini_quote(fq)
