import random
import streamlit as st
import plotly.graph_objects as go
from config.settings import PILLARS, MOTIVATIONAL_QUOTES, get_score_label, get_score_color
from services.wheel_service import get_current_wheel, get_total_score, get_score_summary
from components.wheel_chart import create_wheel_chart
from components.metrics_row import render_metrics_row
from components.custom_theme import render_hero_stats
from services.nudge_engine import get_active_nudges
from services.coin_service import get_coin_balance, award_daily_coins
from db.database import get_connection

user_id = st.session_state.user_id
display_name = st.session_state.get("display_name", "there")

# ── Header ──────────────────────────────────────────────────────────────────
st.title(f"Welcome back, {display_name}!")
st.markdown(f"*{random.choice(MOTIVATIONAL_QUOTES)}*")

# ── Future Self Letter Delivery ─────────────────────────────────────────────
from datetime import date as _date
_today_str = _date.today().isoformat()
_conn_letters = get_connection()
try:
    _due = _conn_letters.execute(
        "SELECT * FROM future_self_letters WHERE user_id = ? AND delivered = 0 AND delivery_date <= ?",
        (user_id, _today_str),
    ).fetchall()
    if _due:
        for _letter in _due:
            _l = dict(_letter)
            st.success(f":love_letter: **A letter from your past self has arrived!** (Written {_l['created_at'][:10]})")
            st.markdown(f"> {_l['letter_text']}")
            _conn_letters.execute("UPDATE future_self_letters SET delivered = 1 WHERE id = ?", (_l["id"],))
        _conn_letters.commit()
except Exception:
    pass
finally:
    _conn_letters.close()

# ── Proactive Nudges ────────────────────────────────────────────────────────
nudges = get_active_nudges(user_id)
if nudges:
    for nudge in nudges:
        col_msg, col_btn = st.columns([4, 1])
        with col_msg:
            if nudge["color"] == "warning":
                st.warning(f"{nudge['icon']} **{nudge['title']}** — {nudge['message']}")
            elif nudge["color"] == "error":
                st.error(f"{nudge['icon']} **{nudge['title']}** — {nudge['message']}")
            else:
                st.info(f"{nudge['icon']} **{nudge['title']}** — {nudge['message']}")
        with col_btn:
            if nudge.get("action_label") and nudge.get("action_page"):
                if st.button(nudge["action_label"], key=f"nudge_{nudge['type']}", use_container_width=True):
                    st.switch_page(nudge["action_page"])

st.divider()

# ── Current Wheel ───────────────────────────────────────────────────────────
assessment = get_current_wheel(user_id)

if not assessment:
    st.info("You haven't taken a Wheel of Life assessment yet.")
    st.markdown("Start by assessing where you stand across the **6 pillars of lifestyle medicine**.")
    if st.button("Take Your First Assessment", type="primary", use_container_width=True):
        st.switch_page("pages/wheel_assessment.py")
