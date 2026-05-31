"""CPET report extraction, storage, and coach-facing interpretation."""

from __future__ import annotations

import io
import json
import re
from datetime import date
from typing import Any

from dateutil import parser as date_parser

from db.database import get_connection


CPET_CONTEXTS = {
    "general": "General health / lifestyle medicine",
    "endurance": "Endurance athlete",
    "hybrid": "Hybrid athlete (HYROX / CrossFit)",
    "cardiology": "Cardiology review",
}


CPET_METRIC_SPECS: dict[str, dict[str, Any]] = {
    "age_years": {
        "label": "Age",
        "unit": "years",
        "layer": "Context",
        "coach_use": "Used to estimate predicted HR if the report does not provide one.",
        "labels": ["Age"],
        "min": 10,
        "max": 100,
    },
    "weight_kg": {
        "label": "Weight",
        "unit": "kg",
        "layer": "Context",
        "coach_use": "Used to convert absolute VO2 to relative VO2 when needed.",
        "labels": ["Weight", "Body Weight"],
        "min": 25,
        "max": 250,
    },
    "test_duration_min": {
        "label": "Incremental duration",
        "unit": "min",
        "layer": "Quality",
        "coach_use": "A well-sized ramp usually reaches peak in roughly 8-12 min of incremental work.",
        "labels": ["Test Duration", "Exercise Duration", "Ramp Duration", "Time to Exhaustion"],
        "min": 2,
        "max": 40,
    },
    "peak_vo2_ml_kg_min": {
        "label": "Peak VO2",
        "unit": "mL/kg/min",
        "layer": "Measured",
        "coach_use": "Aerobic ceiling. Interpret only after checking effort and the client's population.",
        "labels": ["Peak VO2", "VO2peak", "VO2 max", "VO2max", "Peak oxygen uptake"],
        "min": 5,
        "max": 100,
    },
    "peak_vo2_l_min": {
        "label": "Peak VO2 absolute",
        "unit": "L/min",
        "layer": "Measured",
        "coach_use": "Absolute oxygen uptake; useful for larger athletes and rowing/cycling contexts.",
        "labels": ["Peak VO2 absolute", "Absolute VO2", "VO2 L/min", "Peak oxygen uptake absolute"],
        "min": 0.5,
        "max": 9.0,
    },
    "peak_vo2_pct_pred": {
        "label": "Peak VO2 % predicted",
        "unit": "%",
        "layer": "Interpreted",
        "coach_use": "Prediction-equation dependent; athlete interpretation needs a higher bar than general population normal.",
        "labels": ["Peak VO2 % predicted", "% predicted peak VO2", "VO2 % predicted", "VO2peak % predicted"],
        "min": 10,
        "max": 250,
    },
    "peak_rer": {
        "label": "Peak RER",
        "unit": "ratio",
        "layer": "Derived",
        "coach_use": "Primary effort gate for peak VO2; thresholds and VE/VCO2 remain useful if effort is submaximal.",
        "labels": ["Peak RER", "RER peak", "Respiratory Exchange Ratio", "Peak respiratory exchange ratio"],
        "min": 0.6,
        "max": 1.6,
    },
    "rest_hr_bpm": {
        "label": "Resting HR",
        "unit": "bpm",
        "layer": "Measured",
        "coach_use": "Needed for chronotropic index if available.",
        "labels": ["Resting HR", "Rest HR", "HR rest"],
        "min": 25,
        "max": 140,
    },
    "peak_hr_bpm": {
        "label": "Peak HR",
        "unit": "bpm",
        "layer": "Measured",
        "coach_use": "Effort and chronotropic response context; medication status matters.",
        "labels": ["Peak HR", "HR peak", "Maximum HR", "Max HR"],
        "min": 60,
        "max": 230,
    },
    "predicted_hr_bpm": {
        "label": "Predicted HR",
        "unit": "bpm",
        "layer": "Interpreted",
        "coach_use": "Used for effort context. Tanaka estimate is 208 - 0.7 x age when report value is absent.",
        "labels": ["Predicted HR", "Predicted Max HR", "Age predicted HR", "Age-predicted HR"],
        "min": 80,
        "max": 230,
    },
    "hr_pct_pred": {
        "label": "Peak HR % predicted",
        "unit": "%",
        "layer": "Interpreted",
        "coach_use": "Secondary effort marker; beta-blockers and chronotropic disease change interpretation.",
        "labels": ["Peak HR % predicted", "HR % predicted", "% predicted HR"],
        "min": 30,
        "max": 130,
    },
    "vt1_vo2_ml_kg_min": {
        "label": "VT1 VO2",
        "unit": "mL/kg/min",
        "layer": "Interpreted",
        "coach_use": "First threshold; anchors easy/moderate training and is relatively effort independent.",
        "labels": ["VT1 VO2", "AT VO2", "Anaerobic Threshold VO2", "GET VO2", "LT1 VO2"],
        "min": 3,
        "max": 90,
    },
    "vt1_hr_bpm": {
        "label": "VT1 HR",
        "unit": "bpm",
        "layer": "Interpreted",
        "coach_use": "Upper boundary of easy aerobic work when measured in the same modality.",
        "labels": ["VT1 HR", "AT HR", "GET HR", "LT1 HR", "Aerobic Threshold HR"],
        "min": 50,
        "max": 220,
    },
    "vt1_power_w": {
        "label": "VT1 power",
        "unit": "W",
        "layer": "Interpreted",
        "coach_use": "Best cycling anchor for Zone 1 ceiling when measured directly.",
        "labels": ["VT1 Power", "AT Power", "GET Power", "LT1 Power", "Power at VT1"],
        "min": 20,
        "max": 700,
    },
    "vt1_speed_kmh": {
        "label": "VT1 speed",
        "unit": "km/h",
        "layer": "Interpreted",
        "coach_use": "Running pace anchor if treadmill protocol and calibration are appropriate.",
        "labels": ["VT1 Speed", "AT Speed", "GET Speed", "LT1 Speed", "Speed at VT1"],
        "min": 3,
        "max": 30,
    },
    "vt2_vo2_ml_kg_min": {
        "label": "VT2 VO2",
        "unit": "mL/kg/min",
        "layer": "Interpreted",
        "coach_use": "Second threshold / respiratory compensation point; separates heavy from severe work.",
        "labels": ["VT2 VO2", "RCP VO2", "LT2 VO2", "Respiratory Compensation Point VO2"],
        "min": 5,
        "max": 95,
    },
    "vt2_hr_bpm": {
        "label": "VT2 HR",
        "unit": "bpm",
        "layer": "Interpreted",
        "coach_use": "Upper heavy-domain anchor; HR drift still matters during long work.",
        "labels": ["VT2 HR", "RCP HR", "LT2 HR", "Anaerobic Threshold 2 HR"],
        "min": 60,
        "max": 230,
    },
    "vt2_power_w": {
        "label": "VT2 power",
        "unit": "W",
        "layer": "Interpreted",
        "coach_use": "Cycling severe-domain boundary when measured directly.",
        "labels": ["VT2 Power", "RCP Power", "LT2 Power", "Power at VT2"],
        "min": 30,
        "max": 800,
    },
    "vt2_speed_kmh": {
        "label": "VT2 speed",
        "unit": "km/h",
        "layer": "Interpreted",
        "coach_use": "Running severe-domain boundary when measured directly.",
        "labels": ["VT2 Speed", "RCP Speed", "LT2 Speed", "Speed at VT2"],
        "min": 4,
        "max": 35,
    },
    "ve_vco2_slope": {
        "label": "VE/VCO2 slope",
        "unit": "slope",
        "layer": "Derived",
        "coach_use": "Ventilatory efficiency; a major prognostic marker in cardiology and useful dyspnea context.",
        "labels": ["VE/VCO2 slope", "VE VCO2 slope", "Ventilatory efficiency slope", "VE/VCO2"],
        "min": 10,
        "max": 80,
    },
    "ve_vco2_nadir": {
        "label": "VE/VCO2 nadir",
        "unit": "ratio",
        "layer": "Derived",
        "coach_use": "High nadir supports ventilatory inefficiency; interpret with PETCO2 and phenotype.",
        "labels": ["VE/VCO2 nadir", "VE VCO2 nadir", "VE/VCO2 minimum"],
        "min": 10,
        "max": 80,
    },
    "breathing_reserve_pct": {
        "label": "Breathing reserve",
        "unit": "%",
        "layer": "Derived",
        "coach_use": "Low reserve suggests ventilatory limitation; in isolated HF it is often preserved.",
        "labels": ["Breathing Reserve", "BR", "Ventilatory Reserve"],
        "min": -20,
        "max": 80,
    },
    "peak_ve_l_min": {
        "label": "Peak VE",
        "unit": "L/min",
        "layer": "Measured",
        "coach_use": "Used with MVV to estimate ventilatory reserve.",
        "labels": ["Peak VE", "VE peak", "Minute ventilation peak", "Peak ventilation"],
        "min": 10,
        "max": 300,
    },
    "mvv_l_min": {
        "label": "MVV",
        "unit": "L/min",
        "layer": "Measured/estimated",
        "coach_use": "Max voluntary ventilation, often estimated from FEV1 x 40.",
        "labels": ["MVV", "Maximum voluntary ventilation"],
        "min": 20,
        "max": 300,
    },
    "o2_pulse_ml_beat": {
        "label": "O2 pulse",
        "unit": "mL/beat",
        "layer": "Derived",
        "coach_use": "VO2/HR; a stroke-volume x extraction surrogate, not a direct cardiac output measurement.",
        "labels": ["O2 pulse", "Oxygen pulse", "VO2/HR"],
        "min": 2,
        "max": 40,
    },
    "o2_pulse_pct_pred": {
        "label": "O2 pulse % predicted",
        "unit": "%",
        "layer": "Interpreted",
        "coach_use": "Low value or early flattening can support an oxygen-delivery limitation pattern.",
        "labels": ["O2 pulse % predicted", "Oxygen pulse % predicted", "% predicted O2 pulse"],
        "min": 20,
        "max": 200,
    },
    "vo2_wr_slope_ml_min_w": {
        "label": "VO2/work-rate slope",
        "unit": "mL/min/W",
        "layer": "Derived",
        "coach_use": "Normally around 10 mL/min/W; flattening supports oxygen-delivery limitation.",
        "labels": ["VO2/work-rate slope", "VO2/WR slope", "VO2 work rate slope", "VO2-WR slope"],
        "min": 3,
        "max": 20,
    },
    "petco2_at_mmhg": {
        "label": "PETCO2 at AT",
        "unit": "mmHg",
        "layer": "Measured",
        "coach_use": "Low or blunted PETCO2 supports hyperventilation, dead space, HF severity, or pulmonary vascular pattern.",
        "labels": ["PETCO2 at AT", "PETCO2 AT", "PETCO2 anaerobic threshold"],
        "min": 10,
        "max": 60,
    },
    "petco2_peak_mmhg": {
        "label": "Peak PETCO2",
        "unit": "mmHg",
        "layer": "Measured",
        "coach_use": "Read with VE/VCO2 slope and oxygen saturation.",
        "labels": ["Peak PETCO2", "PETCO2 peak"],
        "min": 10,
        "max": 60,
    },
    "spo2_nadir_pct": {
        "label": "SpO2 nadir",
        "unit": "%",
        "layer": "Measured",
        "coach_use": "Exercise desaturation changes the safety and referral conversation.",
        "labels": ["SpO2 nadir", "Minimum SpO2", "Lowest SpO2", "Oxygen saturation nadir"],
        "min": 50,
        "max": 100,
    },
    "oues": {
        "label": "OUES",
        "unit": "slope",
        "layer": "Derived",
        "coach_use": "Submaximal cardiorespiratory reserve marker; useful when peak effort is limited.",
        "labels": ["OUES", "Oxygen uptake efficiency slope"],
        "min": 0.2,
        "max": 8,
    },
    "peak_lactate_mmol_l": {
        "label": "Peak lactate",
        "unit": "mmol/L",
        "layer": "Measured",
        "coach_use": "Effort and anaerobic contribution context; not all CPETs sample lactate.",
        "labels": ["Peak lactate", "Lactate peak", "Blood lactate peak"],
        "min": 0.5,
        "max": 25,
    },
    "fatmax_g_min": {
        "label": "Max fat oxidation",
        "unit": "g/min",
        "layer": "Derived",
        "coach_use": "Only valid during submaximal steady-state stages where RER is not inflated by buffering.",
        "labels": ["Max fat oxidation", "MFO", "FatMax oxidation", "Fat oxidation max"],
        "min": 0.01,
        "max": 2.5,
    },
    "fatmax_vo2_pct": {
        "label": "FatMax intensity",
        "unit": "% VO2max",
        "layer": "Interpreted",
        "coach_use": "Population and protocol dependent; not a universal Zone 2 prescription.",
        "labels": ["FatMax %VO2max", "FatMax intensity", "MFO intensity"],
        "min": 20,
        "max": 90,
    },
}


