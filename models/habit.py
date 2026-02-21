from db.database import get_connection


def create_habit(user_id: int, pillar_id: int, name: str, description: str = "",
                 frequency: str = "daily", custom_days: str = None, target_per_day: int = 1,
                 cue_behavior: str = None, location: str = None,
                 implementation_intention: str = None) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO habits (user_id, pillar_id, name, description, frequency, custom_days,
               target_per_day, cue_behavior, location, implementation_intention)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, pillar_id, name, description, frequency, custom_days, target_per_day,
             cue_behavior, location, implementation_intention),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_active_habits(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM habits WHERE user_id = ? AND is_active = 1 ORDER BY pillar_id, sort_order",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_habits_by_pillar(user_id: int, pillar_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM habits WHERE user_id = ? AND pillar_id = ? AND is_active = 1 ORDER BY sort_order",
            (user_id, pillar_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def toggle_habit(habit_id: int, user_id: int, log_date: str, completed: bool):
    conn = get_connection()
    try:
        count = 1 if completed else 0
        conn.execute(
            "INSERT OR REPLACE INTO habit_log (habit_id, user_id, log_date, completed_count) VALUES (?, ?, ?, ?)",
            (habit_id, user_id, log_date, count),
        )
        conn.commit()
    finally:
        conn.close()


def get_habit_log_for_range(user_id: int, start_date: str, end_date: str) -> dict:
    """Returns {(habit_id, log_date): completed_count}."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT habit_id, log_date, completed_count FROM habit_log WHERE user_id = ? AND log_date BETWEEN ? AND ?",
            (user_id, start_date, end_date),
        ).fetchall()
        return {(r["habit_id"], r["log_date"]): r["completed_count"] for r in rows}
    finally:
        conn.close()


def deactivate_habit(habit_id: int, user_id: int):
    conn = get_connection()
    try:
        conn.execute("UPDATE habits SET is_active = 0 WHERE id = ? AND user_id = ?", (habit_id, user_id))
        conn.commit()
    finally:
        conn.close()


def get_habit_streak(habit_id: int, user_id: int) -> int:
    """Count consecutive days backwards from today where habit was completed."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT log_date FROM habit_log WHERE habit_id = ? AND user_id = ? AND completed_count > 0 ORDER BY log_date DESC",
            (habit_id, user_id),
        ).fetchall()
        if not rows:
            return 0

        from datetime import date, timedelta
        streak = 0
        expected = date.today()
        for row in rows:
            d = date.fromisoformat(row["log_date"])
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d < expected:
                break
        return streak
    finally:
        conn.close()


def get_all_habits(user_id: int) -> list:
    """Get all habits including inactive ones."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM habits WHERE user_id = ? ORDER BY is_active DESC, pillar_id, sort_order",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
