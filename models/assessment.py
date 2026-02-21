import uuid
from db.database import get_connection


def create_assessment(user_id: int, scores: dict, notes: dict = None, stages: dict = None) -> str:
    """Create a wheel assessment session. scores = {pillar_id: score}, notes = {pillar_id: text}."""
    session_id = str(uuid.uuid4())
    notes = notes or {}
    conn = get_connection()
    try:
        for pillar_id, score in scores.items():
            conn.execute(
                "INSERT INTO wheel_assessments (user_id, pillar_id, score, notes, session_id) VALUES (?, ?, ?, ?, ?)",
                (user_id, pillar_id, score, notes.get(pillar_id, ""), session_id),
            )
        if stages:
            for pillar_id, stage in stages.items():
                if stage:
                    conn.execute(
                        "INSERT INTO stage_of_change (user_id, pillar_id, stage) VALUES (?, ?, ?)",
                        (user_id, pillar_id, stage),
                    )
        conn.commit()
        return session_id
    finally:
        conn.close()


def get_latest_assessment(user_id: int) -> dict | None:
    """Get the most recent assessment as {pillar_id: score}."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT session_id FROM wheel_assessments WHERE user_id = ? ORDER BY assessed_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return get_assessment_by_session(row["session_id"])
    finally:
        conn.close()


def get_assessment_by_session(session_id: str) -> dict:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT pillar_id, score, notes, assessed_at FROM wheel_assessments WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        if not rows:
            return {}
        return {
            "session_id": session_id,
            "assessed_at": rows[0]["assessed_at"],
            "scores": {r["pillar_id"]: r["score"] for r in rows},
            "notes": {r["pillar_id"]: r["notes"] for r in rows},
        }
    finally:
        conn.close()


def get_assessment_history(user_id: int, limit: int = 20) -> list:
    """Get list of assessment sessions ordered newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT session_id, assessed_at,
                      GROUP_CONCAT(pillar_id || ':' || score) as scores_str
               FROM wheel_assessments
               WHERE user_id = ?
               GROUP BY session_id
               ORDER BY assessed_at DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        result = []
        for row in rows:
            scores = {}
            for pair in row["scores_str"].split(","):
                pid, score = pair.split(":")
                scores[int(pid)] = int(score)
            result.append({
                "session_id": row["session_id"],
                "assessed_at": row["assessed_at"],
                "scores": scores,
                "total": sum(scores.values()),
            })
        return result
    finally:
        conn.close()


def get_latest_stages(user_id: int) -> dict:
    """Get the most recent stage of change for each pillar."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT pillar_id, stage FROM stage_of_change
               WHERE user_id = ? AND id IN (
                   SELECT MAX(id) FROM stage_of_change WHERE user_id = ? GROUP BY pillar_id
               )""",
            (user_id, user_id),
        ).fetchall()
        return {r["pillar_id"]: r["stage"] for r in rows}
    finally:
        conn.close()
