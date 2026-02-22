"""Service for sleep logging, scoring, chronotype assessment, and analysis."""

from db.database import get_connection
from datetime import datetime, timedelta, date


def log_sleep(user_id, sleep_date, bedtime, wake_time, sleep_latency_min=0,
              awakenings=0, wake_duration_min=0, sleep_quality=3,
              naps_min=0, caffeine_cutoff=None, screen_cutoff=None,
              alcohol=0, exercise_today=0, notes=None):
    """Log a sleep entry and auto-compute total_sleep, efficiency, and score."""
    # Compute total sleep minutes
    bed_dt = datetime.strptime(bedtime, "%H:%M")
    wake_dt = datetime.strptime(wake_time, "%H:%M")
    # Handle midnight crossing
    if wake_dt <= bed_dt:
        wake_dt += timedelta(days=1)
    time_in_bed = (wake_dt - bed_dt).total_seconds() / 60
    total_sleep = max(0, time_in_bed - sleep_latency_min - wake_duration_min)

    # Sleep efficiency
    efficiency = round((total_sleep / time_in_bed) * 100, 1) if time_in_bed > 0 else 0

    # Compute score
    score = calculate_sleep_score(
        total_sleep_min=total_sleep,
        sleep_latency_min=sleep_latency_min,
        efficiency=efficiency,
        awakenings=awakenings,
        sleep_quality=sleep_quality,
        user_id=user_id,
    )

    conn = get_connection()
    conn.execute(
        """INSERT INTO sleep_logs
           (user_id, sleep_date, bedtime, wake_time, sleep_latency_min,
            awakenings, wake_duration_min, sleep_quality, naps_min,
            caffeine_cutoff, screen_cutoff, alcohol, exercise_today,
            notes, total_sleep_min, sleep_efficiency, sleep_score)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(user_id, sleep_date) DO UPDATE SET
             bedtime=excluded.bedtime, wake_time=excluded.wake_time,
             sleep_latency_min=excluded.sleep_latency_min,
             awakenings=excluded.awakenings, wake_duration_min=excluded.wake_duration_min,
             sleep_quality=excluded.sleep_quality, naps_min=excluded.naps_min,
             caffeine_cutoff=excluded.caffeine_cutoff, screen_cutoff=excluded.screen_cutoff,
             alcohol=excluded.alcohol, exercise_today=excluded.exercise_today,
             notes=excluded.notes, total_sleep_min=excluded.total_sleep_min,
             sleep_efficiency=excluded.sleep_efficiency, sleep_score=excluded.sleep_score""",
        (user_id, sleep_date, bedtime, wake_time, sleep_latency_min,
         awakenings, wake_duration_min, sleep_quality, naps_min,
         caffeine_cutoff, screen_cutoff, alcohol, exercise_today,
         notes, round(total_sleep), round(efficiency, 1), score),
    )
    conn.commit()
    conn.close()
    return {"total_sleep_min": round(total_sleep), "efficiency": round(efficiency, 1), "score": score}


def calculate_sleep_score(total_sleep_min, sleep_latency_min, efficiency,
                          awakenings, sleep_quality, user_id=None):
    """Calculate composite sleep score (0-100) based on PSQI components."""
    from config.sleep_data import SLEEP_SCORE_WEIGHTS
    w = SLEEP_SCORE_WEIGHTS

    # Duration component (7-9h = 420-540 min optimal)
    hours = total_sleep_min / 60
    if 7.0 <= hours <= 9.0:
        duration_score = 1.0
    elif 6.0 <= hours < 7.0 or 9.0 < hours <= 10.0:
        duration_score = 0.7
    elif 5.0 <= hours < 6.0 or 10.0 < hours <= 11.0:
        duration_score = 0.4
    else:
        duration_score = 0.1

    # Latency component
    if sleep_latency_min <= 15:
        latency_score = 1.0
    elif sleep_latency_min <= 30:
        latency_score = 0.7
    elif sleep_latency_min <= 60:
        latency_score = 0.4
    else:
        latency_score = 0.1

    # Efficiency component
    if efficiency >= 90:
        efficiency_score = 1.0
    elif efficiency >= 85:
        efficiency_score = 0.7
    elif efficiency >= 75:
        efficiency_score = 0.4
    else:
        efficiency_score = 0.1

    # Disturbance component
    if awakenings <= 1:
        disturbance_score = 1.0
    elif awakenings <= 3:
        disturbance_score = 0.7
    elif awakenings <= 5:
        disturbance_score = 0.4
    else:
        disturbance_score = 0.1

    # Subjective quality (1-5 scale)
    quality_score = max(0, min(1.0, (sleep_quality - 1) / 4))

    # Consistency (requires history)
    consistency_score = 0.7  # default if no history
    if user_id:
        consistency_score = _compute_consistency(user_id)

    score = (
        duration_score * w["duration"]["weight"]
        + latency_score * w["latency"]["weight"]
        + efficiency_score * w["efficiency"]["weight"]
        + disturbance_score * w["disturbance"]["weight"]
        + quality_score * w["quality"]["weight"]
        + consistency_score * w["consistency"]["weight"]
    ) * 100

    return round(min(100, max(0, score)))


