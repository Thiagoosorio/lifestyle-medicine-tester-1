"""Service for computing recovery scores from sleep, stress, habits, and mood.

Recovery Score (0-100) based on psychoneuroimmunology research.
Components:
  - Sleep (30%): Last night's sleep score
  - Stress management (20%): Most recent stress-management pillar rating
  - Training Load (20%): Inverse of acute training load (last 48h)
  - Activity (10%): Exercise consistency score
  - Habit consistency (10%): Recent habit completion rate
  - Mood (10%): Current mood rating
"""

from datetime import date, timedelta
from db.database import get_connection


RECOVERY_WEIGHTS = {
    "sleep": 0.30,
    "stress": 0.20,
    "training_load": 0.20,
    "activity": 0.10,
    "habits": 0.10,
    "mood": 0.10,
}


def calculate_recovery_score(user_id):
    """Calculate the composite recovery score (0-100).
    Returns dict with score, zone, and component breakdown.
    """
    components = get_recovery_components(user_id)

    if not components:
        return None

    available = [key for key, item in components.items() if item["raw"] is not None]
    available_weight = sum(RECOVERY_WEIGHTS[key] for key in available)
    if available_weight <= 0:
        return None
    score = round(
        sum(components[key]["score"] * RECOVERY_WEIGHTS[key] for key in available)
        / available_weight
    )
    score = max(0, min(100, score))

    coverage_pct = round(available_weight * 100)
    zone = (
        get_recovery_zone(score)
        if coverage_pct >= 50
        else {
            "label": "Limited Data",
            "color": "#8E8E93",
            "icon": "&#9675;",
            "message": "More data is needed before treating this as a readiness signal.",
            "recommendation": "Log sleep and a daily check-in; do not use this partial score to select hard training.",
        }
    )

    return {
        "score": score,
        "zone": zone,
        "components": components,
        "coverage_pct": coverage_pct,
    }


def get_recovery_components(user_id):
    """Get individual recovery component scores."""
    sleep_score = _get_sleep_component(user_id)
    stress_score = _get_stress_component(user_id)
    training_load_score = _get_training_load_component(user_id)
    activity_score = _get_activity_component(user_id)
    habits_score = _get_habits_component(user_id)
    mood_score = _get_mood_component(user_id)

    # If we have no data at all, return None
    has_data = any(c["raw"] is not None for c in [
        sleep_score, stress_score, training_load_score,
        activity_score, habits_score, mood_score
    ])
    if not has_data:
        return None

    return {
        "sleep": sleep_score,
        "stress": stress_score,
        "training_load": training_load_score,
        "activity": activity_score,
        "habits": habits_score,
        "mood": mood_score,
    }


def _get_sleep_component(user_id):
    """Sleep component: last night's sleep score (0-100)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT sleep_score FROM sleep_logs WHERE user_id = ? ORDER BY sleep_date DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()

    if row and row["sleep_score"] is not None:
        return {"score": row["sleep_score"], "raw": row["sleep_score"],
                "label": "Sleep", "icon": "&#128164;"}
    return {"score": 50, "raw": None, "label": "Sleep", "icon": "&#128164;"}


def _get_stress_component(user_id):
    """Stress-management component: higher pillar ratings are better (1-10)."""
    conn = get_connection()
    row = conn.execute(
        """SELECT stress_rating FROM daily_checkins
           WHERE user_id = ? AND stress_rating IS NOT NULL
           ORDER BY checkin_date DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    conn.close()

    if row and row["stress_rating"] is not None:
        raw = row["stress_rating"]
        score = round(raw / 10 * 100)
        return {"score": score, "raw": raw, "label": "Stress Management", "icon": "&#129495;"}
    return {"score": 50, "raw": None, "label": "Stress Management", "icon": "&#129495;"}


