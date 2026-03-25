"""Running training service — VDOT pace zones, race prediction, training load, plan generation.

Implements the Jack Daniels VDOT model for pace zones, the Riegel formula for
race time prediction, and the session-RPE training load model.

References:
  - Daniels, J. (2022) "Daniels' Running Formula", 4th ed. Human Kinetics.
  - Riegel, P.S. (1981) "Athletic Records and Human Endurance", American Scientist.
  - Foster, C. et al. (2001) "A new approach to monitoring exercise training",
    J Strength Cond Res 15(1):109-115. PMID: 11219501.
  - Seiler, S. (2010) "What is best practice for training intensity and duration
    distribution in endurance athletes?", Int J Sports Physiol Perform 5(3):276-291.
    PMID: 20930776.
  - Gabbett, T.J. (2016) "The training-injury prevention paradox",
    Br J Sports Med 50(5):273-280. PMID: 26758673. (ACWR methodology)
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from db.database import get_connection
from config.running_data import (
    VDOT_TABLE,
    RACE_DISTANCES,
    PACE_ZONE_DEFINITIONS,
    TRAINING_PLAN_TEMPLATES,
)


# ── VDOT Estimation ──────────────────────────────────────────────────────

def estimate_vdot(distance_km: float, time_minutes: float) -> float:
    """Estimate VDOT from a race result or time trial.

    Uses the Daniels/Gilbert oxygen-cost model (simplified regression).
    The formula relates velocity (m/min) and duration to %VO2max, then
    back-calculates the VDOT that matches the performance.

    Args:
        distance_km: Race distance in kilometres.
        time_minutes: Finish time in decimal minutes.

    Returns:
        Estimated VDOT value (typically 30-85 for recreational to elite).
    """
    if distance_km <= 0 or time_minutes <= 0:
        return 0.0

    velocity = distance_km * 1000.0 / time_minutes  # metres per minute

    # Oxygen cost of running (ml O2/kg/min) — Daniels/Gilbert polynomial
    # VO2 = -4.60 + 0.182258*v + 0.000104*v^2
    vo2 = -4.60 + 0.182258 * velocity + 0.000104 * velocity ** 2

    # Percent of VO2max sustained over the duration
    # %VO2max = 0.8 + 0.1894393*e^(-0.012778*t) + 0.2989558*e^(-0.1932605*t)
    pct_max = (
        0.8
        + 0.1894393 * math.exp(-0.012778 * time_minutes)
        + 0.2989558 * math.exp(-0.1932605 * time_minutes)
    )

    if pct_max <= 0:
        return 0.0

    vdot = vo2 / pct_max
    return round(vdot, 1)


# ── Pace Zones ────────────────────────────────────────────────────────────

def _vdot_to_velocity(vdot: float) -> float:
    """Convert VDOT to approximate race-pace velocity in m/min.

    Inverts the Daniels oxygen-cost equation for a ~12-minute effort
    (%VO2max ≈ 1.0 at VDOT pace) to get the reference velocity.
    """
    # At VDOT pace, VO2 ≈ VDOT (by definition, %max ≈ 1.0 for short race)
    # Solve: VDOT = -4.60 + 0.182258*v + 0.000104*v^2  for v
    # Quadratic: 0.000104*v^2 + 0.182258*v + (-4.60 - VDOT) = 0
    a = 0.000104
    b = 0.182258
    c = -4.60 - vdot
    discriminant = b ** 2 - 4 * a * c
    if discriminant < 0:
        return 0.0
    return (-b + math.sqrt(discriminant)) / (2 * a)


def _velocity_to_pace(velocity_m_per_min: float) -> float:
    """Convert velocity (m/min) to pace (min/km)."""
    if velocity_m_per_min <= 0:
        return 0.0
    return 1000.0 / velocity_m_per_min


def _format_pace(min_per_km: float) -> str:
    """Format decimal min/km to 'M:SS' string."""
    if min_per_km <= 0:
        return "—"
    minutes = int(min_per_km)
    seconds = int(round((min_per_km - minutes) * 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d}"


def get_pace_zones(vdot: float) -> dict:
    """Compute training pace zones from a VDOT value.

    Returns a dict keyed by zone id (z1-z5) with:
        name, short, color, description, min_pace, max_pace (min/km as float),
        min_pace_fmt, max_pace_fmt (M:SS strings).

    The zones are derived from the VDOT reference velocity scaled by each
    zone's %VDOT range as defined in PACE_ZONE_DEFINITIONS.
    """
    ref_velocity = _vdot_to_velocity(vdot)  # m/min at ~VDOT pace
    if ref_velocity <= 0:
        return {}

    zones = {}
    for key, zdef in PACE_ZONE_DEFINITIONS.items():
        pct_lo, pct_hi = zdef["vdot_pct_range"]
        # Lower %VDOT → slower velocity → higher min/km (slower pace)
        # Higher %VDOT → faster velocity → lower min/km (faster pace)
        slow_velocity = ref_velocity * pct_lo
        fast_velocity = ref_velocity * pct_hi
        slow_pace = _velocity_to_pace(slow_velocity)
        fast_pace = _velocity_to_pace(fast_velocity)

        zones[key] = {
            "name": zdef["name"],
            "short": zdef["short"],
            "color": zdef["color"],
            "description": zdef["description"],
            "min_pace": round(fast_pace, 2),   # faster end (lower number)
            "max_pace": round(slow_pace, 2),   # slower end (higher number)
            "min_pace_fmt": _format_pace(fast_pace),
            "max_pace_fmt": _format_pace(slow_pace),
        }

    return zones


def get_pace_zones_from_table(vdot: float) -> dict | None:
    """Look up training paces from the VDOT_TABLE for the nearest integer VDOT.

    Returns None if the VDOT is outside the table range (30-70).
    """
    vdot_int = round(vdot)
    # Snap to nearest even number in the table
    if vdot_int % 2 != 0:
        lower = vdot_int - 1
        upper = vdot_int + 1
        vdot_int = lower if lower in VDOT_TABLE else upper
    if vdot_int not in VDOT_TABLE:
        return None
    row = VDOT_TABLE[vdot_int]
    return {
        "vdot": vdot_int,
        "easy_pace": row["easy_pace"],
        "easy_pace_fmt": _format_pace(row["easy_pace"]),
        "tempo_pace": row["tempo_pace"],
        "tempo_pace_fmt": _format_pace(row["tempo_pace"]),
        "interval_pace": row["interval_pace"],
        "interval_pace_fmt": _format_pace(row["interval_pace"]),
        "rep_pace": row["rep_pace"],
        "rep_pace_fmt": _format_pace(row["rep_pace"]),
        "marathon_pace": row["marathon_pace"],
        "marathon_pace_fmt": _format_pace(row["marathon_pace"]),
    }


# ── Race Predictor (Riegel Formula) ──────────────────────────────────────

def predict_race_times(distance_km: float, time_minutes: float) -> dict:
    """Predict race times using the Riegel formula.

    T2 = T1 * (D2 / D1) ^ 1.06

    Args:
        distance_km: Known race distance in km.
        time_minutes: Known finish time in decimal minutes.

    Returns:
        Dict keyed by race name (5k, 10k, half_marathon, marathon) with:
            distance_km, predicted_time_min, predicted_time_fmt (H:MM:SS or M:SS),
            predicted_pace (min/km), predicted_pace_fmt.
    """
    if distance_km <= 0 or time_minutes <= 0:
        return {}

    predictions = {}
    for race_key, race_info in RACE_DISTANCES.items():
        target_km = race_info["km"]
        predicted_min = time_minutes * (target_km / distance_km) ** 1.06

        pace = predicted_min / target_km

        # Format finish time
        total_seconds = int(round(predicted_min * 60))
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours > 0:
            time_fmt = f"{hours}:{mins:02d}:{secs:02d}"
        else:
            time_fmt = f"{mins}:{secs:02d}"

        predictions[race_key] = {
            "label": race_info["label"],
            "distance_km": target_km,
            "predicted_time_min": round(predicted_min, 2),
            "predicted_time_fmt": time_fmt,
            "predicted_pace": round(pace, 2),
            "predicted_pace_fmt": _format_pace(pace),
        }

    return predictions


# ── Running Log Analytics ─────────────────────────────────────────────────

def get_running_history(user_id: int, days: int = 90) -> list[dict]:
    """Return running-only exercise logs for the last N days, newest first.

    Filters exercise_logs by exercise_type = 'run'.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM exercise_logs
               WHERE user_id = ? AND exercise_type = 'run' AND exercise_date >= ?
               ORDER BY exercise_date DESC, created_at DESC""",
            (user_id, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_running_stats(user_id: int, days: int = 30) -> dict:
    """Compute running-specific stats for the last N days.

    Returns:
        total_runs, total_km, total_min, avg_pace (min/km), avg_pace_fmt,
        longest_run_km, longest_run_date, weekly_avg_km, weekly_avg_runs,
        total_elevation_m (placeholder — only if column exists).
    """
    runs = get_running_history(user_id, days=days)

    if not runs:
        return {
            "total_runs": 0,
            "total_km": 0.0,
            "total_min": 0,
            "avg_pace": None,
            "avg_pace_fmt": "—",
            "longest_run_km": 0.0,
            "longest_run_date": None,
            "weekly_avg_km": 0.0,
            "weekly_avg_runs": 0.0,
        }

    total_km = 0.0
    total_min = 0
    longest_km = 0.0
    longest_date = None

    for r in runs:
        dist = r.get("distance_km") or 0.0
        dur = r.get("duration_min") or 0
        total_km += dist
        total_min += dur
        if dist > longest_km:
            longest_km = dist
            longest_date = r.get("exercise_date")

    avg_pace = (total_min / total_km) if total_km > 0 else None
    weeks = max(1, days / 7.0)

    return {
        "total_runs": len(runs),
        "total_km": round(total_km, 1),
        "total_min": total_min,
        "avg_pace": round(avg_pace, 2) if avg_pace else None,
        "avg_pace_fmt": _format_pace(avg_pace) if avg_pace else "—",
        "longest_run_km": round(longest_km, 1),
        "longest_run_date": longest_date,
        "weekly_avg_km": round(total_km / weeks, 1),
        "weekly_avg_runs": round(len(runs) / weeks, 1),
    }


# ── Training Load (Session RPE) ──────────────────────────────────────────

def calculate_training_load(user_id: int, days: int = 42) -> dict:
    """Calculate acute and chronic training load using session-RPE method.

    Training load per session = duration_min * RPE (Foster et al., 2001).
    When RPE is not recorded, intensity is mapped to a default RPE:
        light → 3, moderate → 5, vigorous → 7.

    Metrics:
        ATL (Acute Training Load):  7-day sum of session loads
        CTL (Chronic Training Load): 42-day rolling average (daily load)
        ACWR (Acute:Chronic Workload Ratio): ATL / CTL
            <0.8  = under-training / detraining
            0.8-1.3 = "sweet spot" (Gabbett, 2016)
            >1.5  = spike — elevated injury risk

    Returns:
        atl, ctl, acwr, atl_label, daily_loads (list of per-day dicts),
        total_load_7d, total_load_42d.
    """
    # Fetch extra days to have 42-day chronic window fully populated
    total_days = days + 7  # buffer
    cutoff = (date.today() - timedelta(days=total_days)).isoformat()
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT exercise_date, duration_min, intensity, rpe
               FROM exercise_logs
               WHERE user_id = ? AND exercise_type = 'run' AND exercise_date >= ?
               ORDER BY exercise_date""",
            (user_id, cutoff),
        ).fetchall()
    finally:
        conn.close()

    # Default RPE mapping when RPE is not recorded
    intensity_rpe_map = {"light": 3, "moderate": 5, "vigorous": 7}

    # Accumulate daily loads
    daily_load_map: dict[str, float] = {}
    for r in rows:
        r = dict(r)
        rpe = r.get("rpe")
        if rpe is None:
            rpe = intensity_rpe_map.get(r.get("intensity", "moderate"), 5)
        session_load = (r.get("duration_min") or 0) * rpe
        d = r["exercise_date"]
        daily_load_map[d] = daily_load_map.get(d, 0.0) + session_load

    # Build daily series for the last `days` calendar days
    today = date.today()
    daily_loads = []
    for i in range(days, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        daily_loads.append({"date": d, "load": daily_load_map.get(d, 0.0)})

    # ATL = sum of last 7 days
    atl = sum(entry["load"] for entry in daily_loads[-7:])

    # CTL = 42-day average daily load × 7 (to put on same weekly scale as ATL)
    # Or equivalently: sum of last 42 days / 6 (since ATL is 7-day sum)
    loads_42 = [entry["load"] for entry in daily_loads[-42:]] if len(daily_loads) >= 42 else [entry["load"] for entry in daily_loads]
    total_42 = sum(loads_42)
    ctl_daily_avg = total_42 / max(len(loads_42), 1)
    ctl = ctl_daily_avg * 7  # scale to weekly for comparison with ATL

    # ACWR
    acwr = round(atl / ctl, 2) if ctl > 0 else 0.0

    # Interpret ACWR
    if acwr < 0.8:
        acwr_label = "Under-training — consider increasing volume gradually"
    elif acwr <= 1.3:
        acwr_label = "Sweet spot — good balance of load and recovery"
    elif acwr <= 1.5:
        acwr_label = "Caution — elevated injury risk, monitor fatigue"
    else:
        acwr_label = "Danger zone — significant spike, reduce load"

    return {
        "atl": round(atl, 1),
        "ctl": round(ctl, 1),
        "acwr": acwr,
        "acwr_label": acwr_label,
        "total_load_7d": round(atl, 1),
        "total_load_42d": round(total_42, 1),
        "daily_loads": daily_loads,
    }


# ── Training Plan Generation ─────────────────────────────────────────────

def get_training_plan(
    goal: str,
    current_weekly_km: float,
    weeks: int,
) -> dict:
    """Generate a structured running training plan.

    Args:
        goal: One of "5k", "10k", "half_marathon", "marathon".
        current_weekly_km: Athlete's current average weekly running volume in km.
        weeks: Number of weeks for the plan.

    Returns:
        Dict with plan metadata and a week-by-week list of sessions, each
        containing day, type, target_km, description.
    """
    template = TRAINING_PLAN_TEMPLATES.get(goal)
    if not template:
        return {"error": f"Unknown goal: {goal}. Choose from: {', '.join(TRAINING_PLAN_TEMPLATES.keys())}"}

    # Clamp weeks to template bounds
    min_w = template["min_weeks"]
    max_w = template["max_weeks"]
    weeks = max(min_w, min(max_w, weeks))

    # Ensure minimum sensible weekly km
    current_weekly_km = max(5.0, current_weekly_km)

    peak_km = current_weekly_km * template["peak_weekly_km_factor"]
    taper_weeks = template["taper_weeks"]
    build_weeks = weeks - taper_weeks
    progression_pct = template["progression_pct_per_week"]
    weekly_structure = template["weekly_structure"]

    # Start on next Monday
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    plan_start = today if days_until_monday == 0 else today + timedelta(days=days_until_monday)

    day_offsets = {
        "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
        "Fri": 4, "Sat": 5, "Sun": 6,
    }

    plan_weeks = []
    for week_num in range(1, weeks + 1):
        is_taper = week_num > build_weeks
        is_deload = (not is_taper) and (week_num % 4 == 0)

        # Progressive overload with 10% rule, then taper
        if is_taper:
            taper_progress = (week_num - build_weeks) / taper_weeks
            week_km = peak_km * (1.0 - 0.4 * taper_progress)  # 40% reduction
        elif is_deload:
            # Previous week's volume * 0.7
            prev_km = current_weekly_km * (1.0 + progression_pct * (week_num - 1))
            week_km = min(prev_km * 0.7, peak_km)
        else:
            week_km = min(
                current_weekly_km * (1.0 + progression_pct * (week_num - 1)),
                peak_km,
            )

        week_km = round(week_km, 1)
        week_start = plan_start + timedelta(weeks=week_num - 1)

        sessions = []
        for session in weekly_structure:
            session_km = round(week_km * session["km_pct"], 1)
            session_date = week_start + timedelta(days=day_offsets[session["day"]])
            sessions.append({
                "date": session_date.isoformat(),
                "day": session["day"],
                "type": session["type"],
                "target_km": session_km,
                "description": session["description"],
            })

        label = "Taper" if is_taper else ("Deload" if is_deload else f"Week {week_num}")
        plan_weeks.append({
            "week": week_num,
            "week_start": week_start.isoformat(),
            "label": label,
            "is_taper": is_taper,
            "is_deload": is_deload,
            "total_km": week_km,
            "sessions": sessions,
        })

    return {
        "goal": goal,
        "goal_label": template["label"],
        "description": template["description"],
        "start_date": plan_start.isoformat(),
        "weeks": weeks,
        "current_weekly_km": current_weekly_km,
        "peak_weekly_km": round(peak_km, 1),
        "sessions_per_week": template["sessions_per_week"],
        "plan_weeks": plan_weeks,
    }


# ── Coach Integration ─────────────────────────────────────────────────────

def get_running_coach_context(user_id: int) -> str | None:
    """Build running training context string for the AI coach.

    Returns a multi-line string covering recent stats, training load, ACWR,
    and pace zones (if a recent race result is available in the logs).
    Returns None if no running data exists.
    """
    stats = get_running_stats(user_id, days=30)
    if stats["total_runs"] == 0:
        return None

    load = calculate_training_load(user_id, days=42)

    parts = [
        "=== RUNNING TRAINING SUMMARY (last 30 days) ===",
        f"Runs: {stats['total_runs']} | Total: {stats['total_km']} km | Avg pace: {stats['avg_pace_fmt']}",
        f"Weekly avg: {stats['weekly_avg_km']} km/week, {stats['weekly_avg_runs']} runs/week",
        f"Longest run: {stats['longest_run_km']} km ({stats['longest_run_date'] or 'N/A'})",
        "",
        "=== TRAINING LOAD (session RPE) ===",
        f"ATL (7-day load): {load['atl']}",
        f"CTL (42-day avg weekly load): {load['ctl']}",
        f"ACWR: {load['acwr']} — {load['acwr_label']}",
    ]

    # Try to estimate VDOT from fastest short run with distance data
    recent_runs = get_running_history(user_id, days=90)
    best_vdot = 0.0
    for r in recent_runs:
        dist = r.get("distance_km") or 0.0
        dur = r.get("duration_min") or 0
        if dist >= 3.0 and dur > 0:
            v = estimate_vdot(dist, dur)
            if v > best_vdot:
                best_vdot = v

    if best_vdot >= 30:
        zones = get_pace_zones(best_vdot)
        parts.append("")
        parts.append(f"=== PACE ZONES (estimated VDOT: {best_vdot}) ===")
        for key in ("z1", "z2", "z3", "z4", "z5"):
            z = zones.get(key)
            if z:
                parts.append(f"{z['short']}: {z['min_pace_fmt']} – {z['max_pace_fmt']} /km")

    return "\n".join(parts)
