"""Exercise prescription generation service.

Generates science-based training programs using PPL split, RP volume
landmarks, and mesocycle periodization. Pulls exercises from the
existing exercise library.
"""

from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from db.database import get_connection
from config.exercise_prescription_data import (
    VOLUME_LANDMARKS,
    MESOCYCLE_TEMPLATES,
    PPL_SPLIT,
    SCHEDULE_TEMPLATES,
    RIR_GUIDE,
    DELOAD_PROTOCOL,
)
from config.exercise_library_data import EXERCISE_LIBRARY


# ── Helpers ───────────────────────────────────────────────────────────────

def _get_exercises_for_slot(muscle_group: str, exercise_type: str) -> list[dict]:
    """Return exercises from the library matching a muscle group and type."""
    return [
        e for e in EXERCISE_LIBRARY
        if e["muscle_group"] == muscle_group and e["type"] == exercise_type
    ]


def _pick_exercise(muscle_group: str, exercise_type: str, exclude_ids: set | None = None, prefer_id: str | None = None) -> dict | None:
    """Pick an exercise for a slot, avoiding duplicates within a session."""
    exclude_ids = exclude_ids or set()
    candidates = [
        e for e in _get_exercises_for_slot(muscle_group, exercise_type)
        if e["id"] not in exclude_ids
    ]
    # If a preferred exercise is specified, try it first
    if prefer_id and candidates:
        preferred = [e for e in candidates if e["id"] == prefer_id]
        if preferred:
            return preferred[0]
    if candidates:
        return candidates[0]
    # Fallback: any exercise for this muscle group
    fallbacks = [
        e for e in EXERCISE_LIBRARY
        if e["muscle_group"] == muscle_group and e["id"] not in exclude_ids
    ]
    return fallbacks[0] if fallbacks else None


def _compute_week_sets(muscle: str, volume_pct: float, level: str) -> int:
    """Compute target sets for a muscle group in a given week.

    volume_pct: 0.0 = MEV, 1.0 = MRV, -1 = deload
    """
    vl = VOLUME_LANDMARKS.get(muscle)
    if not vl:
        return 0
    mev = vl["mev"]
    mav_mid = (vl["mav_low"] + vl["mav_high"]) / 2
    mrv = vl["mrv"]

    if volume_pct < 0:  # deload
        return max(round(vl["mv"] * DELOAD_PROTOCOL["volume_reduction"]), 2)

    # Interpolate: 0.0 = MEV, 0.5 = mid MAV, 1.0 = MRV
    if volume_pct <= 0.5:
        frac = volume_pct / 0.5
        return round(mev + (mav_mid - mev) * frac)
    else:
        frac = (volume_pct - 0.5) / 0.5
        return round(mav_mid + (mrv - mav_mid) * frac)


# ── Program Generation ────────────────────────────────────────────────────

def generate_program(
    level: str = "intermediate",
    schedule: str = "ppl_6",
    goal: str = "hypertrophy",
) -> dict:
    """Generate a full training program.

    Returns a dict with mesocycle info and per-day exercise prescriptions.
    """
    meso = MESOCYCLE_TEMPLATES[level]
    sched = SCHEDULE_TEMPLATES[schedule]

    program = {
        "level": level,
        "schedule": schedule,
        "goal": goal,
        "mesocycle": {
            "label": meso["label"],
            "weeks": meso["weeks"],
            "note": meso["note"],
        },
        "schedule_info": {
            "label": sched["label"],
            "days_per_week": sched["days_per_week"],
            "note": sched["note"],
        },
        "weeks": [],
    }

    for week_info in meso["progression"]:
        week_num = week_info["week"]
        vol_pct = week_info["volume_pct"]
        rir = week_info["rir"]
        is_deload = vol_pct < 0

        week_data = {
            "week": week_num,
            "label": week_info["label"],
            "rir": rir,
            "is_deload": is_deload,
            "days": [],
        }

        for day_idx, day_key in enumerate(sched["schedule"]):
            split = PPL_SPLIT[day_key]
            day_data = {
                "day": day_idx + 1,
                "split": day_key,
                "label": split["label"],
                "icon": split["icon"],
                "color": split["color"],
                "subtitle": split["subtitle"],
                "exercises": [],
            }

            used_ids: set[str] = set()
            for slot in split["slots"]:
                ex = _pick_exercise(slot["muscle"], slot["type"], used_ids, slot.get("prefer_id"))
                if not ex:
                    continue
                used_ids.add(ex["id"])

                # Adjust sets based on volume progression
                base_sets = slot["sets"]
                if is_deload:
                    adj_sets = max(round(base_sets * DELOAD_PROTOCOL["volume_reduction"]), 1)
                elif vol_pct == 0.0:
                    adj_sets = max(base_sets - 1, 2)  # MEV: slightly lower
                elif vol_pct >= 0.75:
                    adj_sets = base_sets + 1  # High MAV: slightly higher
                else:
                    adj_sets = base_sets

                # Adjust RIR for this slot (compound vs isolation)
                slot_rir = rir
                if slot["type"] == "isolation" and rir > 0:
                    slot_rir = max(rir - 1, 0)  # Push isolation closer to failure

                day_data["exercises"].append({
                    "exercise_id": ex["id"],
                    "exercise_name": ex["name"],
                    "muscle_group": ex["muscle_group"],
                    "equipment": ex["equipment"],
                    "slot_label": slot["label"],
                    "sets": adj_sets,
                    "reps": slot["reps"],
                    "rir": slot_rir,
                    "type": slot["type"],
                })

            week_data["days"].append(day_data)

        program["weeks"].append(week_data)

    return program


