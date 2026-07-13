"""InBody report extraction, storage, and coach-facing interpretation."""

from __future__ import annotations

import io
import json
import re
from datetime import date
from typing import Any

from dateutil import parser as date_parser

from db.database import get_connection


INBODY_METRIC_SPECS: dict[str, dict[str, Any]] = {
    "height_cm": {
        "label": "Height",
        "unit": "cm",
        "tier": "context",
        "trust": "Scale/profile context",
        "coach_use": "Use for trend context and body-size normalization.",
        "labels": ["Height", "Stature"],
        "min": 80,
        "max": 230,
    },
    "weight_kg": {
        "label": "Weight",
        "unit": "kg",
        "tier": "context",
        "trust": "Direct scale value",
        "coach_use": "Useful for trend and energy planning; not a body-composition diagnosis.",
        "labels": ["Weight", "Body Weight"],
        "min": 25,
        "max": 350,
    },
    "total_body_water_l": {
        "label": "Total body water",
        "unit": "L",
        "tier": "Tier 1",
        "trust": "Closest to raw impedance signal",
        "coach_use": "Foundation for most other InBody outputs; compare only under standardized conditions.",
        "labels": ["Total Body Water", "TBW"],
        "min": 10,
        "max": 100,
    },
    "intracellular_water_l": {
        "label": "Intracellular water",
        "unit": "L",
        "tier": "Tier 1",
        "trust": "Water compartment estimate",
        "coach_use": "Rising ICW over repeated standardized scans usually supports real lean-tissue gain.",
        "labels": ["Intracellular Water", "ICW"],
        "min": 5,
        "max": 70,
    },
    "extracellular_water_l": {
        "label": "Extracellular water",
        "unit": "L",
        "tier": "Tier 1",
        "trust": "Water compartment estimate",
        "coach_use": "Rising ECW without ICW gain can reflect fluid retention, inflammation, or recent stress.",
        "labels": ["Extracellular Water", "ECW"],
        "min": 3,
        "max": 40,
    },
    "ecw_tbw_ratio": {
        "label": "ECW/TBW ratio",
        "unit": "ratio",
        "tier": "Tier 1",
        "trust": "High clinical utility",
        "coach_use": "Best InBody signal for fluid balance, swelling, and recovery trend.",
        "labels": ["ECW/TBW", "ECW Ratio", "ECW/TBW Ratio", "ECW / TBW", "ECW/TBW Analysis"],
        "min": 0.25,
        "max": 0.55,
    },
    "phase_angle_deg": {
        "label": "Phase angle",
        "unit": "deg",
        "tier": "Tier 1",
        "trust": "Directly derived from resistance/reactance",
        "coach_use": "A useful cell-health and muscle-quality trend marker; compare to age/sex/context.",
        "labels": ["Phase Angle", "Whole Body Phase Angle", "PhA"],
        "min": 1,
        "max": 15,
    },
    "skeletal_muscle_mass_kg": {
        "label": "Skeletal muscle mass",
        "unit": "kg",
        "tier": "Tier 2",
        "trust": "Derived from body water",
        "coach_use": "Good trend marker when testing conditions are consistent.",
        "labels": ["Skeletal Muscle Mass", "SMM"],
        "min": 5,
        "max": 80,
    },
    "soft_lean_mass_kg": {
        "label": "Soft lean mass",
        "unit": "kg",
        "tier": "Tier 2",
        "trust": "Derived from body water",
        "coach_use": "Track direction over time; hydration changes can distort short-term shifts.",
        "labels": ["Soft Lean Mass", "SLM"],
        "min": 10,
        "max": 160,
    },
    "fat_free_mass_kg": {
        "label": "Fat-free mass",
        "unit": "kg",
        "tier": "Tier 2",
        "trust": "Derived from body water",
        "coach_use": "Use as a trend, not a precise muscle diagnosis.",
        "labels": ["Fat Free Mass", "Fat-Free Mass", "FFM", "Lean Body Mass"],
        "min": 10,
        "max": 180,
    },
    "body_fat_mass_kg": {
        "label": "Body fat mass",
        "unit": "kg",
        "tier": "Tier 3",
        "trust": "Subtraction estimate",
        "coach_use": "Useful for direction of travel; absolute value can differ from DEXA.",
        "labels": ["Body Fat Mass", "BFM"],
        "min": 1,
        "max": 150,
    },
    "body_fat_pct": {
        "label": "Percent body fat",
        "unit": "%",
        "tier": "Tier 3",
        "trust": "Subtraction estimate",
        "coach_use": "Use for trend on the same device; do not overinterpret one scan.",
        "labels": ["Percent Body Fat", "PBF", "Body Fat %", "Body Fat Percentage"],
        "min": 2,
        "max": 75,
    },
    "bmi": {
        "label": "BMI",
        "unit": "kg/m2",
        "tier": "context",
        "trust": "Formula from weight and height",
        "coach_use": "Simple population-level context; waist and composition trend add nuance.",
        "labels": ["BMI", "Body Mass Index"],
        "min": 10,
        "max": 80,
    },
    "bmr_kcal": {
        "label": "Basal metabolic rate",
        "unit": "kcal/day",
        "tier": "Tier 3",
        "trust": "Regression estimate",
        "coach_use": "Rough planning anchor only, not a precise calorie target.",
        "labels": ["Basal Metabolic Rate", "BMR"],
        "min": 500,
        "max": 4000,
    },
    "visceral_fat_area_cm2": {
        "label": "Visceral fat area",
        "unit": "cm2",
        "tier": "Tier 3",
        "trust": "Modeled estimate",
        "coach_use": "Track relative change; CT/MRI is the reference standard for exact area.",
        "labels": ["Visceral Fat Area", "VFA"],
        "min": 1,
        "max": 400,
    },
    "visceral_fat_level": {
        "label": "Visceral fat level",
        "unit": "level",
        "tier": "Tier 3",
        "trust": "Modeled estimate",
        "coach_use": "Trend marker only; pair with waist and cardiometabolic labs.",
        "labels": ["Visceral Fat Level", "Visceral Fat"],
        "min": 1,
        "max": 40,
    },
    "waist_hip_ratio": {
        "label": "Waist-hip ratio",
        "unit": "ratio",
        "tier": "Tier 3",
        "trust": "Often modeled on InBody",
        "coach_use": "Confirm with a tape measure when central adiposity is a key question.",
        "labels": ["Waist-Hip Ratio", "Waist Hip Ratio", "WHR"],
        "min": 0.5,
        "max": 1.5,
    },
    "inbody_score": {
        "label": "InBody score",
        "unit": "score",
        "tier": "Tier 3",
        "trust": "Proprietary composite",
        "coach_use": "Motivational summary only; do not use as a clinical endpoint.",
        "labels": ["InBody Score", "InBodyScore"],
        "min": 1,
        "max": 120,
    },
}


