"""Cycling training service — FTP zones, TSS/IF, PMC (CTL/ATL/TSB), plan generation.

Implements the Coggan power model and Banister impulse-response PMC.
References:
  - Allen & Coggan (2019) "Training and Racing with a Power Meter" 3rd ed.
  - Banister et al. (1975) impulse-response model for training load.
"""

from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from db.database import get_connection
from config.cycling_data import (
    POWER_ZONES,
    WORKOUT_LIBRARY,
    WORKOUT_LIBRARY_BY_ID,
    TRAINING_PHASES,
    PROGRESSION_DEFAULTS,
    DIFFICULTY_SURVEY_OPTIONS,
)


# ── Profile ────────────────────────────────────────────────────────────────

def get_cycling_profile(user_id: int) -> dict | None:
    """Return the user's cycling profile or None if not set."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM cycling_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_cycling_profile(
    user_id: int,
    ftp_watts: int,
    weight_kg: float | None = None,
    athlete_type: str = "All-Around",
    goal_event: str | None = None,
    goal_date: str | None = None,
) -> None:
    """Insert or update the user's cycling profile."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO cycling_profile
               (user_id, ftp_watts, weight_kg, athlete_type, goal_event, goal_date,
                ftp_tested_date, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, date('now'), datetime('now'))
               ON CONFLICT(user_id) DO UPDATE SET
                 ftp_watts = excluded.ftp_watts,
                 weight_kg = excluded.weight_kg,
                 athlete_type = excluded.athlete_type,
                 goal_event = excluded.goal_event,
                 goal_date = excluded.goal_date,
                 ftp_tested_date = date('now'),
                 updated_at = datetime('now')""",
            (user_id, ftp_watts, weight_kg, athlete_type, goal_event, goal_date),
        )
        conn.commit()
    finally:
        conn.close()


# ── Power Zones ────────────────────────────────────────────────────────────

def get_zones(ftp_watts: int) -> dict:
    """Compute absolute watt ranges for each power zone based on FTP."""
    zones = {}
    for key, zone in POWER_ZONES.items():
        min_w = round(ftp_watts * zone["min_pct"] / 100)
        max_w = round(ftp_watts * zone["max_pct"] / 100)
        zones[key] = {**zone, "min_watts": min_w, "max_watts": max_w}
    return zones


# ── TSS / IF Calculations ──────────────────────────────────────────────────

def calculate_if(avg_power: float, ftp_watts: int) -> float:
    """Intensity Factor = Normalized Power / FTP (simplified: avg / FTP)."""
    if ftp_watts <= 0:
        return 0.0
    return round(avg_power / ftp_watts, 3)


def calculate_tss(duration_min: float, avg_power: float, ftp_watts: int) -> float:
    """Training Stress Score (simplified, no NP — uses avg power).

    TSS = (duration_hr × avg_power × IF) / FTP × 100
    With IF = avg_power / FTP:
    TSS = (duration_hr × avg_power²) / FTP² × 100
    """
    if ftp_watts <= 0 or avg_power <= 0:
        return 0.0
    if_score = avg_power / ftp_watts
    tss = (duration_min / 60.0) * avg_power * if_score / ftp_watts * 100
    return round(tss, 1)


# ── Ride Logging ───────────────────────────────────────────────────────────

def log_ride(user_id: int, data: dict) -> int:
    """Save a completed ride. Returns the new ride id."""
    # Auto-calculate TSS/IF if not already provided
    avg_power = data.get("avg_power") or 0
    if_score = data.get("if_score")
    tss = data.get("tss")
    if avg_power and not if_score:
        profile = get_cycling_profile(user_id)
        ftp = profile["ftp_watts"] if profile else 200
        if_score = calculate_if(avg_power, ftp)
        tss = calculate_tss(data.get("duration_min", 60), avg_power, ftp)

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO cycling_ride_logs
               (user_id, ride_date, duration_min, avg_power, normalized_power,
                if_score, tss, elevation_m, difficulty_survey, workout_id, notes, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                data.get("ride_date", date.today().isoformat()),
                data.get("duration_min", 0),
                avg_power if avg_power else None,
                data.get("normalized_power") or None,
                if_score,
                tss,
                data.get("elevation_m") or None,
                data.get("difficulty_survey") or None,
                data.get("workout_id") or None,
                data.get("notes") or None,
                data.get("source", "manual"),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT last_insert_rowid()").fetchone()
        return row[0]
    finally:
        conn.close()


def get_ride_history(user_id: int, days: int = 90) -> list[dict]:
    """Return rides from the past N days, newest first."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM cycling_ride_logs
               WHERE user_id = ? AND ride_date >= ?
               ORDER BY ride_date DESC, created_at DESC""",
            (user_id, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── PMC — Performance Management Chart ────────────────────────────────────

def get_pmc_data(user_id: int, days: int = 90) -> list[dict]:
    """Compute CTL/ATL/TSB (Performance Management Chart) over N days.

    Uses Banister impulse-response model:
      CTL (Fitness)  = 42-day exponential weighted average of TSS
      ATL (Fatigue)  = 7-day exponential weighted average of TSS
      TSB (Form)     = yesterday's CTL − yesterday's ATL
    """
    # Fetch extra history to prime CTL (42-day lag)
    total_days = days + 42
    cutoff = (date.today() - timedelta(days=total_days)).isoformat()
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT ride_date, SUM(tss) as daily_tss
               FROM cycling_ride_logs
               WHERE user_id = ? AND ride_date >= ? AND tss IS NOT NULL
               GROUP BY ride_date""",
            (user_id, cutoff),
        ).fetchall()
    finally:
        conn.close()

    tss_by_date: dict[str, float] = {r["ride_date"]: float(r["daily_tss"]) for r in rows}

    # Walk every calendar day
    start = date.today() - timedelta(days=total_days - 1)
    today = date.today()
    ctl = 0.0
    atl = 0.0
    result = []
    current = start
    while current <= today:
        d_str = current.isoformat()
        tsb = ctl - atl  # form going INTO today (before today's training)
        daily_tss = tss_by_date.get(d_str, 0.0)
        ctl = ctl + (daily_tss - ctl) / 42.0
        atl = atl + (daily_tss - atl) / 7.0
        result.append({
            "date": d_str,
            "tss": daily_tss,
            "ctl": round(ctl, 1),
            "atl": round(atl, 1),
            "tsb": round(tsb, 1),
        })
        current += timedelta(days=1)

    # Return only the last `days` entries
    return result[-days:]


