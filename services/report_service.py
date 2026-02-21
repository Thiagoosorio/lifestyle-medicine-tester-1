"""Auto Weekly Report: data-driven weekly analysis with trends, correlations, and recommendations."""

import json
from datetime import date, timedelta
from db.database import get_connection
from config.settings import PILLARS


def get_or_generate_report(user_id: int, week_start: date) -> dict | None:
    """Get a cached weekly report or generate a new one."""
    week_str = week_start.isoformat()

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT report_text, stats_json FROM auto_weekly_reports WHERE user_id = ? AND week_start = ?",
            (user_id, week_str),
        ).fetchone()
        if row:
            stats = json.loads(row["stats_json"]) if row["stats_json"] else {}
            return {"report": row["report_text"], "stats": stats}
    finally:
        conn.close()

    # Generate new report
    report = _generate_report(user_id, week_start)
    if report:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO auto_weekly_reports (user_id, week_start, report_text, stats_json) VALUES (?, ?, ?, ?)",
                (user_id, week_str, report["report"], json.dumps(report["stats"])),
            )
            conn.commit()
        finally:
            conn.close()
    return report


def _generate_report(user_id: int, week_start: date) -> dict | None:
    """Generate a data-driven weekly report."""
    week_end = week_start + timedelta(days=6)
    week_str = week_start.isoformat()
    end_str = week_end.isoformat()

    conn = get_connection()
    try:
        # Get check-ins for the week
        checkins = conn.execute(
            "SELECT * FROM daily_checkins WHERE user_id = ? AND checkin_date BETWEEN ? AND ?",
            (user_id, week_str, end_str),
        ).fetchall()
        checkins = [dict(r) for r in checkins]

        if not checkins:
            return None

        # Get habit data
        habits = conn.execute(
            "SELECT * FROM habits WHERE user_id = ? AND is_active = 1", (user_id,)
        ).fetchall()
        habit_log = conn.execute(
            "SELECT * FROM habit_log WHERE user_id = ? AND log_date BETWEEN ? AND ?",
            (user_id, week_str, end_str),
        ).fetchall()

        # Previous week for comparison
        prev_start = week_start - timedelta(days=7)
        prev_end = week_start - timedelta(days=1)
        prev_checkins = conn.execute(
            "SELECT * FROM daily_checkins WHERE user_id = ? AND checkin_date BETWEEN ? AND ?",
            (user_id, prev_start.isoformat(), prev_end.isoformat()),
        ).fetchall()
        prev_checkins = [dict(r) for r in prev_checkins]
    finally:
        conn.close()

    # Calculate stats
    stats = _calculate_stats(checkins, habits, habit_log, prev_checkins)
    report_text = _build_report_text(stats, week_start)

    return {"report": report_text, "stats": stats}


