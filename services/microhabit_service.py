"""Micro Habits service: 2-Minute Rule, Habit Stacking, 4 Laws, Never Miss Twice,
Identity Statements, Temptation Bundling, Completion Heatmap, Milestones."""

from datetime import date, timedelta
from db.database import get_connection
from config.settings import MICRO_VERSIONS, FOUR_LAWS_QUESTIONS, MILESTONE_THRESHOLDS
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


# ── Identity Statements ──────────────────────────────────────────────────────

def set_identity(habit_id: int, statement: str) -> None:
    """Set or update the identity_statement column for a habit."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE habits SET identity_statement = ? WHERE id = ?",
            (statement, habit_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_identity(habit_id: int) -> str | None:
    """Get the identity statement for a habit. Returns None if not set."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT identity_statement FROM habits WHERE id = ?", (habit_id,),
        ).fetchone()
        if not row:
            return None
        return row["identity_statement"]
    finally:
        conn.close()


# ── Temptation Bundling ──────────────────────────────────────────────────────

def set_temptation_bundle(habit_id: int, bundle_text: str) -> None:
    """Set or update the temptation_bundle column for a habit."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE habits SET temptation_bundle = ? WHERE id = ?",
            (bundle_text, habit_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_temptation_bundle(habit_id: int) -> str | None:
    """Get the temptation bundle for a habit. Returns None if not set."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT temptation_bundle FROM habits WHERE id = ?", (habit_id,),
        ).fetchone()
        if not row:
            return None
        return row["temptation_bundle"]
    finally:
        conn.close()


# ── Completion Heatmap ───────────────────────────────────────────────────────

def get_completion_heatmap_data(user_id: int, weeks: int = 12,
                                ref_date: date = None) -> dict:
    """Return {date_str: completion_rate} for the past N weeks.

    completion_rate = completed_habits / total_active_habits for each day.
    """
    if ref_date is None:
        ref_date = date.today()
    start = ref_date - timedelta(days=weeks * 7)

    conn = get_connection()
    try:
        # Count active habits
        habit_rows = conn.execute(
            "SELECT id FROM habits WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchall()
        total_habits = len(habit_rows)
        if total_habits == 0:
            return {}

        # Get all completions in the date range
        logs = conn.execute(
            "SELECT log_date, COUNT(DISTINCT habit_id) AS done "
            "FROM habit_log "
            "WHERE user_id = ? AND log_date >= ? AND log_date < ? "
            "AND completed_count > 0 "
            "GROUP BY log_date",
            (user_id, start.isoformat(), ref_date.isoformat()),
        ).fetchall()

        log_map = {r["log_date"]: r["done"] for r in logs}

        result = {}
        for i in range(weeks * 7):
            d = (start + timedelta(days=i)).isoformat()
            done = log_map.get(d, 0)
            result[d] = round(done / total_habits, 2)
        return result
    finally:
        conn.close()


# ── Milestone Badges ─────────────────────────────────────────────────────────

def _get_max_streak(habit_id: int, user_id: int, ref_date: date) -> int:
    """Compute the maximum consecutive-day streak for a habit up to ref_date."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT log_date FROM habit_log "
            "WHERE habit_id = ? AND user_id = ? AND completed_count > 0 "
            "AND log_date <= ? "
            "ORDER BY log_date DESC",
            (habit_id, user_id, ref_date.isoformat()),
        ).fetchall()
        if not rows:
            return 0

        dates = sorted(date.fromisoformat(r["log_date"]) for r in rows)
        max_streak = 1
        current = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i - 1]).days == 1:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 1
        return max_streak
    finally:
        conn.close()


def get_habit_milestones(habit_id: int, user_id: int,
                         ref_date: date = None) -> list[dict]:
    """Return milestone badge status for a habit.

    Each item: {days, label, emoji, tier, earned: bool}
    """
    if ref_date is None:
        ref_date = date.today()
    streak = _get_max_streak(habit_id, user_id, ref_date)
    result = []
    for m in MILESTONE_THRESHOLDS:
        result.append({
            "days": m["days"],
            "label": m["label"],
            "emoji": m["emoji"],
            "tier": m["tier"],
            "earned": streak >= m["days"],
        })
    return result


def get_all_milestones_summary(user_id: int, ref_date: date = None) -> dict:
    """Return summary: total_earned, best_streak across all active habits."""
    if ref_date is None:
        ref_date = date.today()
    habits = get_active_habits(user_id)
    total_earned = 0
    best_streak = 0
    for h in habits:
        streak = _get_max_streak(h["id"], user_id, ref_date)
        best_streak = max(best_streak, streak)
        for m in MILESTONE_THRESHOLDS:
            if streak >= m["days"]:
                total_earned += 1
    return {"total_earned": total_earned, "best_streak": best_streak}
