"""Service for exercise/workout logging, weekly summaries, and scoring.

Exercise Score (0-100) based on ACLM / WHO 2020 guidelines (PMID: 33239350):
- Aerobic volume (50 pts): moderate_min + 2*vigorous_min vs 150 target
- Strength frequency (25 pts): strength days vs 2/week target
- Consistency (15 pts): session count this week
- Variety (10 pts): different exercise types this week
"""

from datetime import date, timedelta
from db.database import get_connection
from config.exercise_data import EXERCISE_TYPES, WEEKLY_TARGETS


# ---------------------------------------------------------------------------
#  CRUD
# ---------------------------------------------------------------------------

def log_exercise(user_id, exercise_date, exercise_type, duration_min,
                 intensity, distance_km=None, calories=None,
                 avg_hr=None, max_hr=None, rpe=None, notes=None,
                 source="manual", external_id=None):
    """Log an exercise session. Returns the inserted row id."""
    type_info = EXERCISE_TYPES.get(exercise_type, EXERCISE_TYPES["other"])
    category = type_info["category"]

    # For external sources, generate a unique external_id if not provided
    if source == "manual" and external_id is None:
        external_id = f"manual_{exercise_date}_{exercise_type}_{duration_min}"

    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO exercise_logs
               (user_id, exercise_date, exercise_type, category, duration_min,
                intensity, distance_km, calories, avg_hr, max_hr, rpe,
                notes, source, external_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, exercise_date, external_id) DO UPDATE SET
                 duration_min = excluded.duration_min,
                 intensity = excluded.intensity,
                 distance_km = excluded.distance_km,
                 calories = excluded.calories,
                 avg_hr = excluded.avg_hr,
                 max_hr = excluded.max_hr,
                 rpe = excluded.rpe,
                 notes = excluded.notes""",
            (user_id, exercise_date, exercise_type, category, duration_min,
             intensity, distance_km, calories, avg_hr, max_hr, rpe,
             notes, source, external_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_exercise_history(user_id, days=30):
    """Get exercise logs for the last N days, newest first."""
    conn = get_connection()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT * FROM exercise_logs
           WHERE user_id = ? AND exercise_date >= ?
           ORDER BY exercise_date DESC, created_at DESC""",
        (user_id, cutoff),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_exercises_by_date(user_id, exercise_date):
    """Get all exercises for a specific date."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM exercise_logs
           WHERE user_id = ? AND exercise_date = ?
           ORDER BY created_at""",
        (user_id, exercise_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_exercise(user_id, exercise_id):
    """Delete an exercise log entry."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM exercise_logs WHERE id = ? AND user_id = ?",
            (exercise_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
#  Weekly Summary
# ---------------------------------------------------------------------------

def get_current_week_start():
    """Get the Monday of the current week as ISO string."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def get_weekly_stats(user_id, week_start=None):
    """Compute weekly exercise stats from exercise_logs.

    Returns dict with total_min, cardio_min, strength_min, flexibility_min,
    moderate_min, vigorous_min, session_count, strength_days, types_used,
    aerobic_equivalent_min.
    """
    if week_start is None:
        week_start = get_current_week_start()

    week_end = (date.fromisoformat(week_start) + timedelta(days=7)).isoformat()

    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM exercise_logs
           WHERE user_id = ? AND exercise_date >= ? AND exercise_date < ?
           ORDER BY exercise_date""",
        (user_id, week_start, week_end),
    ).fetchall()
    conn.close()

    stats = {
        "week_start": week_start,
        "total_min": 0,
        "cardio_min": 0,
        "strength_min": 0,
        "flexibility_min": 0,
        "moderate_min": 0,
        "vigorous_min": 0,
        "light_min": 0,
        "session_count": len(rows),
        "strength_days": 0,
        "types_used": set(),
        "aerobic_equivalent_min": 0,
    }

    strength_dates = set()
    for r in rows:
        r = dict(r)
        dur = r["duration_min"]
        stats["total_min"] += dur
        stats["types_used"].add(r["exercise_type"])

        cat = r["category"]
        if cat == "cardio":
            stats["cardio_min"] += dur
        elif cat == "strength":
            stats["strength_min"] += dur
            strength_dates.add(r["exercise_date"])
        elif cat == "flexibility":
            stats["flexibility_min"] += dur
        else:  # mixed
            stats["cardio_min"] += dur // 2
            stats["strength_min"] += dur // 2

        intensity = r["intensity"]
        if intensity == "moderate":
            stats["moderate_min"] += dur
        elif intensity == "vigorous":
            stats["vigorous_min"] += dur
        else:
            stats["light_min"] += dur

    stats["strength_days"] = len(strength_dates)
    # Aerobic equivalent: moderate + 2*vigorous (WHO guideline)
    stats["aerobic_equivalent_min"] = stats["moderate_min"] + (stats["vigorous_min"] * 2)
    stats["types_used"] = list(stats["types_used"])

    return stats


def update_weekly_summary(user_id, week_start=None):
    """Compute and save weekly summary to exercise_weekly_summary table."""
    stats = get_weekly_stats(user_id, week_start)
    score = _calculate_score_from_stats(stats)

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO exercise_weekly_summary
               (user_id, week_start, total_min, cardio_min, strength_min,
                flexibility_min, moderate_min, vigorous_min, session_count,
                exercise_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, week_start) DO UPDATE SET
                 total_min = excluded.total_min,
                 cardio_min = excluded.cardio_min,
                 strength_min = excluded.strength_min,
                 flexibility_min = excluded.flexibility_min,
                 moderate_min = excluded.moderate_min,
                 vigorous_min = excluded.vigorous_min,
                 session_count = excluded.session_count,
                 exercise_score = excluded.exercise_score""",
            (user_id, stats["week_start"], stats["total_min"],
             stats["cardio_min"], stats["strength_min"],
             stats["flexibility_min"], stats["moderate_min"],
             stats["vigorous_min"], stats["session_count"], score),
        )
        conn.commit()
    finally:
        conn.close()

    return {**stats, "exercise_score": score}