def _get_training_load_component(user_id):
    """Training load component: inverse of acute training load from last 48h.

    Calculates load = sum(duration_min * intensity_multiplier) where
    light=0.5, moderate=1.0, vigorous=2.0. High load means lower recovery
    readiness; rest days boost recovery.

    Thresholds:
      load == 0   → rest day, score 90 (boosted recovery)
      load <= 60  → light load, score 75
      load <= 120 → moderate load, score 55
      load > 120  → heavy load, score 30
    """
    intensity_multipliers = {"light": 0.5, "moderate": 1.0, "vigorous": 2.0}

    conn = get_connection()
    cutoff = (date.today() - timedelta(days=2)).isoformat()
    rows = conn.execute(
        """SELECT duration_min, intensity FROM exercise_logs
           WHERE user_id = ? AND exercise_date >= ?""",
        (user_id, cutoff),
    ).fetchall()
    conn.close()

    if not rows:
        # No exercise data at all — this is *absence of information*, not a
        # logged rest day. Return raw=None (neutral score) so the whole-app
        # "no data" guard in get_recovery_components() fires instead of
        # fabricating a boosted recovery score. The rest-day boost below only
        # applies when rows exist but sum to zero load.
        return {"score": 50, "raw": None, "label": "Training Load", "icon": "&#9878;"}

    load = 0.0
    for r in rows:
        mult = intensity_multipliers.get(r["intensity"], 1.0)
        load += r["duration_min"] * mult

    load = round(load, 1)

    # Inverse scoring: higher load → lower recovery readiness
    if load == 0:
        score = 90  # Rest day — recovery boosted
    elif load <= 60:
        score = 75  # Light load
    elif load <= 120:
        score = 55  # Moderate load
    else:
        # Scale down from 30 to 10 as load goes from 120 to 240+
        score = max(10, round(30 - (load - 120) / 120 * 20))

    return {"score": score, "raw": load, "label": "Training Load", "icon": "&#9878;"}


def _get_activity_component(user_id):
    """Activity component: prefer exercise_logs data, fallback to check-in ratings."""
    # Try exercise_logs first (detailed workout data)
    try:
        from services.exercise_service import calculate_exercise_score
        ex_score = calculate_exercise_score(user_id)
        if ex_score is not None:
            return {"score": ex_score, "raw": ex_score, "label": "Activity", "icon": "&#127939;"}
    except Exception:
        pass

    # Fallback to daily check-in activity_rating
    conn = get_connection()
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    rows = conn.execute(
        """SELECT activity_rating FROM daily_checkins
           WHERE user_id = ? AND activity_rating IS NOT NULL AND checkin_date >= ?
           ORDER BY checkin_date DESC""",
        (user_id, cutoff),
    ).fetchall()
    conn.close()

    if rows:
        avg = sum(r["activity_rating"] for r in rows) / len(rows)
        # activity_rating 1-10 → scale to 100
        score = round(avg / 10 * 100)
        return {"score": score, "raw": round(avg, 1), "label": "Activity", "icon": "&#127939;"}
    return {"score": 50, "raw": None, "label": "Activity", "icon": "&#127939;"}


def _get_habits_component(user_id):
    """Habit consistency: completion rate over last 7 days."""
    conn = get_connection()
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    row = conn.execute(
        """SELECT COUNT(*) as total,
                  SUM(CASE WHEN completed_count >= 1 THEN 1 ELSE 0 END) as done
           FROM habit_log
           WHERE user_id = ? AND log_date >= ?""",
        (user_id, cutoff),
    ).fetchone()
    conn.close()

    if row and row["total"] > 0:
        rate = row["done"] / row["total"]
        score = round(rate * 100)
        return {"score": score, "raw": round(rate * 100),
                "label": "Habits", "icon": "&#9989;"}
    return {"score": 50, "raw": None, "label": "Habits", "icon": "&#9989;"}


