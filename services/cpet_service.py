"""CPET report extraction, storage, and coach-facing interpretation."""

from __future__ import annotations

import io
import json
import re
from datetime import date
from typing import Any

from dateutil import parser as date_parser

from config.cpet_norms import classify_vo2max
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
    "fatmax_hr_bpm": {
        "label": "FatMax HR",
        "unit": "bpm",
        "layer": "Interpreted",
        "coach_use": "Heart rate at maximal fat oxidation; a low-intensity fat-burning anchor, usually at or below VT1.",
        "labels": ["FatMax HR", "MFO heart rate", "Heart rate at max fat oxidation"],
        "min": 50,
        "max": 190,
    },
    "peak_power_w": {
        "label": "Peak work rate",
        "unit": "W",
        "layer": "Measured",
        "coach_use": "Maximal work rate achieved; the cycling ceiling and a serial-comparison anchor.",
        "labels": ["Peak Power", "Peak work rate", "Max work rate", "Maximum work rate"],
        "min": 20,
        "max": 800,
    },
    "height_cm": {
        "label": "Height",
        "unit": "cm",
        "layer": "Context",
        "coach_use": "Context for predicted-value equations.",
        "labels": ["Height"],
        "min": 120,
        "max": 220,
    },
    "vt1_vo2_l_min": {
        "label": "VT1 VO2 absolute",
        "unit": "L/min",
        "layer": "Interpreted",
        "coach_use": "Absolute oxygen uptake at the first threshold.",
        "labels": ["VT1 VO2 absolute", "AT VO2 absolute"],
        "min": 0.3,
        "max": 6.0,
    },
    "vt2_vo2_l_min": {
        "label": "VT2 VO2 absolute",
        "unit": "L/min",
        "layer": "Interpreted",
        "coach_use": "Absolute oxygen uptake at the second threshold / RCP.",
        "labels": ["VT2 VO2 absolute", "RCP VO2 absolute"],
        "min": 0.4,
        "max": 7.0,
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
    """Extract likely CPET values from report text using conservative label patterns.

    Cortex MetaSoft/MetaLyzer reports (tabular, ``V'O2`` notation) are parsed by a
    dedicated column-aware parser first; the generic label scanner then fills any
    gaps without overwriting the more reliable structured values.
    """
    normalized = _normalize_text(text)
    metrics: dict[str, Any] = {}

    is_cortex = _looks_like_cortex(normalized, text)
    if is_cortex:
        metrics.update(parse_cortex_report(text))

    for field, spec in CPET_METRIC_SPECS.items():
        if field in metrics:
            continue
        value = _find_labeled_number(normalized, spec["labels"], spec.get("min"), spec.get("max"))
        if value is not None:
            metrics[field] = _round_metric(field, value["value"])

    metrics = normalize_cpet_metrics(metrics)
    return {
        "test_date": _find_test_date(normalized),
        "test_modality": _find_test_modality(normalized),
        "protocol": _find_protocol(normalized),
        "source_format": "cortex_metasoft" if is_cortex else "generic",
        "metrics": metrics,
        "extraction_warnings": _build_extraction_warnings(metrics),
    }


# ── Cortex MetaSoft / MetaLyzer structured parser ───────────────────────────
# The Summary Table prints 10 value columns per variable row:
#   [Rest, VT1.val, VT1.%norm, VT1.%max, VT2.val, VT2.%norm, VT2.%max,
#    peak.val, peak.%norm, Norm]
_CORTEX_SUMMARY_IDX = {"rest": 0, "vt1": 1, "vt1_pctmax": 3, "vt2": 4,
                       "vt2_pctmax": 6, "peak": 7, "peak_pctnorm": 8, "norm": 9}
# The "CPET Summary" Test Results table prints 6 columns per variable row:
#   [Rest, VT1, VT2, VO2peak, Recovery, Norm]
_CORTEX_TESTRESULTS_IDX = {"rest": 0, "vt1": 1, "vt2": 2, "peak": 3, "recovery": 4, "norm": 5}

# normalized variable label -> (vt1_field, vt2_field, peak_field, norm_field)
_CORTEX_ROW_MAP: dict[str, tuple[str | None, str | None, str | None, str | None]] = {
    "VO2/kg": ("vt1_vo2_ml_kg_min", "vt2_vo2_ml_kg_min", "peak_vo2_ml_kg_min", None),
    "VO2": ("vt1_vo2_l_min", "vt2_vo2_l_min", "peak_vo2_l_min", None),
    "HR": ("vt1_hr_bpm", "vt2_hr_bpm", "peak_hr_bpm", "predicted_hr_bpm"),
    "WR": ("vt1_power_w", "vt2_power_w", "peak_power_w", None),
    "VO2/HR": (None, None, "o2_pulse_ml_beat", None),
    "VE": (None, None, "peak_ve_l_min", "mvv_l_min"),
    "RER": (None, None, "peak_rer", None),
}
# peak.%norm column -> % predicted field (Summary Table only)
_CORTEX_PCTNORM_MAP = {"VO2/kg": "peak_vo2_pct_pred", "VO2": "peak_vo2_pct_pred",
                       "HR": "hr_pct_pred", "VO2/HR": "o2_pulse_pct_pred"}


def _looks_like_cortex(normalized_text: str, raw_text: str = "") -> bool:
    lowered = normalized_text.lower()
    markers = ("metasoft", "metalyzer", "cortex", "9-panel-plot", "cpet basic results")
    if any(marker in lowered for marker in markers):
        return True
    # Tell-tale Cortex prime notation in the ORIGINAL text (V'O2 / V'CO2 / V'E).
    # COSMED and other carts use plain "VO2" or a combining dot, not an apostrophe,
    # so this stays specific to Cortex and does not false-positive on generic
    # reports that merely contain the substrings "vo2/kg" and "vo2peak".
    return bool(re.search(r"V['’ʹ′]\s?(?:O2|CO2|E)\b", raw_text))


def _cortex_tokens(rest_of_line: str) -> list[float | None]:
    """Numbers and dash placeholders after a variable label (dashes hold columns)."""
    out: list[float | None] = []
    for tok in re.findall(r"-?\d+(?:[.,]\d+)?|-", rest_of_line):
        out.append(_parse_number(tok) if tok not in {"-", "--"} else None)
    return out


def parse_cortex_report(text: str) -> dict[str, Any]:
    """Column-aware parse of a Cortex MetaSoft CPET export.

    The table layout is chosen by the section header the row sits under, not by a
    raw token count. The Summary Table prints 10 value columns (with dash
    placeholders); the CPET Summary "Test Results" table prints 6. Guessing purely
    by token count misreads a Summary row that lost a blank cell as a 6-column row,
    turning percent-columns into VT2/peak values, so section tracking is primary.
    """
    metrics: dict[str, Any] = {}
    lines = [_normalize_notation(line).strip() for line in text.splitlines()]
    labels = sorted(_CORTEX_ROW_MAP.keys(), key=len, reverse=True)
    section = None  # "summary" | "testresults" | None

    for line in lines:
        lowered = line.lower()
        if "summary table" in lowered:
            section = "summary"
            continue
        if "test results" in lowered:
            section = "testresults"
            continue

        for label in labels:
            # Label must be followed by whitespace (unit or first value); the
            # whitespace lookahead stops "VE" matching "VE/VO2" or "VE/VCO2" rows.
            match = re.match(rf"^{re.escape(label)}(?=\s)(.*)$", line)
            if not match:
                continue
            values = _cortex_tokens(match.group(1))
            # Prefer the section's known layout. Fall back to token count only when
            # the section is unknown: >=7 tokens can only be a Summary row (its key
            # VT1/VT2/peak indices 1/4/7 are present), exactly 6 is Test Results.
            if section == "summary":
                idx = _CORTEX_SUMMARY_IDX if len(values) >= 7 else None
            elif section == "testresults":
                idx = _CORTEX_TESTRESULTS_IDX if len(values) >= 6 else None
            elif len(values) >= 7:
                idx = _CORTEX_SUMMARY_IDX
            elif len(values) == 6:
                idx = _CORTEX_TESTRESULTS_IDX
            else:
                idx = None
            if idx is None:
                break
            f_vt1, f_vt2, f_peak, f_norm = _CORTEX_ROW_MAP[label]

            def _put(field: str | None, key: str) -> None:
                if field is None or key not in idx or idx[key] >= len(values):
                    return
                value = values[idx[key]]
                if value is not None and field not in metrics:
                    metrics[field] = _round_metric(field, value)

            _put(f_vt1, "vt1")
            _put(f_vt2, "vt2")
            _put(f_peak, "peak")
            _put(f_norm, "norm")

            if idx is _CORTEX_SUMMARY_IDX:
                if label in _CORTEX_PCTNORM_MAP and idx["peak_pctnorm"] < len(values):
                    pct = values[idx["peak_pctnorm"]]
                    if pct is not None:
                        metrics.setdefault(_CORTEX_PCTNORM_MAP[label], round(pct, 1))
                if label == "VO2/kg":
                    if values[idx["vt1_pctmax"]] is not None:
                        metrics.setdefault("vt1_pct_peak_vo2", round(values[idx["vt1_pctmax"]], 1))
                    if values[idx["vt2_pctmax"]] is not None:
                        metrics.setdefault("vt2_pct_peak_vo2", round(values[idx["vt2_pctmax"]], 1))
            break

    _parse_cortex_scalars(text, metrics)

    # Compute breathing reserve from peak VE and the predicted ventilation ceiling
    # (VE "Norm" = MVV surrogate). This overrides Cortex's ambiguous "%BR" row and
    # blocks the generic scanner from scraping the wrong ventilation column.
    peak_ve = _as_float(metrics.get("peak_ve_l_min"))
    mvv = _as_float(metrics.get("mvv_l_min"))
    if peak_ve is not None and mvv:
        metrics["breathing_reserve_pct"] = round((mvv - peak_ve) / mvv * 100, 1)

    return metrics


def _parse_cortex_scalars(text: str, metrics: dict[str, Any]) -> None:
    """Pull single-value fields (demographics, VE/VCO2 slope, FatMax) from prose."""
    joined = _normalize_text(text)

    slope = re.search(r"VE\s*\(\s*VCO2\s*\).{0,40}?Slope[:\s]+(\d+(?:[.,]\d+)?)", joined, re.I)
    if not slope:
        slope = re.search(r"Slope[:\s]+(\d+(?:[.,]\d+)?)\s*Correlation", joined, re.I)
    if slope:
        metrics.setdefault("ve_vco2_slope", _round_metric("ve_vco2_slope", _parse_number(slope.group(1))))

    sex = re.search(r"\bSex\b\s*[:\-]?\s*(male|female|m|f)\b", joined, re.I)
    if sex:
        metrics.setdefault("sex", {"m": "male", "f": "female"}.get(sex.group(1).lower(), sex.group(1).lower()))
    age = re.search(r"\bAge\b\s*[:\-]?\s*(\d{1,3})\b", joined, re.I)
    if age and "age_years" not in metrics:
        metrics["age_years"] = float(age.group(1))
    weight = re.search(r"\bWeight\b\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*kg", joined, re.I)
    if weight and "weight_kg" not in metrics:
        metrics["weight_kg"] = _parse_number(weight.group(1))
    height = re.search(r"\bHeight\b\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*cm", joined, re.I)
    if height and "height_cm" not in metrics:
        metrics["height_cm"] = _parse_number(height.group(1))

    lipid = re.search(r"lipid metabolism\s*=?\s*(\d+)(?:\s*-\s*(\d+))?\s*g/h", joined, re.I)
    if lipid and "fatmax_g_min" not in metrics:
        low = float(lipid.group(1))
        high = float(lipid.group(2)) if lipid.group(2) else low
        metrics["fatmax_g_min"] = round(((low + high) / 2.0) / 60.0, 2)
    fatmax_hr = re.search(r"Heart Rate Range\s*=?\s*(\d+)\s*-\s*(\d+)\s*/?\s*min", joined, re.I)
    if fatmax_hr:
        low, high = float(fatmax_hr.group(1)), float(fatmax_hr.group(2))
        metrics.setdefault("fatmax_hr_low_bpm", low)
        metrics.setdefault("fatmax_hr_high_bpm", high)
        metrics.setdefault("fatmax_hr_bpm", round((low + high) / 2.0))


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
    modality: str | None = None,
) -> dict[str, Any]:
    """Create coach-facing CPET interpretation with medical guardrails."""
    normalized = normalize_cpet_metrics(metrics)
    fitness = _classify_fitness(normalized, modality)
    validity = _build_validity_gate(normalized)
    flags = _build_coach_flags(normalized, client_context, fitness)
    training_zones = build_training_zones(normalized, modality)
    metabolic_profile = build_metabolic_profile(normalized)
    consistency_rows = _build_consistency_checks(normalized, fitness, raw_metrics=metrics)
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
        "fitness_classification": fitness,
        "validity_gate": validity,
        "coach_flags": flags,
        "training_zones": training_zones,
        "metabolic_profile": metabolic_profile,
        "training_narrative": _training_narrative(normalized, training_zones),
        "metabolic_narrative": _metabolic_narrative(normalized, metabolic_profile),
        "consistency_rows": consistency_rows,
        "trend_notes": trend_notes,
        "standardization_checks": STANDARDIZATION_CHECKS,
        "talking_points": _talking_points(client_context, normalized, fitness),
    }


