import random
import streamlit as st
import plotly.graph_objects as go
from config.settings import PILLARS, MOTIVATIONAL_QUOTES, get_score_label, get_score_color
from services.wheel_service import get_current_wheel, get_total_score, get_score_summary
from components.wheel_chart import create_wheel_chart
from components.custom_theme import APPLE, render_hero_stats, render_hero_banner, render_section_header
from services.nudge_engine import get_active_nudges
from services.coin_service import get_coin_balance, award_daily_coins
from db.database import get_connection
from services.sleep_service import get_sleep_history as _get_sleep_hist
from services.recovery_service import calculate_recovery_score as _calc_recovery
from services.body_metrics_service import get_latest_metrics as _get_latest_bm
from services.fasting_service import get_active_fast as _get_active_fast

A = APPLE
user_id = st.session_state.user_id
display_name = st.session_state.get("display_name", "there")

# ══════════════════════════════════════════════════════════════════════════════
# HERO BANNER — Fitness+ gradient with Apple HIG typography
# ══════════════════════════════════════════════════════════════════════════════
quote = random.choice(MOTIVATIONAL_QUOTES)
render_hero_banner(f"Welcome back, {display_name}!", quote)


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

# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════
assessment = get_current_wheel(user_id)

if not assessment:
    # ── Empty State — Take First Assessment CTA ──────────────────────────
    cta_html = (
        f'<div style="border-radius:{A["radius_xl"]};padding:40px;text-align:center;'
        f'margin-bottom:24px;background:rgba(94,92,230,0.10);'
        f'border:1px solid rgba(94,92,230,0.20)">'
        f'<div style="font-size:2.5rem;margin-bottom:12px">&#127905;</div>'
        f'<div style="font-family:{A["font_display"]};font-size:20px;line-height:24px;'
        f'font-weight:600;color:{A["label_primary"]};margin-bottom:8px">Start Your Journey</div>'
        f'<div style="font-size:15px;line-height:20px;color:{A["label_secondary"]};'
        f'max-width:420px;margin:0 auto 20px auto">'
        f'Assess where you stand across the 6 pillars of lifestyle medicine '
        f'and begin your transformation.</div>'
        f'</div>'
    )
    st.markdown(cta_html, unsafe_allow_html=True)
    if st.button("Take Your First Assessment", type="primary", use_container_width=True):
        st.switch_page("pages/wheel_assessment.py")