def _calculate_stats(checkins: list, habits: list, habit_log: list, prev_checkins: list) -> dict:
    """Calculate weekly statistics."""
    def avg(values):
        return round(sum(values) / len(values), 1) if values else None

    # Current week averages
    mood_vals = [c["mood"] for c in checkins if c.get("mood")]
    energy_vals = [c["energy"] for c in checkins if c.get("energy")]

    pillar_fields = {
        1: "nutrition_rating", 2: "activity_rating", 3: "sleep_rating",
        4: "stress_rating", 5: "connection_rating", 6: "substance_rating",
    }
    pillar_avgs = {}
    for pid, field in pillar_fields.items():
        vals = [c[field] for c in checkins if c.get(field)]
        pillar_avgs[pid] = avg(vals)

    # Previous week averages for comparison
    prev_mood = avg([c["mood"] for c in prev_checkins if c.get("mood")])
    prev_energy = avg([c["energy"] for c in prev_checkins if c.get("energy")])
    prev_pillar_avgs = {}
    for pid, field in pillar_fields.items():
        vals = [c[field] for c in prev_checkins if c.get(field)]
        prev_pillar_avgs[pid] = avg(vals)

    # Habit completion
    total_habits = len(habits)
    completed_logs = [l for l in habit_log if dict(l).get("completed_count", 0) > 0]
    total_possible = total_habits * 7
    habit_completion = len(completed_logs) / total_possible if total_possible > 0 else 0

    # Check-in count
    checkin_count = len(checkins)

    # Best and worst day (by mood)
    if mood_vals and checkins:
        best_day = max(checkins, key=lambda c: c.get("mood", 0))
        worst_day = min(checkins, key=lambda c: c.get("mood", 0))
    else:
        best_day = worst_day = None

    # Top and bottom pillars
    ranked_pillars = sorted(
        [(pid, v) for pid, v in pillar_avgs.items() if v is not None],
        key=lambda x: x[1], reverse=True,
    )
    top_pillar = ranked_pillars[0] if ranked_pillars else None
    bottom_pillar = ranked_pillars[-1] if ranked_pillars else None

    # Week-over-week changes
    pillar_changes = {}
    for pid in pillar_fields:
        curr = pillar_avgs.get(pid)
        prev = prev_pillar_avgs.get(pid)
        if curr is not None and prev is not None:
            pillar_changes[pid] = round(curr - prev, 1)

    return {
        "checkin_count": checkin_count,
        "avg_mood": avg(mood_vals),
        "avg_energy": avg(energy_vals),
        "prev_avg_mood": prev_mood,
        "prev_avg_energy": prev_energy,
        "pillar_avgs": pillar_avgs,
        "pillar_changes": pillar_changes,
        "habit_completion": round(habit_completion * 100, 1),
        "top_pillar": top_pillar,
        "bottom_pillar": bottom_pillar,
        "best_day": best_day["checkin_date"] if best_day else None,
        "worst_day": worst_day["checkin_date"] if worst_day else None,
    }


def _build_report_text(stats: dict, week_start: date) -> str:
    """Build a readable weekly report."""
    week_end = week_start + timedelta(days=6)
    lines = []

    lines.append(f"**Weekly Report: {week_start.strftime('%b %d')} — {week_end.strftime('%b %d, %Y')}**")
    lines.append("")

    # Consistency
    lines.append(f"You checked in **{stats['checkin_count']}/7** days this week.")

    # Mood & Energy
    if stats["avg_mood"]:
        mood_line = f"Average mood: **{stats['avg_mood']}/10**"
        if stats["prev_avg_mood"]:
            diff = round(stats["avg_mood"] - stats["prev_avg_mood"], 1)
            arrow = "+" if diff > 0 else ""
            mood_line += f" ({arrow}{diff} vs last week)"
        lines.append(mood_line)

    if stats["avg_energy"]:
        energy_line = f"Average energy: **{stats['avg_energy']}/10**"
        if stats["prev_avg_energy"]:
            diff = round(stats["avg_energy"] - stats["prev_avg_energy"], 1)
            arrow = "+" if diff > 0 else ""
            energy_line += f" ({arrow}{diff} vs last week)"
        lines.append(energy_line)

    lines.append("")

    # Pillar highlights
    if stats["top_pillar"]:
        pid, score = stats["top_pillar"]
        lines.append(f"Strongest pillar: **{PILLARS[pid]['display_name']}** ({score}/10)")
    if stats["bottom_pillar"]:
        pid, score = stats["bottom_pillar"]
        lines.append(f"Focus area: **{PILLARS[pid]['display_name']}** ({score}/10)")

    # Changes
    improving = [(pid, ch) for pid, ch in stats.get("pillar_changes", {}).items() if ch > 0.5]
    declining = [(pid, ch) for pid, ch in stats.get("pillar_changes", {}).items() if ch < -0.5]

    if improving:
        names = ", ".join(f"{PILLARS[pid]['display_name']} (+{ch})" for pid, ch in improving)
        lines.append(f"Improving: {names}")
    if declining:
        names = ", ".join(f"{PILLARS[pid]['display_name']} ({ch})" for pid, ch in declining)
        lines.append(f"Needs attention: {names}")

    lines.append("")

    # Habits
    lines.append(f"Habit completion: **{stats['habit_completion']}%**")

    return "\n\n".join(lines)