STANDARDIZATION_CHECKS = [
    "Same lab, metabolic cart, ergometer, ramp protocol, and software when possible.",
    "Ramp sized for roughly 8-12 min of incremental work.",
    "Daily gas and volume calibration documented.",
    "Same breath averaging method, commonly around 30 s.",
    "Similar training week, no hard training the day before.",
    "Consistent food, hydration, caffeine, alcohol, smoking, and medication timing.",
    "Same threshold method or experienced reader for serial comparisons.",
]


NINE_PANEL_ROWS = [
    {"Panel": "1", "Read": "VE vs work", "Coach flag": "Ventilatory demand; plateau near MVV suggests ventilatory ceiling."},
    {"Panel": "2", "Read": "HR and O2 pulse", "Coach flag": "Chronotropy and stroke-volume surrogate; early O2-pulse flattening is a referral clue."},
    {"Panel": "3", "Read": "VO2 and VCO2", "Coach flag": "Peak VO2, VO2/work slope, and whether oxygen uptake rose normally with work."},
    {"Panel": "4", "Read": "VE vs VCO2", "Coach flag": "VE/VCO2 slope; high values suggest inefficient ventilation or cardiopulmonary disease context."},
    {"Panel": "5", "Read": "V-slope", "Coach flag": "Primary VT1/AT placement; should be visually checked."},
    {"Panel": "6", "Read": "Ventilatory equivalents", "Coach flag": "Confirms VT1 and VT2; high VE/VCO2 nadir supports inefficiency."},
    {"Panel": "7", "Read": "Tidal volume vs VE", "Coach flag": "Mechanics and breathing reserve; BR <15% suggests ventilatory limitation."},
    {"Panel": "8", "Read": "RER", "Coach flag": "Effort gate; peak RER >=1.10 supports adequate peak effort."},
    {"Panel": "9", "Read": "End-tidal gases", "Coach flag": "PETCO2 pattern helps interpret hyperventilation, dead space, HF, or pulmonary vascular physiology."},
]