else:
    scores = assessment["scores"]

    # Metrics row
    conn = get_connection()
    try:
        # Active goals count
        goals_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM goals WHERE user_id = ? AND status = 'active'", (user_id,)
        ).fetchone()
        active_goals = goals_row["cnt"]

        # Habits completed today
        from datetime import date
        today = date.today().isoformat()
        habits_total = conn.execute(
            "SELECT COUNT(*) as cnt FROM habits WHERE user_id = ? AND is_active = 1", (user_id,)
        ).fetchone()["cnt"]
        habits_done = conn.execute(
            "SELECT COUNT(*) as cnt FROM habit_log WHERE user_id = ? AND log_date = ? AND completed_count > 0",
            (user_id, today),
        ).fetchone()["cnt"]

        # Streak (consecutive days with a check-in)
        checkin_dates = conn.execute(
            "SELECT DISTINCT checkin_date FROM daily_checkins WHERE user_id = ? ORDER BY checkin_date DESC",
            (user_id,),
        ).fetchall()
        streak = 0
        if checkin_dates:
            from datetime import timedelta
            expected = date.today()
            for row in checkin_dates:
                d = date.fromisoformat(row["checkin_date"])
                if d == expected:
                    streak += 1
                    expected -= timedelta(days=1)
                elif d < expected:
                    break
    finally:
        conn.close()

    coins = get_coin_balance(user_id)

    render_hero_stats([
        {"label": "Current Streak", "value": f"{streak} days", "icon": "\U0001f525", "color": "#FF9800"},
        {"label": "Habits Today", "value": f"{habits_done}/{habits_total}", "icon": "\u2705", "color": "#4CAF50"},
        {"label": "Active Goals", "value": str(active_goals), "icon": "\U0001f3af", "color": "#2196F3"},
        {"label": "Wheel Score", "value": f"{get_total_score(scores)}/60", "icon": "\U0001f3a1", "color": "#9C27B0"},
        {"label": "LifeCoins", "value": str(coins), "icon": "\u2b50", "color": "#FFD700"},
    ])

    st.divider()

    # Wheel + pillar breakdown
    col_wheel, col_details = st.columns([3, 2])

    with col_wheel:
        fig = create_wheel_chart(scores)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(get_score_summary(scores))

    with col_details:
        st.markdown("### Pillar Breakdown")
        for pid in sorted(scores.keys()):
            score = scores[pid]
            label = get_score_label(score)
            color = get_score_color(score)
            pct = score * 10
            st.markdown(
                f"**{PILLARS[pid]['icon']} {PILLARS[pid]['display_name']}** — {score}/10 ({label})"
            )
            st.progress(pct / 100)

        st.divider()
        if st.button("Take New Assessment", use_container_width=True):
            st.switch_page("pages/wheel_assessment.py")

    # ── 14-Day Sparkline Trends ──────────────────────────────────────────────
    st.divider()
    st.markdown("### 14-Day Snapshot")

    from datetime import timedelta as _td
    _spark_start = (date.today() - _td(days=13)).isoformat()
    conn = get_connection()
    try:
        _spark_rows = conn.execute(
            "SELECT checkin_date, mood, energy FROM daily_checkins WHERE user_id = ? AND checkin_date >= ? ORDER BY checkin_date",
            (user_id, _spark_start),
        ).fetchall()
        _habit_rates = []
        for i in range(14):
            _d = (date.today() - _td(days=13 - i)).isoformat()
            _htotal = conn.execute(
                "SELECT COUNT(*) as c FROM habits WHERE user_id = ? AND is_active = 1", (user_id,)
            ).fetchone()["c"]
            _hdone = conn.execute(
                "SELECT COUNT(*) as c FROM habit_log WHERE user_id = ? AND log_date = ? AND completed_count > 0",
                (user_id, _d),
            ).fetchone()["c"]
            _habit_rates.append((_d, _hdone / _htotal if _htotal > 0 else 0))
    finally:
        conn.close()

    spark_col1, spark_col2 = st.columns(2)

    with spark_col1:
        if _spark_rows:
            _dates = [r["checkin_date"] for r in _spark_rows]
            _moods = [r["mood"] for r in _spark_rows]
            _energies = [r["energy"] for r in _spark_rows]
            _fig_spark = go.Figure()
            _fig_spark.add_trace(go.Scatter(
                x=_dates, y=_moods, mode='lines',
                name='Mood', line=dict(color='#FF9800', width=2.5),
                fill='tozeroy', fillcolor='rgba(255,152,0,0.08)',
            ))
            _fig_spark.add_trace(go.Scatter(
                x=_dates, y=_energies, mode='lines',
                name='Energy', line=dict(color='#2196F3', width=2.5),
                fill='tozeroy', fillcolor='rgba(33,150,243,0.08)',
            ))
            _fig_spark.update_layout(
                height=160, margin=dict(t=5, b=20, l=30, r=10),
                yaxis=dict(range=[0, 10.5], showgrid=False, dtick=5),
                xaxis=dict(showgrid=False, tickformat="%b %d"),
                legend=dict(orientation="h", yanchor="top", y=1.15, xanchor="center", x=0.5, font=dict(size=10)),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(_fig_spark, use_container_width=True, key="spark_mood")
        else:
            st.caption("No check-ins yet — start logging to see mood & energy trends.")

    with spark_col2:
        if any(r[1] > 0 for r in _habit_rates):
            _h_dates = [r[0] for r in _habit_rates]
            _h_vals = [round(r[1] * 100) for r in _habit_rates]
            _bar_colors = ['#4CAF50' if v >= 80 else '#FF9800' if v >= 50 else '#F44336' for v in _h_vals]
            _fig_hab = go.Figure()
            _fig_hab.add_trace(go.Bar(
                x=_h_dates, y=_h_vals,
                marker_color=_bar_colors,
                text=[f"{v}%" for v in _h_vals],
                textposition='outside', textfont=dict(size=8),
            ))
            _fig_hab.update_layout(
                height=160, margin=dict(t=5, b=20, l=30, r=10),
                yaxis=dict(range=[0, 115], showgrid=False, title=""),
                xaxis=dict(showgrid=False, tickformat="%b %d"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            st.plotly_chart(_fig_hab, use_container_width=True, key="spark_habits")
        else:
            st.caption("No habit data yet — track habits to see your daily completion rates.")

    # ── Today's check-in widget ─────────────────────────────────────────────
    st.divider()
    st.markdown("### Quick Daily Check-in")
    conn = get_connection()
    try:
        today_checkin = conn.execute(
            "SELECT * FROM daily_checkins WHERE user_id = ? AND checkin_date = ?",
            (user_id, today),
        ).fetchone()
    finally:
        conn.close()

    if today_checkin:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mood", f"{today_checkin['mood']}/10")
        with col2:
            st.metric("Energy", f"{today_checkin['energy']}/10")
        with col3:
            if today_checkin["journal_entry"]:
                st.markdown(f"**Journal:** {today_checkin['journal_entry'][:100]}...")
        st.success("Today's check-in complete!")

        # Award daily coins
        award_daily_coins(user_id, today)

        # Post-check-in AI insight
        from services.insight_service import get_or_generate_insight
        insight = get_or_generate_insight(user_id, today)
        if insight:
            st.info(f":material/psychology: **Today's Insight** — {insight}")
    else:
        st.caption("How are you feeling today?")
        with st.form("quick_checkin"):
            qc1, qc2 = st.columns(2)
            with qc1:
                mood = st.slider("Mood", 1, 10, 5)
            with qc2:
                energy = st.slider("Energy", 1, 10, 5)
            journal = st.text_area("How was your day? (optional)", height=68)
            if st.form_submit_button("Save Check-in", use_container_width=True):
                conn = get_connection()
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO daily_checkins (user_id, checkin_date, mood, energy, journal_entry) VALUES (?, ?, ?, ?, ?)",
                        (user_id, today, mood, energy, journal),
                    )
                    conn.commit()
                finally:
                    conn.close()
                award_daily_coins(user_id, today)
                st.toast(":material/stars: +1 LifeCoin for checking in!")
                st.rerun()

    # ── Active goals summary ────────────────────────────────────────────────
    st.divider()
    st.markdown("### Active Goals")
    conn = get_connection()
    try:
        active = conn.execute(
            "SELECT * FROM goals WHERE user_id = ? AND status = 'active' ORDER BY target_date ASC LIMIT 5",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not active:
        st.caption("No active goals yet.")
        if st.button("Set Your First Goal", use_container_width=True):
            st.switch_page("pages/goals.py")
    else:
        for goal in active:
            g = dict(goal)
            col_g, col_p = st.columns([3, 1])
            with col_g:
                pillar_name = PILLARS.get(g["pillar_id"], {}).get("display_name", "")
                st.markdown(f"**{g['title']}** — *{pillar_name}*")
            with col_p:
                st.progress(g["progress_pct"] / 100)
                st.caption(f"{g['progress_pct']}% — Due: {g['target_date'][:10]}")

    # ── Today's Micro-Lesson ──────────────────────────────────────────────────
    st.divider()
    st.markdown("### Today's Micro-Lesson")
    conn = get_connection()
    try:
        # Find first uncompleted lesson
        completed_ids = [r["lesson_id"] for r in conn.execute(
            "SELECT lesson_id FROM user_lesson_progress WHERE user_id = ?", (user_id,)
        ).fetchall()]
        all_lessons = conn.execute(
            "SELECT id, title, pillar_id, lesson_type FROM micro_lessons ORDER BY pillar_id, id"
        ).fetchall()
        next_lesson = None
        for l in all_lessons:
            if l["id"] not in completed_ids:
                next_lesson = dict(l)
                break
        total_lessons = len(all_lessons)
        done_lessons = len(completed_ids)
    finally:
        conn.close()

    if next_lesson:
        pillar_name = PILLARS.get(next_lesson["pillar_id"], {}).get("display_name", "")
        ltype = {"article": "Read", "exercise": "Practice", "reflection": "Reflect"}.get(next_lesson.get("lesson_type", ""), "Learn")
        lesson_col1, lesson_col2 = st.columns([3, 1])
        with lesson_col1:
            st.markdown(f":book: **{next_lesson['title']}** — *{pillar_name}* ({ltype})")
            st.caption(f"{done_lessons}/{total_lessons} lessons completed")
        with lesson_col2:
            if st.button("Start Lesson", use_container_width=True, key="start_lesson_dash"):
                st.switch_page("pages/lessons.py")
    elif total_lessons > 0:
        st.success(f"All {total_lessons} lessons completed! You're a lifestyle medicine expert.")
    else:
        st.caption("Lessons will appear once the content is loaded.")

    # ── Smart Insights Widget ──────────────────────────────────────────────
    st.divider()
    st.markdown("### Smart Insights")
    try:
        from components.smart_insights import render_smart_insights
        render_smart_insights(user_id)
    except Exception:
        st.caption("Insights will appear once you have enough check-in data.")