def _classify_fitness(metrics: dict[str, Any], modality: str | None) -> dict[str, Any] | None:
    """Place peak VO2 on age/sex/modality percentile norms (FRIEND/ACSM)."""
    peak_vo2 = _as_float(metrics.get("peak_vo2_ml_kg_min"))
    if peak_vo2 is None:
        return None
    return classify_vo2max(
        peak_vo2,
        metrics.get("sex"),
        _as_float(metrics.get("age_years")),
        modality,
    )


# ── Training zones ───────────────────────────────────────────────────────────
# Tunable conventions (exposed, not buried — see the research spec's "do not
# hard-code blindly" flags). The endurance "Zone 2" floor is the lower shoulder
# of the moderate domain; its ceiling is ALWAYS VT1/LT1.
ZONE2_FLOOR_COEFF = 0.90          # Z1<->Z2 boundary on power/VO2 = coeff x VT1
# The endurance "Zone 2" is the narrow window at the TOP of the aerobic base, just
# under the first lactate threshold (LT1 ~2 mmol, gas-exchange proxy VT1/GET). The
# training TARGET is the top of the band (VT1 - target offset), NOT FatMax, which
# sits at the floor. All four are tunable conventions, not physiological constants.
ZONE2_CORE_WIDTH_BPM = 10.0       # "true Zone 2" stimulus band width just under LT1
ZONE2_TARGET_OFFSET_BPM = 6.0     # Zone 2 bullseye = VT1_HR - this (just under LT1)
ZONE2_FLOOR_CAP_BPM = 15.0        # endurance-band floor no lower than VT1_HR - this
LT1_LACTATE_MMOL = 2.0            # aerobic threshold (VT1/GET proxy)
LT2_LACTATE_MMOL = 4.0            # anaerobic threshold / OBLA 4.0 (VT2/RCP proxy; MLSS is individual)

