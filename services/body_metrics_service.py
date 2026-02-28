"""Service for body metrics tracking — weight, measurements, BMI, composition, DEXA."""

from pathlib import Path
from db.database import get_connection
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


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


# ══════════════════════════════════════════════════════════════════════════════
# DEXA Scan Management
# ══════════════════════════════════════════════════════════════════════════════

# All columns in the dexa_scans table (excluding id, user_id, scan_date, created_at)
_DEXA_FIELDS = [
    "lab_name", "scanner_model",
    "weight_kg", "total_fat_pct", "total_fat_g",
    "lean_mass_g", "bone_mass_g", "bmi",
    "bmd_g_cm2", "t_score", "z_score",
    "vat_mass_g", "vat_volume_cm3", "vat_area_cm2",
    "android_fat_pct", "gynoid_fat_pct", "ag_ratio",
    "left_arm_fat_pct", "right_arm_fat_pct", "trunk_fat_pct",
    "left_leg_fat_pct", "right_leg_fat_pct",
    "left_arm_lean_g", "right_arm_lean_g", "trunk_lean_g",
    "left_leg_lean_g", "right_leg_lean_g",
    "alm_kg", "alm_h2", "ffmi",
    "notes", "source",
]


def save_dexa_scan(user_id, scan_date, **kwargs):
    """Insert or update a DEXA scan. Computes derived indices automatically."""
    # ── Derived indices ──────────────────────────────────────────────────
    arm_lean = (kwargs.get("left_arm_lean_g") or 0) + (kwargs.get("right_arm_lean_g") or 0)
    leg_lean = (kwargs.get("left_leg_lean_g") or 0) + (kwargs.get("right_leg_lean_g") or 0)
    if arm_lean > 0 and leg_lean > 0:
        alm_g = arm_lean + leg_lean
        kwargs["alm_kg"] = round(alm_g / 1000, 2)
        height = get_latest_height(user_id)
        if height and height > 0:
            kwargs["alm_h2"] = round((alm_g / 1000) / (height / 100) ** 2, 2)

    lean_g = kwargs.get("lean_mass_g")
    if lean_g:
        height = get_latest_height(user_id)
        if height and height > 0:
            kwargs["ffmi"] = round((lean_g / 1000) / (height / 100) ** 2, 1)

    # ── Build dynamic INSERT ─────────────────────────────────────────────
    provided = {k: kwargs[k] for k in _DEXA_FIELDS if k in kwargs and kwargs[k] is not None}
    fields = ["user_id", "scan_date"] + list(provided.keys())
    values = [user_id, scan_date] + list(provided.values())
    placeholders = ", ".join(["?"] * len(fields))
    field_names = ", ".join(fields)
    update_clause = ", ".join(f"{f} = excluded.{f}" for f in provided)

    conn = get_connection()
    try:
        conn.execute(
            f"INSERT INTO dexa_scans ({field_names}) VALUES ({placeholders})"
            f" ON CONFLICT(user_id, scan_date) DO UPDATE SET {update_clause}",
            values,
        )
        conn.commit()
    finally:
        conn.close()

    # Cross-populate body_metrics
    if kwargs.get("total_fat_pct") or kwargs.get("weight_kg"):
        _sync_dexa_to_body_metrics(user_id, scan_date, kwargs)


def get_dexa_history(user_id):
    """Return all DEXA scans for a user, sorted by scan_date ASC."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM dexa_scans WHERE user_id = ? ORDER BY scan_date ASC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_latest_dexa(user_id):
    """Return the most recent DEXA scan."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM dexa_scans WHERE user_id = ? ORDER BY scan_date DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_dexa_scan(user_id, scan_id):
    """Delete a DEXA scan entry."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM dexa_scans WHERE id = ? AND user_id = ?", (scan_id, user_id))
        conn.commit()
    finally:
        conn.close()


def extract_dexa_from_pdf(pdf_bytes: bytes) -> dict:
    """Use Claude to extract DEXA scan values from a PDF report.

    Returns a dict with all recognized DEXA fields (nulls for unavailable).
    """
    import anthropic
    import json
    import re
    import io

    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pdf_text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc

    if len(pdf_text) < 20:
        raise ValueError("PDF has no readable text — may be a scanned image.")

    prompt = (
        "Below is text from a DEXA (DXA) body composition scan report.\n"
        "Extract ALL available values and return ONLY a valid JSON object.\n\n"
        "{\n"
        '  "scan_date": "YYYY-MM-DD",\n'
        '  "lab_name": "string or null",\n'
        '  "scanner_model": "string or null",\n'
        '  "weight_kg": number, "total_fat_pct": number, "total_fat_g": number,\n'
        '  "lean_mass_g": number, "bone_mass_g": number, "bmi": number,\n'
        '  "bmd_g_cm2": number, "t_score": number, "z_score": number,\n'
        '  "vat_mass_g": number, "vat_volume_cm3": number, "vat_area_cm2": number,\n'
        '  "android_fat_pct": number, "gynoid_fat_pct": number, "ag_ratio": number,\n'
        '  "left_arm_fat_pct": number, "right_arm_fat_pct": number,\n'
        '  "trunk_fat_pct": number,\n'
        '  "left_leg_fat_pct": number, "right_leg_fat_pct": number,\n'
        '  "left_arm_lean_g": number, "right_arm_lean_g": number,\n'
        '  "trunk_lean_g": number,\n'
        '  "left_leg_lean_g": number, "right_leg_lean_g": number\n'
        "}\n\n"
        "Rules:\n"
        "- Convert all masses to grams EXCEPT weight_kg\n"
        "- Percentages as plain numbers (9.5 not '9.5%')\n"
        "- Commas may be decimal separators (European format)\n"
        "- If arms are reported combined, split evenly for left/right\n"
        "- BMC = bone_mass_g, BMD = bmd_g_cm2\n"
        "- Use null for unavailable values\n"
        "- Return ONLY the JSON object\n\n"
        "--- DEXA REPORT TEXT ---\n"
        f"{pdf_text}"
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_match:
        raise ValueError(f"Claude did not return JSON. Response: {raw[:400]}")

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse error: {exc}. Raw: {raw[:400]}") from exc


def _sync_dexa_to_body_metrics(user_id, scan_date, dexa_data):
    """Auto-populate body_metrics with DEXA data (body_fat_pct, weight)."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM body_metrics WHERE user_id = ? AND log_date = ?",
            (user_id, scan_date),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE body_metrics SET body_fat_pct = ? WHERE id = ?",
                (dexa_data.get("total_fat_pct"), existing["id"]),
            )
        else:
            weight = dexa_data.get("weight_kg")
            if weight:
                height = get_latest_height(user_id)
                conn.execute(
                    """INSERT OR IGNORE INTO body_metrics
                       (user_id, log_date, weight_kg, height_cm, body_fat_pct, notes)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, scan_date, weight, height,
                     dexa_data.get("total_fat_pct"), "Auto-populated from DEXA scan"),
                )
        conn.commit()
    finally:
        conn.close()