SEGMENT_LABELS = {
    "right_arm": "Right arm",
    "left_arm": "Left arm",
    "trunk": "Trunk",
    "right_leg": "Right leg",
    "left_leg": "Left leg",
}


STANDARDIZATION_CHECKS = [
    "Same machine and testing mode each time.",
    "Same time of day, ideally morning.",
    "Fasted, bladder emptied, and normally hydrated.",
    "No hard exercise immediately before the scan.",
    "No alcohol the day before.",
    "Compare the same point in the training week whenever possible.",
]


def read_pdf_text(pdf_bytes: bytes) -> str:
    """Extract readable text from a digital PDF."""
    from services.document_safety_service import extract_pdf_text_safely

    return extract_pdf_text_safely(pdf_bytes, label="InBody report PDF")


def extract_inbody_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Extract InBody metrics from a readable PDF report."""
    raw_text = read_pdf_text(pdf_bytes)
    extracted = extract_inbody_from_text(raw_text)
    extracted["raw_text"] = raw_text
    return extracted


def extract_inbody_from_text(text: str) -> dict[str, Any]:
    """Extract likely InBody fields from report text using conservative patterns."""
    normalized = _normalize_text(text)
    metrics: dict[str, Any] = {}

    for field, spec in INBODY_METRIC_SPECS.items():
        value = _find_labeled_number(normalized, spec["labels"], spec.get("min"), spec.get("max"))
        if value is not None:
            metrics[field] = _convert_metric_unit(field, value["value"], value.get("unit"))

    metrics = normalize_inbody_metrics(metrics)
    segmental_ecw = _extract_segmental_ecw_ratios(normalized)
    if segmental_ecw:
        metrics["segmental_ecw_ratio"] = segmental_ecw

    return {
        "scan_date": _find_scan_date(normalized),
        "device_model": _find_device_model(normalized),
        "metrics": metrics,
        "extraction_warnings": _build_extraction_warnings(metrics),
    }


def normalize_inbody_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Add derived values that can be computed directly from extracted fields."""
    normalized = dict(metrics)
    tbw = _as_float(normalized.get("total_body_water_l"))
    ecw = _as_float(normalized.get("extracellular_water_l"))
    icw = _as_float(normalized.get("intracellular_water_l"))
    weight = _as_float(normalized.get("weight_kg"))
    height = _as_float(normalized.get("height_cm"))

    if tbw and ecw and not normalized.get("ecw_tbw_ratio"):
        normalized["ecw_tbw_ratio"] = round(ecw / tbw, 3)
    if icw and ecw and not tbw:
        normalized["total_body_water_l"] = round(icw + ecw, 1)
        normalized.setdefault("ecw_tbw_ratio", round(ecw / (icw + ecw), 3))
    if weight and height and not normalized.get("bmi"):
        normalized["bmi"] = round(weight / ((height / 100.0) ** 2), 1)

    return normalized