# Maximal fat-oxidation (MFO) reference bands, g/min, absolute (Randell 2017,
# Jeukendrup & Wallis). Used to classify the metabolic profile.
_MFO_BANDS = [(0.40, "Low"), (0.60, "Typical (recreational)"), (0.80, "Good (trained)")]

_ZONE_META = [
    ("Z1", "Recovery", "Active recovery, warm-up/cool-down."),
    ("Z2", "Endurance (\"Zone 2\")", "Aerobic base: mitochondria + fat oxidation. Most weekly hours live here."),
    ("Z3", "Tempo", "Aerobic-threshold work; useful but fatiguing 'grey zone' — use sparingly."),
    ("Z4", "Threshold", "At/around VT2 — the lever that pushes the anaerobic threshold up."),
    ("Z5", "VO2max / severe", "Above VT2: maximal aerobic power and anaerobic work."),
]


def _round_metric_display(value: float, decimals: int) -> str:
    if decimals == 0:
        return f"{round(value)}"
    return f"{value:.{decimals}f}"


def _zone_range_strings(v1: float, v2: float, floor: float, decimals: int) -> list[str]:
    """Return the five zone-range strings for one metric (Z1..Z5)."""
    midpoint = (v1 + v2) / 2.0
    f = lambda x: _round_metric_display(x, decimals)  # noqa: E731
    return [
        f"< {f(floor)}",
        f"{f(floor)}-{f(v1)}",
        f"{f(v1)}-{f(midpoint)}",
        f"{f(midpoint)}-{f(v2)}",
        f">= {f(v2)}",
    ]