# ── Progression Levels ─────────────────────────────────────────────────────

def get_progression_levels(user_id: int) -> dict:
    """Return current progression levels. Falls back to defaults if none saved."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM cycling_progression_levels WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return {k: round(float(row[k]), 1) for k in PROGRESSION_DEFAULTS}
        return {**PROGRESSION_DEFAULTS}
    finally:
        conn.close()


def update_progression_levels(user_id: int, workout_type: str, difficulty_survey: int) -> None:
    """Advance or maintain progression level based on post-ride difficulty survey."""
    if workout_type not in PROGRESSION_DEFAULTS:
        return
    survey_info = DIFFICULTY_SURVEY_OPTIONS.get(difficulty_survey, {})
    delta = survey_info.get("progression_delta", 0.0)

    conn = get_connection()
    try:
        conn.execute(
            f"""INSERT INTO cycling_progression_levels (user_id, {workout_type}, updated_at)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(user_id) DO UPDATE SET
                  {workout_type} = MIN(10.0, MAX(1.0, {workout_type} + ?)),
                  updated_at = datetime('now')""",
            (user_id, 1.0 + delta, delta),
        )
        conn.commit()
    finally:
        conn.close()


# ── Workout Suggestion ─────────────────────────────────────────────────────

def suggest_todays_workout(user_id: int) -> dict | None:
    """Suggest a workout matching the user's current progression levels.

    Finds the energy system with the most room to grow (lowest level) and
    returns a workout within ±1 difficulty level of the current progression.
    """
    levels = get_progression_levels(user_id)
    # Prioritise energy systems with lowest levels (most need for development)
    sorted_types = sorted(levels.items(), key=lambda x: x[1])
    for energy_type, current_level in sorted_types:
        candidates = [
            w for w in WORKOUT_LIBRARY
            if w["type"] == energy_type
            and (current_level - 0.5) <= w["difficulty_level"] <= (current_level + 1.5)
        ]
        if candidates:
            return candidates[0]
    # Fallback: return any matching workout regardless of level
    for energy_type, _ in sorted_types:
        matches = [w for w in WORKOUT_LIBRARY if w["type"] == energy_type]
        if matches:
            return matches[0]
    return None


# ── Training Plan Generation ───────────────────────────────────────────────

def generate_training_plan(
    user_id: int,
    phase: str,
    weeks: int,
    days_per_week: int,
) -> dict:
    """Generate a structured training plan with weekly workout assignments."""
    phase_data = TRAINING_PHASES[phase]
    days_per_week = max(3, min(6, days_per_week))
    weekly_template = phase_data["weekly_structure"].get(days_per_week, [])
    deload_template = phase_data["deload_structure"].get(days_per_week, [])

    start = date.today()
    # Start on next Monday
    days_until_monday = (7 - start.weekday()) % 7
    if days_until_monday == 0:
        plan_start = start
    else:
        plan_start = start + timedelta(days=days_until_monday)

    plan_weeks = []
    # Map days_per_week to actual weekday indices (Mon=0, distribute evenly)
    # For simplicity: 3 days → Mon/Wed/Fri, 4 → Mon/Tue/Thu/Sat, etc.
    day_slots = {
        3: [0, 2, 4],       # Mon, Wed, Fri
        4: [0, 1, 3, 5],    # Mon, Tue, Thu, Sat
        5: [0, 1, 2, 4, 5], # Mon, Tue, Wed, Fri, Sat
        6: [0, 1, 2, 3, 4, 5],  # Mon–Sat
    }.get(days_per_week, [0, 2, 4])

    total_tss = 0
    for week_num in range(1, weeks + 1):
        is_deload = (week_num % 4 == 0) or (week_num == weeks and phase == "specialty")
        template = deload_template if is_deload else weekly_template
        week_start = plan_start + timedelta(weeks=week_num - 1)

        week_workouts = []
        for day_idx, weekday_offset in enumerate(day_slots):
            if day_idx >= len(template):
                break
            workout_id = template[day_idx]
            workout = WORKOUT_LIBRARY_BY_ID.get(workout_id)
            workout_date = week_start + timedelta(days=weekday_offset)
            tss_est = workout["tss_estimate"] if workout else 0
            total_tss += tss_est
            week_workouts.append({
                "plan_workout_id": f"w{week_num}d{day_idx + 1}",
                "date": workout_date.isoformat(),
                "workout_id": workout_id,
                "status": "scheduled",
                "tss_estimate": tss_est,
            })

        plan_weeks.append({
            "week": week_num,
            "is_deload": is_deload,
            "label": "Deload" if is_deload else f"Week {week_num}",
            "workouts": week_workouts,
            "week_start": week_start.isoformat(),
        })

    avg_weekly_tss = round(total_tss / weeks) if weeks else 0
    return {
        "phase": phase,
        "phase_label": phase_data["label"],
        "start_date": plan_start.isoformat(),
        "weeks": weeks,
        "days_per_week": days_per_week,
        "avg_weekly_tss": avg_weekly_tss,
        "plan_weeks": plan_weeks,
    }


def save_training_plan(user_id: int, plan: dict) -> int:
    """Save a training plan, deactivating any existing active plan first."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE cycling_plan SET active = 0 WHERE user_id = ?", (user_id,)
        )
        conn.execute(
            """INSERT INTO cycling_plan
               (user_id, phase, start_date, weeks, days_per_week, tss_per_week,
                program_json, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                user_id,
                plan["phase"],
                plan["start_date"],
                plan["weeks"],
                plan["days_per_week"],
                plan.get("avg_weekly_tss"),
                json.dumps(plan),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT last_insert_rowid()").fetchone()
        return row[0]
    finally:
        conn.close()


def get_active_plan(user_id: int) -> dict | None:
    """Return the user's current active training plan or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT id, program_json, created_at FROM cycling_plan
               WHERE user_id = ? AND active = 1
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        if row:
            plan = json.loads(row["program_json"])
            plan["_db_id"] = row["id"]
            plan["_created_at"] = row["created_at"]
            return plan
        return None
    finally:
        conn.close()


def get_this_week_workouts(user_id: int) -> list[dict]:
    """Return the scheduled workouts for the current week from the active plan."""
    plan = get_active_plan(user_id)
    if not plan:
        return []
    today = date.today()
    start = date.fromisoformat(plan["start_date"])
    week_num = (today - start).days // 7  # 0-indexed
    for week in plan.get("plan_weeks", []):
        if week["week"] == week_num + 1:
            return week["workouts"]
    return []


def complete_workout(user_id: int, plan_workout_id: str, difficulty_survey: int) -> None:
    """Mark a plan workout as completed and update progression levels."""
    plan = get_active_plan(user_id)
    if not plan:
        return
    workout_type = None
    for week in plan.get("plan_weeks", []):
        for w in week.get("workouts", []):
            if w["plan_workout_id"] == plan_workout_id:
                w["status"] = "completed"
                workout_type = WORKOUT_LIBRARY_BY_ID.get(w["workout_id"], {}).get("type")
                break

    conn = get_connection()
    try:
        conn.execute(
            "UPDATE cycling_plan SET program_json = ? WHERE id = ?",
            (json.dumps(plan), plan["_db_id"]),
        )
        conn.commit()
    finally:
        conn.close()

    if workout_type:
        update_progression_levels(user_id, workout_type, difficulty_survey)


def reschedule_workout(user_id: int, plan_workout_id: str, new_date: str) -> None:
    """Move a scheduled workout to a new date."""
    plan = get_active_plan(user_id)
    if not plan:
        return
    for week in plan.get("plan_weeks", []):
        for w in week.get("workouts", []):
            if w["plan_workout_id"] == plan_workout_id:
                w["date"] = new_date
                w["status"] = "rescheduled"
                break

    conn = get_connection()
    try:
        conn.execute(
            "UPDATE cycling_plan SET program_json = ? WHERE id = ?",
            (json.dumps(plan), plan["_db_id"]),
        )
        conn.commit()
    finally:
        conn.close()


# ── Weekly TSS ─────────────────────────────────────────────────────────────

def calculate_weekly_tss(user_id: int, week_start: str) -> float:
    """Sum TSS for all rides in the 7-day window starting from week_start."""
    week_end = (date.fromisoformat(week_start) + timedelta(days=7)).isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(tss), 0) as total
               FROM cycling_ride_logs
               WHERE user_id = ? AND ride_date >= ? AND ride_date < ?""",
            (user_id, week_start, week_end),
        ).fetchone()
        return float(row["total"]) if row else 0.0
    finally:
        conn.close()


# ── Adaptive Suggestions ───────────────────────────────────────────────────

def get_adaptive_suggestions(user_id: int) -> list[dict]:
    """Generate adaptive training recommendations based on recent activity.

    Rules:
    1. Last ride survey <= 2 (easy) → suggest upgrading to harder variant
    2. Last ride survey == 5 (all out) → suggest easier or recovery next
    3. Weekly TSS > phase_max * 1.1 → suggest rest day
    4. Overdue scheduled workouts → suggest rescheduling
    """
    suggestions = []
    today_str = date.today().isoformat()

    # Last ride difficulty
    conn = get_connection()
    try:
        last_row = conn.execute(
            """SELECT difficulty_survey, workout_id FROM cycling_ride_logs
               WHERE user_id = ? AND difficulty_survey IS NOT NULL
               ORDER BY ride_date DESC, created_at DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if last_row:
        survey = last_row["difficulty_survey"]
        last_workout_type = (WORKOUT_LIBRARY_BY_ID.get(last_row["workout_id"] or "", {}) or {}).get("type")
        if survey and survey <= 2 and last_workout_type:
            suggestions.append({
                "type": "upgrade",
                "message": f"Your last {last_workout_type} workout felt {DIFFICULTY_SURVEY_OPTIONS[survey]['label'].lower()}. Consider stepping up to a harder variant next session.",
                "workout_id": None,
            })
        elif survey and survey == 5:
            suggestions.append({
                "type": "downgrade",
                "message": "Your last ride was an all-out effort. Prioritise rest or an easy recovery spin before your next hard session.",
                "workout_id": None,
            })

    # Weekly TSS vs plan target
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    weekly_tss = calculate_weekly_tss(user_id, week_start)
    plan = get_active_plan(user_id)
    if plan and weekly_tss > (plan.get("avg_weekly_tss", 400) or 400) * 1.1:
        suggestions.append({
            "type": "recovery_day",
            "message": f"You've accumulated {weekly_tss:.0f} TSS this week — above your target of {plan.get('avg_weekly_tss', 400)} TSS. Consider a recovery spin or rest day.",
            "workout_id": None,
        })

    # Overdue workouts
    if plan:
        for week in plan.get("plan_weeks", []):
            for w in week.get("workouts", []):
                if w.get("status") == "scheduled" and w.get("date", "") < today_str:
                    workout = WORKOUT_LIBRARY_BY_ID.get(w["workout_id"], {})
                    suggestions.append({
                        "type": "reschedule",
                        "message": f"Missed workout: {workout.get('name', w['workout_id'])} scheduled for {w['date']}. Reschedule or mark as skipped.",
                        "workout_id": w["plan_workout_id"],
                    })

    return suggestions[:4]  # Cap at 4 suggestions


