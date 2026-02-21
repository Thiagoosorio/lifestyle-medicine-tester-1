from datetime import date, timedelta
from models.habit import (
    create_habit, get_active_habits, toggle_habit,
    get_habit_log_for_range, get_habit_streak,
)
from config.settings import DEFAULT_HABITS


def initialize_default_habits(user_id: int):
    """Create default habits for a new user."""
    existing = get_active_habits(user_id)
    if existing:
        return
    for pillar_id, habit_names in DEFAULT_HABITS.items():
        for name in habit_names:
            create_habit(user_id, pillar_id, name)


def get_week_habit_data(user_id: int, week_start: date) -> dict:
    """Get habits and their completion status for a week.
    Returns {habit_id: {habit: {...}, completions: {date_str: bool}}}
    """
    habits = get_active_habits(user_id)
    week_end = week_start + timedelta(days=6)
    log = get_habit_log_for_range(user_id, week_start.isoformat(), week_end.isoformat())

    result = {}
    for h in habits:
        completions = {}
        for i in range(7):
            d = (week_start + timedelta(days=i)).isoformat()
            completions[d] = log.get((h["id"], d), 0) > 0
        result[h["id"]] = {"habit": h, "completions": completions}
    return result


def get_day_completion_rate(user_id: int, day: str) -> float:
    """Get the percentage of habits completed on a specific day."""
    habits = get_active_habits(user_id)
    if not habits:
        return 0.0
    log = get_habit_log_for_range(user_id, day, day)
    completed = sum(1 for h in habits if log.get((h["id"], day), 0) > 0)
    return completed / len(habits)


def get_week_completion_rate(user_id: int, week_start: date) -> float:
    """Average daily completion rate for a week."""
    rates = []
    for i in range(7):
        d = (week_start + timedelta(days=i)).isoformat()
        rates.append(get_day_completion_rate(user_id, d))
    return sum(rates) / len(rates) if rates else 0.0


def get_overall_streak(user_id: int) -> int:
    """Consecutive days with at least one habit completed or check-in done."""
    from db.database import get_connection
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT DISTINCT log_date as d FROM habit_log WHERE user_id = ? AND completed_count > 0
               UNION
               SELECT DISTINCT checkin_date as d FROM daily_checkins WHERE user_id = ?
               ORDER BY d DESC""",
            (user_id, user_id),
        ).fetchall()
        if not rows:
            return 0

        streak = 0
        expected = date.today()
        for row in rows:
            d = date.fromisoformat(row["d"])
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d < expected:
                break
        return streak
    finally:
        conn.close()