def build_training_zones(metrics: dict[str, Any], modality: str | None = None) -> dict[str, Any]:
    """Build a threshold-anchored 5-zone prescription plus a polarized monitor.

    Zone 2 (endurance) tops out at VT1/LT1; FatMax refines its floor. Prescribe
    on power/pace when available (drift-proof); HR is a cross-check.
    """
    vt1_hr = _as_float(metrics.get("vt1_hr_bpm"))
    vt2_hr = _as_float(metrics.get("vt2_hr_bpm"))
    vt1_pw = _as_float(metrics.get("vt1_power_w"))
    vt2_pw = _as_float(metrics.get("vt2_power_w"))
    vt1_sp = _as_float(metrics.get("vt1_speed_kmh"))
    vt2_sp = _as_float(metrics.get("vt2_speed_kmh"))
    vt1_vo2 = _as_float(metrics.get("vt1_vo2_ml_kg_min"))
    vt2_vo2 = _as_float(metrics.get("vt2_vo2_ml_kg_min"))
    fatmax_hr = _as_float(metrics.get("fatmax_hr_bpm"))
    fatmax_low = _as_float(metrics.get("fatmax_hr_low_bpm"))
    fatmax_high = _as_float(metrics.get("fatmax_hr_high_bpm"))

    is_running = "run" in str(modality or "").lower() or "tread" in str(modality or "").lower()

    # Which metrics have both thresholds (needed for the full 5-zone split)?
    metric_defs = [
        ("HR (bpm)", vt1_hr, vt2_hr, 0, "heart rate"),
        ("Power (W)", vt1_pw, vt2_pw, 0, "power"),
        ("Speed (km/h)", vt1_sp, vt2_sp, 1, "pace"),
        ("VO2 (mL/kg/min)", vt1_vo2, vt2_vo2, 1, "VO2"),
    ]
    available = [(label, v1, v2, dec, kind) for (label, v1, v2, dec, kind) in metric_defs if v1 is not None and v2 is not None]

    result: dict[str, Any] = {"has_zones": bool(available)}
    if not available:
        result["incomplete_note"] = (
            "Need VT1 and VT2 (on HR, power, pace, or VO2) to build training zones. "
            "Add the threshold anchors; do not prescribe from fixed %HRmax alone."
        )
        return result

    # Endurance-zone HR floor: no lower than VT1 - 15 bpm; extend down to the FatMax
    # low when given (the fat-oxidation floor of the window).
    zone2_floor_hr = None
    if vt1_hr is not None:
        zone2_floor_hr = vt1_hr - ZONE2_FLOOR_CAP_BPM
        if fatmax_low is not None:
            zone2_floor_hr = max(fatmax_low, vt1_hr - ZONE2_FLOOR_CAP_BPM)

    # Per-metric zone ranges. HR uses the FatMax-refined floor; others use 0.90xVT1.
    column_ranges: dict[str, list[str]] = {}
    for label, v1, v2, dec, _kind in available:
        floor = zone2_floor_hr if (label.startswith("HR") and zone2_floor_hr is not None) else ZONE2_FLOOR_COEFF * v1
        column_ranges[label] = _zone_range_strings(v1, v2, floor, dec)

    zone_table: list[dict[str, Any]] = []
    for i, (zid, name, purpose) in enumerate(_ZONE_META):
        row: dict[str, Any] = {"Zone": f"{zid} {name}"}
        for label, _v1, _v2, _dec, _kind in available:
            row[label] = column_ranges[label][i]
        row["Purpose"] = purpose
        zone_table.append(row)

    # Primary anchor: power/pace beat HR (drift-proof). VO2 is lab-only.
    if any(label == "Power (W)" for label, *_ in available):
        primary = "power"
    elif any(label == "Speed (km/h)" for label, *_ in available):
        primary = "pace"
    elif any(label.startswith("HR") for label, *_ in available):
        primary = "heart rate"
    else:
        primary = "VO2"

    # Endurance (Zone 2) detail. The band is the endurance base; the TARGET is the
    # narrow window at its TOP, just under LT1 (~2 mmol) — not FatMax (the floor).
    zone2: dict[str, Any] = {"ceiling_label": f"LT1 / aerobic threshold (~{LT1_LACTATE_MMOL:g} mmol)"}
    if vt1_hr is not None and zone2_floor_hr is not None:
        core_lo = vt1_hr - ZONE2_CORE_WIDTH_BPM
        bullseye = vt1_hr - ZONE2_TARGET_OFFSET_BPM
        zone2["hr"] = f"{round(zone2_floor_hr)}-{round(vt1_hr)} bpm"
        zone2["core_hr"] = f"{round(core_lo)}-{round(vt1_hr)} bpm"
        zone2["target_hr"] = f"~{round(bullseye)} bpm"
        zone2["ceiling_hr"] = round(vt1_hr)
        if fatmax_low is not None and fatmax_high is not None:
            zone2["fatmax_floor"] = f"{round(fatmax_low)}-{round(min(fatmax_high, vt1_hr))} bpm"
        elif fatmax_hr is not None and fatmax_hr <= vt1_hr:
            zone2["fatmax_floor"] = f"~{round(fatmax_hr)} bpm"
        # Training-status: FatMax converges with LT1 in trained athletes, diverges
        # (sits well below) in the untrained — which changes how hard to push.
        anchor = fatmax_high if fatmax_high is not None else fatmax_hr
        if anchor is not None:
            gap = vt1_hr - anchor
            zone2["fatmax_vt1_gap"] = round(gap)
            zone2["training_pattern"] = "divergent" if gap >= 7 else ("converged" if gap <= 4 else "mild")
    if vt1_pw is not None:
        zone2["power"] = f"{round(ZONE2_FLOOR_COEFF * vt1_pw)}-{round(vt1_pw)} W"
    if vt1_sp is not None:
        zone2["speed"] = f"{ZONE2_FLOOR_COEFF * vt1_sp:.1f}-{vt1_sp:.1f} km/h"
    result["zone2"] = zone2

    # Numeric anchors for charting (zone bar). None-safe; edges are the shared
    # thresholds so the SVG never re-derives them.
    peak_hr = _as_float(metrics.get("peak_hr_bpm"))
    peak_pw = _as_float(metrics.get("peak_power_w"))
    chart: dict[str, Any] = {}
    if vt1_hr is not None and vt2_hr is not None:
        chart["hr"] = {
            "floor": round(zone2_floor_hr) if zone2_floor_hr is not None else None,
            "vt1": round(vt1_hr), "mid": round((vt1_hr + vt2_hr) / 2), "vt2": round(vt2_hr),
            "peak": round(peak_hr) if peak_hr is not None else round(vt2_hr + 12),
            "fatmax_low": round(fatmax_low) if fatmax_low is not None else None,
            "fatmax_high": round(min(fatmax_high, vt1_hr)) if fatmax_high is not None else None,
            "target": round(vt1_hr - ZONE2_TARGET_OFFSET_BPM),
            "core_lo": round(vt1_hr - ZONE2_CORE_WIDTH_BPM),
        }
    if vt1_pw is not None and vt2_pw is not None:
        chart["power"] = {
            "floor": round(ZONE2_FLOOR_COEFF * vt1_pw), "vt1": round(vt1_pw),
            "mid": round((vt1_pw + vt2_pw) / 2), "vt2": round(vt2_pw),
            "peak": round(peak_pw) if peak_pw is not None else round(vt2_pw * 1.15),
        }
    result["chart"] = chart

    # Polarized 3-zone monitor (distribution monitoring only — NOT the prescriptive Z2).
    def _pol(v1, v2, unit, dec):
        if v1 is None or v2 is None:
            return None
        f = lambda x: _round_metric_display(x, dec)  # noqa: E731
        return f"< {f(v1)} / {f(v1)}-{f(v2)} / >= {f(v2)} {unit}"

    polarized_rows = []
    pol_specs = [("Heart rate", vt1_hr, vt2_hr, "bpm", 0), ("Power", vt1_pw, vt2_pw, "W", 0), ("Speed", vt1_sp, vt2_sp, "km/h", 1)]
    for name, v1, v2, unit, dec in pol_specs:
        val = _pol(v1, v2, unit, dec)
        if val:
            polarized_rows.append({"Anchor": name, "Easy (<VT1) / Grey (VT1-VT2) / Hard (>VT2)": val})
    result["polarized_rows"] = polarized_rows
    result["polarized_target"] = "Aim ~75-80% of training time below VT1, <=5-10% in the VT1-VT2 grey zone, ~15-20% above VT2."

    result["zone_table"] = zone_table
    result["primary_anchor"] = primary
    result["caveats"] = _zone_caveats(primary, metrics)
    return result