def _compute_consistency(user_id):
    """Compute bedtime consistency from the last 7 days."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT bedtime FROM sleep_logs
           WHERE user_id = ? ORDER BY sleep_date DESC LIMIT 7""",
        (user_id,),
    ).fetchall()
    conn.close()

    if len(rows) < 2:
        return 0.7  # not enough data

    minutes = []
    for r in rows:
        bt = r["bedtime"]
        if bt:
            parts = bt.split(":")
            m = int(parts[0]) * 60 + int(parts[1])
            if m < 360:  # before 6 AM = after midnight
                m += 1440
            minutes.append(m)

    if len(minutes) < 2:
        return 0.7

    avg = sum(minutes) / len(minutes)
    variance = sum((m - avg) ** 2 for m in minutes) / len(minutes)
    std_dev = variance ** 0.5

    if std_dev <= 30:
        return 1.0
    elif std_dev <= 60:
        return 0.7
    elif std_dev <= 90:
        return 0.4
    else:
        return 0.1


def get_sleep_history(user_id, days=30):
    """Get sleep log history for the last N days."""
    conn = get_connection()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT * FROM sleep_logs
           WHERE user_id = ? AND sleep_date >= ?
           ORDER BY sleep_date DESC""",
        (user_id, cutoff),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_sleep_history(user_id):
    """Get all sleep logs for a user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sleep_logs WHERE user_id = ? ORDER BY sleep_date",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_sleep_averages(user_id, days=30):
    """Get average sleep metrics over the last N days."""
    conn = get_connection()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    row = conn.execute(
        """SELECT
             AVG(total_sleep_min) as avg_duration,
             AVG(sleep_efficiency) as avg_efficiency,
             AVG(sleep_latency_min) as avg_latency,
             AVG(awakenings) as avg_awakenings,
             AVG(sleep_quality) as avg_quality,
             AVG(sleep_score) as avg_score,
             COUNT(*) as log_count
           FROM sleep_logs
           WHERE user_id = ? AND sleep_date >= ?""",
        (user_id, cutoff),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_latest_sleep_score(user_id):
    """Get the most recent sleep score."""
    conn = get_connection()
    row = conn.execute(
        "SELECT sleep_score FROM sleep_logs WHERE user_id = ? ORDER BY sleep_date DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return row["sleep_score"] if row else None


def assess_chronotype(user_id, answers):
    """Assess chronotype from MEQ quiz answers and save result.
    answers: list of scores (one per question).
    """
    from config.sleep_data import (
        CHRONOTYPES, MEQ_SCALE_MIN, MEQ_SCALE_MAX,
        MEQ_MAPPED_MIN, MEQ_MAPPED_MAX,
    )

    raw_score = sum(answers)
    # Scale 5-25 → 16-86
    meq_score = round(
        MEQ_MAPPED_MIN + (raw_score - MEQ_SCALE_MIN) * (MEQ_MAPPED_MAX - MEQ_MAPPED_MIN) / (MEQ_SCALE_MAX - MEQ_SCALE_MIN)
    )
    meq_score = max(MEQ_MAPPED_MIN, min(MEQ_MAPPED_MAX, meq_score))

    # Determine chronotype
    chronotype = "bear"  # default
    for ctype_key, ctype in CHRONOTYPES.items():
        if ctype["meq_min"] is not None and ctype["meq_max"] is not None:
            if ctype["meq_min"] <= meq_score <= ctype["meq_max"]:
                chronotype = ctype_key
                break

    ctype_data = CHRONOTYPES[chronotype]

    conn = get_connection()
    conn.execute(
        """INSERT INTO chronotype_assessments
           (user_id, meq_score, chronotype, ideal_bedtime, ideal_waketime)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             meq_score=excluded.meq_score, chronotype=excluded.chronotype,
             ideal_bedtime=excluded.ideal_bedtime, ideal_waketime=excluded.ideal_waketime,
             assessed_at=CURRENT_TIMESTAMP""",
        (user_id, meq_score, chronotype,
         ctype_data["ideal_bedtime"], ctype_data["ideal_waketime"]),
    )
    conn.commit()
    conn.close()
    return {"meq_score": meq_score, "chronotype": chronotype, "data": ctype_data}


def get_chronotype(user_id):
    """Get the user's chronotype assessment."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM chronotype_assessments WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    from config.sleep_data import CHRONOTYPES
    result = dict(row)
    result["data"] = CHRONOTYPES.get(result["chronotype"], {})
    return result


def get_sleep_score_zone(score):
    """Return the zone info for a given sleep score."""
    from config.sleep_data import SLEEP_SCORE_ZONES
    for zone_key, zone in SLEEP_SCORE_ZONES.items():
        if zone["min"] <= score <= zone["max"]:
            return zone
    return SLEEP_SCORE_ZONES["poor"]


def analyze_sleep_hygiene(user_id, days=14):
    """Analyze sleep hygiene patterns and return relevant tips."""
    from config.sleep_data import SLEEP_HYGIENE_TIPS
    history = get_sleep_history(user_id, days=days)
    if not history:
        return []

    tips = []
    avg_latency = sum(h.get("sleep_latency_min", 0) for h in history) / len(history)
    avg_awakenings = sum(h.get("awakenings", 0) for h in history) / len(history)
    alcohol_nights = sum(1 for h in history if h.get("alcohol"))
    avg_efficiency = sum(h.get("sleep_efficiency", 0) for h in history) / len(history)

    if avg_latency > 30:
        tips.append(SLEEP_HYGIENE_TIPS["latency"])
    if alcohol_nights > len(history) * 0.3:
        tips.append(SLEEP_HYGIENE_TIPS["alcohol"])
    if avg_efficiency < 85:
        tips.append(SLEEP_HYGIENE_TIPS["consistency"])
    if avg_awakenings > 3:
        tips.append(SLEEP_HYGIENE_TIPS["environment"])

    # Always include general tip if fewer than 2 tips
    if len(tips) < 2:
        tips.append(SLEEP_HYGIENE_TIPS["environment"])

    return tips
