"""Progressive Habit Unlocking: users start with limited habits, unlock more with consistency."""

from db.database import get_connection
from datetime import date, timedelta

# Unlocking gates: (required_consistency_days, max_habits_allowed, level, label)
UNLOCK_GATES = [
    (0, 3, 1, "Beginner"),
    (3, 6, 2, "Getting Started"),
    (7, 9, 3, "Building Momentum"),
    (14, 12, 4, "Habit Builder"),
    (21, 15, 5, "Consistent"),
    (30, 18, 6, "Committed"),
    (60, 999, 7, "Lifestyle Master"),
]


def get_journey(user_id: int) -> dict:
    """Get or create the user's journey state."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM user_journey WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return dict(row)

        # Create initial journey
        conn.execute(
            "INSERT OR IGNORE INTO user_journey (user_id, max_habits, consistency_days, level) VALUES (?, 3, 0, 1)",
            (user_id,),
        )
        conn.commit()
        return {"user_id": user_id, "max_habits": 3, "consistency_days": 0, "level": 1}
    finally:
        conn.close()


def update_journey(user_id: int) -> dict | None:
    """Recalculate consistency days and check for unlocks. Returns unlock info if leveled up."""
    conn = get_connection()
    try:
        # Calculate consecutive days with at least one habit completed
        rows = conn.execute(
            """SELECT DISTINCT log_date FROM habit_log
               WHERE user_id = ? AND completed_count > 0
               ORDER BY log_date DESC""",
            (user_id,),
        ).fetchall()

        streak = 0
        if rows:
            expected = date.today()
            for row in rows:
                d = date.fromisoformat(row["log_date"])
                if d == expected:
                    streak += 1
                    expected -= timedelta(days=1)
                elif d < expected:
                    break

        # Get current journey
        journey = get_journey(user_id)
        old_level = journey["level"]

        # Determine new level
        new_level = 1
        new_max = 3
        for req_days, max_h, lvl, label in UNLOCK_GATES:
            if streak >= req_days:
                new_level = lvl
                new_max = max_h

        # Update
        conn.execute(
            "UPDATE user_journey SET consistency_days = ?, max_habits = ?, level = ? WHERE user_id = ?",
            (streak, new_max, new_level, user_id),
        )
        conn.commit()

        if new_level > old_level:
            gate = UNLOCK_GATES[new_level - 1]
            return {
                "level": new_level,
                "label": gate[3],
                "max_habits": new_max,
                "consistency_days": streak,
            }
        return None
    finally:
        conn.close()


def get_next_unlock(user_id: int) -> dict | None:
    """Get info about the next unlock gate."""
    journey = get_journey(user_id)
    current_level = journey["level"]

    if current_level >= len(UNLOCK_GATES):
        return None  # Max level

    next_gate = UNLOCK_GATES[current_level]
    return {
        "required_days": next_gate[0],
        "current_days": journey["consistency_days"],
        "days_remaining": max(0, next_gate[0] - journey["consistency_days"]),
        "new_habits_allowed": next_gate[1],
        "next_level": next_gate[2],
        "next_label": next_gate[3],
    }


def can_add_habit(user_id: int) -> tuple[bool, str]:
    """Check if user can add a new habit. Returns (allowed, reason)."""
    journey = get_journey(user_id)
    conn = get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM habits WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()["cnt"]
    finally:
        conn.close()

    if count < journey["max_habits"]:
        return True, ""

    next_unlock = get_next_unlock(user_id)
    if next_unlock:
        return False, f"You've reached your habit limit ({journey['max_habits']}). Keep your streak going — {next_unlock['days_remaining']} more days to unlock {next_unlock['new_habits_allowed']} habits! (Level {next_unlock['next_label']})"
    return False, f"You've reached your habit limit ({journey['max_habits']})."


def get_level_label(level: int) -> str:
    """Get the label for a level."""
    if 1 <= level <= len(UNLOCK_GATES):
        return UNLOCK_GATES[level - 1][3]
    return "Unknown"