def read_pdf_text(pdf_bytes: bytes) -> str:
    """Extract readable text from a digital CPET PDF."""
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc

    if len(text) < 20:
        raise ValueError("PDF has no readable text. It may be a scanned image.")
    return text


def extract_cpet_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    raw_text = read_pdf_text(pdf_bytes)
    extracted = extract_cpet_from_text(raw_text)
    extracted["raw_text"] = raw_text
    return extracted


def extract_cpet_from_text(text: str) -> dict[str, Any]:
    """Extract likely CPET values from report text using conservative label patterns."""
    normalized = _normalize_text(text)
    metrics: dict[str, Any] = {}

    for field, spec in CPET_METRIC_SPECS.items():
        value = _find_labeled_number(normalized, spec["labels"], spec.get("min"), spec.get("max"))
        if value is not None:
            metrics[field] = _round_metric(field, value["value"])

    metrics = normalize_cpet_metrics(metrics)
    return {
        "test_date": _find_test_date(normalized),
        "test_modality": _find_test_modality(normalized),
        "protocol": _find_protocol(normalized),
        "metrics": metrics,
        "extraction_warnings": _build_extraction_warnings(metrics),
    }


def normalize_cpet_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Add directly derived CPET values when enough inputs are present."""
    normalized = dict(metrics)
    age = _as_float(normalized.get("age_years"))
    weight = _as_float(normalized.get("weight_kg"))
    peak_vo2_rel = _as_float(normalized.get("peak_vo2_ml_kg_min"))
    peak_vo2_abs = _as_float(normalized.get("peak_vo2_l_min"))
    peak_hr = _as_float(normalized.get("peak_hr_bpm"))
    pred_hr = _as_float(normalized.get("predicted_hr_bpm"))
    rest_hr = _as_float(normalized.get("rest_hr_bpm"))
    peak_ve = _as_float(normalized.get("peak_ve_l_min"))
    mvv = _as_float(normalized.get("mvv_l_min"))

    if pred_hr is None and age is not None:
        pred_hr = round(208 - 0.7 * age)
        normalized["predicted_hr_bpm"] = pred_hr
    if peak_hr is not None and pred_hr:
        normalized.setdefault("hr_pct_pred", round(peak_hr / pred_hr * 100, 1))
        normalized.setdefault("hr_reserve_bpm", round(pred_hr - peak_hr, 1))
    if peak_hr is not None and pred_hr and rest_hr is not None and pred_hr > rest_hr:
        normalized.setdefault("chronotropic_index", round((peak_hr - rest_hr) / (pred_hr - rest_hr), 2))
    if peak_vo2_abs is None and peak_vo2_rel is not None and weight:
        normalized["peak_vo2_l_min"] = round((peak_vo2_rel * weight) / 1000.0, 2)
    if peak_vo2_rel is None and peak_vo2_abs is not None and weight:
        peak_vo2_rel = round((peak_vo2_abs * 1000.0) / weight, 1)
        normalized["peak_vo2_ml_kg_min"] = peak_vo2_rel
    if mvv and peak_ve and "breathing_reserve_pct" not in normalized:
        normalized["breathing_reserve_pct"] = round((mvv - peak_ve) / mvv * 100, 1)
    if peak_vo2_abs and peak_hr and "o2_pulse_ml_beat" not in normalized:
        normalized["o2_pulse_ml_beat"] = round((peak_vo2_abs * 1000.0) / peak_hr, 1)
    if peak_vo2_rel:
        vt1 = _as_float(normalized.get("vt1_vo2_ml_kg_min"))
        vt2 = _as_float(normalized.get("vt2_vo2_ml_kg_min"))
        if vt1 is not None:
            normalized.setdefault("vt1_pct_peak_vo2", round(vt1 / peak_vo2_rel * 100, 1))
        if vt2 is not None:
            normalized.setdefault("vt2_pct_peak_vo2", round(vt2 / peak_vo2_rel * 100, 1))

    return normalized


def build_cpet_coach_summary(
    metrics: dict[str, Any],
    client_context: str = "general",
    previous_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create coach-facing CPET interpretation with medical guardrails."""
    normalized = normalize_cpet_metrics(metrics)
    validity = _build_validity_gate(normalized)
    flags = _build_coach_flags(normalized, client_context)
    zone_rows = build_zone_rows(normalized)
    trend_notes = _build_trend_notes(normalized, previous_metrics or {})

    if not flags:
        flags.append(
            {
                "Priority": "Routine",
                "Area": "CPET review",
                "Signal": "No obvious CPET review flags from the entered values.",
                "Coach action": "Use measured thresholds for zones, compare serial tests, and keep clinical interpretation with the supervising clinician.",
            }
        )

    return {
        "trust_rows": _build_trust_rows(normalized),
        "validity_gate": validity,
        "coach_flags": flags,
        "zone_rows": zone_rows,
        "trend_notes": trend_notes,
        "standardization_checks": STANDARDIZATION_CHECKS,
        "talking_points": _talking_points(client_context),
    }


