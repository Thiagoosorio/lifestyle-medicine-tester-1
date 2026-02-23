"""Service for body metrics tracking — weight, measurements, BMI, composition."""

from db.database import get_connection


def log_body_metrics(user_id, log_date, weight_kg, height_cm=None,
                     waist_cm=None, hip_cm=None, body_fat_pct=None,
                     notes=None, photo_note=None):
    """Insert or update a body metrics entry for a given date."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO body_metrics
               (user_id, log_date, weight_kg, height_cm, waist_cm, hip_cm,
                body_fat_pct, notes, photo_note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, log_date, weight_kg, height_cm, waist_cm, hip_cm,
             body_fat_pct, notes, photo_note),
        )
        conn.commit()
    finally:
        conn.close()

    # Auto-update weight goals if applicable
    _auto_update_weight_goal(user_id, weight_kg)


def get_body_metrics_history(user_id):
    """Return all body metric entries for a user, sorted by date ASC."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM body_metrics WHERE user_id = ? ORDER BY log_date ASC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_latest_metrics(user_id):
    """Return the most recent body metrics entry."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM body_metrics WHERE user_id = ? ORDER BY log_date DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_latest_height(user_id):
    """Get the most recent height entry for a user."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT height_cm FROM body_metrics WHERE user_id = ? "
            "AND height_cm IS NOT NULL ORDER BY log_date DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return row["height_cm"] if row else None
    finally:
        conn.close()


def delete_body_metrics(user_id, entry_id):
    """Delete a body metrics entry."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM body_metrics WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_goal_weight(user_id):
    """Get the user's goal weight from user_settings."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT goal_weight_kg FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row["goal_weight_kg"] if row else None
    finally:
        conn.close()


def set_goal_weight(user_id, kg):
    """Set or update the user's goal weight."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO user_settings (user_id, goal_weight_kg, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(user_id) DO UPDATE SET
               goal_weight_kg = excluded.goal_weight_kg,
               updated_at = datetime('now')""",
            (user_id, kg),
        )
        conn.commit()
    finally:
        conn.close()


def compute_bmi(weight_kg, height_cm):
    """Compute BMI from weight (kg) and height (cm)."""
    if not weight_kg or not height_cm or height_cm <= 0:
        return None
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 1)


def compute_waist_hip_ratio(waist_cm, hip_cm):
    """Compute waist-to-hip ratio."""
    if not waist_cm or not hip_cm or hip_cm <= 0:
        return None
    return round(waist_cm / hip_cm, 2)


def _auto_update_weight_goal(user_id, weight_kg):
    """If user has an active weight goal, auto-update its current_value."""
    if not weight_kg:
        return
    conn = get_connection()
    try:
        # Find active goals related to weight/body
        rows = conn.execute(
            """SELECT id, target_value, current_value FROM goals
               WHERE user_id = ? AND status = 'active'
               AND (LOWER(title) LIKE '%weight%' OR LOWER(title) LIKE '%kg%'
                    OR LOWER(unit) = 'kg')""",
            (user_id,),
        ).fetchall()
        for row in rows:
            goal_id = row["id"]
            target = row["target_value"]
            if target is not None:
                # Compute progress percentage based on direction
                start_val = row["current_value"] or weight_kg
                total_change = abs(target - start_val) if start_val != target else 1
                current_change = abs(weight_kg - start_val)
                pct = min(100, round(current_change / total_change * 100)) if total_change > 0 else 0
                conn.execute(
                    """UPDATE goals SET current_value = ?, progress_pct = ?,
                       updated_at = datetime('now') WHERE id = ?""",
                    (weight_kg, pct, goal_id),
                )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()
