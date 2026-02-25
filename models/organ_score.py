"""CRUD operations for organ score definitions and computed results."""

import json
from db.database import get_connection


def get_all_score_definitions() -> list:
    """Return all organ score definitions ordered by sort_order."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM organ_score_definitions ORDER BY sort_order"
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["required_biomarkers"] = json.loads(d["required_biomarkers"])
            d["required_clinical"] = json.loads(d["required_clinical"]) if d["required_clinical"] else []
            d["interpretation"] = json.loads(d["interpretation"])
            results.append(d)
        return results
    finally:
        conn.close()


def get_definitions_by_organ(organ_system: str) -> list:
    """Return organ score definitions for a given organ system."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM organ_score_definitions WHERE organ_system = ? ORDER BY sort_order",
            (organ_system,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["required_biomarkers"] = json.loads(d["required_biomarkers"])
            d["required_clinical"] = json.loads(d["required_clinical"]) if d["required_clinical"] else []
            d["interpretation"] = json.loads(d["interpretation"])
            results.append(d)
        return results
    finally:
        conn.close()


def get_definition_by_code(code: str) -> dict | None:
    """Return a single organ score definition by its code."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM organ_score_definitions WHERE code = ?", (code,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["required_biomarkers"] = json.loads(d["required_biomarkers"])
        d["required_clinical"] = json.loads(d["required_clinical"]) if d["required_clinical"] else []
        d["interpretation"] = json.loads(d["interpretation"])
        return d
    finally:
        conn.close()


def save_score_result(user_id: int, score_def_id: int, value: float,
                      label: str, severity: str, input_snapshot: dict,
                      lab_date: str):
    """Save a computed organ score result (insert or replace)."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO organ_score_results
               (user_id, score_def_id, value, label, severity, input_snapshot, lab_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, score_def_id, lab_date)
               DO UPDATE SET value = excluded.value,
                             label = excluded.label,
                             severity = excluded.severity,
                             input_snapshot = excluded.input_snapshot,
                             computed_at = datetime('now')""",
            (user_id, score_def_id, value, label, severity,
             json.dumps(input_snapshot), lab_date),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_scores(user_id: int) -> list:
    """Return the most recently computed result for each organ score."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT osr.*, osd.code, osd.name, osd.organ_system, osd.tier,
                      osd.citation_pmid, osd.citation_text, osd.description as score_description,
                      osd.interpretation as score_interpretation
               FROM organ_score_results osr
               JOIN organ_score_definitions osd ON osr.score_def_id = osd.id
               WHERE osr.user_id = ?
                 AND osr.computed_at = (
                     SELECT MAX(osr2.computed_at)
                     FROM organ_score_results osr2
                     WHERE osr2.user_id = osr.user_id
                       AND osr2.score_def_id = osr.score_def_id
                 )
               ORDER BY osd.sort_order""",
            (user_id,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["input_snapshot"] = json.loads(d["input_snapshot"])
            d["score_interpretation"] = json.loads(d["score_interpretation"]) if d["score_interpretation"] else {}
            results.append(d)
        return results
    finally:
        conn.close()


def get_score_history(user_id: int, score_code: str, limit: int = 50) -> list:
    """Return historical values for a specific organ score, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT osr.*, osd.code, osd.name, osd.organ_system, osd.tier
               FROM organ_score_results osr
               JOIN organ_score_definitions osd ON osr.score_def_id = osd.id
               WHERE osr.user_id = ? AND osd.code = ?
               ORDER BY osr.lab_date DESC
               LIMIT ?""",
            (user_id, score_code, limit),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["input_snapshot"] = json.loads(d["input_snapshot"])
            results.append(d)
        return results
    finally:
        conn.close()


def get_scores_by_organ(user_id: int, organ_system: str) -> list:
    """Return the latest computed scores for a specific organ system."""
    all_scores = get_latest_scores(user_id)
    return [s for s in all_scores if s["organ_system"] == organ_system]