def build_zone_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a 3-zone threshold prescription table from measured VT1/VT2 anchors."""
    rows: list[dict[str, Any]] = []
    anchors = [
        ("HR", "bpm", _as_float(metrics.get("vt1_hr_bpm")), _as_float(metrics.get("vt2_hr_bpm"))),
        ("Power", "W", _as_float(metrics.get("vt1_power_w")), _as_float(metrics.get("vt2_power_w"))),
        ("Speed", "km/h", _as_float(metrics.get("vt1_speed_kmh")), _as_float(metrics.get("vt2_speed_kmh"))),
        ("VO2", "mL/kg/min", _as_float(metrics.get("vt1_vo2_ml_kg_min")), _as_float(metrics.get("vt2_vo2_ml_kg_min"))),
    ]
    for anchor, unit, vt1, vt2 in anchors:
        if vt1 is None and vt2 is None:
            continue
        rows.append(
            {
                "Anchor": anchor,
                "Zone 1 / moderate": f"< {vt1:g} {unit}" if vt1 is not None else "Needs VT1",
                "Zone 2 / heavy": f"{vt1:g}-{vt2:g} {unit}" if vt1 is not None and vt2 is not None else "Needs VT1 and VT2",
                "Zone 3 / severe": f"> {vt2:g} {unit}" if vt2 is not None else "Needs VT2",
                "Use note": "Measured threshold anchor; HR is secondary when power or speed is available.",
            }
        )
    return rows


def save_cpet_report(
    user_id: int,
    test_date: str,
    client_context: str,
    metrics: dict[str, Any],
    source_filename: str | None = None,
    test_modality: str | None = None,
    protocol: str | None = None,
    raw_text: str | None = None,
    notes: str | None = None,
) -> None:
    """Save a CPET report snapshot."""
    clean_metrics = normalize_cpet_metrics(_drop_empty(metrics))
    conn = get_connection()
    try:
        _ensure_cpet_reports_schema(conn)
        conn.execute(
            """
            INSERT INTO cpet_reports
                (user_id, test_date, source_filename, test_modality, protocol,
                 client_context, metrics_json, raw_text, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, test_date) DO UPDATE SET
                source_filename = excluded.source_filename,
                test_modality = excluded.test_modality,
                protocol = excluded.protocol,
                client_context = excluded.client_context,
                metrics_json = excluded.metrics_json,
                raw_text = excluded.raw_text,
                notes = excluded.notes,
                updated_at = datetime('now')
            """,
            (
                user_id,
                test_date,
                source_filename,
                test_modality,
                protocol,
                client_context,
                json.dumps(clean_metrics, sort_keys=True),
                raw_text,
                notes,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_cpet_reports(user_id: int) -> list[dict[str, Any]]:
    """Return saved CPET reports, newest first."""
    conn = get_connection()
    try:
        _ensure_cpet_reports_schema(conn)
        rows = conn.execute(
            """
            SELECT * FROM cpet_reports
            WHERE user_id = ?
            ORDER BY test_date DESC, updated_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [_row_to_report(row) for row in rows]
    finally:
        conn.close()