# ── W/kg Utilities ─────────────────────────────────────────────────────────

def get_wkg_category(ftp_watts: int, weight_kg: float) -> str:
    """Return racer category label for a given W/kg ratio."""
    from config.cycling_data import WATT_KG_CATEGORIES
    if weight_kg <= 0:
        return "Unknown"
    wkg = ftp_watts / weight_kg
    for cat in WATT_KG_CATEGORIES:
        if cat["min_wkg"] <= wkg < cat["max_wkg"]:
            return cat["label"]
    return WATT_KG_CATEGORIES[-1]["label"]


# ── AI Coach Context ────────────────────────────────────────────────────────

def get_cycling_coach_context(user_id: int) -> str:
    """Assemble all cycling training data into a structured text block for the AI coach.

    Returns a multi-line string covering FTP, PMC fitness metrics, progression levels,
    recent rides, and the active training plan.
    """
    profile = get_cycling_profile(user_id)
    if not profile:
        return (
            "No cycling profile found. The athlete has not set their FTP yet. "
            "Ask them to go to Settings in the Cycling Training page and enter their FTP."
        )

    ftp = profile["ftp_watts"]
    weight = profile.get("weight_kg") or 0.0
    wkg = round(ftp / weight, 2) if weight > 0 else None
    category = get_wkg_category(ftp, weight) if weight > 0 else "Unknown"

    # Days since FTP test
    tested_date = profile.get("ftp_tested_date") or "unknown"
    days_since_test: str = "unknown"
    if tested_date and tested_date != "unknown":
        try:
            days_since_test = str((date.today() - date.fromisoformat(tested_date)).days)
        except Exception:
            pass

    # PMC — last 90 days; extract latest entry for CTL/ATL/TSB
    pmc = get_pmc_data(user_id, days=90)
    ctl = atl = tsb = 0.0
    ctl_7d_ago = 0.0
    if pmc:
        last = pmc[-1]
        ctl, atl, tsb = last["ctl"], last["atl"], last["tsb"]
        if len(pmc) >= 8:
            ctl_7d_ago = pmc[-8]["ctl"]
    ctl_trend = round(ctl - ctl_7d_ago, 1)

    if tsb >= 10:
        tsb_label = "Fresh — consider a hard day or race"
    elif tsb >= 0:
        tsb_label = "Neutral — good training zone"
    elif tsb >= -20:
        tsb_label = "Productive fatigue — training adaptation zone"
    elif tsb >= -30:
        tsb_label = "Tired — reduce intensity or volume"
    else:
        tsb_label = "Very Tired — rest day strongly recommended"

    # Progression levels
    levels = get_progression_levels(user_id)
    prog_parts = [f"{k.replace('_', ' ').title()}: {v}" for k, v in levels.items()]
    prog_str = " | ".join(prog_parts)

    # Recent rides (last 28 days, cap at 8)
    rides = get_ride_history(user_id, days=28)
    ride_lines: list[str] = []
    for r in rides[:8]:
        workout_name = ""
        if r.get("workout_id"):
            w = WORKOUT_LIBRARY_BY_ID.get(r["workout_id"], {})
            if w:
                workout_name = f" | {w['name']}"
        survey_str = ""
        if r.get("difficulty_survey"):
            survey_str = f" | Survey: {r['difficulty_survey']}/5"
        ride_lines.append(
            f"{r['ride_date']} | {r['duration_min']}min"
            f" | IF={r.get('if_score', 0):.2f}"
            f" | TSS={r.get('tss', 0):.0f}"
            f"{workout_name}{survey_str}"
        )

    # Active training plan
    plan = get_active_plan(user_id)
    plan_lines: list[str] = ["No active training plan."]
    if plan:
        phase_data = TRAINING_PHASES.get(plan["phase"], {})
        today = date.today()
        try:
            start = date.fromisoformat(plan["start_date"])
            current_week = min((today - start).days // 7 + 1, plan["weeks"])
        except Exception:
            current_week = 1
        week_start_str = (today - timedelta(days=today.weekday())).isoformat()
        actual_tss = calculate_weekly_tss(user_id, week_start_str)
        tss_range = phase_data.get("tss_range", (0, 0))
        plan_lines = [
            f"{phase_data.get('label', plan['phase'])}, Week {current_week}/{plan['weeks']},"
            f" {plan.get('days_per_week', 4)} days/week",
            f"Target TSS: {tss_range[0]}–{tss_range[1]}/wk",
            f"This week actual TSS: {actual_tss:.0f}",
        ]

    lines = [
        "=== CYCLING TRAINING PROFILE ===",
        f"FTP: {ftp}W | Weight: {weight}kg | W/kg: {wkg if wkg else 'N/A'} | Category: {category}",
        f"Athlete Type: {profile.get('athlete_type', 'All-Around')}"
        f" | FTP Last Tested: {tested_date} ({days_since_test} days ago)",
        "",
        "=== CURRENT FITNESS (PMC — Banister Impulse-Response Model) ===",
        f"CTL (Fitness):  {ctl:.1f} TSS (7d trend: {ctl_trend:+.1f})",
        f"ATL (Fatigue):  {atl:.1f} TSS",
        f"TSB (Form):     {tsb:+.1f} — {tsb_label}",
        "",
        "=== PROGRESSION LEVELS (scale 1.0–10.0) ===",
        prog_str,
        "",
        "=== RECENT RIDES (last 28 days) ===",
    ] + (ride_lines if ride_lines else ["No rides logged yet."]) + [
        "",
        "=== ACTIVE TRAINING PLAN ===",
    ] + plan_lines

    return "\n".join(lines)