def _get_mood_component(user_id):
    """Mood component: most recent mood rating (1-10)."""
    conn = get_connection()
    row = conn.execute(
        """SELECT mood FROM daily_checkins
           WHERE user_id = ? AND mood IS NOT NULL
           ORDER BY checkin_date DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    conn.close()

    if row and row["mood"] is not None:
        raw = row["mood"]
        score = round(raw / 10 * 100)
        return {"score": score, "raw": raw, "label": "Mood", "icon": "&#128522;"}
    return {"score": 50, "raw": None, "label": "Mood", "icon": "&#128522;"}


def get_recovery_zone(score):
    """Return zone info for a recovery score."""
    if score >= 80:
        return {
            "label": "Green",
            "color": "#30D158",
            "icon": "&#128994;",
            "message": "Fully recovered. You're ready for high-intensity training or challenging tasks.",
            "recommendation": "Push yourself today — your body and mind are primed for peak performance.",
        }
    elif score >= 60:
        return {
            "label": "Yellow",
            "color": "#FFD60A",
            "icon": "&#128993;",
            "message": "Moderate recovery. You can train but consider reducing intensity.",
            "recommendation": "Focus on moderate activity. Prioritize sleep tonight and manage stress.",
        }
    else:
        return {
            "label": "Red",
            "color": "#FF453A",
            "icon": "&#128308;",
            "message": "Low recovery. Your body needs rest and restoration.",
            "recommendation": "Take an active recovery day. Prioritize sleep, nutrition, and stress management.",
        }


def get_recovery_history(user_id, days=30):
    """Compute recovery scores for the last N days using historical data."""
    conn = get_connection()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    # Get daily data points
    sleep_rows = conn.execute(
        "SELECT sleep_date, sleep_score FROM sleep_logs WHERE user_id = ? AND sleep_date >= ? ORDER BY sleep_date",
        (user_id, cutoff),
    ).fetchall()
    checkin_rows = conn.execute(
        """SELECT checkin_date, mood, stress_rating, activity_rating
           FROM daily_checkins WHERE user_id = ? AND checkin_date >= ?
           ORDER BY checkin_date""",
        (user_id, cutoff),
    ).fetchall()

    # Get habit log data
    habit_rows = conn.execute(
        """SELECT log_date,
                  COUNT(*) as total,
                  SUM(CASE WHEN completed_count >= 1 THEN 1 ELSE 0 END) as done
           FROM habit_log WHERE user_id = ? AND log_date >= ?
           GROUP BY log_date""",
        (user_id, cutoff),
    ).fetchall()

    # Get exercise log data for training load (2-day rolling window)
    exercise_cutoff = (date.today() - timedelta(days=days + 2)).isoformat()
    exercise_rows = conn.execute(
        """SELECT exercise_date, duration_min, intensity FROM exercise_logs
           WHERE user_id = ? AND exercise_date >= ?
           ORDER BY exercise_date""",
        (user_id, exercise_cutoff),
    ).fetchall()
    conn.close()

    sleep_by_date = {r["sleep_date"]: r["sleep_score"] for r in sleep_rows}
    checkin_by_date = {r["checkin_date"]: dict(r) for r in checkin_rows}
    habits_by_date = {r["log_date"]: round(r["done"] / r["total"] * 100) if r["total"] > 0 else 50 for r in habit_rows}

    # Build exercise load by date for 48h rolling window calculation
    intensity_multipliers = {"light": 0.5, "moderate": 1.0, "vigorous": 2.0}
    exercise_by_date: dict[str, float] = {}
    for r in exercise_rows:
        d = r["exercise_date"]
        mult = intensity_multipliers.get(r["intensity"], 1.0)
        exercise_by_date[d] = exercise_by_date.get(d, 0.0) + r["duration_min"] * mult

    def _training_load_score_for_date(d_str):
        """Compute training load recovery score for a given date (48h window)."""
        d_date = date.fromisoformat(d_str)
        d_minus1 = (d_date - timedelta(days=1)).isoformat()
        d_minus2 = (d_date - timedelta(days=2)).isoformat()
        window_dates = (d_str, d_minus1, d_minus2)
        if not any(day in exercise_by_date for day in window_dates):
            return None
        load = sum(exercise_by_date.get(day, 0) for day in window_dates)
        if load == 0:
            return 90
        elif load <= 60:
            return 75
        elif load <= 120:
            return 55
        else:
            return max(10, round(30 - (load - 120) / 120 * 20))

    # Collect all dates
    all_dates = sorted(
        set(sleep_by_date) | set(checkin_by_date) | set(habits_by_date) | set(exercise_by_date)
    )

    history = []
    for d in all_dates:
        sleep = sleep_by_date.get(d)
        ci = checkin_by_date.get(d, {})
        stress_raw = ci.get("stress_rating")
        stress = round(stress_raw / 10 * 100) if stress_raw else None
        activity_raw = ci.get("activity_rating")
        activity = round(activity_raw / 10 * 100) if activity_raw else None
        mood_raw = ci.get("mood")
        mood = round(mood_raw / 10 * 100) if mood_raw else None
        habits = habits_by_date.get(d)
        training_load = _training_load_score_for_date(d)

        values = {
            "sleep": sleep,
            "stress": stress,
            "training_load": training_load,
            "activity": activity,
            "habits": habits,
            "mood": mood,
        }
        available_weight = sum(
            RECOVERY_WEIGHTS[key] for key, value in values.items() if value is not None
        )
        if available_weight <= 0:
            continue
        score = round(
            sum(
                value * RECOVERY_WEIGHTS[key]
                for key, value in values.items()
                if value is not None
            )
            / available_weight
        )
        score = max(0, min(100, score))
        history.append({"date": d, "score": score, "coverage_pct": round(available_weight * 100)})

    return history
