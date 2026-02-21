from db.database import get_connection


def create_goal(user_id: int, data: dict) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO goals (user_id, pillar_id, title, specific, measurable, achievable,
               relevant, time_bound, evidence_base, strategic, tailored,
               target_value, unit, start_date, target_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, data["pillar_id"], data["title"],
                data["specific"], data["measurable"], data["achievable"],
                data["relevant"], data["time_bound"],
                data.get("evidence_base", ""), data.get("strategic", ""), data.get("tailored", ""),
                data.get("target_value"), data.get("unit", ""),
                data["start_date"], data["target_date"],
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_goals(user_id: int, status: str = None, pillar_id: int = None) -> list:
    conn = get_connection()
    try:
        query = "SELECT * FROM goals WHERE user_id = ?"
        params = [user_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        if pillar_id:
            query += " AND pillar_id = ?"
            params.append(pillar_id)
        query += " ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'paused' THEN 1 WHEN 'completed' THEN 2 ELSE 3 END, target_date ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_goal(goal_id: int, user_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_goal_progress(goal_id: int, user_id: int, progress_pct: int, current_value: float = None, notes: str = ""):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE goals SET progress_pct = ?, current_value = COALESCE(?, current_value), updated_at = datetime('now') WHERE id = ? AND user_id = ?",
            (progress_pct, current_value, goal_id, user_id),
        )
        conn.execute(
            "INSERT INTO goal_progress (goal_id, user_id, progress_pct, current_value, notes) VALUES (?, ?, ?, ?, ?)",
            (goal_id, user_id, progress_pct, current_value, notes),
        )
        if progress_pct >= 100:
            conn.execute(
                "UPDATE goals SET status = 'completed', completed_at = datetime('now') WHERE id = ? AND user_id = ?",
                (goal_id, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def update_goal_status(goal_id: int, user_id: int, status: str, reason: str = ""):
    conn = get_connection()
    try:
        if status == "abandoned":
            conn.execute(
                "UPDATE goals SET status = ?, abandoned_at = datetime('now'), abandon_reason = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?",
                (status, reason, goal_id, user_id),
            )
        elif status == "completed":
            conn.execute(
                "UPDATE goals SET status = ?, completed_at = datetime('now'), progress_pct = 100, updated_at = datetime('now') WHERE id = ? AND user_id = ?",
                (status, goal_id, user_id),
            )
        else:
            conn.execute(
                "UPDATE goals SET status = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?",
                (status, goal_id, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_goal_progress_history(goal_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM goal_progress WHERE goal_id = ? ORDER BY logged_at ASC",
            (goal_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