def _zone_caveats(primary: str, metrics: dict[str, Any]) -> list[str]:
    caveats = [
        "The Zone 2 ceiling is anchored to VT1/GET as the LT1 (~2 mmol aerobic threshold) proxy. Gas-exchange VT1 "
        "sits at or slightly ABOVE the true first lactate rise, so this ceiling can read a few bpm high — train at or "
        "just below it, and confirm with a lactate strip (baseline + 0.5 mmol) when precision matters.",
        "VT2 is the LT2/anaerobic-threshold proxy (~4 mmol OBLA). True steady-state (MLSS) is individual (2.5-6 mmol) "
        "and sits just below VT2/RCP.",
        f"Prescribe on {primary}; heart rate is a cross-check. Above VT2, never lead with HR — it lags and drifts.",
        "Zones are valid only for the tested modality (cycle/treadmill/row); do not reuse them for another sport.",
        "Each boundary is a band, not a line (~+-5 bpm on HR, ~+-5% on power/pace) from test-retest and day-to-day noise.",
        "On long efforts (>45-60 min) expect ~5-10 bpm/hr of cardiac drift; hold power/pace, not HR.",
        "Heat, dehydration, poor sleep, illness, caffeine, and altitude shift HR; trust power/pace + RPE on those days.",
        "Re-test every 6-8 weeks or after a phase change, illness, or detraining; zones expire.",
    ]
    # Beta-blocker / medication gate is surfaced only when relevant context exists; keep the general note.
    caveats.append(
        "Beta-blockers or rate-limiting drugs invalidate %HRmax zones — use only threshold HRs measured on the "
        "medication, lead with power/pace + RPE, and keep interpretation with the supervising clinician."
    )
    return caveats


def build_metabolic_profile(metrics: dict[str, Any]) -> dict[str, Any] | None:
    """Interpret the substrate / fat-oxidation portion of the CPET."""
    mfo = _as_float(metrics.get("fatmax_g_min"))
    fatmax_hr = _as_float(metrics.get("fatmax_hr_bpm"))
    fatmax_pct = _as_float(metrics.get("fatmax_vo2_pct"))
    vt1_hr = _as_float(metrics.get("vt1_hr_bpm"))
    peak_rer = _as_float(metrics.get("peak_rer"))
    if mfo is None and fatmax_hr is None:
        return None

    profile: dict[str, Any] = {}
    if mfo is not None:
        mfo_class = "High (trained/elite)"
        for cutoff, label in _MFO_BANDS:
            if mfo < cutoff:
                mfo_class = label
                break
        profile["mfo_g_min"] = round(mfo, 2)
        profile["mfo_g_h"] = round(mfo * 60)
        profile["mfo_class"] = mfo_class

    if fatmax_hr is not None:
        profile["fatmax_hr"] = round(fatmax_hr)
        if vt1_hr is not None:
            if fatmax_hr < vt1_hr - 1:
                profile["fatmax_vs_vt1"] = "just below your aerobic threshold (VT1), as expected"
            elif fatmax_hr <= vt1_hr + 1:
                profile["fatmax_vs_vt1"] = "right at your aerobic threshold (VT1)"
            else:
                profile["fatmax_vs_vt1"] = "above VT1 — unusual; re-check the fat-oxidation curve and effort quality"
    if fatmax_pct is not None:
        profile["fatmax_pct_vo2max"] = round(fatmax_pct)

    # Interpretation logic.
    notes: list[str] = []
    if mfo is not None and mfo < 0.40:
        notes.append(
            "A low peak fat-oxidation rate points to glycogen reliance at easy intensities (metabolic inflexibility). "
            "Prescribe more Zone 2 volume and re-test in 6-8 weeks, expecting roughly a 15-30% rise."
        )
    elif mfo is not None:
        notes.append(
            "Fat oxidation is in the expected range; keep a consistent Zone 2 base to defend and slowly extend it "
            "(a ~15-30% gain and a rightward FatMax shift are realistic over 6-8 weeks of volume)."
        )
    if peak_rer is not None and peak_rer >= 1.0:
        notes.append(
            "Any fat/carbohydrate numbers reported near or above the second threshold (RER ~1.0+) are not valid "
            "and are omitted — CO2 from lactate buffering inflates the estimate."
        )
    profile["interpretation"] = notes
    return profile


def _training_narrative(metrics: dict[str, Any], zones: dict[str, Any]) -> str | None:
    """Plain-language training-zone explanation for a coach."""
    if not zones.get("has_zones"):
        return None
    vt1_hr = _as_float(metrics.get("vt1_hr_bpm"))
    vt2_hr = _as_float(metrics.get("vt2_hr_bpm"))
    z2 = zones.get("zone2", {})
    primary = zones.get("primary_anchor", "the measured anchor")

    parts: list[str] = []
    if vt1_hr is not None and vt2_hr is not None:
        parts.append(
            f"Your first lactate threshold (LT1, ~{LT1_LACTATE_MMOL:g} mmol aerobic threshold, measured as VT1) is "
            f"{round(vt1_hr)} bpm, and your second threshold (LT2, ~{LT2_LACTATE_MMOL:g} mmol / MLSS, measured as VT2) "
            f"is {round(vt2_hr)} bpm."
        )

    if z2.get("target_hr") and z2.get("ceiling_hr"):
        power = f" ({z2['power']}, work the upper end)" if z2.get("power") else ""
        parts.append(
            f"True endurance Zone 2 is the narrow window just UNDER LT1, not the whole span up to VT2. Work the top of "
            f"the band: aim about {z2['target_hr']} and cap at {z2['ceiling_hr']} bpm — that ceiling is your ~2 mmol "
            f"lactate line{power}. This is the highest intensity where lactate still clears, so it gives the biggest "
            "mitochondrial and fat-oxidation stimulus for the least fatigue; the bulk of weekly hours belong here."
        )
        if z2.get("fatmax_floor"):
            parts.append(
                f"Your FatMax ({z2['fatmax_floor']}) is the FLOOR of this window, not the target — treat it as the "
                "bottom of Zone 2, and push toward the top just under LT1."
            )
        if z2.get("training_pattern") == "divergent":
            parts.append(
                "Your FatMax sits well below LT1 (a recreational pattern), so the target is still just under LT1 but your "
                "productive window legitimately extends down to FatMax; if lactate does not settle near the top, bias a "
                "few bpm lower and confirm with a lactate strip. Percent-of-max-HR zone charts do not fit you — anchor on "
                "your measured VT1."
            )

    if primary in ("power", "pace"):
        parts.append(
            f"Prescribe off {primary}: at these low intensities heart rate lags the effort by 20-30 s and drifts on long "
            "sessions, so treat bpm as a cross-check."
        )
    parts.append("Use the Threshold zone (around VT2/LT2) as the specific lever to raise your anaerobic threshold.")
    return " ".join(p for p in parts if p)


