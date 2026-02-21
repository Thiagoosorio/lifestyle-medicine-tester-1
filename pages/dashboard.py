import random
import streamlit as st
from config.settings import PILLARS, MOTIVATIONAL_QUOTES, get_score_label, get_score_color
from services.wheel_service import get_current_wheel, get_total_score, get_score_summary
from components.wheel_chart import create_wheel_chart
from components.metrics_row import render_metrics_row
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

    render_metrics_row([
        {"label": "Current Streak", "value": f"{streak} days", "help": "Consecutive days with a check-in"},
        {"label": "Habits Today", "value": f"{habits_done}/{habits_total}", "help": "Habits completed today"},
        {"label": "Active Goals", "value": str(active_goals)},
        {"label": "Total Wheel Score", "value": f"{get_total_score(scores)}/60"},
        {"label": ":material/stars: LifeCoins", "value": str(coins), "help": "Earn coins by completing daily check-ins, habits, and staying consistent"},
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
