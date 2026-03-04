"""Atomic Habits microhabit service: 2-Minute Rule, Habit Stacking, 4 Laws, Never Miss Twice."""

from datetime import date, timedelta
from db.database import get_connection
from config.settings import MICRO_VERSIONS, FOUR_LAWS_QUESTIONS
from models.habit import get_habit_by_id, get_active_habits


# ── 2-Minute Rule ─────────────────────────────────────────────────────────────

def get_micro_version(habit_id: int) -> str:
    """Return the micro version text for a habit.

    Priority: stored micro_version > MICRO_VERSIONS lookup by name > generic.
    """
    habit = get_habit_by_id(habit_id)
    if not habit:
        return ""
    if habit.get("micro_version"):
        return habit["micro_version"]
    preset = MICRO_VERSIONS.get(habit["name"])
    if preset:
        return preset
    return f"Do '{habit['name']}' for just 2 minutes"


def set_micro_version(habit_id: int, micro_text: str) -> None:
    """Set or update the micro_version column for a habit."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE habits SET micro_version = ? WHERE id = ?",
            (micro_text, habit_id),
        )
        conn.commit()
    finally:
        conn.close()


def create_micro_habit(parent_habit_id: int, user_id: int) -> int:
    """Create a new habit that IS the micro version of the parent.

    Sets is_micro=1, copies pillar_id, uses micro_version as name.
    Returns the new habit_id.
    """
    parent = get_habit_by_id(parent_habit_id)
    if not parent:
        raise ValueError(f"Habit {parent_habit_id} not found")

    micro_name = get_micro_version(parent_habit_id)
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO habits (user_id, pillar_id, name, description, is_micro)
               VALUES (?, ?, ?, ?, 1)""",
            (user_id, parent["pillar_id"], micro_name,
             f"Micro version of: {parent['name']}"),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# ── Habit Stacking ────────────────────────────────────────────────────────────

def create_stack(user_id: int, name: str, anchor_cue: str = None,
                 anchor_time: str = None) -> int:
    """Create a new habit stack. Returns stack_id."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO habit_stacks (user_id, name, anchor_cue, anchor_time)
               VALUES (?, ?, ?, ?)""",
            (user_id, name, anchor_cue, anchor_time),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_stacks(user_id: int) -> list[dict]:
    """Get all active stacks for a user, each with habit_count."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT s.*, COUNT(h.id) AS habit_count
               FROM habit_stacks s
               LEFT JOIN habits h ON h.stack_id = s.id AND h.is_active = 1
               WHERE s.user_id = ? AND s.is_active = 1
               GROUP BY s.id
               ORDER BY s.name""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_to_stack(habit_id: int, stack_id: int, position: int = None) -> None:
    """Add a habit to a stack at the given position (or append at end)."""
    conn = get_connection()
    try:
        if position is None:
            row = conn.execute(
                "SELECT COALESCE(MAX(stack_order), 0) + 1 AS next_pos "
                "FROM habits WHERE stack_id = ?",
                (stack_id,),
            ).fetchone()
            position = row["next_pos"]
        conn.execute(
            "UPDATE habits SET stack_id = ?, stack_order = ? WHERE id = ?",
            (stack_id, position, habit_id),
        )
        conn.commit()
    finally:
        conn.close()


def remove_from_stack(habit_id: int) -> None:
    """Remove a habit from its stack, reorder remaining habits."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT stack_id, stack_order FROM habits WHERE id = ?", (habit_id,),
        ).fetchone()
        if not row or not row["stack_id"]:
            return
        stack_id = row["stack_id"]

        conn.execute(
            "UPDATE habits SET stack_id = NULL, stack_order = 0 WHERE id = ?",
            (habit_id,),
        )
        # Reorder remaining: close the gap
        remaining = conn.execute(
            "SELECT id FROM habits WHERE stack_id = ? AND is_active = 1 ORDER BY stack_order",
            (stack_id,),
        ).fetchall()
        for idx, r in enumerate(remaining, start=1):
            conn.execute(
                "UPDATE habits SET stack_order = ? WHERE id = ?", (idx, r["id"]),
            )
        conn.commit()
    finally:
        conn.close()


