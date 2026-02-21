"""Engagement coin system: earn LifeCoins for daily activities."""

from db.database import get_connection
from datetime import date


def get_coin_balance(user_id: int) -> int:
    """Get total coin balance for a user."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as balance FROM coin_transactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row["balance"]
    finally:
        conn.close()


def award_coins(user_id: int, amount: int, reason: str, ref_date: str = None):
    """Award coins to a user. Unique per user+reason+date to prevent duplicates."""
    if ref_date is None:
        ref_date = date.today().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO coin_transactions (user_id, amount, reason, ref_date) VALUES (?, ?, ?, ?)",
            (user_id, amount, reason, ref_date),
        )
        conn.commit()
    finally:
        conn.close()


def award_daily_coins(user_id: int, today_str: str = None):
    """Check and award coins for today's completed activities."""
    if today_str is None:
        today_str = date.today().isoformat()

    conn = get_connection()
    try:
        # 1 coin for daily check-in
        checkin = conn.execute(
            "SELECT id FROM daily_checkins WHERE user_id = ? AND checkin_date = ?",
            (user_id, today_str),
        ).fetchone()
        if checkin:
            award_coins(user_id, 1, "checkin", today_str)

        # 1 coin for completing all habits
        total_habits = conn.execute(
            "SELECT COUNT(*) as cnt FROM habits WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()["cnt"]

        if total_habits > 0:
            done_habits = conn.execute(
                "SELECT COUNT(*) as cnt FROM habit_log WHERE user_id = ? AND log_date = ? AND completed_count > 0",
                (user_id, today_str),
            ).fetchone()["cnt"]
            if done_habits >= total_habits:
                award_coins(user_id, 2, "all_habits", today_str)

        # 1 bonus coin for streak milestones (7, 14, 21, 30, 60, 90...)
        _check_streak_milestone(conn, user_id, today_str)

    finally:
        conn.close()


def _check_streak_milestone(conn, user_id, today_str):
    """Award bonus coins for streak milestones."""
    from datetime import timedelta

    rows = conn.execute(
        """SELECT DISTINCT d FROM (
            SELECT log_date as d FROM habit_log WHERE user_id = ? AND completed_count > 0
            UNION
            SELECT checkin_date as d FROM daily_checkins WHERE user_id = ?
        ) ORDER BY d DESC""",
        (user_id, user_id),
    ).fetchall()

    streak = 0
    expected = date.fromisoformat(today_str)
    for row in rows:
        d = date.fromisoformat(row["d"])
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break

    milestones = [7, 14, 21, 30, 60, 90, 180, 365]
    if streak in milestones:
        award_coins(user_id, 5, f"streak_{streak}", today_str)


def get_coin_history(user_id: int, limit: int = 20) -> list:
    """Get recent coin transactions."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM coin_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


COIN_REASON_LABELS = {
    "checkin": "Daily Check-in",
    "all_habits": "All Habits Complete",
    "streak_7": "7-Day Streak!",
    "streak_14": "14-Day Streak!",
    "streak_21": "21-Day Streak!",
    "streak_30": "30-Day Streak!",
    "streak_60": "60-Day Streak!",
    "streak_90": "90-Day Streak!",
    "streak_180": "6-Month Streak!",
    "streak_365": "1-Year Streak!",
}