def _metabolic_narrative(metrics: dict[str, Any], profile: dict[str, Any] | None) -> str | None:
    """Plain-language metabolic/substrate explanation for a coach."""
    if not profile:
        return None
    bits = []
    fatmax_hr = profile.get("fatmax_hr")
    mfo = profile.get("mfo_g_min")
    if fatmax_hr is not None and mfo is not None:
        pos = profile.get("fatmax_vs_vt1", "in your endurance range")
        bits.append(
            f"Your fat oxidation peaks (FatMax) at about {fatmax_hr} bpm, {pos}, burning roughly {mfo:g} g of fat per "
            f"minute (~{profile.get('mfo_g_h', round(mfo * 60))} g/h) — a {profile.get('mfo_class', '').lower()} rate."
        )
    elif mfo is not None:
        bits.append(f"Peak fat oxidation is about {mfo:g} g/min (~{profile.get('mfo_g_h')} g/h), a {profile.get('mfo_class', '').lower()} rate.")
    elif fatmax_hr is not None:
        bits.append(f"Fat oxidation peaks (FatMax) at about {fatmax_hr} bpm, {profile.get('fatmax_vs_vt1', 'in your endurance range')}.")
    bits.append(
        "FatMax marks the peak fat-oxidation rate and sits at the FLOOR of Zone 2; the Zone 2 training target is a "
        "little higher, just under your first lactate threshold. Long sessions in that window build exactly the system "
        "that raises fat oxidation, sparing glycogen on efforts over 2-3 h."
    )
    for note in profile.get("interpretation", []):
        bits.append(note)
    return " ".join(bits)


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
        rows.append({"Gate": "Peak effort", "Status": "Strong", "Interpretation": f"Peak RER {rer:.2f} indicates a clearly maximal effort (ATS/ACCP >=1.15)."})
    elif rer >= 1.10:
        rows.append({"Gate": "Peak effort", "Status": "Maximal", "Interpretation": f"Peak RER {rer:.2f} meets the primary maximal-effort criterion (EACPR/AHA >=1.10)."})
    elif rer >= 1.05:
        rows.append(
            {
                "Gate": "Peak effort",
                "Status": "Borderline",
                "Interpretation": f"Peak RER {rer:.2f}; do not confirm maximal effort on RER alone. Peak VO2 may understate capacity; lean more on VT and VE/VCO2.",
            }
        )
    else:
        rows.append(
            {
                "Gate": "Peak effort",
                "Status": "Submaximal",
                "Interpretation": f"Peak RER {rer:.2f} (<1.05); likely submaximal, so do not read low peak VO2 as a true ceiling.",
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

    peak_ve = _as_float(metrics.get("peak_ve_l_min"))
    mvv = _as_float(metrics.get("mvv_l_min"))
    if peak_ve is not None and mvv:
        ve_ratio = peak_ve / mvv * 100
        if ve_ratio >= 85:
            rows.append(
                {
                    "Gate": "Ventilatory ceiling",
                    "Status": "Reached",
                    "Interpretation": (
                        f"Peak VE was {ve_ratio:.0f}% of the predicted ventilation ceiling; ventilation approached "
                        "its limit, which is consistent with a strong maximal effort in a fit person."
                    ),
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


def _build_consistency_checks(
    metrics: dict[str, Any],
    fitness: dict[str, Any] | None,
    raw_metrics: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Internal-consistency and cart-vs-norm validation of the entered CPET values.

    Cross-checks only run on values the report actually reported. ``raw_metrics``
    is the pre-normalisation input; a value derived by ``normalize_cpet_metrics``
    (e.g. absolute VO2 back-computed from relative VO2, or O2 pulse from VO2/HR)
    is skipped so the check can't trivially "agree" with its own derivation.
    """
    rows: list[dict[str, str]] = []
    raw = raw_metrics if raw_metrics is not None else metrics

    def add(check: str, status: str, detail: str) -> None:
        rows.append({"Check": check, "Status": status, "Detail": detail})

    def reported(field: str) -> bool:
        return raw.get(field) is not None and raw.get(field) != ""

    vt1 = _as_float(metrics.get("vt1_vo2_ml_kg_min"))
    vt2 = _as_float(metrics.get("vt2_vo2_ml_kg_min"))
    peak = _as_float(metrics.get("peak_vo2_ml_kg_min"))
    ordered = [v for v in (vt1, vt2, peak) if v is not None]
    if len(ordered) >= 2:
        if ordered != sorted(ordered):
            add("Threshold ordering", "Check", "VT1/VT2/peak VO2 are not in ascending order; re-check which value maps to which threshold.")
        elif len(set(ordered)) != len(ordered):
            add("Threshold ordering", "Check", "Two of VT1/VT2/peak VO2 are equal, which is physiologically implausible; confirm the threshold values.")
        else:
            add("Threshold ordering", "OK", "VT1 < VT2 < peak VO2 as expected.")

    rel = _as_float(metrics.get("peak_vo2_ml_kg_min"))
    abs_vo2 = _as_float(metrics.get("peak_vo2_l_min"))
    weight = _as_float(metrics.get("weight_kg"))
    # Only meaningful when relative and absolute VO2 were BOTH reported (not one
    # back-derived from the other via weight).
    if rel is not None and abs_vo2 is not None and weight and reported("peak_vo2_ml_kg_min") and reported("peak_vo2_l_min"):
        implied = abs_vo2 * 1000.0 / weight
        if abs(implied - rel) <= max(2.0, 0.07 * rel):
            add("Relative vs absolute VO2", "OK", f"Absolute {abs_vo2:.2f} L/min at {weight:.0f} kg implies {implied:.0f} mL/kg/min, matching the reported {rel:.0f}.")
        else:
            add("Relative vs absolute VO2", "Check", f"Absolute {abs_vo2:.2f} L/min at {weight:.0f} kg implies {implied:.0f} mL/kg/min, but relative is {rel:.0f}. Verify body weight and units.")

    o2p = _as_float(metrics.get("o2_pulse_ml_beat"))
    peak_hr = _as_float(metrics.get("peak_hr_bpm"))
    # Only when O2 pulse was reported directly (not derived from VO2/HR).
    if o2p is not None and abs_vo2 is not None and peak_hr and reported("o2_pulse_ml_beat"):
        implied_o2p = abs_vo2 * 1000.0 / peak_hr
        if abs(implied_o2p - o2p) <= max(1.5, 0.15 * o2p):
            add("O2 pulse consistency", "OK", f"VO2/HR = {abs_vo2:.2f} L/min / {peak_hr:.0f} bpm = {implied_o2p:.1f} mL/beat, matching the reported O2 pulse.")
        else:
            add("O2 pulse consistency", "Check", f"VO2/HR implies {implied_o2p:.1f} mL/beat but O2 pulse is {o2p:.1f}; peak VO2 and peak HR may be from different time points.")

    peak_pct = _as_float(metrics.get("peak_vo2_pct_pred"))
    if fitness and fitness.get("percentile") is not None and peak_pct is not None and peak_pct >= 100:
        pct = fitness["percentile"]
        # A genuine conflict is a clearly high %-predicted paired with a clearly
        # low percentile. Near-100% with a mid percentile is normal agreement.
        if peak_pct >= 115 and pct < 40:
            add(
                "Percent-predicted vs percentile",
                "Conflict",
                f"{peak_pct:.0f}% of predicted looks high but the age/sex/modality percentile is only {fitness.get('percentile_label', '')}. "
                "The predicted-VO2 equation is likely soft; defer to the percentile and note the reference-model difference.",
            )
        else:
            add(
                "Percent-predicted vs percentile",
                "Reconciled",
                f"{peak_pct:.0f}% of predicted and the {fitness.get('percentile_label', '')} both indicate normal-to-strong capacity. "
                "Report the percentile as the headline; %-predicted answers 'normal for a patient?', not 'how fit vs peers?'.",
            )

    return rows


def _build_coach_flags(
    metrics: dict[str, Any],
    client_context: str,
    fitness: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    peak_vo2 = _as_float(metrics.get("peak_vo2_ml_kg_min"))
    peak_pct = _as_float(metrics.get("peak_vo2_pct_pred"))
    ve_slope = _as_float(metrics.get("ve_vco2_slope"))
    age = _as_float(metrics.get("age_years"))
    br = _as_float(metrics.get("breathing_reserve_pct"))
    o2_pulse_pct = _as_float(metrics.get("o2_pulse_pct_pred"))
    vo2_wr = _as_float(metrics.get("vo2_wr_slope_ml_min_w"))
    petco2_at = _as_float(metrics.get("petco2_at_mmhg"))
    spo2 = _as_float(metrics.get("spo2_nadir_pct"))
    vt1_pct = _as_float(metrics.get("vt1_pct_peak_vo2"))
    vt2_pct = _as_float(metrics.get("vt2_pct_peak_vo2"))
    peak_rer = _as_float(metrics.get("peak_rer"))
    dyspnea_context = client_context == "cardiology"

    # Headline aerobic capacity: prefer the age/sex/modality percentile classification.
    if peak_vo2 is not None and fitness and fitness.get("percentile") is not None:
        percentile = fitness["percentile"]
        priority = "High" if percentile < 20 else ("Medium" if percentile < 40 else "Routine")
        flags.append(
            {
                "Priority": priority,
                "Area": "Aerobic capacity (age/sex norms)",
                "Signal": (
                    f"Peak VO2 {peak_vo2:.1f} mL/kg/min = {fitness['category']} "
                    f"({fitness.get('percentile_label', '')}) for {fitness.get('reference_group', 'this profile')}, "
                    f"{fitness.get('modality_used', 'unknown')} norms."
                ),
                "Coach action": (
                    "Classify against age/sex/modality percentiles, not the cart's one-word label. "
                    + fitness["reference"] + "."
                ),
            }
        )

    has_percentile = fitness is not None and fitness.get("percentile") is not None
    if peak_vo2 is None:
        flags.append(
            {
                "Priority": "High",
                "Area": "Missing headline metric",
                "Signal": "Peak VO2 is missing.",
                "Coach action": "Add peak VO2 before building fitness or prognosis explanations.",
            }
        )
    elif has_percentile:
        # Percentile headline already added above; add sport-context caveats additively.
        if client_context == "endurance":
            if peak_vo2 < 50:
                flags.append(
                    {
                        "Priority": "High",
                        "Area": "Athlete aerobic ceiling",
                        "Signal": f"Peak VO2 {peak_vo2:.1f} mL/kg/min is below the usual endurance-athlete range despite a normal population percentile.",
                        "Coach action": "Verify effort quality, protocol, health status, and training load; population norms can look adequate while under-serving the sport.",
                    }
                )
            flags.append(
                {
                    "Priority": "Routine",
                    "Area": "Endurance-athlete context",
                    "Signal": "General-population percentile norms can under-rate a trained endurance athlete.",
                    "Coach action": "Judge against the sport, prior tests, and threshold/economy/durability data, not population norms alone.",
                }
            )
        elif client_context == "hybrid":
            if peak_vo2 < 45:
                flags.append(
                    {
                        "Priority": "Medium",
                        "Area": "Hybrid-sport aerobic base",
                        "Signal": f"Peak VO2 {peak_vo2:.1f} mL/kg/min is a modest aerobic base for hybrid competition.",
                        "Coach action": "Combine threshold work with sport-specific repeated efforts to lift the ceiling.",
                    }
                )
            flags.append(
                {
                    "Priority": "Routine",
                    "Area": "Hybrid-sport context",
                    "Signal": "Ramp CPET captures the aerobic ceiling but not repeated mixed-modality station fatigue.",
                    "Coach action": "Pair the aerobic ceiling with sled, carry, burpee, and pre-fatigued sport-specific checks.",
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
        # No age/sex to place percentiles: fall back to coarse capacity bands and
        # prompt for the demographics needed to classify properly.
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
                "Coach action": "Add age and biological sex to classify against percentile norms instead of coarse bands.",
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
        # Arena/Myers ventilatory classes (Circulation 2007): VC-I <30, II 30-35.9,
        # III 36-44.9, IV >=45. Normal slope rises ~0.12-0.13/yr of age (Habedank).
        if ve_slope >= 45:
            priority, meaning = "High", "Arena ventilatory class IV (>=45)"
        elif ve_slope >= 36:
            priority, meaning = "High", "Arena class III (36-44.9), elevated inefficiency"
        elif ve_slope >= 30:
            priority, meaning = "Medium", "Arena class II (30-35.9), borderline"
        elif ve_slope >= 26:
            priority, meaning = "Routine", "class I, normal/efficient"
        else:
            priority, meaning = "Routine", "class I, excellent/highly efficient"
        signal = f"VE/VCO2 slope is {ve_slope:.1f}, {meaning}."
        if age is not None:
            expected = round(0.125 * age + 22.0, 1)  # midpoint of Habedank sex equations
            signal += f" Age-typical normal is roughly {expected:.0f}."
        flags.append(
            {
                "Priority": priority,
                "Area": "Ventilatory efficiency",
                "Signal": signal,
                "Coach action": "Read with PETCO2, breathing reserve, symptoms, and cardiology/pulmonary context. Arena classes were validated in heart failure; in a healthy person a low slope simply confirms efficient ventilation.",
            }
        )

    if br is not None:
        maximal_effort = peak_rer is not None and peak_rer >= 1.10
        spo2_confirmed_ok = spo2 is not None and spo2 >= 94
        desat_or_dyspnea = (
            (spo2 is not None and spo2 < 94)
            or (petco2_at is not None and petco2_at < 30)
            or dyspnea_context
        )
        if br < 15 and desat_or_dyspnea:
            flags.append(
                {
                    "Priority": "High",
                    "Area": "Breathing reserve",
                    "Signal": f"Breathing reserve is {br:.0f}% with desaturation, low PETCO2, or a dyspnea-limited context.",
                    "Coach action": "This combination can fit a true ventilatory limitation; defer medical interpretation to the CPET clinician and avoid unsupervised intensity progression.",
                }
            )
        elif br < 15 and maximal_effort and spo2_confirmed_ok:
            flags.append(
                {
                    "Priority": "Routine",
                    "Area": "Breathing reserve",
                    "Signal": f"Breathing reserve is {br:.0f}% (ventilation reached its ceiling at peak; SpO2 stayed normal).",
                    "Coach action": "In a fit person at true maximal effort with preserved oxygen saturation, a low/absent breathing reserve is a normal ceiling phenomenon, not on its own a limitation.",
                }
            )
        elif br < 15 and maximal_effort:
            flags.append(
                {
                    "Priority": "Medium",
                    "Area": "Breathing reserve",
                    "Signal": f"Breathing reserve is {br:.0f}%; SpO2 was not recorded.",
                    "Coach action": "A low breathing reserve at true maximal effort is usually a normal ceiling in a fit person, but without SpO2 you cannot rule out exertional desaturation. Confirm no limiting dyspnea or desaturation before progressing intensity.",
                }
            )
        elif br < 15:
            flags.append(
                {
                    "Priority": "High",
                    "Area": "Breathing reserve",
                    "Signal": f"Breathing reserve is {br:.0f}% and effort was not confirmed maximal.",
                    "Coach action": "Possible ventilatory limitation; defer medical interpretation to the CPET clinician.",
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

    if o2_pulse_pct is not None:
        if o2_pulse_pct < 80:
            flags.append(
                {
                    "Priority": "High",
                    "Area": "O2 pulse",
                    "Signal": f"O2 pulse is {o2_pulse_pct:.0f}% predicted.",
                    "Coach action": "Low O2 pulse can support oxygen-delivery limitation; refer interpretation to clinician.",
                }
            )
        elif o2_pulse_pct >= 100:
            flags.append(
                {
                    "Priority": "Routine",
                    "Area": "O2 pulse",
                    "Signal": f"O2 pulse is {o2_pulse_pct:.0f}% predicted (reassuring).",
                    "Coach action": "A normal/high O2 pulse without an early plateau is against a stroke-volume/oxygen-delivery limitation; still read the O2-pulse curve shape, not just the peak.",
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

    if not build_training_zones(metrics).get("has_zones"):
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


def _talking_points(
    client_context: str,
    metrics: dict[str, Any] | None = None,
    fitness: dict[str, Any] | None = None,
) -> list[str]:
    metrics = metrics or {}
    points = [
        "Start with the validity gate: peak RER, HR response, symptoms, and protocol quality.",
        "Peak VO2 is the engine size, but it is not the whole story.",
        "Endurance Zone 2 is a narrow band that tops out at VT1/LT1 (near FatMax) — not the whole VT1-to-VT2 span, which is tempo-to-threshold work.",
        "Prescribe zones on power or pace when available; heart rate lags and drifts and is a cross-check, not the primary anchor above VT2.",
        "VE/VCO2 slope, breathing reserve, O2 pulse, PETCO2, and SpO2 are medical-pattern clues, not coaching diagnoses.",
        "Compare serial tests only when protocol and preparation are similar.",
    ]

    if fitness and fitness.get("percentile") is not None:
        points.append(
            f"Fitness headline: peak VO2 is {fitness['category']} ({fitness.get('percentile_label', '')}) "
            f"on {fitness.get('modality_used', 'unknown')} norms for {fitness.get('reference_group', 'this profile')}. "
            "Report this age/sex/modality percentile, not the cart's one-word fitness label."
        )
        if fitness.get("modality_used") == "cycle":
            points.append(
                "This is a cycle test: cycle VO2peak reads ~15% below treadmill, so a cart that grades it against "
                "treadmill norms (a common cause of a misleading 'fair/poor' label) understates true fitness."
            )

    peak_pct = _as_float(metrics.get("peak_vo2_pct_pred"))
    if peak_pct is not None and peak_pct > 110:
        points.append(
            f"'{peak_pct:.0f}% of predicted' reflects the reference equation (often soft for young/female clients), "
            "not a fitness grade; do not present >100% predicted as exceptional fitness."
        )

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


def _normalize_notation(text: str) -> str:
    """Fold gas-analysis glyph variants (V-dot, primes, subscripts) to plain ASCII.

    Cortex MetaSoft exports the dotted volume symbols (V\u0307O2, V\u0307CO2, V\u0307E) as ``V'O2`` /
    ``V'CO2`` / ``V'E`` \u2014 an apostrophe standing in for the dot. Without folding that
    apostrophe, every ``VO2`` label pattern misses on Cortex reports.
    """
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
    # Fold "V" + (combining dot / prime / apostrophe / backtick / period) -> "V".
    text = re.sub(r"V[\u0307\u02d9\u2032\u02b9'`.]", "V", text)
    text = re.sub(r"O[\u2082\u00b2]", "O2", text)
    text = re.sub(r"CO[\u2082\u00b2]", "CO2", text)
    return text


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", _normalize_notation(text)).strip()


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