def get_stack_habits(stack_id: int) -> list[dict]:
    """Get all habits in a stack, ordered by stack_order."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM habits WHERE stack_id = ? AND is_active = 1 ORDER BY stack_order",
            (stack_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def reorder_stack(stack_id: int, habit_ids: list[int]) -> None:
    """Reorder habits in a stack according to the provided list order."""
    conn = get_connection()
    try:
        for idx, hid in enumerate(habit_ids, start=1):
            conn.execute(
                "UPDATE habits SET stack_order = ? WHERE id = ? AND stack_id = ?",
                (idx, hid, stack_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_stack_text(stack_id: int) -> str:
    """Generate human-readable stack chain text."""
    conn = get_connection()
    try:
        stack = conn.execute(
            "SELECT * FROM habit_stacks WHERE id = ?", (stack_id,),
        ).fetchone()
        if not stack:
            return ""

        habits = get_stack_habits(stack_id)
        parts = []
        if stack["anchor_cue"]:
            parts.append(stack["anchor_cue"])
        for h in habits:
            parts.append(h["name"])
        return " → ".join(parts)
    finally:
        conn.close()


# ── 4 Laws Scorecard ─────────────────────────────────────────────────────────

def save_four_laws(habit_id: int, obvious: int, attractive: int,
                   easy: int, satisfying: int) -> None:
    """Save the 4 Laws scores for a habit (each 1-5)."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE habits
               SET law_obvious = ?, law_attractive = ?, law_easy = ?, law_satisfying = ?
               WHERE id = ?""",
            (obvious, attractive, easy, satisfying, habit_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_four_laws(habit_id: int) -> dict | None:
    """Get the 4 Laws scores for a habit. Returns dict or None if not scored."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT law_obvious, law_attractive, law_easy, law_satisfying FROM habits WHERE id = ?",
            (habit_id,),
        ).fetchone()
        if not row or row["law_obvious"] is None:
            return None
        return {
            "obvious": row["law_obvious"],
            "attractive": row["law_attractive"],
            "easy": row["law_easy"],
            "satisfying": row["law_satisfying"],
        }
    finally:
        conn.close()


def get_weakest_law(habit_id: int) -> str | None:
    """Return the name of the weakest law for a habit."""
    scores = get_four_laws(habit_id)
    if not scores:
        return None
    return min(scores, key=scores.get)


def diagnose_all_habits(user_id: int) -> list[dict]:
    """For each active habit with 4-laws scores, return habit info + weakest law + tip."""
    habits = get_active_habits(user_id)
    results = []
    for h in habits:
        scores = get_four_laws(h["id"])
        if not scores:
            continue
        weakest = min(scores, key=scores.get)
        tips = FOUR_LAWS_QUESTIONS.get(weakest, {}).get("tips", [])
        results.append({
            "id": h["id"],
            "name": h["name"],
            "pillar_id": h["pillar_id"],
            "scores": scores,
            "weakest_law": weakest,
            "tip": tips[0] if tips else "",
        })
    return results


def get_four_laws_averages(user_id: int) -> dict:
    """Return average 4-laws scores across all scored active habits."""
    habits = get_active_habits(user_id)
    totals = {"obvious": 0.0, "attractive": 0.0, "easy": 0.0, "satisfying": 0.0}
    count = 0
    for h in habits:
        scores = get_four_laws(h["id"])
        if not scores:
            continue
        for key in totals:
            totals[key] += scores[key]
        count += 1
    if count == 0:
        return {k: 0.0 for k in totals}
    return {k: v / count for k, v in totals.items()}


# ── Never Miss Twice ──────────────────────────────────────────────────────────

def get_missed_yesterday(user_id: int, ref_date: date = None) -> list[dict]:
    """Return list of active habits NOT completed yesterday."""
    if ref_date is None:
        ref_date = date.today()
    yesterday = (ref_date - timedelta(days=1)).isoformat()

    conn = get_connection()
    try:
        habits = conn.execute(
            "SELECT * FROM habits WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchall()

        completed_ids = set()
        rows = conn.execute(
            "SELECT habit_id FROM habit_log WHERE user_id = ? AND log_date = ? AND completed_count > 0",
            (user_id, yesterday),
        ).fetchall()
        for r in rows:
            completed_ids.add(r["habit_id"])

        missed = []
        for h in habits:
            if h["id"] not in completed_ids:
                missed.append(dict(h))
        return missed
    finally:
        conn.close()


def get_never_miss_twice_alerts(user_id: int, ref_date: date = None) -> list[dict]:
    """Return habits missed BOTH yesterday AND the day before (critical alerts)."""
    if ref_date is None:
        ref_date = date.today()
    yesterday = (ref_date - timedelta(days=1)).isoformat()
    day_before = (ref_date - timedelta(days=2)).isoformat()

    conn = get_connection()
    try:
        habits = conn.execute(
            "SELECT * FROM habits WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchall()

        # Get completions for both days
        rows = conn.execute(
            "SELECT habit_id, log_date FROM habit_log "
            "WHERE user_id = ? AND log_date IN (?, ?) AND completed_count > 0",
            (user_id, yesterday, day_before),
        ).fetchall()

        completed = {}  # {habit_id: set of dates}
        for r in rows:
            completed.setdefault(r["habit_id"], set()).add(r["log_date"])

        alerts = []
        for row in habits:
            h = dict(row)
            hid = h["id"]
            done_yesterday = yesterday in completed.get(hid, set())
            done_day_before = day_before in completed.get(hid, set())
            if not done_yesterday and not done_day_before:
                micro = h.get("micro_version") or MICRO_VERSIONS.get(h["name"], "")
                msg = (f"You missed '{h['name']}' 2 days in a row! "
                       f"Try just 2 minutes: {micro}") if micro else (
                       f"You missed '{h['name']}' 2 days in a row! Do it today.")
                alerts.append({**h, "days_missed": 2, "message": msg})
        return alerts
    finally:
        conn.close()