def get_week_volume_summary(program: dict, week_idx: int) -> dict[str, int]:
    """Compute total weekly sets per muscle group for a given week."""
    if week_idx >= len(program["weeks"]):
        return {}

    week = program["weeks"][week_idx]
    volume: dict[str, int] = {}
    for day in week["days"]:
        for ex in day["exercises"]:
            mg = ex["muscle_group"]
            volume[mg] = volume.get(mg, 0) + ex["sets"]
    return volume


def get_volume_targets(level: str) -> dict[str, dict]:
    """Return MEV/MAV/MRV targets for display."""
    targets = {}
    for key, vl in VOLUME_LANDMARKS.items():
        # Map volume landmark keys to exercise library muscle groups
        lib_key = key
        if key == "shoulders_side":
            lib_key = "shoulders"
        elif key == "shoulders_front":
            continue  # Skip — covered by pressing
        elif key in ("quads", "hamstrings"):
            lib_key = "legs"
        elif key == "calves":
            continue  # Grouped under legs

        if lib_key in targets:
            # Merge (e.g., quads + hamstrings → legs)
            targets[lib_key]["mev"] += vl["mev"]
            targets[lib_key]["mav_low"] += vl["mav_low"]
            targets[lib_key]["mav_high"] += vl["mav_high"]
            targets[lib_key]["mrv"] += vl["mrv"]
        else:
            targets[lib_key] = {
                "label": vl["label"],
                "mev": vl["mev"],
                "mav_low": vl["mav_low"],
                "mav_high": vl["mav_high"],
                "mrv": vl["mrv"],
            }
    return targets


# ── Persistence (save/load user programs) ─────────────────────────────────

def save_program(user_id: int, program: dict) -> int:
    """Save a generated program to the database."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO exercise_programs
               (user_id, level, schedule, goal, program_json, created_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (user_id, program["level"], program["schedule"],
             program["goal"], json.dumps(program)),
        )
        conn.commit()
        row = conn.execute("SELECT last_insert_rowid()").fetchone()
        return row[0]
    finally:
        conn.close()


def get_saved_program(user_id: int) -> dict | None:
    """Get the user's most recent saved program."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT id, program_json, created_at FROM exercise_programs
               WHERE user_id = ? ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        if row:
            program = json.loads(row[1])
            program["_db_id"] = row[0]
            program["_created_at"] = row[2]
            return program
        return None
    finally:
        conn.close()


def delete_program(user_id: int, program_id: int):
    """Delete a saved program."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM exercise_programs WHERE id = ? AND user_id = ?",
            (program_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


# ── Workout Logging (weight, reps, RPE per set) ──────────────────────────

def log_workout_sets(
    user_id: int,
    workout_date: str,
    week_number: int,
    day_number: int,
    split_type: str,
    sets_data: list[dict],
) -> int:
    """Save all sets for a workout session.

    sets_data: list of dicts with keys:
        exercise_id, exercise_name, set_number, prescribed_reps,
        actual_reps, weight_kg, rpe, notes
    Returns count of sets saved.
    """
    conn = get_connection()
    try:
        # Delete existing sets for this date+day (allows re-logging)
        conn.execute(
            """DELETE FROM workout_sets
               WHERE user_id = ? AND workout_date = ? AND day_number = ?""",
            (user_id, workout_date, day_number),
        )
        count = 0
        for s in sets_data:
            if not s.get("actual_reps") and not s.get("weight_kg"):
                continue  # Skip empty rows
            conn.execute(
                """INSERT INTO workout_sets
                   (user_id, workout_date, week_number, day_number, split_type,
                    exercise_id, exercise_name, set_number, prescribed_reps,
                    actual_reps, weight_kg, rpe, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, workout_date, week_number, day_number, split_type,
                 s["exercise_id"], s["exercise_name"], s["set_number"],
                 s.get("prescribed_reps"), s.get("actual_reps"),
                 s.get("weight_kg"), s.get("rpe"), s.get("notes")),
            )
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def get_workout_log(user_id: int, workout_date: str, day_number: int) -> list[dict]:
    """Get logged sets for a specific workout session."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM workout_sets
               WHERE user_id = ? AND workout_date = ? AND day_number = ?
               ORDER BY exercise_id, set_number""",
            (user_id, workout_date, day_number),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_workouts(user_id: int, limit: int = 10) -> list[dict]:
    """Get recent workout sessions (grouped by date + day)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT workout_date, day_number, split_type, week_number,
                      COUNT(*) as total_sets,
                      COUNT(DISTINCT exercise_id) as exercises,
                      SUM(actual_reps) as total_reps,
                      AVG(rpe) as avg_rpe
               FROM workout_sets
               WHERE user_id = ?
               GROUP BY workout_date, day_number
               ORDER BY workout_date DESC, day_number DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_exercise_history(user_id: int, exercise_id: str, limit: int = 20) -> list[dict]:
    """Get history for a specific exercise (for progressive overload tracking)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT workout_date, set_number, actual_reps, weight_kg, rpe
               FROM workout_sets
               WHERE user_id = ? AND exercise_id = ?
               ORDER BY workout_date DESC, set_number
               LIMIT ?""",
            (user_id, exercise_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_last_weight_for_exercise(user_id: int, exercise_id: str) -> float | None:
    """Get the last recorded weight for an exercise (for pre-filling forms)."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT weight_kg FROM workout_sets
               WHERE user_id = ? AND exercise_id = ? AND weight_kg IS NOT NULL
               ORDER BY workout_date DESC, set_number DESC
               LIMIT 1""",
            (user_id, exercise_id),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()