def delete_cpet_report(user_id: int, report_id: int) -> None:
    conn = get_connection()
    try:
        _ensure_cpet_reports_schema(conn)
        conn.execute("DELETE FROM cpet_reports WHERE id = ? AND user_id = ?", (report_id, user_id))
        conn.commit()
    finally:
        conn.close()


def _ensure_cpet_reports_schema(conn) -> None:
    """Create the CPET report table for older deployed SQLite databases."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cpet_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            test_date TEXT NOT NULL,
            source_filename TEXT,
            test_modality TEXT,
            protocol TEXT,
            client_context TEXT NOT NULL DEFAULT 'general',
            metrics_json TEXT NOT NULL,
            raw_text TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, test_date)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cpet_reports_user ON cpet_reports(user_id, test_date)"
    )


def _build_validity_gate(metrics: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rer = _as_float(metrics.get("peak_rer"))
    hr_pct = _as_float(metrics.get("hr_pct_pred"))
    duration = _as_float(metrics.get("test_duration_min"))

    if rer is None:
        rows.append(
            {
                "Gate": "Peak effort",
                "Status": "Needs review",
                "Interpretation": "Peak RER is missing. Interpret peak VO2 cautiously; thresholds and VE/VCO2 may still be useful.",
            }
        )
    elif rer >= 1.15:
        rows.append({"Gate": "Peak effort", "Status": "Strong", "Interpretation": f"Peak RER {rer:.2f} supports maximal effort."})
    elif rer >= 1.10:
        rows.append({"Gate": "Peak effort", "Status": "Adequate", "Interpretation": f"Peak RER {rer:.2f} supports adequate effort."})
    elif rer >= 1.05:
        rows.append(
            {
                "Gate": "Peak effort",
                "Status": "Borderline",
                "Interpretation": f"Peak RER {rer:.2f}; peak VO2 may understate capacity. Lean more on VT and VE/VCO2.",
            }
        )
    else:
        rows.append(
            {
                "Gate": "Peak effort",
                "Status": "Submaximal",
                "Interpretation": f"Peak RER {rer:.2f}; do not overinterpret low peak VO2 as true ceiling.",
            }
        )

    if hr_pct is not None:
        if hr_pct >= 90:
            status = "Supportive"
        elif hr_pct >= 85:
            status = "Acceptable"
        else:
            status = "Caution"
        rows.append(
            {
                "Gate": "Heart-rate response",
                "Status": status,
                "Interpretation": f"Peak HR reached {hr_pct:.0f}% predicted; medication and chronotropic context matter.",
            }
        )

    if duration is not None:
        if 8 <= duration <= 12:
            status = "Ideal ramp"
        elif 6 <= duration <= 15:
            status = "Acceptable"
        else:
            status = "Protocol caution"
        rows.append(
            {
                "Gate": "Ramp duration",
                "Status": status,
                "Interpretation": f"Incremental phase was {duration:.1f} min; ramp length affects peak and threshold detection.",
            }
        )

    return rows


def _build_coach_flags(metrics: dict[str, Any], client_context: str) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    peak_vo2 = _as_float(metrics.get("peak_vo2_ml_kg_min"))
    peak_pct = _as_float(metrics.get("peak_vo2_pct_pred"))
    ve_slope = _as_float(metrics.get("ve_vco2_slope"))
    br = _as_float(metrics.get("breathing_reserve_pct"))
    o2_pulse_pct = _as_float(metrics.get("o2_pulse_pct_pred"))
    vo2_wr = _as_float(metrics.get("vo2_wr_slope_ml_min_w"))
    petco2_at = _as_float(metrics.get("petco2_at_mmhg"))
    spo2 = _as_float(metrics.get("spo2_nadir_pct"))
    vt1_pct = _as_float(metrics.get("vt1_pct_peak_vo2"))
    vt2_pct = _as_float(metrics.get("vt2_pct_peak_vo2"))
    peak_rer = _as_float(metrics.get("peak_rer"))

    if peak_vo2 is None:
        flags.append(
            {
                "Priority": "High",
                "Area": "Missing headline metric",
                "Signal": "Peak VO2 is missing.",
                "Coach action": "Add peak VO2 before building fitness or prognosis explanations.",
            }
        )
    elif client_context == "endurance":
        if peak_vo2 < 50:
            flags.append(
                {
                    "Priority": "High",
                    "Area": "Athlete aerobic ceiling",
                    "Signal": f"Peak VO2 is {peak_vo2:.1f} mL/kg/min.",
                    "Coach action": "For an endurance athlete this may be below expectation; verify effort, protocol, health status, and training load.",
                }
            )
        elif peak_vo2 >= 70:
            flags.append(
                {
                    "Priority": "Routine",
                    "Area": "Athlete aerobic ceiling",
                    "Signal": f"Peak VO2 is {peak_vo2:.1f} mL/kg/min.",
                    "Coach action": "High aerobic ceiling; performance gains may depend more on thresholds, economy, and durability.",
                }
            )
    elif client_context == "hybrid":
        if peak_vo2 < 45:
            flags.append(
                {
                    "Priority": "Medium",
                    "Area": "Hybrid-sport aerobic base",
                    "Signal": f"Peak VO2 is {peak_vo2:.1f} mL/kg/min.",
                    "Coach action": "Hybrid competition still needs a strong aerobic ceiling; combine threshold work with sport-specific repeated efforts.",
                }
            )
        else:
            flags.append(
                {
                    "Priority": "Routine",
                    "Area": "Hybrid-sport context",
                    "Signal": f"Peak VO2 is {peak_vo2:.1f} mL/kg/min.",
                    "Coach action": "Incremental CPET captures aerobic ceiling but not sled, carry, burpee, and pre-fatigued station demands.",
                }
            )
    else:
        if peak_vo2 < 10:
            priority, klass = "High", "severely reduced"
        elif peak_vo2 < 16:
            priority, klass = "High", "reduced"
        elif peak_vo2 < 20:
            priority, klass = "Medium", "mildly reduced"
        else:
            priority, klass = "Routine", "above classic Weber high-risk bands"
        flags.append(
            {
                "Priority": priority,
                "Area": "Aerobic capacity",
                "Signal": f"Peak VO2 is {peak_vo2:.1f} mL/kg/min, {klass}.",
                "Coach action": "Use with effort quality, symptoms, and clinician interpretation; do not make diagnosis from VO2 alone.",
            }
        )

    if peak_pct is not None and client_context in {"endurance", "hybrid"} and peak_pct < 120:
        flags.append(
            {
                "Priority": "Medium",
                "Area": "Athlete predicted norms",
                "Signal": f"Peak VO2 is {peak_pct:.0f}% predicted.",
                "Coach action": "General-population predicted normal can be too low for athletes; compare with sport and prior tests.",
            }
        )

    if ve_slope is not None:
        if ve_slope >= 45:
            priority, meaning = "High", "Arena class IV range"
        elif ve_slope >= 36:
            priority, meaning = "High", "elevated ventilatory inefficiency range"
        elif ve_slope >= 30:
            priority, meaning = "Medium", "borderline-to-mildly elevated range"
        else:
            priority, meaning = "Routine", "typical normal range"
        flags.append(
            {
                "Priority": priority,
                "Area": "Ventilatory efficiency",
                "Signal": f"VE/VCO2 slope is {ve_slope:.1f}, {meaning}.",
                "Coach action": "Read with PETCO2, breathing reserve, symptoms, and cardiology/pulmonary context.",
            }
        )

    if br is not None:
        if br < 15:
            flags.append(
                {
                    "Priority": "High",
                    "Area": "Breathing reserve",
                    "Signal": f"Breathing reserve is {br:.0f}%.",
                    "Coach action": "Possible ventilatory limitation; coach should defer medical interpretation to the CPET clinician.",
                }
            )
        elif br <= 20:
            flags.append(
                {
                    "Priority": "Medium",
                    "Area": "Breathing reserve",
                    "Signal": f"Breathing reserve is {br:.0f}%.",
                    "Coach action": "Low-normal reserve; interpret with spirometry, VE, symptoms, and modality.",
                }
            )

    if o2_pulse_pct is not None and o2_pulse_pct < 80:
        flags.append(
            {
                "Priority": "High",
                "Area": "O2 pulse",
                "Signal": f"O2 pulse is {o2_pulse_pct:.0f}% predicted.",
                "Coach action": "Low O2 pulse can support oxygen-delivery limitation; refer interpretation to clinician.",
            }
        )

    if vo2_wr is not None and vo2_wr < 8:
        flags.append(
            {
                "Priority": "High",
                "Area": "VO2/work-rate slope",
                "Signal": f"VO2/WR slope is {vo2_wr:.1f} mL/min/W.",
                "Coach action": "Below the usual ~10 mL/min/W expectation; clinician should review for oxygen-delivery limitation pattern.",
            }
        )

    if petco2_at is not None and petco2_at < 33:
        flags.append(
            {
                "Priority": "Medium",
                "Area": "PETCO2",
                "Signal": f"PETCO2 at AT is {petco2_at:.0f} mmHg.",
                "Coach action": "Low PETCO2 can fit hyperventilation, dead space, HF severity, or pulmonary vascular physiology.",
            }
        )

    if spo2 is not None and spo2 < 90:
        flags.append(
            {
                "Priority": "High",
                "Area": "Exercise oxygen saturation",
                "Signal": f"SpO2 nadir is {spo2:.0f}%.",
                "Coach action": "Exercise desaturation is a medical review item; avoid unsupervised intensity escalation.",
            }
        )

    if vt1_pct is not None and vt1_pct < 40:
        flags.append(
            {
                "Priority": "Medium",
                "Area": "First threshold",
                "Signal": f"VT1 is {vt1_pct:.0f}% of peak VO2.",
                "Coach action": "Early VT1 can reflect deconditioning, cardiac limitation, mitochondrial/peripheral limitation, or protocol issues.",
            }
        )

    if vt2_pct is not None and vt2_pct >= 80:
        flags.append(
            {
                "Priority": "Routine",
                "Area": "Second threshold",
                "Signal": f"VT2 is {vt2_pct:.0f}% of peak VO2.",
                "Coach action": "High fractional utilization; performance gains may need economy, durability, and sport specificity.",
            }
        )

    if not build_zone_rows(metrics):
        flags.append(
            {
                "Priority": "Medium",
                "Area": "Zone prescription",
                "Signal": "VT1/VT2 anchors are incomplete.",
                "Coach action": "Avoid fixed %HRmax zones as the primary prescription; enter threshold HR, power, speed, or VO2.",
            }
        )

    if peak_rer is not None and peak_rer > 1.0 and ("fatmax_g_min" in metrics or "fatmax_vo2_pct" in metrics):
        flags.append(
            {
                "Priority": "Routine",
                "Area": "Substrate interpretation",
                "Signal": "Peak RER is above 1.0.",
                "Coach action": "Fat-oxidation estimates are valid only from submaximal steady stages before bicarbonate-buffered CO2 inflates VCO2.",
            }
        )

    return flags


def _build_trust_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field, spec in CPET_METRIC_SPECS.items():
        if field not in metrics:
            continue
        rows.append(
            {
                "Metric": spec["label"],
                "Value": _format_metric_value(field, metrics[field]),
                "Layer": spec["layer"],
                "Coach use": spec["coach_use"],
            }
        )
    return rows


def _build_trend_notes(metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    comparisons = [
        ("peak_vo2_ml_kg_min", "Peak VO2", "mL/kg/min", 2.0),
        ("peak_vo2_pct_pred", "Peak VO2 predicted", "%", 5.0),
        ("vt1_hr_bpm", "VT1 HR", "bpm", 3.0),
        ("vt2_hr_bpm", "VT2 HR", "bpm", 3.0),
        ("ve_vco2_slope", "VE/VCO2 slope", "", 2.0),
        ("peak_rer", "Peak RER", "", 0.03),
    ]
    for field, label, unit, threshold in comparisons:
        current = _as_float(metrics.get(field))
        previous = _as_float(previous_metrics.get(field))
        if current is None or previous is None:
            continue
        delta = current - previous
        if abs(delta) < threshold:
            continue
        if field == "peak_rer":
            notes.append(f"{label} changed by {delta:+.2f}; confirm effort comparability.")
        elif unit:
            notes.append(f"{label} changed by {delta:+.1f} {unit}.")
        else:
            notes.append(f"{label} changed by {delta:+.1f}.")
    if notes:
        notes.append("For serial CPET, treat roughly 2-5% VO2max variation as normal test-retest noise unless the lab provides its own typical error.")
    return notes


def _talking_points(client_context: str) -> list[str]:
    points = [
        "Start with the validity gate: peak RER, HR response, symptoms, and protocol quality.",
        "Peak VO2 is the engine size, but it is not the whole story.",
        "VT1 and VT2 are the training-zone spine; prescribe from measured thresholds before fixed %HRmax shortcuts.",
        "VE/VCO2 slope, breathing reserve, O2 pulse, PETCO2, and SpO2 are medical-pattern clues, not coaching diagnoses.",
        "Compare serial tests only when protocol and preparation are similar.",
    ]
    if client_context == "endurance":
        points.append("For endurance athletes, normal population VO2 can still be underperforming; thresholds, economy, and durability separate good from great.")
    if client_context == "hybrid":
        points.append("For HYROX/CrossFit-style athletes, ramp CPET captures the aerobic ceiling but not repeated mixed-modality station fatigue.")
    if client_context == "cardiology":
        points.append("For cardiology, multiparametric interpretation beats any single number; coach-facing actions should stay inside clinician recommendations.")
    return points


def _build_extraction_warnings(metrics: dict[str, Any]) -> list[str]:
    warnings = []
    if not metrics:
        warnings.append("No standard CPET metrics were detected. Enter values manually or upload a text-readable report.")
    if "peak_vo2_ml_kg_min" not in metrics and "peak_vo2_l_min" not in metrics:
        warnings.append("Peak VO2 was not detected; add it manually before interpreting aerobic capacity.")
    if "peak_rer" not in metrics:
        warnings.append("Peak RER was not detected; add it manually to judge whether peak VO2 reflects maximal effort.")
    if not any(key in metrics for key in ("vt1_hr_bpm", "vt1_power_w", "vt1_speed_kmh", "vt1_vo2_ml_kg_min")):
        warnings.append("VT1/AT was not detected; this is needed for threshold-based coaching zones.")
    return warnings


def _normalize_text(text: str) -> str:
    replacements = {
        "\u00a0": " ",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00b2": "2",
        "\u207b": "-",
        "\u00b7": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"V[\u0307\u02d9]?", "V", text)
    text = re.sub(r"O[\u2082\u00b2]", "O2", text)
    text = re.sub(r"CO[\u2082\u00b2]", "CO2", text)
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
    units = r"(mL/kg/min|ml/kg/min|mL/min/kg|L/min|l/min|mmol/L|mmol/l|mL/min/W|ml/min/W|mmHg|bpm|beats/min|kg|W|watts|km/h|mph|%|ratio|min|minutes)?"
    for label in labels:
        escaped = re.escape(label)
        patterns = [
            rf"(?i)(?:^|[^A-Za-z0-9]){escaped}(?:\s*\([^)]*\))?.{{0,70}}?(-?\d+(?:[\.,]\d+)?)\s*{units}",
            rf"(?i)(-?\d+(?:[\.,]\d+)?)\s*{units}.{{0,35}}?{escaped}",
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
                return {"value": value, "unit": match.group(2) if len(match.groups()) > 1 else None}
    return None


def _find_test_date(text: str) -> str | None:
    date_pattern = r"([0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2}|[0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{4})"
    for label in ("Test Date", "CPET Date", "Exercise Test Date", "Date of Test", "Date"):
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


def _find_test_modality(text: str) -> str | None:
    lowered = text.lower()
    if "treadmill" in lowered:
        return "treadmill"
    if "cycle" in lowered or "bike" in lowered or "ergometer" in lowered:
        return "cycle ergometer"
    if "row" in lowered:
        return "row ergometer"
    return None


def _find_protocol(text: str) -> str | None:
    match = re.search(r"(?i)(?:Protocol|Ramp protocol|Exercise protocol).{0,30}?([A-Za-z0-9 +/\-]+?)(?:\.|,|;|$)", text)
    if not match:
        return None
    value = match.group(1).strip()
    return value[:80] if value else None


def _round_metric(field: str, value: float) -> float:
    if field in {"peak_rer", "chronotropic_index"}:
        return round(value, 2)
    if "pct" in field or field.endswith("_pct_pred"):
        return round(value, 1)
    if field in {"ve_vco2_slope", "ve_vco2_nadir", "vo2_wr_slope_ml_min_w", "oues"}:
        return round(value, 2)
    if field.endswith("_l_min"):
        return round(value, 2)
    return round(value, 1)


def _format_metric_value(field: str, value: Any) -> str:
    numeric = _as_float(value)
    spec = CPET_METRIC_SPECS.get(field, {})
    unit = spec.get("unit", "")
    if numeric is None:
        return "--"
    if field in {"peak_rer", "chronotropic_index"}:
        return f"{numeric:.2f}"
    if unit == "%":
        return f"{numeric:.1f}%"
    if unit:
        return f"{numeric:g} {unit}"
    return f"{numeric:g}"


def _row_to_report(row) -> dict[str, Any]:
    report = dict(row)
    try:
        report["metrics"] = json.loads(report.get("metrics_json") or "{}")
    except json.JSONDecodeError:
        report["metrics"] = {}
    return report


def _drop_empty(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metrics.items() if value is not None and value != ""}


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
