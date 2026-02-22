"""Service for fasting session management, zone tracking, and stats."""

from db.database import get_connection
from datetime import datetime, timedelta, date


def start_fast(user_id, fasting_type, target_hours=None, notes=None):
    """Start a new fasting session. Returns the session ID."""
    from config.fasting_data import FASTING_TYPES

    ft = FASTING_TYPES.get(fasting_type, {})
    if target_hours is None:
        target_hours = ft.get("target_hours", 16)

    # End any active fast first
    active = get_active_fast(user_id)
    if active:
        end_fast(user_id, active["id"])

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO fasting_sessions
           (user_id, start_time, target_hours, fasting_type, notes, completed)
           VALUES (?, ?, ?, ?, ?, 0)""",
        (user_id, now, target_hours, fasting_type, notes),
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def end_fast(user_id, session_id=None):
    """End a fasting session. Auto-computes actual hours."""
    conn = get_connection()
    if session_id:
        row = conn.execute(
            "SELECT * FROM fasting_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM fasting_sessions WHERE user_id = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
            (user_id,),
        ).fetchone()

    if not row:
        conn.close()
        return None

    session = dict(row)
    now = datetime.now()
    start = datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S")
    actual_hours = round((now - start).total_seconds() / 3600, 1)
    completed = 1 if actual_hours >= (session["target_hours"] or 0) else 0

    conn.execute(
        """UPDATE fasting_sessions
           SET end_time = ?, actual_hours = ?, completed = ?
           WHERE id = ?""",
        (now.strftime("%Y-%m-%d %H:%M:%S"), actual_hours, completed, session["id"]),
    )
    conn.commit()
    conn.close()
    return {"actual_hours": actual_hours, "completed": completed}


def get_active_fast(user_id):
    """Get the currently active (uncompleted) fast."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM fasting_sessions WHERE user_id = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None

    session = dict(row)
    # Compute elapsed hours
    start = datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S")
    elapsed = (datetime.now() - start).total_seconds() / 3600
    session["elapsed_hours"] = round(elapsed, 2)
    session["progress_pct"] = min(100, round(elapsed / (session["target_hours"] or 1) * 100))
    session["current_zone"] = get_current_zone(elapsed)
    return session


def get_current_zone(elapsed_hours):
    """Get the metabolic zone for the current elapsed time."""
    from config.fasting_data import FASTING_ZONES
    for zone in reversed(FASTING_ZONES):
        if elapsed_hours >= zone["start_hours"]:
            return zone
    return FASTING_ZONES[0]


def get_fasting_history(user_id, limit=30):
    """Get completed fasting sessions, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM fasting_sessions
           WHERE user_id = ? AND end_time IS NOT NULL
           ORDER BY start_time DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_fasting_sessions(user_id):
    """Get all fasting sessions (completed and active)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM fasting_sessions WHERE user_id = ? ORDER BY start_time",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_fasting_stats(user_id, days=30):
    """Get fasting statistics for the last N days."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        """SELECT * FROM fasting_sessions
           WHERE user_id = ? AND end_time IS NOT NULL AND start_time >= ?""",
        (user_id, cutoff),
    ).fetchall()
    conn.close()

    if not rows:
        return {
            "total_fasts": 0, "completed_fasts": 0, "avg_hours": 0,
            "longest_fast": 0, "completion_rate": 0, "total_fasting_hours": 0,
            "streak": 0,
        }

    sessions = [dict(r) for r in rows]
    completed = [s for s in sessions if s["completed"]]
    hours = [s["actual_hours"] or 0 for s in sessions]

    return {
        "total_fasts": len(sessions),
        "completed_fasts": len(completed),
        "avg_hours": round(sum(hours) / len(hours), 1) if hours else 0,
        "longest_fast": round(max(hours), 1) if hours else 0,
        "completion_rate": round(len(completed) / len(sessions) * 100) if sessions else 0,
        "total_fasting_hours": round(sum(hours), 1),
        "streak": _compute_streak(user_id),
    }


def _compute_streak(user_id):
    """Compute current fasting streak (consecutive days with a completed fast)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT DISTINCT DATE(start_time) as fast_date
           FROM fasting_sessions
           WHERE user_id = ? AND completed = 1
           ORDER BY fast_date DESC""",
        (user_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return 0

    streak = 0
    today = date.today()
    for i, row in enumerate(rows):
        fast_date = date.fromisoformat(row["fast_date"])
        expected = today - timedelta(days=i)
        if fast_date == expected:
            streak += 1
        elif i == 0 and fast_date == expected - timedelta(days=1):
            # Allow starting from yesterday
            streak += 1
            today = fast_date + timedelta(days=1)
        else:
            break
    return streak