def build_inbody_coach_summary(
    metrics: dict[str, Any],
    previous_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build coach-facing interpretation from the InBody validation hierarchy."""
    normalized = normalize_inbody_metrics(metrics)
    trust_rows = _build_trust_rows(normalized)
    flags = _build_coach_flags(normalized)
    trend_notes = _build_trend_notes(normalized, previous_metrics or {})

    if not flags:
        flags.append(
            {
                "Priority": "Routine",
                "Area": "Trend review",
                "Signal": "No obvious InBody review flags from the entered values.",
                "Coach action": "Focus on standardized retesting, behavior adherence, and 4-8 week trend direction.",
            }
        )

    talking_points = [
        "Start with test quality before interpretation: hydration, timing, exercise, alcohol, and same device.",
        "Explain the trust hierarchy: phase angle and water compartments first, lean mass second, fat/BMR/score last.",
        "Use ECW/TBW and segmental ECW as the swelling or recovery story, especially after injury.",
        "Use skeletal muscle and lean mass as trend markers, not single-scan proof of muscle gain.",
        "Treat body fat, visceral fat, BMR, and InBody score as estimates that need waist, labs, photos, function, and history.",
    ]

    return {
        "trust_rows": trust_rows,
        "coach_flags": flags,
        "trend_notes": trend_notes,
        "standardization_checks": STANDARDIZATION_CHECKS,
        "talking_points": talking_points,
    }


def save_inbody_report(
    user_id: int,
    scan_date: str,
    metrics: dict[str, Any],
    source_filename: str | None = None,
    device_model: str | None = None,
    raw_text: str | None = None,
    notes: str | None = None,
) -> None:
    """Save an InBody report and sync basic values to Body Metrics."""
    clean_metrics = normalize_inbody_metrics(_drop_empty(metrics))
    conn = get_connection()
    try:
        _ensure_inbody_reports_schema(conn)
        conn.execute(
            """
            INSERT INTO inbody_reports
                (user_id, scan_date, source_filename, device_model, metrics_json, raw_text, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, scan_date) DO UPDATE SET
                source_filename = excluded.source_filename,
                device_model = excluded.device_model,
                metrics_json = excluded.metrics_json,
                raw_text = excluded.raw_text,
                notes = excluded.notes,
                updated_at = datetime('now')
            """,
            (
                user_id,
                scan_date,
                source_filename,
                device_model,
                json.dumps(clean_metrics, sort_keys=True),
                raw_text,
                notes,
            ),
        )
        _sync_inbody_to_body_metrics(conn, user_id, scan_date, clean_metrics)
        conn.commit()
    finally:
        conn.close()


def get_inbody_reports(user_id: int) -> list[dict[str, Any]]:
    """Return saved InBody reports, newest first."""
    conn = get_connection()
    try:
        _ensure_inbody_reports_schema(conn)
        rows = conn.execute(
            """
            SELECT * FROM inbody_reports
            WHERE user_id = ?
            ORDER BY scan_date DESC, updated_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [_row_to_report(row) for row in rows]
    finally:
        conn.close()


def get_latest_inbody_report(user_id: int) -> dict[str, Any] | None:
    """Return the latest saved InBody report."""
    reports = get_inbody_reports(user_id)
    return reports[0] if reports else None


def delete_inbody_report(user_id: int, report_id: int) -> None:
    """Delete a saved InBody report for a user."""
    conn = get_connection()
    try:
        _ensure_inbody_reports_schema(conn)
        conn.execute("DELETE FROM inbody_reports WHERE id = ? AND user_id = ?", (report_id, user_id))
        conn.commit()
    finally:
        conn.close()


def _ensure_inbody_reports_schema(conn) -> None:
    """Create the InBody report table for older deployed SQLite databases."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inbody_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            scan_date TEXT NOT NULL,
            source_filename TEXT,
            device_model TEXT,
            metrics_json TEXT NOT NULL,
            raw_text TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, scan_date)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_inbody_reports_user ON inbody_reports(user_id, scan_date)"
    )


def _normalize_text(text: str) -> str:
    replacements = {
        "\u00a0": " ",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00b2": "2",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def _parse_number(raw: str) -> float | None:
    value = raw.strip().replace(" ", "")
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    value = value.replace(",", "")
    try:
        return float(value)
    except ValueError:
        return None


def _find_labeled_number(
    text: str,
    labels: list[str],
    minimum: float | None = None,
    maximum: float | None = None,
) -> dict[str, Any] | None:
    units = r"(kg|lbs|lb|l|L|%|kcal|cm2|deg|degree|degrees|score)?"
    for label in labels:
        escaped = re.escape(label)
        patterns = [
            rf"(?i)(?:^|[^A-Za-z]){escaped}(?:\s*\([^)]*\))?.{{0,70}}?(-?\d+(?:[\.,]\d+)?)\s*{units}",
            rf"(?i)(-?\d+(?:[\.,]\d+)?)\s*{units}.{{0,30}}?{escaped}",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                value = _parse_number(match.group(1))
                if value is None:
                    continue
                if minimum is not None and value < minimum:
                    continue
                if maximum is not None and value > maximum:
                    continue
                unit = None
                if len(match.groups()) >= 2 and match.group(2):
                    unit = match.group(2)
                return {"value": value, "unit": unit}
    return None


def _convert_metric_unit(field: str, value: float, unit: str | None) -> float:
    unit_l = (unit or "").lower()
    if field.endswith("_kg") and unit_l in {"lb", "lbs"}:
        return round(value * 0.45359237, 1)
    return round(value, 3 if "ratio" in field else 1)


def _find_scan_date(text: str) -> str | None:
    date_pattern = r"([0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2}|[0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{4})"
    for label in ("Test Date", "Scan Date", "Measurement Date", "Date of Test", "Date"):
        match = re.search(rf"(?i){re.escape(label)}.{{0,35}}?{date_pattern}", text)
        if match:
            parsed = _parse_date(match.group(1))
            if parsed:
                return parsed
    return None


def _parse_date(value: str) -> str | None:
    try:
        parsed = date_parser.parse(value, dayfirst=False, fuzzy=True)
        if 1990 <= parsed.year <= date.today().year + 1:
            return parsed.date().isoformat()
    except (ValueError, OverflowError):
        return None
    return None


def _find_device_model(text: str) -> str | None:
    match = re.search(r"(?i)\bInBody\s*([0-9]{2,4}[A-Za-z]?)\b", text)
    if match:
        return f"InBody {match.group(1)}"
    return None


def _extract_segmental_ecw_ratios(text: str) -> dict[str, float]:
    segmental: dict[str, float] = {}
    for key, label in SEGMENT_LABELS.items():
        value = _find_labeled_number(
            text,
            [f"{label} ECW/TBW", f"{label} ECW Ratio", f"ECW/TBW {label}", f"ECW Ratio {label}"],
            0.25,
            0.55,
        )
        if value is not None:
            segmental[key] = round(value["value"], 3)
    return segmental


def _build_extraction_warnings(metrics: dict[str, Any]) -> list[str]:
    warnings = []
    if not metrics:
        warnings.append("No standard InBody metrics were detected. Enter values manually or upload a text-readable report.")
    if "ecw_tbw_ratio" not in metrics:
        warnings.append("ECW/TBW was not detected; this is one of the highest-value coach metrics.")
    if "phase_angle_deg" not in metrics:
        warnings.append("Phase angle was not detected; add it manually if the report includes it.")
    return warnings


def _build_trust_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field, spec in INBODY_METRIC_SPECS.items():
        if field not in metrics:
            continue
        rows.append(
            {
                "Metric": spec["label"],
                "Value": _format_metric_value(field, metrics[field]),
                "Tier": spec["tier"],
                "Trust": spec["trust"],
                "Coach use": spec["coach_use"],
            }
        )
    return rows


def _build_coach_flags(metrics: dict[str, Any]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    ecw_ratio = _as_float(metrics.get("ecw_tbw_ratio"))
    phase_angle = _as_float(metrics.get("phase_angle_deg"))
    visceral_area = _as_float(metrics.get("visceral_fat_area_cm2"))
    visceral_level = _as_float(metrics.get("visceral_fat_level"))
    inbody_score = _as_float(metrics.get("inbody_score"))
    body_fat_pct = _as_float(metrics.get("body_fat_pct"))
    segmental = metrics.get("segmental_ecw_ratio") or {}

    if ecw_ratio is None:
        flags.append(
            {
                "Priority": "High",
                "Area": "Missing Tier 1 signal",
                "Signal": "ECW/TBW ratio is missing.",
                "Coach action": "Add ECW/TBW from the report if available; it is central to fluid and recovery interpretation.",
            }
        )
    elif ecw_ratio >= 0.400:
        flags.append(
            {
                "Priority": "High",
                "Area": "Fluid balance",
                "Signal": f"Whole-body ECW/TBW is {ecw_ratio:.3f}.",
                "Coach action": "Review edema, injury, inflammation, recent hard training, sodium, sleep, and medications; persistent elevation deserves clinician review.",
            }
        )
    elif ecw_ratio >= 0.390:
        flags.append(
            {
                "Priority": "Medium",
                "Area": "Fluid balance",
                "Signal": f"Whole-body ECW/TBW is near the upper reference band at {ecw_ratio:.3f}.",
                "Coach action": "Retest under standardized conditions and compare segmental ratios before calling it body-composition change.",
            }
        )
    elif ecw_ratio < 0.360:
        flags.append(
            {
                "Priority": "Medium",
                "Area": "Hydration context",
                "Signal": f"Whole-body ECW/TBW is below the usual reference band at {ecw_ratio:.3f}.",
                "Coach action": "Check dehydration, fasting duration, diuretics, and test timing before interpreting lean or fat shifts.",
            }
        )

    if segmental:
        segment_values = {key: _as_float(value) for key, value in segmental.items()}
        values = [value for value in segment_values.values() if value is not None]
        elevated = [SEGMENT_LABELS[key] for key, value in segment_values.items() if value is not None and value >= 0.390]
        if elevated:
            flags.append(
                {
                    "Priority": "Medium",
                    "Area": "Segmental ECW",
                    "Signal": "Elevated segmental ECW/TBW: " + ", ".join(elevated) + ".",
                    "Coach action": "Ask about local injury, soreness, swelling, or asymmetrical loading; trend against the partner limb.",
                }
            )
        if len(values) >= 2 and max(values) - min(values) >= 0.010:
            flags.append(
                {
                    "Priority": "Medium",
                    "Area": "Side-to-side recovery",
                    "Signal": f"Segmental ECW/TBW spread is {max(values) - min(values):.3f}.",
                    "Coach action": "Use this as a recovery clue, then confirm with pain, range of motion, girth, and functional testing.",
                }
            )

    if phase_angle is None:
        flags.append(
            {
                "Priority": "Medium",
                "Area": "Missing Tier 1 signal",
                "Signal": "Phase angle is missing.",
                "Coach action": "Add phase angle manually if available; it is the most defensible single InBody trend marker.",
            }
        )
    elif phase_angle < 5.0:
        flags.append(
            {
                "Priority": "Medium",
                "Area": "Cell health trend",
                "Signal": f"Phase angle is {phase_angle:.1f} deg.",
                "Coach action": "Interpret by age, sex, body size, and disease context; review nutrition, resistance training, inflammation, and sleep trend.",
            }
        )
    elif phase_angle >= 7.0:
        flags.append(
            {
                "Priority": "Routine",
                "Area": "Cell health trend",
                "Signal": f"Phase angle is {phase_angle:.1f} deg.",
                "Coach action": "Favorable marker in many adults; focus on maintaining trend rather than chasing a single target.",
            }
        )

    if visceral_area is not None and visceral_area >= 100:
        flags.append(
            {
                "Priority": "Medium",
                "Area": "Central adiposity",
                "Signal": f"Modeled visceral fat area is {visceral_area:.0f} cm2.",
                "Coach action": "Confirm with waist trend and cardiometabolic labs; use as a relative-change marker, not CT-level precision.",
            }
        )
    elif visceral_level is not None and visceral_level >= 10:
        flags.append(
            {
                "Priority": "Medium",
                "Area": "Central adiposity",
                "Signal": f"Modeled visceral fat level is {visceral_level:.0f}.",
                "Coach action": "Pair with waist, triglycerides, glucose, blood pressure, and behavior adherence.",
            }
        )

    if body_fat_pct is not None:
        flags.append(
            {
                "Priority": "Routine",
                "Area": "Body fat estimate",
                "Signal": f"Body fat is estimated at {body_fat_pct:.1f}%.",
                "Coach action": "Use same-device trend; explain that hydration and upstream lean-mass estimates can shift this value.",
            }
        )

    if inbody_score is not None:
        flags.append(
            {
                "Priority": "Routine",
                "Area": "InBody score",
                "Signal": f"InBody score is {inbody_score:.0f}.",
                "Coach action": "Use only as motivational shorthand; do not use it as a validated clinical score.",
            }
        )

    return flags


def _build_trend_notes(metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    comparisons = [
        ("phase_angle_deg", "Phase angle", "deg"),
        ("ecw_tbw_ratio", "ECW/TBW", ""),
        ("intracellular_water_l", "ICW", "L"),
        ("skeletal_muscle_mass_kg", "Skeletal muscle mass", "kg"),
        ("body_fat_pct", "Body fat", "%"),
        ("weight_kg", "Weight", "kg"),
    ]
    for field, label, unit in comparisons:
        current = _as_float(metrics.get(field))
        previous = _as_float(previous_metrics.get(field))
        if current is None or previous is None:
            continue
        delta = current - previous
        if abs(delta) < (0.001 if field == "ecw_tbw_ratio" else 0.05):
            continue
        suffix = unit
        if field == "ecw_tbw_ratio":
            notes.append(f"{label} changed by {delta:+.3f} since the prior report.")
        else:
            notes.append(f"{label} changed by {delta:+.1f} {suffix} since the prior report.")
    return notes


def _format_metric_value(field: str, value: Any) -> str:
    numeric = _as_float(value)
    spec = INBODY_METRIC_SPECS.get(field, {})
    unit = spec.get("unit", "")
    if numeric is None:
        return "--"
    if "ratio" in field or unit == "ratio":
        return f"{numeric:.3f}"
    if field == "inbody_score":
        return f"{numeric:.0f}"
    if unit == "%":
        return f"{numeric:.1f}%"
    if unit:
        return f"{numeric:.1f} {unit}"
    return f"{numeric:.1f}"


def _sync_inbody_to_body_metrics(conn, user_id: int, scan_date: str, metrics: dict[str, Any]) -> None:
    weight = _as_float(metrics.get("weight_kg"))
    height = _as_float(metrics.get("height_cm"))
    body_fat = _as_float(metrics.get("body_fat_pct"))
    if weight is None and height is None and body_fat is None:
        return

    existing = conn.execute(
        "SELECT id, notes FROM body_metrics WHERE user_id = ? AND log_date = ?",
        (user_id, scan_date),
    ).fetchone()
    note = "Auto-populated from InBody report"
    if existing:
        fields = []
        values: list[Any] = []
        if weight is not None:
            fields.append("weight_kg = ?")
            values.append(weight)
        if height is not None:
            fields.append("height_cm = ?")
            values.append(height)
        if body_fat is not None:
            fields.append("body_fat_pct = ?")
            values.append(body_fat)
        existing_note = existing["notes"] or ""
        if note.lower() not in existing_note.lower():
            fields.append("notes = ?")
            values.append((existing_note + "; " + note).strip("; "))
        if fields:
            values.extend([existing["id"], user_id])
            conn.execute(
                f"UPDATE body_metrics SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
                values,
            )
    else:
        conn.execute(
            """
            INSERT INTO body_metrics
                (user_id, log_date, weight_kg, height_cm, body_fat_pct, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, scan_date, weight, height, body_fat, note),
        )


def _row_to_report(row) -> dict[str, Any]:
    report = dict(row)
    try:
        report["metrics"] = json.loads(report.get("metrics_json") or "{}")
    except json.JSONDecodeError:
        report["metrics"] = {}
    return report


def _drop_empty(metrics: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in metrics.items():
        if isinstance(value, dict):
            nested = _drop_empty(value)
            if nested:
                clean[key] = nested
            continue
        if value is None or value == "":
            continue
        clean[key] = value
    return clean


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
