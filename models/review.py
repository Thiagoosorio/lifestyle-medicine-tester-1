from db.database import get_connection


def save_weekly_review(user_id: int, week_start: str, data: dict):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO weekly_reviews
               (user_id, week_start, avg_mood, avg_energy, habit_completion_pct,
                reflection, highlights, challenges, next_week_focus,
                ai_summary, ai_insights, ai_suggestions)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, week_start,
                data.get("avg_mood"), data.get("avg_energy"),
                data.get("habit_completion_pct"),
                data.get("reflection"), data.get("highlights"),
                data.get("challenges"), data.get("next_week_focus"),
                data.get("ai_summary"), data.get("ai_insights"),
                data.get("ai_suggestions"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_weekly_review(user_id: int, week_start: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM weekly_reviews WHERE user_id = ? AND week_start = ?",
            (user_id, week_start),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_weekly_reviews_for_month(user_id: int, year: int, month: int) -> list:
    conn = get_connection()
    try:
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"
        rows = conn.execute(
            "SELECT * FROM weekly_reviews WHERE user_id = ? AND week_start >= ? AND week_start < ? ORDER BY week_start",
            (user_id, start, end),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