else:
    scores = assessment["scores"]

    # ── Fetch Stats ──────────────────────────────────────────────────────
    conn = get_connection()
    try:
        active_goals = conn.execute(
            "SELECT COUNT(*) as cnt FROM goals WHERE user_id = ? AND status = 'active'", (user_id,)
        ).fetchone()["cnt"]

        from datetime import date
        today = date.today().isoformat()
        habits_total = conn.execute(
            "SELECT COUNT(*) as cnt FROM habits WHERE user_id = ? AND is_active = 1", (user_id,)
        ).fetchone()["cnt"]
        habits_done = conn.execute(
            "SELECT COUNT(*) as cnt FROM habit_log WHERE user_id = ? AND log_date = ? AND completed_count > 0",
            (user_id, today),
        ).fetchone()["cnt"]

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

    # ── Extra health stats ────────────────────────────────────────────────
    _sleep_val = "--"
    try:
        _sl = _get_sleep_hist(user_id, days=1)
        if _sl:
            _sleep_val = f"{_sl[0].get('sleep_score', 0)}/100"
    except Exception:
        pass

    _recovery_val = "--"
    _recovery_color = "#64D2FF"
    try:
        _rec = _calc_recovery(user_id)
        if _rec:
            _recovery_val = str(_rec["score"])
            _recovery_color = _rec["zone"]["color"]
    except Exception:
        pass

    _weight_val = "--"
    try:
        _bm = _get_latest_bm(user_id)
        if _bm and _bm.get("weight_kg"):
            _weight_val = f"{_bm['weight_kg']:.1f}kg"
    except Exception:
        pass

    # ── Hero Stat Cards (Apple Health colors) ────────────────────────────
    _hero_cards = [
        {"label": "Current Streak", "value": f"{streak} days", "icon": "\U0001f525", "color": "#FA2D55"},
        {"label": "Habits Today", "value": f"{habits_done}/{habits_total}", "icon": "\u2705", "color": "#34C759"},
        {"label": "Active Goals", "value": str(active_goals), "icon": "\U0001f3af", "color": "#5E5CE6"},
        {"label": "Wheel Score", "value": f"{get_total_score(scores)}/60", "icon": "\U0001f3a1", "color": "#BF5AF2"},
        {"label": "Sleep Score", "value": _sleep_val, "icon": "\U0001f319", "color": "#5E5CE6"},
        {"label": "Recovery", "value": _recovery_val, "icon": "\u2764\ufe0f", "color": _recovery_color},
        {"label": "Weight", "value": _weight_val, "icon": "\u2696\ufe0f", "color": "#64D2FF"},
        {"label": "LifeCoins", "value": str(coins), "icon": "\u2b50", "color": "#FFD60A"},
    ]

    # If actively fasting, replace LifeCoins with fast timer
    try:
        _af = _get_active_fast(user_id)
        if _af:
            _elapsed = _af.get("elapsed_hours", 0)
            _hero_cards[-1] = {"label": "Fasting", "value": f"{_elapsed:.1f}h", "icon": "\u23f1\ufe0f", "color": "#FF9F0A"}
    except Exception:
        pass

    render_hero_stats(_hero_cards)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Today's Protocols Checklist ────────────────────────────────────────
    from services.protocol_service import get_daily_protocol_status, log_protocol_completion
    _proto_status = get_daily_protocol_status(user_id, today)
    if _proto_status:
        render_section_header("Today's Protocols", "Science-backed daily actions")
        _done_count = sum(1 for p in _proto_status if p["completed"])
        _total_count = len(_proto_status)
        _pct = round(_done_count / _total_count * 100) if _total_count else 0
        _bar_color = "#34C759" if _pct >= 80 else "#FF9F0A" if _pct >= 50 else "#FF453A"
        _progress_html = (
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">'
            f'<div style="flex:1;height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden">'
            f'<div style="width:{_pct}%;height:100%;background:{_bar_color};border-radius:3px"></div>'
            f'</div>'
            f'<span style="font-size:13px;font-weight:600;color:{_bar_color}">{_done_count}/{_total_count}</span>'
            f'</div>'
        )
        st.markdown(_progress_html, unsafe_allow_html=True)
        for _p in _proto_status:
            _pcol1, _pcol2 = st.columns([1, 5])
            with _pcol1:
                _checked = st.checkbox(
                    "done", value=bool(_p["completed"]),
                    key=f"dash_proto_{_p['protocol_id']}",
                    label_visibility="collapsed",
                )
                if _checked != bool(_p["completed"]):
                    log_protocol_completion(user_id, _p["protocol_id"], today, int(_checked))
                    st.rerun()
            with _pcol2:
                _pil = PILLARS.get(_p["pillar_id"], {})
                _pil_color = _pil.get("color", "#888")
                _pil_emoji = {1: "&#127813;", 2: "&#127939;", 3: "&#127769;", 4: "&#129502;", 5: "&#128101;", 6: "&#128683;"}.get(_p["pillar_id"], "")
                _timing = f' &middot; {_p["timing"]}' if _p.get("timing") else ""
                _line_style = f"text-decoration:line-through;opacity:0.5" if _p["completed"] else ""
                _proto_html = (
                    f'<div style="font-size:14px;line-height:20px;{_line_style}">'
                    f'<span style="color:{_pil_color};font-weight:600">{_pil_emoji} </span>'
                    f'<span style="color:{A["label_primary"]}">{_p["name"]}</span>'
                    f'<span style="color:{A["label_tertiary"]};font-size:12px">{_timing}</span>'
                    f'</div>'
                )
                st.markdown(_proto_html, unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Wheel + Pillar Breakdown ─────────────────────────────────────────
    col_wheel, col_details = st.columns([3, 2])

    with col_wheel:
        fig = create_wheel_chart(scores)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(get_score_summary(scores))

    with col_details:
        render_section_header("Pillar Breakdown", "Your current scores")
        for pid in sorted(scores.keys()):
            score = scores[pid]
            label = get_score_label(score)
            pillar = PILLARS[pid]
            st.markdown(f"**{pillar['icon']} {pillar['display_name']}** — {score}/10 ({label})")
            st.progress(score * 10 / 100)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Take New Assessment", use_container_width=True):
            st.switch_page("pages/wheel_assessment.py")

    # ── 14-Day Sparkline Trends ──────────────────────────────────────────
    st.divider()
    render_section_header("14-Day Snapshot", "Mood, energy & habit trends")

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
            _fig = go.Figure()
            _fig.add_trace(go.Scatter(
                x=_dates, y=_moods, mode='lines', name='Mood',
                line=dict(color='#FF9F0A', width=2.5, shape='spline'),
                fill='tozeroy', fillcolor='rgba(255,159,10,0.06)',
            ))
            _fig.add_trace(go.Scatter(
                x=_dates, y=_energies, mode='lines', name='Energy',
                line=dict(color='#32C8FF', width=2.5, shape='spline'),
                fill='tozeroy', fillcolor='rgba(50,200,255,0.06)',
            ))
            _fig.update_layout(
                height=180, margin=dict(t=10, b=20, l=30, r=10),
                yaxis=dict(range=[0, 10.5], showgrid=False, dtick=5, color='rgba(255,255,255,0.3)'),
                xaxis=dict(showgrid=False, tickformat="%b %d", color='rgba(255,255,255,0.3)'),
                legend=dict(orientation="h", yanchor="top", y=1.18, xanchor="center", x=0.5,
                           font=dict(size=10, color='rgba(255,255,255,0.5)')),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color='rgba(255,255,255,0.4)'),
            )
            st.plotly_chart(_fig, use_container_width=True, key="spark_mood")
        else:
            st.caption("No check-ins yet — start logging to see trends.")

    with spark_col2:
        if any(r[1] > 0 for r in _habit_rates):
            _h_dates = [r[0] for r in _habit_rates]
            _h_vals = [round(r[1] * 100) for r in _habit_rates]
            _bar_colors = ['#34C759' if v >= 80 else '#FF9F0A' if v >= 50 else '#FF453A' for v in _h_vals]
            _fig2 = go.Figure()
            _fig2.add_trace(go.Bar(
                x=_h_dates, y=_h_vals, marker_color=_bar_colors, marker_line_width=0,
                text=[f"{v}%" for v in _h_vals],
                textposition='outside', textfont=dict(size=8, color='rgba(255,255,255,0.4)'),
            ))
            _fig2.update_layout(
                height=180, margin=dict(t=10, b=20, l=30, r=10),
                yaxis=dict(range=[0, 115], showgrid=False, color='rgba(255,255,255,0.3)'),
                xaxis=dict(showgrid=False, tickformat="%b %d", color='rgba(255,255,255,0.3)'),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False, font=dict(color='rgba(255,255,255,0.4)'), bargap=0.3,
            )
            st.plotly_chart(_fig2, use_container_width=True, key="spark_habits")
        else:
            st.caption("No habit data yet — track habits to see completion rates.")

    # ── Quick Daily Check-in ─────────────────────────────────────────────
    st.divider()
    render_section_header("Quick Daily Check-in", "How are you feeling today?")
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
        award_daily_coins(user_id, today)

        from services.insight_service import get_or_generate_insight
        insight = get_or_generate_insight(user_id, today)
        if insight:
            st.info(f":material/psychology: **Today's Insight** — {insight}")
    else:
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

    # ── Active Goals ─────────────────────────────────────────────────────
    st.divider()
    render_section_header("Active Goals", "Your current objectives")
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

    # ── Today's Micro-Lesson ─────────────────────────────────────────────
    st.divider()
    render_section_header("Today's Micro-Lesson", "Keep learning every day")
    conn = get_connection()
    try:
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
        lc1, lc2 = st.columns([3, 1])
        with lc1:
            st.markdown(f":book: **{next_lesson['title']}** — *{pillar_name}* ({ltype})")
            st.caption(f"{done_lessons}/{total_lessons} lessons completed")
        with lc2:
            if st.button("Start Lesson", use_container_width=True, key="start_lesson_dash"):
                st.switch_page("pages/lessons.py")
    elif total_lessons > 0:
        st.success(f"All {total_lessons} lessons completed!")
    else:
        st.caption("Lessons will appear once content is loaded.")

    # ── Smart Insights ───────────────────────────────────────────────────
    st.divider()
    render_section_header("Smart Insights", "AI-powered patterns from your data")
    try:
        from components.smart_insights import render_smart_insights
        render_smart_insights(user_id)
    except Exception:
        st.caption("Insights will appear once you have enough check-in data.")
