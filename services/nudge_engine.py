"""Proactive nudge engine: contextual coaching messages based on user behavior patterns."""

from datetime import date, timedelta
from db.database import get_connection
from config.settings import PILLARS


def get_active_nudges(user_id: int, max_nudges: int = 3) -> list:
    """Return a prioritized list of nudges for the user's dashboard."""
    nudges = []
    today = date.today().isoformat()

    conn = get_connection()
    try:
        # 1. Streak at risk — habits done yesterday but not today
        _check_streak_risk(conn, user_id, today, nudges)

        # 2. Pillar decline — any pillar dropped 2+ pts week-over-week
        _check_pillar_decline(conn, user_id, nudges)

        # 3. Goal deadline approaching with low progress
        _check_goal_deadlines(conn, user_id, today, nudges)

        # 4. Assessment reminder — 30+ days since last assessment
        _check_assessment_reminder(conn, user_id, today, nudges)

        # 5. No check-in today
        _check_missing_checkin(conn, user_id, today, nudges)

        # 6. Poor sleep quality (last 3 nights)
        _check_poor_sleep(conn, user_id, today, nudges)

        # 7. Low recovery score
        _check_low_recovery(user_id, nudges)

        # 8. Weight milestone toward goal
        _check_weight_milestone(conn, user_id, nudges)

    finally:
        conn.close()

    # Sort by priority (lower = more important) and return top N
    nudges.sort(key=lambda n: n["priority"])
    return nudges[:max_nudges]


def _check_streak_risk(conn, user_id, today, nudges):
    """Check if any habit streaks are at risk (done yesterday, not today)."""
    yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()

    rows = conn.execute("""
        SELECT h.id, h.name, h.pillar_id
        FROM habits h
        WHERE h.user_id = ? AND h.is_active = 1
        AND h.id IN (
            SELECT habit_id FROM habit_log
            WHERE user_id = ? AND log_date = ? AND completed_count > 0
        )
        AND h.id NOT IN (
            SELECT habit_id FROM habit_log
            WHERE user_id = ? AND log_date = ? AND completed_count > 0
        )
    """, (user_id, user_id, yesterday, user_id, today)).fetchall()

    if rows:
        # Get streak length for the most important one
        for row in rows[:2]:
            streak = _quick_streak(conn, user_id, row["id"], yesterday)
            if streak >= 3:
                pillar = PILLARS.get(row["pillar_id"], {})
                nudges.append({
                    "type": "streak_risk",
                    "priority": 1,
                    "icon": ":material/local_fire_department:",
                    "color": "warning",
                    "title": f"Streak at Risk!",
                    "message": f"Your **{row['name']}** streak is at **{streak} days**! Don't let it slip — you're building real momentum.",
                    "action_label": "Go to Weekly Plan",
                    "action_page": "pages/weekly_plan.py",
                })


def _quick_streak(conn, user_id, habit_id, from_date):
    """Quick streak count for a specific habit."""
    rows = conn.execute(
        "SELECT log_date FROM habit_log WHERE habit_id = ? AND user_id = ? AND completed_count > 0 ORDER BY log_date DESC",
        (habit_id, user_id),
    ).fetchall()
    streak = 0
    expected = date.fromisoformat(from_date)
    for row in rows:
        d = date.fromisoformat(row["log_date"])
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break
    return streak


def _check_pillar_decline(conn, user_id, nudges):
    """Check if any pillar rating dropped 2+ points week-over-week."""
    today = date.today()
    this_week_start = (today - timedelta(days=6)).isoformat()
    last_week_start = (today - timedelta(days=13)).isoformat()
    last_week_end = (today - timedelta(days=7)).isoformat()

    pillar_fields = {
        1: "nutrition_rating", 2: "activity_rating", 3: "sleep_rating",
        4: "stress_rating", 5: "connection_rating", 6: "substance_rating",
    }

    for pid, field in pillar_fields.items():
        this_avg = conn.execute(
            f"SELECT AVG({field}) as avg_val FROM daily_checkins WHERE user_id = ? AND checkin_date >= ? AND {field} IS NOT NULL",
            (user_id, this_week_start),
        ).fetchone()

        last_avg = conn.execute(
            f"SELECT AVG({field}) as avg_val FROM daily_checkins WHERE user_id = ? AND checkin_date >= ? AND checkin_date <= ? AND {field} IS NOT NULL",
            (user_id, last_week_start, last_week_end),
        ).fetchone()

        if this_avg["avg_val"] and last_avg["avg_val"]:
            drop = last_avg["avg_val"] - this_avg["avg_val"]
            if drop >= 2.0:
                pillar = PILLARS.get(pid, {})
                nudges.append({
                    "type": "pillar_decline",
                    "priority": 2,
                    "icon": pillar.get("icon", ":material/trending_down:"),
                    "color": "error",
                    "title": f"{pillar.get('display_name', '')} Trending Down",
                    "message": f"Your **{pillar.get('display_name', '')}** ratings dropped **{drop:.1f} points** this week. Want to explore what's going on?",
                    "action_label": "Talk to AI Coach",
                    "action_page": "pages/ai_coach.py",
                })
                break  # Only show one pillar decline