# ---------------------------------------------------------------------------
#  Scoring (0-100)
# ---------------------------------------------------------------------------

def _calculate_score_from_stats(stats):
    """Calculate exercise score (0-100) from weekly stats.

    Components:
    - Aerobic volume (50 pts): aerobic_equivalent_min / 150 target, capped at 1.0
    - Strength frequency (25 pts): strength_days / 2 target, capped at 1.0
    - Consistency (15 pts): session_count / 5 ideal sessions, capped at 1.0
    - Variety (10 pts): len(types_used) / 3 types, capped at 1.0
    """
    target_aerobic = WEEKLY_TARGETS["aerobic_moderate_min"]
    target_strength = WEEKLY_TARGETS["strength_days"]

    aerobic_ratio = min(1.0, stats["aerobic_equivalent_min"] / target_aerobic) if target_aerobic > 0 else 0
    strength_ratio = min(1.0, stats["strength_days"] / target_strength) if target_strength > 0 else 0
    consistency_ratio = min(1.0, stats["session_count"] / 5)
    types_list = stats["types_used"] if isinstance(stats["types_used"], list) else list(stats["types_used"])
    variety_ratio = min(1.0, len(types_list) / 3)

    score = round(
        aerobic_ratio * 50
        + strength_ratio * 25
        + consistency_ratio * 15
        + variety_ratio * 10
    )
    return max(0, min(100, score))


def calculate_exercise_score(user_id):
    """Calculate current week's exercise score (0-100)."""
    stats = get_weekly_stats(user_id)
    if stats["session_count"] == 0:
        return None
    return _calculate_score_from_stats(stats)


# ---------------------------------------------------------------------------
#  Trends
# ---------------------------------------------------------------------------

