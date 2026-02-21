from db.database import get_connection


def save_checkin(user_id: int, checkin_date: str, data: dict):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO daily_checkins
               (user_id, checkin_date, mood, energy,
                nutrition_rating, activity_rating, sleep_rating,
                stress_rating, connection_rating, substance_rating,
                journal_entry, gratitude, win_of_day, challenge)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, checkin_date,
                data.get("mood"), data.get("energy"),
                data.get("nutrition_rating"), data.get("activity_rating"),
                data.get("sleep_rating"), data.get("stress_rating"),
                data.get("connection_rating"), data.get("substance_rating"),
                data.get("journal_entry"), data.get("gratitude"),
                data.get("win_of_day"), data.get("challenge"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_checkin(user_id: int, checkin_date: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM daily_checkins WHERE user_id = ? AND checkin_date = ?",
            (user_id, checkin_date),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_checkins_for_range(user_id: int, start_date: str, end_date: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM daily_checkins WHERE user_id = ? AND checkin_date BETWEEN ? AND ? ORDER BY checkin_date",
            (user_id, start_date, end_date),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_checkin_dates(user_id: int, limit: int = 365) -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT checkin_date FROM daily_checkins WHERE user_id = ? ORDER BY checkin_date DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [r["checkin_date"] for r in rows]
    finally:
        conn.close()


def get_recent_checkins(user_id: int, days: int = 14) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM daily_checkins
               WHERE user_id = ? AND checkin_date >= date('now', ?)
               ORDER BY checkin_date DESC""",
            (user_id, f"-{days} days"),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