def _check_goal_deadlines(conn, user_id, today, nudges):
    """Check for goals with approaching deadlines and low progress."""
    week_ahead = (date.fromisoformat(today) + timedelta(days=7)).isoformat()

    rows = conn.execute(
        "SELECT title, progress_pct, target_date, pillar_id FROM goals WHERE user_id = ? AND status = 'active' AND target_date <= ? AND progress_pct < 50",
        (user_id, week_ahead),
    ).fetchall()

    for row in rows[:1]:
        days_left = (date.fromisoformat(row["target_date"][:10]) - date.fromisoformat(today)).days
        if days_left < 0:
            days_left = 0
        nudges.append({
            "type": "goal_deadline",
            "priority": 3,
            "icon": ":material/flag:",
            "color": "warning",
            "title": "Goal Deadline Approaching",
            "message": f"Your goal **\"{row['title']}\"** is due in **{days_left} days** and you're at **{row['progress_pct']}%**. Let's break down what's left.",
            "action_label": "View Goals",
            "action_page": "pages/goals.py",
        })


def _check_assessment_reminder(conn, user_id, today, nudges):
    """Remind if it's been 30+ days since last wheel assessment."""
    row = conn.execute(
        "SELECT MAX(assessed_at) as last_at FROM wheel_assessments WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if row and row["last_at"]:
        last_date = date.fromisoformat(row["last_at"][:10])
        days_since = (date.fromisoformat(today) - last_date).days
        if days_since >= 30:
            nudges.append({
                "type": "assessment_reminder",
                "priority": 4,
                "icon": ":material/radar:",
                "color": "info",
                "title": "Time for a Wheel Check-in",
                "message": f"It's been **{days_since} days** since your last Wheel of Life assessment. A new one helps track your growth!",
                "action_label": "Take Assessment",
                "action_page": "pages/wheel_assessment.py",
            })


def _check_missing_checkin(conn, user_id, today, nudges):
    """Nudge if no check-in today."""
    row = conn.execute(
        "SELECT id FROM daily_checkins WHERE user_id = ? AND checkin_date = ?",
        (user_id, today),
    ).fetchone()

    if not row:
        nudges.append({
            "type": "missing_checkin",
            "priority": 5,
            "icon": ":material/edit_note:",
            "color": "info",
            "title": "How are you feeling today?",
            "message": "You haven't checked in yet today. A quick check-in helps track your progress and keeps your streak alive!",
            "action_label": None,  # Handled by the dashboard check-in form
            "action_page": None,
        })


def _check_poor_sleep(conn, user_id, today, nudges):
    """Nudge if last 3 nights have poor sleep scores (avg < 60)."""
    try:
        rows = conn.execute(
            "SELECT sleep_score FROM sleep_logs WHERE user_id = ? ORDER BY sleep_date DESC LIMIT 3",
            (user_id,),
        ).fetchall()
        if len(rows) >= 3:
            avg_score = sum(r["sleep_score"] for r in rows) / len(rows)
            if avg_score < 60:
                nudges.append({
                    "type": "poor_sleep",
                    "priority": 2,
                    "icon": ":material/bedtime_off:",
                    "color": "warning",
                    "title": "Sleep Quality Alert",
                    "message": f"Your average sleep score over the last 3 nights is **{avg_score:.0f}/100**. Consider reviewing your sleep hygiene habits.",
                    "action_label": "Sleep Tracker",
                    "action_page": "pages/sleep_tracker.py",
                })
    except Exception:
        pass


def _check_low_recovery(user_id, nudges):
    """Nudge if today's recovery score is below 40."""
    try:
        from services.recovery_service import calculate_recovery_score
        rec = calculate_recovery_score(user_id)
        if rec and rec["score"] < 40:
            zone = rec["zone"]
            nudges.append({
                "type": "low_recovery",
                "priority": 2,
                "icon": ":material/hotel:",
                "color": "error",
                "title": "Low Recovery — Consider Resting",
                "message": f"Your recovery score is **{rec['score']}/100** ({zone['label']}). {zone.get('recommendation', 'Consider a rest day or gentle activity.')}",
                "action_label": "View Recovery",
                "action_page": "pages/recovery.py",
            })
    except Exception:
        pass


def _check_weight_milestone(conn, user_id, nudges):
    """Celebrate when user crosses a 1kg milestone toward their weight goal."""
    try:
        goal_row = conn.execute(
            "SELECT goal_weight_kg FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not goal_row or not goal_row["goal_weight_kg"]:
            return

        goal = goal_row["goal_weight_kg"]

        rows = conn.execute(
            "SELECT weight_kg FROM body_metrics WHERE user_id = ? AND weight_kg IS NOT NULL ORDER BY log_date DESC LIMIT 2",
            (user_id,),
        ).fetchall()
        if len(rows) < 2:
            return

        latest = rows[0]["weight_kg"]
        previous = rows[1]["weight_kg"]
        remaining = abs(latest - goal)

        # Check if we crossed a whole-kg milestone toward the goal
        if goal < latest:  # Losing weight
            if int(previous) > int(latest) and latest > goal:
                nudges.append({
                    "type": "weight_milestone",
                    "priority": 4,
                    "icon": ":material/emoji_events:",
                    "color": "success",
                    "title": "Weight Milestone!",
                    "message": f"You reached **{latest:.1f} kg** — only **{remaining:.1f} kg** to your goal of {goal:.1f} kg!",
                    "action_label": "Body Metrics",
                    "action_page": "pages/body_metrics.py",
                })
        elif goal > latest:  # Gaining weight
            if int(previous) < int(latest) and latest < goal:
                nudges.append({
                    "type": "weight_milestone",
                    "priority": 4,
                    "icon": ":material/emoji_events:",
                    "color": "success",
                    "title": "Weight Milestone!",
                    "message": f"You reached **{latest:.1f} kg** — only **{remaining:.1f} kg** to your goal of {goal:.1f} kg!",
                    "action_label": "Body Metrics",
                    "action_page": "pages/body_metrics.py",
                })
    except Exception:
        pass