def get_weekly_history(user_id, weeks=12):
    """Get weekly summaries for the last N weeks."""
    conn = get_connection()
    cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()
    rows = conn.execute(
        """SELECT * FROM exercise_weekly_summary
           WHERE user_id = ? AND week_start >= ?
           ORDER BY week_start""",
        (user_id, cutoff),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_exercise_type_distribution(user_id, days=30):
    """Get exercise type distribution for the last N days."""
    conn = get_connection()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT exercise_type, SUM(duration_min) as total_min, COUNT(*) as count
           FROM exercise_logs
           WHERE user_id = ? AND exercise_date >= ?
           GROUP BY exercise_type
           ORDER BY total_min DESC""",
        (user_id, cutoff),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
#  Coach Integration
# ---------------------------------------------------------------------------

def get_exercise_summary_for_coach(user_id):
    """Build exercise context string for the AI coach."""
    stats = get_weekly_stats(user_id)
    if stats["session_count"] == 0:
        return None

    score = _calculate_score_from_stats(stats)
    target = WEEKLY_TARGETS["aerobic_moderate_min"]
    aeq = stats["aerobic_equivalent_min"]
    pct = round(aeq / target * 100) if target > 0 else 0

    parts = [
        f"Weekly exercise: {aeq}/{target} min aerobic equivalent ({pct}%)",
        f"Strength: {stats['strength_days']}/{WEEKLY_TARGETS['strength_days']} days",
        f"Sessions: {stats['session_count']} this week",
        f"Exercise score: {score}/100",
    ]
    if stats["types_used"]:
        type_labels = [EXERCISE_TYPES.get(t, {}).get("label", t) for t in stats["types_used"]]
        parts.append(f"Activities: {', '.join(type_labels)}")

    # Running stats (if user runs)
    running_ctx = _get_running_stats_for_coach(user_id)
    if running_ctx:
        parts.append(running_ctx)

    # Training load balance (acute vs chronic)
    load_ctx = _get_training_load_balance(user_id)
    if load_ctx:
        parts.append(load_ctx)

    # Recovery zone
    try:
        from services.recovery_service import calculate_recovery_score
        recovery = calculate_recovery_score(user_id)
        if recovery:
            zone = recovery["zone"]
            parts.append(
                f"Recovery: {recovery['score']}/100 ({zone['label']} zone)"
            )
    except Exception:
        pass

    # Recent strength PRs
    try:
        from services.exercise_prescription_service import get_recent_prs
        recent_prs = get_recent_prs(user_id, days=14)
        if recent_prs:
            pr_strs = [
                f"{pr['exercise_name']} {pr['estimated_1rm']:.0f}kg e1RM"
                for pr in recent_prs[:3]
            ]
            parts.append(f"Recent PRs: {', '.join(pr_strs)}")
    except Exception:
        pass

    # Active training programs (PPL or cycling)
    try:
        from services.exercise_prescription_service import get_saved_program
        ppl = get_saved_program(user_id)
        if ppl:
            meso = ppl.get("mesocycle", {}).get("label", "PPL")
            parts.append(f"Active PPL program: {meso}")
    except Exception:
        pass

    try:
        from services.cycling_service import get_active_plan
        plan = get_active_plan(user_id)
        if plan:
            parts.append(
                f"Active cycling plan: {plan.get('phase_label', plan.get('phase', ''))}"
                f" (week {plan.get('weeks', '?')})"
            )
    except Exception:
        pass

    return " | ".join(parts)


def _get_running_stats_for_coach(user_id):
    """Get running-specific stats if the user has logged runs recently."""
    conn = get_connection()
    cutoff_7d = (date.today() - timedelta(days=7)).isoformat()
    cutoff_28d = (date.today() - timedelta(days=28)).isoformat()

    # Weekly mileage
    week_row = conn.execute(
        """SELECT COALESCE(SUM(distance_km), 0) as km, COUNT(*) as runs,
                  COALESCE(SUM(duration_min), 0) as mins
           FROM exercise_logs
           WHERE user_id = ? AND exercise_type = 'run' AND exercise_date >= ?""",
        (user_id, cutoff_7d),
    ).fetchone()

    # 4-week mileage for context
    month_row = conn.execute(
        """SELECT COALESCE(SUM(distance_km), 0) as km,
                  COALESCE(SUM(duration_min), 0) as mins
           FROM exercise_logs
           WHERE user_id = ? AND exercise_type = 'run' AND exercise_date >= ?""",
        (user_id, cutoff_28d),
    ).fetchone()
    conn.close()

    if not week_row or (week_row["runs"] == 0 and month_row["km"] == 0):
        return None

    parts = []
    weekly_km = round(week_row["km"], 1)
    if weekly_km > 0:
        parts.append(f"Running this week: {weekly_km}km in {week_row['runs']} runs")
        # Average pace (min/km)
        if week_row["mins"] > 0 and weekly_km > 0:
            avg_pace = week_row["mins"] / weekly_km
            pace_min = int(avg_pace)
            pace_sec = int((avg_pace - pace_min) * 60)
            parts.append(f"avg pace {pace_min}:{pace_sec:02d}/km")

    monthly_km = round(month_row["km"], 1)
    if monthly_km > 0:
        avg_weekly = round(monthly_km / 4, 1)
        parts.append(f"4-wk avg: {avg_weekly}km/wk")

    return ", ".join(parts) if parts else None


def _get_training_load_balance(user_id):
    """Compute acute:chronic training load ratio (ACWR).

    Acute = last 7 days, Chronic = last 28 days average per week.
    ACWR between 0.8-1.3 is the "sweet spot" (Gabbett, 2016).
    """
    conn = get_connection()
    cutoff_7d = (date.today() - timedelta(days=7)).isoformat()
    cutoff_28d = (date.today() - timedelta(days=28)).isoformat()

    intensity_multipliers = {"light": 0.5, "moderate": 1.0, "vigorous": 2.0}

    rows_7d = conn.execute(
        """SELECT duration_min, intensity FROM exercise_logs
           WHERE user_id = ? AND exercise_date >= ?""",
        (user_id, cutoff_7d),
    ).fetchall()

    rows_28d = conn.execute(
        """SELECT duration_min, intensity FROM exercise_logs
           WHERE user_id = ? AND exercise_date >= ?""",
        (user_id, cutoff_28d),
    ).fetchall()
    conn.close()

    acute_load = sum(
        r["duration_min"] * intensity_multipliers.get(r["intensity"], 1.0)
        for r in rows_7d
    )
    chronic_load = sum(
        r["duration_min"] * intensity_multipliers.get(r["intensity"], 1.0)
        for r in rows_28d
    )

    if chronic_load == 0:
        return None

    chronic_weekly = chronic_load / 4.0
    acwr = round(acute_load / chronic_weekly, 2) if chronic_weekly > 0 else 0

    if acwr < 0.8:
        label = "underloading"
    elif acwr <= 1.3:
        label = "sweet spot"
    else:
        label = "spike risk"

    return (
        f"Training load: acute {acute_load:.0f} / chronic avg {chronic_weekly:.0f} per wk"
        f" (ACWR {acwr:.2f} — {label})"
    )


def get_comprehensive_exercise_context(user_id):
    """Build comprehensive exercise context for AI coach across all modalities.

    Gathers context from exercise_service (general exercise stats + running),
    cycling_service (if cycling profile exists), and strength PRs.
    """
    sections = []

    # General exercise summary
    summary = get_exercise_summary_for_coach(user_id)
    if summary:
        sections.append(f"=== EXERCISE OVERVIEW ===\n{summary}")

    # Cycling context (if available)
    try:
        from services.cycling_service import get_cycling_coach_context, get_cycling_profile
        profile = get_cycling_profile(user_id)
        if profile:
            cycling_ctx = get_cycling_coach_context(user_id)
            if cycling_ctx:
                sections.append(cycling_ctx)
    except Exception:
        pass

    # Strength training context
    try:
        from services.exercise_prescription_service import get_strength_summary_for_coach
        strength_ctx = get_strength_summary_for_coach(user_id)
        if strength_ctx and "No strength training data" not in strength_ctx:
            sections.append(f"=== STRENGTH TRAINING ===\n{strength_ctx}")
    except Exception:
        pass

    # Recovery context
    try:
        from services.recovery_service import calculate_recovery_score
        recovery = calculate_recovery_score(user_id)
        if recovery:
            zone = recovery["zone"]
            comp_parts = []
            for key, comp in recovery["components"].items():
                comp_parts.append(f"{comp['label']}: {comp['score']}/100")
            sections.append(
                f"=== RECOVERY STATUS ===\n"
                f"Score: {recovery['score']}/100 ({zone['label']} zone)\n"
                f"Components: {' | '.join(comp_parts)}\n"
                f"Recommendation: {zone['recommendation']}"
            )
    except Exception:
        pass

    if not sections:
        return "No exercise data available for this user."

    return "\n\n".join(sections)
