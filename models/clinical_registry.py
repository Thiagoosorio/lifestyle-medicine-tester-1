"""CRUD helpers for clinician-facing structured records.

Stores:
- confirmed diagnoses
- confirmed interventions
- structured clinical test results (CPET, imaging, etc.)
"""

from __future__ import annotations

import json
from db.database import get_connection


def _ensure_schema(conn) -> None:
    """Ensure clinical registry tables exist (safe/idempotent)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS clinical_diagnoses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            diagnosis_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'resolved', 'ruled_out')),
            confirmed_date TEXT,
            confirming_clinician TEXT,
            source TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, diagnosis_name))"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_clinical_diagnoses_user ON clinical_diagnoses(user_id, status, updated_at)"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS clinical_interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            intervention_type TEXT NOT NULL
                CHECK (intervention_type IN ('medication', 'supplement', 'lifestyle', 'training', 'other')),
            name TEXT NOT NULL,
            dose TEXT,
            schedule TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'paused', 'completed', 'stopped')),
            prescriber TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')))"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_clinical_interventions_user ON clinical_interventions(user_id, status, intervention_type, updated_at)"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS clinical_test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            test_type TEXT NOT NULL,
            test_date TEXT,
            status TEXT NOT NULL DEFAULT 'confirmed'
                CHECK (status IN ('confirmed', 'pending', 'excluded')),
            summary TEXT,
            key_metrics_json TEXT,
            source_ref TEXT,
            risk_flag TEXT DEFAULT 'unknown'
                CHECK (risk_flag IN ('low', 'moderate', 'high', 'critical', 'unknown')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')))"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_clinical_tests_user ON clinical_test_results(user_id, test_type, test_date)"
    )
    conn.commit()


def list_diagnoses(user_id: int, active_only: bool = False) -> list[dict]:
    conn = get_connection()
    try:
        _ensure_schema(conn)
        if active_only:
            rows = conn.execute(
                """SELECT * FROM clinical_diagnoses
                   WHERE user_id = ? AND status = 'active'
                   ORDER BY COALESCE(confirmed_date, ''), updated_at DESC""",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM clinical_diagnoses
                   WHERE user_id = ?
                   ORDER BY CASE status
                        WHEN 'active' THEN 0
                        WHEN 'resolved' THEN 1
                        ELSE 2
                   END, COALESCE(confirmed_date, ''), updated_at DESC""",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_diagnosis(
    user_id: int,
    diagnosis_name: str,
    status: str = "active",
    confirmed_date: str | None = None,
    confirming_clinician: str | None = None,
    source: str | None = None,
    notes: str | None = None,
) -> None:
    name = (diagnosis_name or "").strip()
    if not name:
        raise ValueError("Diagnosis name is required.")

    conn = get_connection()
    try:
        _ensure_schema(conn)
        conn.execute(
            """INSERT INTO clinical_diagnoses
               (user_id, diagnosis_name, status, confirmed_date, confirming_clinician, source, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(user_id, diagnosis_name) DO UPDATE SET
                 status = excluded.status,
                 confirmed_date = excluded.confirmed_date,
                 confirming_clinician = excluded.confirming_clinician,
                 source = excluded.source,
                 notes = excluded.notes,
                 updated_at = datetime('now')""",
            (
                user_id,
                name,
                status,
                confirmed_date,
                (confirming_clinician or "").strip() or None,
                (source or "").strip() or None,
                (notes or "").strip() or None,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_diagnosis_status(user_id: int, diagnosis_id: int, status: str) -> None:
    conn = get_connection()
    try:
        _ensure_schema(conn)
        conn.execute(
            """UPDATE clinical_diagnoses
               SET status = ?, updated_at = datetime('now')
               WHERE user_id = ? AND id = ?""",
            (status, user_id, diagnosis_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_interventions(user_id: int, active_only: bool = False) -> list[dict]:
    conn = get_connection()
    try:
        _ensure_schema(conn)
        if active_only:
            rows = conn.execute(
                """SELECT * FROM clinical_interventions
                   WHERE user_id = ? AND status = 'active'
                   ORDER BY COALESCE(start_date, ''), updated_at DESC""",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM clinical_interventions
                   WHERE user_id = ?
                   ORDER BY CASE status
                        WHEN 'active' THEN 0
                        WHEN 'paused' THEN 1
                        WHEN 'completed' THEN 2
                        ELSE 3
                   END, COALESCE(start_date, ''), updated_at DESC""",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_intervention(
    user_id: int,
    intervention_type: str,
    name: str,
    dose: str | None = None,
    schedule: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    status: str = "active",
    prescriber: str | None = None,
    notes: str | None = None,
) -> int:
    nm = (name or "").strip()
    if not nm:
        raise ValueError("Intervention name is required.")

    conn = get_connection()
    try:
        _ensure_schema(conn)
        cur = conn.execute(
            """INSERT INTO clinical_interventions
               (user_id, intervention_type, name, dose, schedule, start_date, end_date,
                status, prescriber, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                user_id,
                intervention_type,
                nm,
                (dose or "").strip() or None,
                (schedule or "").strip() or None,
                start_date,
                end_date,
                status,
                (prescriber or "").strip() or None,
                (notes or "").strip() or None,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def update_intervention_status(user_id: int, intervention_id: int, status: str) -> None:
    conn = get_connection()
    try:
        _ensure_schema(conn)
        conn.execute(
            """UPDATE clinical_interventions
               SET status = ?, updated_at = datetime('now')
               WHERE user_id = ? AND id = ?""",
            (status, user_id, intervention_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_test_results(
    user_id: int,
    confirmed_only: bool = True,
    limit: int | None = None,
) -> list[dict]:
    conn = get_connection()
    try:
        _ensure_schema(conn)
        clause = "AND status = 'confirmed'" if confirmed_only else ""
        limit_clause = f"LIMIT {int(limit)}" if limit and limit > 0 else ""
        rows = conn.execute(
            f"""SELECT * FROM clinical_test_results
                WHERE user_id = ? {clause}
                ORDER BY COALESCE(test_date, ''), updated_at DESC
                {limit_clause}""",
            (user_id,),
        ).fetchall()
        out: list[dict] = []
        for r in rows:
            row = dict(r)
            km = row.get("key_metrics_json")
            if km:
                try:
                    row["key_metrics"] = json.loads(km)
                except (json.JSONDecodeError, TypeError):
                    row["key_metrics"] = {}
            else:
                row["key_metrics"] = {}
            out.append(row)
        return out
    finally:
        conn.close()


def save_test_result(
    user_id: int,
    test_type: str,
    test_date: str | None = None,
    status: str = "confirmed",
    summary: str | None = None,
    key_metrics: dict | None = None,
    source_ref: str | None = None,
    risk_flag: str = "unknown",
) -> int:
    test_name = (test_type or "").strip()
    if not test_name:
        raise ValueError("Test type is required.")

    conn = get_connection()
    try:
        _ensure_schema(conn)
        cur = conn.execute(
            """INSERT INTO clinical_test_results
               (user_id, test_type, test_date, status, summary, key_metrics_json, source_ref, risk_flag, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                user_id,
                test_name,
                test_date,
                status,
                (summary or "").strip() or None,
                json.dumps(key_metrics or {}),
                (source_ref or "").strip() or None,
                risk_flag,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def delete_record(user_id: int, table: str, record_id: int) -> None:
    if table not in {"clinical_diagnoses", "clinical_interventions", "clinical_test_results"}:
        raise ValueError("Unsupported table")
    conn = get_connection()
    try:
        _ensure_schema(conn)
        conn.execute(f"DELETE FROM {table} WHERE user_id = ? AND id = ?", (user_id, record_id))
        conn.commit()
    finally:
        conn.close()
