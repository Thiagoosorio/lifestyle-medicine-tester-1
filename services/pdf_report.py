"""
Health Report Generator — produces a self-contained, print-friendly HTML document
that can be downloaded and printed to PDF from any browser.
"""

from datetime import date, timedelta
from db.database import get_connection
from config.settings import PILLARS


# ── Mapping from pillar_id to the daily_checkins column name ──────────────
_PILLAR_FIELD = {
    1: "nutrition_rating",
    2: "activity_rating",
    3: "sleep_rating",
    4: "stress_rating",
    5: "connection_rating",
    6: "substance_rating",
}


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def generate_health_report(user_id: int, period: str = "month") -> str:
    """Return a complete, self-contained HTML document string for the health report.

    Parameters
    ----------
    user_id : int
        The user whose report is being generated.
    period : str
        One of "week", "month", "quarter", "year", "all".

    Returns
    -------
    str
        A full HTML document with inline CSS, ready for download / print-to-PDF.
    """
    today = date.today()
    start_date, end_date, period_label = _resolve_period(today, period)

    # Fetch the previous-period window for trend comparisons
    delta = end_date - start_date
    prev_start = start_date - delta - timedelta(days=1)
    prev_end = start_date - timedelta(days=1)

    data = _fetch_all_data(user_id, start_date, end_date, prev_start, prev_end)
    data["period_label"] = period_label
    data["generated"] = today.strftime("%B %d, %Y")

    sections = [
        _section_header(data),
        _section_executive_summary(data),
        _section_wheel_snapshot(data),
        _section_pillar_breakdown(data),
        _section_mood_energy(data),
        _section_habit_performance(data),
        _section_goals_progress(data),
        _section_key_insights(data),
        _section_recommendations(data),
        _section_footer(),
    ]

    body = "\n".join(sections)
    return _wrap_html(body)


# ---------------------------------------------------------------------------
#  Period helpers
# ---------------------------------------------------------------------------

def _resolve_period(today: date, period: str):
    """Return (start_date, end_date, human-readable label)."""
    if period == "week":
        start = today - timedelta(days=today.weekday())  # Monday
        end = today
        label = f"Week of {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
    elif period == "month":
        start = today.replace(day=1)
        end = today
        label = today.strftime("%B %Y")
    elif period == "quarter":
        q = (today.month - 1) // 3
        start = today.replace(month=q * 3 + 1, day=1)
        end = today
        label = f"Q{q + 1} {today.year}"
    elif period == "year":
        start = today.replace(month=1, day=1)
        end = today
        label = str(today.year)
    else:  # "all"
        start = date(2000, 1, 1)
        end = today
        label = "All Time"
    return start, end, label


# ---------------------------------------------------------------------------
#  Data fetching — one big gather so we only open a few connections
# ---------------------------------------------------------------------------

