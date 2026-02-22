"""Service for managing science-backed daily protocols."""

from datetime import datetime, timedelta
from db.database import get_connection


def seed_protocols():
    """Populate the protocols table from config/protocols_data.py (idempotent)."""
    conn = get_connection()
    existing = conn.execute("SELECT COUNT(*) FROM protocols").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    from config.protocols_data import PROTOCOL_LIBRARY
    for proto in PROTOCOL_LIBRARY:
        conn.execute(
            """INSERT INTO protocols
               (pillar_id, name, description, timing, duration, frequency,
                difficulty, mechanism, expected_benefit, contraindications, sort_order)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                proto["pillar_id"],
                proto["name"],
                proto["description"],
                proto.get("timing"),
                proto.get("duration"),
                proto.get("frequency", "daily"),
                proto.get("difficulty", 1),
                proto.get("mechanism"),
                proto.get("expected_benefit"),
                proto.get("contraindications"),
                proto.get("sort_order", 0),
            ),
        )
    conn.commit()
    conn.close()


def get_all_protocols():
    """Get all active protocols."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM protocols WHERE is_active = 1 ORDER BY pillar_id, sort_order"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_protocols_for_pillar(pillar_id):
    """Get protocols for a specific pillar."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM protocols WHERE pillar_id = ? AND is_active = 1 ORDER BY sort_order",
        (pillar_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_protocol_by_id(protocol_id):
    """Get a single protocol by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM protocols WHERE id = ?", (protocol_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_protocols(user_id):
    """Get protocols the user has adopted, with protocol details."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT up.*, p.name, p.description, p.timing, p.duration,
                  p.frequency, p.difficulty, p.mechanism, p.expected_benefit,
                  p.pillar_id, p.contraindications
           FROM user_protocols up
           JOIN protocols p ON p.id = up.protocol_id
           WHERE up.user_id = ? AND up.status = 'active'
           ORDER BY p.pillar_id, p.sort_order""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def adopt_protocol(user_id, protocol_id):
    """User adopts a protocol."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO user_protocols (user_id, protocol_id, status)
               VALUES (?, ?, 'active')""",
            (user_id, protocol_id),
        )
        conn.commit()
    except Exception:
        # Already adopted — reactivate if paused/abandoned
        conn.execute(
            """UPDATE user_protocols SET status = 'active', started_at = datetime('now')
               WHERE user_id = ? AND protocol_id = ?""",
            (user_id, protocol_id),
        )
        conn.commit()
    conn.close()


def pause_protocol(user_id, protocol_id):
    """Pause a protocol."""
    conn = get_connection()
    conn.execute(
        "UPDATE user_protocols SET status = 'paused' WHERE user_id = ? AND protocol_id = ?",
        (user_id, protocol_id),
    )
    conn.commit()
    conn.close()


def abandon_protocol(user_id, protocol_id):
    """Abandon a protocol."""
    conn = get_connection()
    conn.execute(
        "UPDATE user_protocols SET status = 'abandoned' WHERE user_id = ? AND protocol_id = ?",
        (user_id, protocol_id),
    )
    conn.commit()
    conn.close()


def log_protocol_completion(user_id, protocol_id, log_date, completed=True, notes=None):
    """Log whether a protocol was completed on a given date."""
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO protocol_log (user_id, protocol_id, log_date, completed, notes)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, protocol_id, log_date, 1 if completed else 0, notes),
    )
    conn.commit()
    conn.close()


def get_daily_protocol_status(user_id, today):
    """Get all user's active protocols with today's completion status."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.id as protocol_id, p.name, p.description, p.timing,
                  p.duration, p.pillar_id, p.difficulty,
                  COALESCE(pl.completed, 0) as completed
           FROM user_protocols up
           JOIN protocols p ON p.id = up.protocol_id
           LEFT JOIN protocol_log pl ON pl.protocol_id = p.id
                AND pl.user_id = ? AND pl.log_date = ?
           WHERE up.user_id = ? AND up.status = 'active'
           ORDER BY CASE
               WHEN p.timing LIKE '%morning%' OR p.timing LIKE '%waking%' THEN 1
               WHEN p.timing LIKE '%afternoon%' OR p.timing LIKE '%midday%' THEN 2
               WHEN p.timing LIKE '%meal%' THEN 3
               WHEN p.timing LIKE '%evening%' OR p.timing LIKE '%night%' OR p.timing LIKE '%bed%' THEN 4
               ELSE 3
           END, p.sort_order""",
        (user_id, today, user_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_protocol_adherence(user_id, protocol_id, days_back=30):
    """Calculate adherence % for a protocol over the last N days."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    row = conn.execute(
        """SELECT
               COUNT(*) as total_logged,
               SUM(completed) as total_completed
           FROM protocol_log
           WHERE user_id = ? AND protocol_id = ? AND log_date >= ?""",
        (user_id, protocol_id, cutoff),
    ).fetchone()
    conn.close()
    if not row or row["total_logged"] == 0:
        return 0.0
    return (row["total_completed"] / days_back) * 100


def get_protocol_adherence_history(user_id, protocol_id, days_back=30):
    """Get daily completion data for a protocol (for sparklines)."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT log_date, completed FROM protocol_log
           WHERE user_id = ? AND protocol_id = ? AND log_date >= ?
           ORDER BY log_date""",
        (user_id, protocol_id, cutoff),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_protocol_adopted(user_id, protocol_id):
    """Check if a user has adopted a specific protocol."""
    conn = get_connection()
    row = conn.execute(
        "SELECT status FROM user_protocols WHERE user_id = ? AND protocol_id = ?",
        (user_id, protocol_id),
    ).fetchone()
    conn.close()
    return row and row["status"] == "active"