def _fetch_all_data(user_id, start, end, prev_start, prev_end):
    """Return a dict with all data needed for every section."""
    s, e = start.isoformat(), end.isoformat()
    ps, pe = prev_start.isoformat(), prev_end.isoformat()

    conn = get_connection()
    try:
        # User info
        user = conn.execute(
            "SELECT display_name FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        display_name = user["display_name"] if user else "User"

        # Check-ins for current period
        checkins = [
            dict(r) for r in conn.execute(
                "SELECT * FROM daily_checkins WHERE user_id = ? AND checkin_date BETWEEN ? AND ? ORDER BY checkin_date",
                (user_id, s, e),
            ).fetchall()
        ]

        # Check-ins for previous period (trends)
        prev_checkins = [
            dict(r) for r in conn.execute(
                "SELECT * FROM daily_checkins WHERE user_id = ? AND checkin_date BETWEEN ? AND ? ORDER BY checkin_date",
                (user_id, ps, pe),
            ).fetchall()
        ]

        # Habits
        habits = [
            dict(r) for r in conn.execute(
                "SELECT * FROM habits WHERE user_id = ? AND is_active = 1 ORDER BY pillar_id, name",
                (user_id,),
            ).fetchall()
        ]

        # Habit log for period
        habit_log = [
            dict(r) for r in conn.execute(
                "SELECT * FROM habit_log WHERE user_id = ? AND log_date BETWEEN ? AND ?",
                (user_id, s, e),
            ).fetchall()
        ]

        # Goals
        goals = [
            dict(r) for r in conn.execute(
                "SELECT * FROM goals WHERE user_id = ? ORDER BY status, target_date",
                (user_id,),
            ).fetchall()
        ]

        # Completed goals in this period
        completed_goals = [
            dict(r) for r in conn.execute(
                "SELECT * FROM goals WHERE user_id = ? AND status = 'completed' AND completed_at BETWEEN ? AND ?",
                (user_id, s, e),
            ).fetchall()
        ]

        # Latest wheel assessment
        latest_session = conn.execute(
            "SELECT session_id FROM wheel_assessments WHERE user_id = ? ORDER BY assessed_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        latest_wheel = {}
        if latest_session:
            rows = conn.execute(
                "SELECT pillar_id, score FROM wheel_assessments WHERE session_id = ?",
                (latest_session["session_id"],),
            ).fetchall()
            latest_wheel = {r["pillar_id"]: r["score"] for r in rows}

        # Previous wheel assessment (second-latest session)
        prev_wheel = {}
        if latest_session:
            prev_session = conn.execute(
                "SELECT session_id FROM wheel_assessments WHERE user_id = ? AND session_id != ? ORDER BY assessed_at DESC LIMIT 1",
                (user_id, latest_session["session_id"]),
            ).fetchone()
            if prev_session:
                rows = conn.execute(
                    "SELECT pillar_id, score FROM wheel_assessments WHERE session_id = ?",
                    (prev_session["session_id"],),
                ).fetchall()
                prev_wheel = {r["pillar_id"]: r["score"] for r in rows}

        # Coin balance
        coin_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as bal FROM coin_transactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        coin_balance = coin_row["bal"] if coin_row else 0

    finally:
        conn.close()

    # Build the habit_log lookup: {habit_id: set_of_completed_dates}
    hl_lookup = {}
    for entry in habit_log:
        hid = entry["habit_id"]
        if entry.get("completed_count", 0) > 0:
            hl_lookup.setdefault(hid, set()).add(entry["log_date"])

    # Count total days in the period (so we know possible habit days)
    total_days = (end - start).days + 1

    return {
        "user_id": user_id,
        "display_name": display_name,
        "start": start,
        "end": end,
        "total_days": total_days,
        "checkins": checkins,
        "prev_checkins": prev_checkins,
        "habits": habits,
        "habit_log_lookup": hl_lookup,
        "goals": goals,
        "completed_goals": completed_goals,
        "latest_wheel": latest_wheel,
        "prev_wheel": prev_wheel,
        "coin_balance": coin_balance,
    }


# ---------------------------------------------------------------------------
#  Tiny helpers
# ---------------------------------------------------------------------------

def _avg(values):
    return round(sum(values) / len(values), 1) if values else None


def _trend_arrow(current, previous):
    if current is None or previous is None:
        return '<span style="color:#9e9e9e;">&mdash;</span>'
    diff = current - previous
    if diff > 0.3:
        return '<span style="color:#4CAF50;">&uarr;</span>'
    elif diff < -0.3:
        return '<span style="color:#F44336;">&darr;</span>'
    return '<span style="color:#FF9800;">&rarr;</span>'


def _score_color(score):
    """Return a CSS color string based on score (1-10 scale)."""
    if score is None:
        return "#9e9e9e"
    if score >= 7:
        return "#4CAF50"
    if score >= 4:
        return "#FF9800"
    return "#F44336"


def _bar_html(value, max_val=10, color="#2196F3", width_px=120):
    """A small inline bar for tables."""
    if value is None:
        return '<span style="color:#bbb;">N/A</span>'
    pct = min(value / max_val * 100, 100)
    return (
        f'<div style="display:inline-block;width:{width_px}px;height:14px;'
        f'background:#e8e8e8;border-radius:7px;overflow:hidden;vertical-align:middle;">'
        f'<div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:7px;"></div>'
        f'</div> <span style="font-size:12px;font-weight:600;">{value:.1f}</span>'
    )


def _progress_bar_html(pct, color="#2196F3"):
    """A horizontal progress bar (0-100%)."""
    pct = max(0, min(pct, 100))
    return (
        f'<div style="width:100%;height:18px;background:#e8e8e8;border-radius:9px;overflow:hidden;">'
        f'<div style="width:{pct}%;height:100%;background:{color};border-radius:9px;'
        f'text-align:center;color:#fff;font-size:11px;line-height:18px;font-weight:600;">'
        f'{pct}%</div></div>'
    )


# ---------------------------------------------------------------------------
#  Section builders
# ---------------------------------------------------------------------------

def _section_header(data):
    return f'''
    <div class="header">
        <div class="header-logo">
            <svg width="40" height="40" viewBox="0 0 40 40" style="vertical-align:middle;margin-right:10px;">
                <circle cx="20" cy="20" r="18" fill="#fff" opacity="0.15"/>
                <path d="M20 8 C14 8 10 13 10 18 C10 26 20 33 20 33 C20 33 30 26 30 18 C30 13 26 8 20 8Z"
                      fill="#e74c6f" stroke="#fff" stroke-width="1.5"/>
            </svg>
            <span class="header-title">Lifestyle Medicine Health Report</span>
        </div>
        <div class="header-meta">
            <table class="header-table">
                <tr><td class="meta-label">Patient</td><td class="meta-value">{_esc(data["display_name"])}</td></tr>
                <tr><td class="meta-label">Period</td><td class="meta-value">{_esc(data["period_label"])}</td></tr>
                <tr><td class="meta-label">Generated</td><td class="meta-value">{data["generated"]}</td></tr>
            </table>
        </div>
    </div>'''


def _section_executive_summary(data):
    checkins = data["checkins"]
    prev = data["prev_checkins"]
    habits = data["habits"]
    hl = data["habit_log_lookup"]

    # Overall health score = average of latest pillar averages from check-ins
    pillar_avgs = {}
    for pid, field in _PILLAR_FIELD.items():
        vals = [c[field] for c in checkins if c.get(field) is not None]
        if vals:
            pillar_avgs[pid] = _avg(vals)

    overall = _avg(list(pillar_avgs.values())) if pillar_avgs else None

    # Previous period overall for trend
    prev_pillar_avgs = {}
    for pid, field in _PILLAR_FIELD.items():
        vals = [c[field] for c in prev if c.get(field) is not None]
        if vals:
            prev_pillar_avgs[pid] = _avg(vals)
    prev_overall = _avg(list(prev_pillar_avgs.values())) if prev_pillar_avgs else None

    # Trend word
    if overall is not None and prev_overall is not None:
        diff = overall - prev_overall
        if diff > 0.3:
            trend_word = "Improving"
            trend_color = "#4CAF50"
        elif diff < -0.3:
            trend_word = "Declining"
            trend_color = "#F44336"
        else:
            trend_word = "Stable"
            trend_color = "#FF9800"
    else:
        trend_word = "Insufficient Data"
        trend_color = "#9e9e9e"

    days_tracked = len(checkins)
    total_habit_completions = sum(len(dates) for dates in hl.values())
    goals_achieved = len(data["completed_goals"])

    # Key highlight
    if overall is not None:
        if overall >= 7:
            highlight = "You are performing exceptionally well across your lifestyle pillars. Keep it up!"
        elif overall >= 5:
            highlight = "You are making solid progress. A few targeted improvements could elevate your wellbeing further."
        else:
            highlight = "There are opportunities to strengthen several lifestyle areas. Small consistent changes make a big difference."
    else:
        highlight = "Start tracking daily to unlock your personalized health insights."

    score_display = f"{overall:.1f}/10" if overall is not None else "N/A"

    return f'''
    <div class="section">
        <h2 class="section-title">Executive Summary</h2>
        <div class="summary-grid">
            <div class="summary-card summary-card-main">
                <div class="summary-big-number" style="color:{_score_color(overall)};">{score_display}</div>
                <div class="summary-label">Overall Health Score</div>
                <div class="summary-trend" style="color:{trend_color};">{trend_word}</div>
            </div>
            <div class="summary-card">
                <div class="summary-number">{days_tracked}</div>
                <div class="summary-label">Days Tracked</div>
            </div>
            <div class="summary-card">
                <div class="summary-number">{total_habit_completions}</div>
                <div class="summary-label">Habits Completed</div>
            </div>
            <div class="summary-card">
                <div class="summary-number">{goals_achieved}</div>
                <div class="summary-label">Goals Achieved</div>
            </div>
        </div>
        <p class="highlight-text">{highlight}</p>
    </div>'''


def _section_wheel_snapshot(data):
    latest = data["latest_wheel"]
    prev = data["prev_wheel"]

    if not latest:
        return '''
        <div class="section">
            <h2 class="section-title">Wheel of Life Snapshot</h2>
            <p class="muted">No wheel assessment has been completed yet. Complete a Wheel of Life assessment to see your snapshot here.</p>
        </div>'''

    # Build a horizontal bar chart in pure HTML
    rows = []
    for pid in sorted(PILLARS.keys()):
        p = PILLARS[pid]
        score = latest.get(pid, 0)
        prev_score = prev.get(pid)
        color = p["color"]
        pct = score / 10 * 100
        trend = _trend_arrow(score, prev_score) if prev_score is not None else ""
        prev_str = f" (prev: {prev_score})" if prev_score is not None else ""

        rows.append(f'''
            <tr>
                <td class="wheel-pillar" style="color:{color};font-weight:600;">{_esc(p["display_name"])}</td>
                <td class="wheel-bar-cell">
                    <div class="wheel-bar-bg">
                        <div class="wheel-bar-fill" style="width:{pct}%;background:{color};"></div>
                    </div>
                </td>
                <td class="wheel-score" style="color:{_score_color(score)};">{score}/10 {trend}</td>
                <td class="wheel-prev">{prev_str}</td>
            </tr>''')

    total = sum(latest.get(pid, 0) for pid in PILLARS)
    avg_score = total / len(PILLARS) if PILLARS else 0

    return f'''
    <div class="section">
        <h2 class="section-title">Wheel of Life Snapshot</h2>
        <table class="wheel-table">
            <thead>
                <tr><th>Pillar</th><th style="width:45%;">Score</th><th>Value</th><th>Previous</th></tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        <p class="wheel-total">Total: <strong>{total}/60</strong> &nbsp;&bull;&nbsp; Average: <strong>{avg_score:.1f}/10</strong></p>
    </div>'''


def _section_pillar_breakdown(data):
    checkins = data["checkins"]
    prev = data["prev_checkins"]
    habits = data["habits"]
    hl = data["habit_log_lookup"]
    total_days = data["total_days"]

    blocks = []
    for pid in sorted(PILLARS.keys()):
        p = PILLARS[pid]
        field = _PILLAR_FIELD[pid]
        color = p["color"]

        # Current period average
        vals = [c[field] for c in checkins if c.get(field) is not None]
        avg_val = _avg(vals)

        # Previous period average
        prev_vals = [c[field] for c in prev if c.get(field) is not None]
        prev_avg = _avg(prev_vals)

        trend = _trend_arrow(avg_val, prev_avg)

        # Best / worst day
        if vals:
            best_checkin = max(
                [c for c in checkins if c.get(field) is not None],
                key=lambda c: c[field],
            )
            worst_checkin = min(
                [c for c in checkins if c.get(field) is not None],
                key=lambda c: c[field],
            )
            best_day = f'{best_checkin["checkin_date"]} ({best_checkin[field]})'
            worst_day = f'{worst_checkin["checkin_date"]} ({worst_checkin[field]})'
        else:
            best_day = "N/A"
            worst_day = "N/A"

        # Related habits
        pillar_habits = [h for h in habits if h["pillar_id"] == pid]
        habit_rows = ""
        for h in pillar_habits:
            completed_dates = hl.get(h["id"], set())
            completion_rate = len(completed_dates) / total_days * 100 if total_days > 0 else 0
            habit_rows += f'<li>{_esc(h["name"])} &mdash; <strong>{completion_rate:.0f}%</strong></li>'
        if not habit_rows:
            habit_rows = "<li class='muted'>No habits tracked for this pillar</li>"

        bar = _bar_html(avg_val, color=color, width_px=150) if avg_val is not None else '<span class="muted">No data</span>'

        blocks.append(f'''
        <div class="pillar-card" style="border-left:4px solid {color};">
            <h3 style="color:{color};margin:0 0 8px 0;">{_esc(p["display_name"])} {trend}</h3>
            <div class="pillar-stats">
                <div>Average: {bar}</div>
                <div class="pillar-meta">Best day: {best_day} &nbsp;|&nbsp; Worst day: {worst_day}</div>
            </div>
            <div class="pillar-habits">
                <strong>Related Habits:</strong>
                <ul>{habit_rows}</ul>
            </div>
        </div>''')

    return f'''
    <div class="section page-break-before">
        <h2 class="section-title">Pillar-by-Pillar Breakdown</h2>
        {"".join(blocks)}
    </div>'''


def _section_mood_energy(data):
    checkins = data["checkins"]
    if not checkins:
        return '''
        <div class="section">
            <h2 class="section-title">Mood &amp; Energy Trends</h2>
            <p class="muted">No check-in data available for this period.</p>
        </div>'''

    # Group by ISO week
    weeks = {}
    for c in checkins:
        d = date.fromisoformat(c["checkin_date"])
        week_key = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
        weeks.setdefault(week_key, {"mood": [], "energy": []})
        if c.get("mood") is not None:
            weeks[week_key]["mood"].append(c["mood"])
        if c.get("energy") is not None:
            weeks[week_key]["energy"].append(c["energy"])

    # Build chart rows
    chart_rows = []
    best_week_mood = None
    best_week_key = None
    for wk in sorted(weeks.keys()):
        m_avg = _avg(weeks[wk]["mood"])
        e_avg = _avg(weeks[wk]["energy"])
        if m_avg is not None and (best_week_mood is None or m_avg > best_week_mood):
            best_week_mood = m_avg
            best_week_key = wk

        m_bar = ""
        e_bar = ""
        if m_avg is not None:
            m_pct = m_avg / 10 * 100
            m_bar = (
                f'<div style="display:flex;align-items:center;gap:6px;">'
                f'<div style="width:{m_pct}%;max-width:200px;height:16px;background:#5C6BC0;border-radius:8px;"></div>'
                f'<span style="font-size:12px;">{m_avg}</span></div>'
            )
        if e_avg is not None:
            e_pct = e_avg / 10 * 100
            e_bar = (
                f'<div style="display:flex;align-items:center;gap:6px;">'
                f'<div style="width:{e_pct}%;max-width:200px;height:16px;background:#26A69A;border-radius:8px;"></div>'
                f'<span style="font-size:12px;">{e_avg}</span></div>'
            )

        chart_rows.append(f'''
            <tr>
                <td style="font-weight:600;white-space:nowrap;">{wk}</td>
                <td>{m_bar or '<span class="muted">-</span>'}</td>
                <td>{e_bar or '<span class="muted">-</span>'}</td>
            </tr>''')

    # Overall averages
    all_mood = [c["mood"] for c in checkins if c.get("mood") is not None]
    all_energy = [c["energy"] for c in checkins if c.get("energy") is not None]
    overall_mood = _avg(all_mood)
    overall_energy = _avg(all_energy)

    summary = (
        f'<div class="mood-summary">'
        f'<span>Overall Mood: <strong>{overall_mood if overall_mood else "N/A"}</strong>/10</span>'
        f'<span>Overall Energy: <strong>{overall_energy if overall_energy else "N/A"}</strong>/10</span>'
        f'<span>Best Week: <strong>{best_week_key or "N/A"}</strong> (mood {best_week_mood or "N/A"})</span>'
        f'</div>'
    )

    return f'''
    <div class="section">
        <h2 class="section-title">Mood &amp; Energy Trends</h2>
        {summary}
        <table class="data-table">
            <thead>
                <tr>
                    <th>Week</th>
                    <th><span style="color:#5C6BC0;">&#9632;</span> Mood</th>
                    <th><span style="color:#26A69A;">&#9632;</span> Energy</th>
                </tr>
            </thead>
            <tbody>
                {"".join(chart_rows)}
            </tbody>
        </table>
    </div>'''


def _section_habit_performance(data):
    habits = data["habits"]
    hl = data["habit_log_lookup"]
    total_days = data["total_days"]

    if not habits:
        return '''
        <div class="section page-break-before">
            <h2 class="section-title">Habit Performance</h2>
            <p class="muted">No active habits found.</p>
        </div>'''

    # Build per-habit stats
    habit_stats = []
    for h in habits:
        completed_dates = hl.get(h["id"], set())
        rate = len(completed_dates) / total_days * 100 if total_days > 0 else 0

        # Calculate streak (consecutive days ending at data["end"])
        streak = 0
        check_date = data["end"]
        while check_date >= data["start"]:
            if check_date.isoformat() in completed_dates:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        habit_stats.append({
            "name": h["name"],
            "pillar_id": h["pillar_id"],
            "rate": rate,
            "streak": streak,
            "completed": len(completed_dates),
        })

    # Sort by rate descending for table
    habit_stats.sort(key=lambda x: x["rate"], reverse=True)

    rows = []
    for i, hs in enumerate(habit_stats):
        p = PILLARS.get(hs["pillar_id"], {})
        color = p.get("color", "#607D8B")
        rate_color = "#4CAF50" if hs["rate"] >= 70 else ("#FF9800" if hs["rate"] >= 50 else "#F44336")
        rows.append(f'''
            <tr>
                <td>{_esc(hs["name"])}</td>
                <td style="color:{color};font-weight:600;">{_esc(p.get("display_name", ""))}</td>
                <td style="text-align:center;color:{rate_color};font-weight:700;">{hs["rate"]:.0f}%</td>
                <td style="text-align:center;">{hs["streak"]}d</td>
            </tr>''')

    # Top 3
    top3 = habit_stats[:3]
    top3_html = ", ".join(
        f'<strong>{_esc(h["name"])}</strong> ({h["rate"]:.0f}%)' for h in top3
    ) if top3 else "N/A"

    # Needs attention
    needs_attn = [h for h in habit_stats if h["rate"] < 50]
    attn_html = ""
    if needs_attn:
        items = ", ".join(
            f'<strong>{_esc(h["name"])}</strong> ({h["rate"]:.0f}%)' for h in needs_attn
        )
        attn_html = f'<p class="attention-text">Needs attention (&lt;50%): {items}</p>'

    return f'''
    <div class="section page-break-before">
        <h2 class="section-title">Habit Performance</h2>
        <p>Top performers: {top3_html}</p>
        {attn_html}
        <table class="data-table">
            <thead>
                <tr><th>Habit</th><th>Pillar</th><th style="text-align:center;">Completion</th><th style="text-align:center;">Streak</th></tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </div>'''


def _section_goals_progress(data):
    goals = data["goals"]
    completed = data["completed_goals"]

    if not goals:
        return '''
        <div class="section">
            <h2 class="section-title">Goals Progress</h2>
            <p class="muted">No goals have been created yet.</p>
        </div>'''

    active = [g for g in goals if g["status"] == "active"]
    paused = [g for g in goals if g["status"] == "paused"]
    overdue = [
        g for g in active
        if g.get("target_date") and date.fromisoformat(g["target_date"][:10]) < date.today()
    ]

    # Active goals with progress bars
    active_rows = []
    for g in active:
        p = PILLARS.get(g.get("pillar_id"), {})
        color = p.get("color", "#2196F3")
        pct = g.get("progress_pct", 0) or 0
        due = g["target_date"][:10] if g.get("target_date") else "No date"
        is_overdue = g.get("target_date") and date.fromisoformat(g["target_date"][:10]) < date.today()
        due_style = 'color:#F44336;font-weight:600;' if is_overdue else ''
        active_rows.append(f'''
            <tr>
                <td><strong>{_esc(g["title"])}</strong></td>
                <td style="color:{color};">{_esc(p.get("display_name", ""))}</td>
                <td style="width:35%;">{_progress_bar_html(pct, color)}</td>
                <td style="{due_style}">{due}{"  (overdue)" if is_overdue else ""}</td>
            </tr>''')

    # Completed goals
    completed_rows = []
    for g in completed:
        p = PILLARS.get(g.get("pillar_id"), {})
        completed_rows.append(
            f'<li><strong>{_esc(g["title"])}</strong> ({_esc(p.get("display_name", ""))})</li>'
        )

    completed_html = ""
    if completed_rows:
        completed_html = f'''
        <div class="goals-completed">
            <h3>Completed This Period ({len(completed)})</h3>
            <ul>{"".join(completed_rows)}</ul>
        </div>'''

    # Needs attention
    attn_html = ""
    if overdue:
        items = "".join(f'<li>{_esc(g["title"])} (due {g["target_date"][:10]})</li>' for g in overdue)
        attn_html = f'<div class="attention-box"><strong>Overdue Goals:</strong><ul>{items}</ul></div>'

    return f'''
    <div class="section">
        <h2 class="section-title">Goals Progress</h2>
        <div class="goals-counts">
            <span>Active: <strong>{len(active)}</strong></span>
            <span>Completed (period): <strong>{len(completed)}</strong></span>
            <span>Paused: <strong>{len(paused)}</strong></span>
        </div>
        {attn_html}
        <table class="data-table">
            <thead><tr><th>Goal</th><th>Pillar</th><th>Progress</th><th>Due Date</th></tr></thead>
            <tbody>{"".join(active_rows)}</tbody>
        </table>
        {completed_html}
    </div>'''


def _section_key_insights(data):
    checkins = data["checkins"]
    if len(checkins) < 5:
        return '''
        <div class="section page-break-before">
            <h2 class="section-title">Key Insights</h2>
            <p class="muted">Need at least 5 check-ins to generate insights. Keep tracking daily!</p>
        </div>'''

    insights = []

    # Insight 1: strongest correlation between any two pillar fields
    fields_list = list(_PILLAR_FIELD.values()) + ["mood", "energy"]
    field_labels = {
        "nutrition_rating": "Nutrition",
        "activity_rating": "Physical Activity",
        "sleep_rating": "Sleep",
        "stress_rating": "Stress Management",
        "connection_rating": "Social Connection",
        "substance_rating": "Substance Avoidance",
        "mood": "Mood",
        "energy": "Energy",
    }

    best_corr = None
    best_pair = None
    for i, f1 in enumerate(fields_list):
        for f2 in fields_list[i + 1:]:
            v1 = [c[f1] for c in checkins if c.get(f1) is not None and c.get(f2) is not None]
            v2 = [c[f2] for c in checkins if c.get(f1) is not None and c.get(f2) is not None]
            if len(v1) >= 5:
                corr = _pearson(v1, v2)
                if corr is not None and (best_corr is None or abs(corr) > abs(best_corr)):
                    best_corr = corr
                    best_pair = (f1, f2)

    if best_pair and best_corr is not None and abs(best_corr) >= 0.25:
        direction = "positively" if best_corr > 0 else "negatively"
        strength = "strongly" if abs(best_corr) >= 0.6 else "moderately"
        l1 = field_labels.get(best_pair[0], best_pair[0])
        l2 = field_labels.get(best_pair[1], best_pair[1])
        insights.append(
            f"<strong>{l1}</strong> and <strong>{l2}</strong> are {strength} {direction} "
            f"correlated (r={best_corr:.2f}) in your data. "
            f"{'Improving one tends to improve the other.' if best_corr > 0 else 'When one goes up, the other tends to go down.'}"
        )

    # Insight 2: best day of week
    day_scores = {}
    for c in checkins:
        d = date.fromisoformat(c["checkin_date"])
        dow = d.strftime("%A")
        mood = c.get("mood")
        if mood is not None:
            day_scores.setdefault(dow, []).append(mood)
    if day_scores:
        best_dow = max(day_scores.items(), key=lambda x: _avg(x[1]) or 0)
        worst_dow = min(day_scores.items(), key=lambda x: _avg(x[1]) or 10)
        if best_dow[0] != worst_dow[0]:
            insights.append(
                f"Your best day tends to be <strong>{best_dow[0]}</strong> "
                f"(avg mood {_avg(best_dow[1])}) while <strong>{worst_dow[0]}</strong> "
                f"is typically your most challenging (avg mood {_avg(worst_dow[1])})."
            )

    # Insight 3: consistency impact
    if len(checkins) >= 7:
        # Compare mood on weeks with high vs low check-in frequency
        mood_vals = [c["mood"] for c in checkins if c.get("mood") is not None]
        if mood_vals:
            tracking_pct = len(checkins) / data["total_days"] * 100 if data["total_days"] > 0 else 0
            if tracking_pct >= 70:
                insights.append(
                    f"You tracked <strong>{tracking_pct:.0f}%</strong> of days this period. "
                    f"Great consistency! Regular tracking is itself linked to better outcomes in lifestyle medicine research."
                )
            else:
                insights.append(
                    f"You tracked <strong>{tracking_pct:.0f}%</strong> of days this period. "
                    f"Increasing check-in consistency could reveal deeper patterns and help you stay on course."
                )

    # Take top 3
    insights = insights[:3]

    if not insights:
        return '''
        <div class="section page-break-before">
            <h2 class="section-title">Key Insights</h2>
            <p class="muted">Not enough variation in data to detect meaningful patterns yet.</p>
        </div>'''

    items = "".join(f'<div class="insight-card"><span class="insight-num">{i+1}</span>{txt}</div>' for i, txt in enumerate(insights))

    return f'''
    <div class="section page-break-before">
        <h2 class="section-title">Key Insights</h2>
        {items}
    </div>'''


def _section_recommendations(data):
    checkins = data["checkins"]
    habits = data["habits"]
    hl = data["habit_log_lookup"]
    goals = data["goals"]
    total_days = data["total_days"]

    recs = []

    # 1. Low-performing pillar recommendation
    pillar_avgs = {}
    for pid, field in _PILLAR_FIELD.items():
        vals = [c[field] for c in checkins if c.get(field) is not None]
        if vals:
            pillar_avgs[pid] = _avg(vals)

    if pillar_avgs:
        weakest_pid = min(pillar_avgs, key=pillar_avgs.get)
        weakest_score = pillar_avgs[weakest_pid]
        p = PILLARS[weakest_pid]
        if weakest_score is not None and weakest_score < 7:
            recs.append(
                f'<strong>Focus on {_esc(p["display_name"])}:</strong> '
                f'Your average score is {weakest_score:.1f}/10. '
                f'{_esc(p.get("quick_tip", "Consider setting a specific goal in this area."))}'
            )

    # 2. Habit consistency recommendation
    low_habits = []
    for h in habits:
        completed = hl.get(h["id"], set())
        rate = len(completed) / total_days * 100 if total_days > 0 else 0
        if rate < 50:
            low_habits.append(h["name"])
    if low_habits:
        if len(low_habits) <= 3:
            names = ", ".join(f'"{n}"' for n in low_habits)
        else:
            names = f"{len(low_habits)} habits"
        recs.append(
            f"<strong>Improve habit consistency:</strong> "
            f"{names} {'is' if len(low_habits) == 1 else 'are'} below 50% completion. "
            f"Try habit stacking or reducing the bar to make them easier to start."
        )

    # 3. Tracking frequency
    if total_days > 0:
        tracking_rate = len(checkins) / total_days
        if tracking_rate < 0.7:
            recs.append(
                "<strong>Check in more consistently:</strong> "
                "You are tracking less than 70% of days. Set a daily reminder to check in "
                "at the same time each day to build the habit of self-monitoring."
            )

    # 4. Goal setting
    active_goals = [g for g in goals if g["status"] == "active"]
    if len(active_goals) == 0:
        recs.append(
            "<strong>Set a new goal:</strong> "
            "You have no active goals. Setting specific, measurable goals is one of the "
            "most effective strategies for behavior change."
        )
    else:
        overdue = [
            g for g in active_goals
            if g.get("target_date") and date.fromisoformat(g["target_date"][:10]) < date.today()
        ]
        if overdue:
            recs.append(
                f"<strong>Review overdue goals:</strong> "
                f"You have {len(overdue)} overdue goal{'s' if len(overdue) > 1 else ''}. "
                f"Consider updating the timeline or breaking them into smaller milestones."
            )

    # 5. Sleep specific recommendation
    sleep_vals = [c["sleep_rating"] for c in checkins if c.get("sleep_rating") is not None]
    if sleep_vals and _avg(sleep_vals) < 6:
        recs.append(
            "<strong>Prioritize sleep:</strong> "
            "Your average sleep rating is below 6. Quality sleep underpins every other "
            "pillar of lifestyle medicine. Try setting a consistent bedtime and limiting "
            "screen time before bed."
        )

    recs = recs[:5]  # cap at 5

    if not recs:
        recs.append(
            "<strong>Keep it up!</strong> Your data looks strong across the board. "
            "Continue your current routines and consider raising the bar with a stretch goal."
        )

    items = "".join(f'<div class="rec-item"><span class="rec-bullet">&#10003;</span>{r}</div>' for r in recs)

    return f'''
    <div class="section">
        <h2 class="section-title">Recommendations</h2>
        {items}
    </div>'''


def _section_footer():
    return '''
    <div class="footer">
        <p class="disclaimer">
            <strong>Disclaimer:</strong> This report is for informational and self-tracking purposes only.
            It does not constitute medical advice, diagnosis, or treatment. Always consult a qualified
            healthcare professional before making changes to your health regimen. The data presented
            reflects self-reported information and may not capture your complete health picture.
        </p>
        <div class="footer-brand">
            <span class="footer-logo">
                <svg width="18" height="18" viewBox="0 0 40 40" style="vertical-align:middle;margin-right:4px;">
                    <path d="M20 8 C14 8 10 13 10 18 C10 26 20 33 20 33 C20 33 30 26 30 18 C30 13 26 8 20 8Z"
                          fill="#e74c6f"/>
                </svg>
            </span>
            <span>Lifestyle Medicine Coach</span>
            <span class="footer-divider">&bull;</span>
            <span>Powered by evidence-based lifestyle medicine</span>
        </div>
    </div>'''


# ---------------------------------------------------------------------------
#  Utility
# ---------------------------------------------------------------------------

def _esc(text):
    """Basic HTML escaping."""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _pearson(x, y):
    """Simple Pearson correlation without external dependencies."""
    n = len(x)
    if n < 3:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    dx = [xi - mx for xi in x]
    dy = [yi - my for yi in y]
    num = sum(a * b for a, b in zip(dx, dy))
    den_x = sum(a * a for a in dx) ** 0.5
    den_y = sum(b * b for b in dy) ** 0.5
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


# ---------------------------------------------------------------------------
#  HTML wrapper with full inline CSS
# ---------------------------------------------------------------------------

def _wrap_html(body: str) -> str:
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lifestyle Medicine Health Report</title>
<style>
/* ── Reset & Base ────────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 14px; }}
body {{
    font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
    color: #2d2d2d;
    background: #f4f5f7;
    line-height: 1.6;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
}}

/* ── Page container ──────────────────────────────────────────────────── */
.page {{
    max-width: 210mm;  /* A4 width */
    margin: 20px auto;
    background: #fff;
    box-shadow: 0 2px 20px rgba(0,0,0,.08);
    border-radius: 6px;
    overflow: hidden;
}}

/* ── Header ──────────────────────────────────────────────────────────── */
.header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: #fff;
    padding: 30px 40px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
}}
.header-logo {{ display: flex; align-items: center; }}
.header-title {{ font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }}
.header-meta {{ text-align: right; }}
.header-table {{ border-collapse: collapse; }}
.header-table td {{ padding: 2px 0; }}
.meta-label {{ color: rgba(255,255,255,.6); padding-right: 14px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
.meta-value {{ color: #fff; font-weight: 600; font-size: 14px; }}

/* ── Sections ────────────────────────────────────────────────────────── */
.section {{
    padding: 28px 40px;
    border-bottom: 1px solid #eee;
}}
.section:last-of-type {{ border-bottom: none; }}
.section-title {{
    font-size: 18px;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 18px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e8e8e8;
    letter-spacing: -0.2px;
}}

/* ── Executive Summary ───────────────────────────────────────────────── */
.summary-grid {{
    display: grid;
    grid-template-columns: 1.5fr 1fr 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}}
.summary-card {{
    background: #f8f9fb;
    border-radius: 8px;
    padding: 18px;
    text-align: center;
    border: 1px solid #eaecf0;
}}
.summary-card-main {{
    background: linear-gradient(135deg, #f0f4ff, #f8f9fb);
    border: 1px solid #d0d9f0;
}}
.summary-big-number {{ font-size: 36px; font-weight: 800; line-height: 1.1; }}
.summary-number {{ font-size: 28px; font-weight: 700; color: #1a1a2e; line-height: 1.1; }}
.summary-label {{ font-size: 12px; color: #666; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
.summary-trend {{ font-size: 14px; font-weight: 600; margin-top: 6px; }}
.highlight-text {{
    background: #f0f7ff;
    border-left: 3px solid #2196F3;
    padding: 12px 16px;
    border-radius: 0 6px 6px 0;
    font-style: italic;
    color: #444;
}}

/* ── Wheel table ─────────────────────────────────────────────────────── */
.wheel-table {{ width: 100%; border-collapse: collapse; }}
.wheel-table th {{
    text-align: left; padding: 8px 10px; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.5px; color: #888;
    border-bottom: 2px solid #e8e8e8;
}}
.wheel-table td {{ padding: 10px; border-bottom: 1px solid #f0f0f0; }}
.wheel-pillar {{ white-space: nowrap; width: 150px; }}
.wheel-bar-cell {{ width: 45%; }}
.wheel-bar-bg {{
    width: 100%; height: 18px; background: #eee; border-radius: 9px; overflow: hidden;
}}
.wheel-bar-fill {{ height: 100%; border-radius: 9px; transition: width .3s; }}
.wheel-score {{ font-weight: 700; white-space: nowrap; width: 100px; }}
.wheel-prev {{ font-size: 12px; color: #999; white-space: nowrap; }}
.wheel-total {{ margin-top: 12px; text-align: right; font-size: 14px; color: #555; }}

/* ── Pillar cards ────────────────────────────────────────────────────── */
.pillar-card {{
    background: #fafbfc;
    border-radius: 0 8px 8px 0;
    padding: 16px 20px;
    margin-bottom: 14px;
}}
.pillar-stats {{ margin: 8px 0; }}
.pillar-meta {{ font-size: 12px; color: #777; margin-top: 4px; }}
.pillar-habits {{ margin-top: 10px; }}
.pillar-habits ul {{ padding-left: 20px; margin-top: 4px; }}
.pillar-habits li {{ font-size: 13px; margin-bottom: 2px; }}

/* ── Data tables ─────────────────────────────────────────────────────── */
.data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.data-table th {{
    text-align: left; padding: 10px 12px; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.5px; color: #666;
    background: #f8f9fb; border-bottom: 2px solid #e0e0e0;
}}
.data-table td {{
    padding: 10px 12px; border-bottom: 1px solid #f0f0f0;
    vertical-align: middle;
}}
.data-table tbody tr:nth-child(even) {{ background: #fafbfc; }}
.data-table tbody tr:hover {{ background: #f0f4ff; }}

/* ── Mood summary ────────────────────────────────────────────────────── */
.mood-summary {{
    display: flex; gap: 24px; flex-wrap: wrap;
    margin-bottom: 14px; font-size: 14px; color: #444;
}}

/* ── Goals ────────────────────────────────────────────────────────────── */
.goals-counts {{
    display: flex; gap: 20px; margin-bottom: 14px;
    font-size: 14px; color: #555;
}}
.goals-completed {{ margin-top: 16px; }}
.goals-completed h3 {{ font-size: 15px; color: #4CAF50; margin-bottom: 6px; }}
.goals-completed ul {{ padding-left: 20px; }}
.goals-completed li {{ margin-bottom: 4px; }}

/* ── Insights & Recommendations ──────────────────────────────────────── */
.insight-card {{
    background: #f0f7ff;
    border-left: 3px solid #2196F3;
    border-radius: 0 6px 6px 0;
    padding: 14px 18px;
    margin-bottom: 12px;
    font-size: 14px;
    line-height: 1.5;
    position: relative;
}}
.insight-num {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 24px; height: 24px; background: #2196F3; color: #fff;
    border-radius: 50%; font-size: 12px; font-weight: 700;
    margin-right: 10px; flex-shrink: 0;
}}
.rec-item {{
    padding: 12px 18px;
    margin-bottom: 10px;
    background: #f6fef6;
    border-left: 3px solid #4CAF50;
    border-radius: 0 6px 6px 0;
    font-size: 14px;
    line-height: 1.5;
}}
.rec-bullet {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 22px; height: 22px; background: #4CAF50; color: #fff;
    border-radius: 50%; font-size: 12px; font-weight: 700;
    margin-right: 10px;
}}

/* ── Attention boxes ─────────────────────────────────────────────────── */
.attention-text {{ color: #e65100; font-size: 13px; margin-bottom: 12px; }}
.attention-box {{
    background: #fff8e1; border-left: 3px solid #FF9800;
    padding: 12px 16px; border-radius: 0 6px 6px 0;
    margin-bottom: 14px; font-size: 13px;
}}
.attention-box ul {{ padding-left: 20px; margin-top: 6px; }}

/* ── Footer ──────────────────────────────────────────────────────────── */
.footer {{
    background: #f8f9fb;
    padding: 24px 40px;
    border-top: 1px solid #e0e0e0;
}}
.disclaimer {{
    font-size: 11px; color: #888; line-height: 1.5;
    margin-bottom: 14px;
    padding: 10px 14px;
    background: #fff;
    border-radius: 6px;
    border: 1px solid #eee;
}}
.footer-brand {{
    font-size: 12px; color: #999;
    display: flex; align-items: center; gap: 6px;
}}
.footer-divider {{ color: #ccc; }}

/* ── Utility ─────────────────────────────────────────────────────────── */
.muted {{ color: #999; font-style: italic; }}

/* ── Print styles ────────────────────────────────────────────────────── */
@media print {{
    body {{ background: #fff; }}
    .page {{
        box-shadow: none;
        margin: 0;
        max-width: 100%;
        border-radius: 0;
    }}
    .header {{
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }}
    .section {{ padding: 20px 30px; }}
    .page-break-before {{ page-break-before: auto; }}
    .footer {{ page-break-inside: avoid; }}
    .pillar-card {{ page-break-inside: avoid; }}
    .data-table {{ page-break-inside: auto; }}
    .data-table tr {{ page-break-inside: avoid; }}
    .insight-card, .rec-item {{ page-break-inside: avoid; }}
    .summary-grid {{ page-break-inside: avoid; }}

    @page {{
        size: A4;
        margin: 12mm 10mm;
    }}
}}

/* ── Responsive (for on-screen preview) ──────────────────────────────── */
@media screen and (max-width: 700px) {{
    .header {{ padding: 20px; flex-direction: column; text-align: center; }}
    .header-meta {{ text-align: center; }}
    .section {{ padding: 18px 20px; }}
    .summary-grid {{ grid-template-columns: 1fr 1fr; }}
    .wheel-table {{ font-size: 12px; }}
}}
</style>
</head>
<body>
<div class="page">
{body}
</div>
</body>
</html>'''
