"""Wearable-data ingestion and 5-domain wheel scoring."""

from __future__ import annotations

import csv
import io
import math
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from db.database import get_connection
from config import wearable_wheel_data as _wheel_cfg

CSV_TEMPLATE_HEADER = _wheel_cfg.CSV_TEMPLATE_HEADER
DIRECT_DOMAIN_METRICS = _wheel_cfg.DIRECT_DOMAIN_METRICS
DOMAIN_ORDER = _wheel_cfg.DOMAIN_ORDER
PROXY_DOMAIN_WEIGHTS = _wheel_cfg.PROXY_DOMAIN_WEIGHTS
WEARABLE_METRIC_SPECS = _wheel_cfg.WEARABLE_METRIC_SPECS
WEARABLE_WHEEL_DOMAINS = _wheel_cfg.WEARABLE_WHEEL_DOMAINS
MAX_OPTIONAL_DOMAIN_WEIGHT_SHARE = getattr(_wheel_cfg, "MAX_OPTIONAL_DOMAIN_WEIGHT_SHARE", 0.35)
WEARABLE_METRIC_ALIASES = getattr(_wheel_cfg, "WEARABLE_METRIC_ALIASES", {})


def get_metric_specs() -> dict[str, dict]:
    return WEARABLE_METRIC_SPECS


def get_domain_specs() -> dict[str, dict]:
    return WEARABLE_WHEEL_DOMAINS


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    columns: set[str] = set()
    for row in rows:
        if isinstance(row, sqlite3.Row):
            columns.add(str(row["name"]).lower())
        else:
            columns.add(str(row[1]).lower())
    return columns


def _ensure_wearable_measurements_schema(conn: sqlite3.Connection) -> None:
    """Self-heal legacy wearable tables that predate source/external columns."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS wearable_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            metric_code TEXT NOT NULL,
            metric_name TEXT,
            value REAL NOT NULL,
            unit TEXT,
            measured_at TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            external_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, metric_code, measured_at, source)
        )"""
    )

    columns = _table_columns(conn, "wearable_measurements")
    missing_columns = {
        "metric_name": "TEXT",
        "unit": "TEXT",
        "measured_at": "TEXT",
        "source": "TEXT DEFAULT 'manual'",
        "external_id": "TEXT",
    }

    for column_name, column_sql in missing_columns.items():
        if column_name in columns:
            continue
        try:
            conn.execute(
                f"ALTER TABLE wearable_measurements ADD COLUMN {column_name} {column_sql}"
            )
        except sqlite3.OperationalError as exc:
            if "duplicate column name" in str(exc).lower():
                continue
            raise

    columns = _table_columns(conn, "wearable_measurements")
    if "measured_at" in columns:
        if "created_at" in columns:
            conn.execute(
                """
                UPDATE wearable_measurements
                SET measured_at = COALESCE(NULLIF(measured_at, ''), created_at, datetime('now'))
                """
            )
        else:
            conn.execute(
                """
                UPDATE wearable_measurements
                SET measured_at = COALESCE(NULLIF(measured_at, ''), datetime('now'))
                """
            )
    if "source" in columns:
        conn.execute(
            """
            UPDATE wearable_measurements
            SET source = 'manual'
            WHERE source IS NULL OR TRIM(source) = ''
            """
        )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_wearable_user_metric ON wearable_measurements(user_id, metric_code, measured_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_wearable_user_time ON wearable_measurements(user_id, measured_at)"
    )
    conn.commit()


def _get_goal_weight_kg(user_id: int) -> float | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT goal_weight_kg FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    value = row["goal_weight_kg"]
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def build_wearable_csv_template() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_TEMPLATE_HEADER)
    writer.writerow(["resting_heart_rate_bpm", "54", "bpm", "2026-03-26T07:00:00", "wearable", ""])
    writer.writerow(["sleep_efficiency_pct", "92", "%", "2026-03-26T07:00:00", "wearable", ""])
    writer.writerow(["recovery_score", "81", "score", "2026-03-26T07:00:00", "wearable", ""])
    writer.writerow(["systolic_bp_mmhg", "118", "mmHg", "2026-03-26T07:00:00", "Withings BPM Connect Pro", ""])
    writer.writerow(["cgm_avg_glucose_mgdl", "101", "mg/dL", "2026-03-26T07:00:00", "CGM FreeStyle Libre", ""])
    writer.writerow(["body_weight_kg", "78.6", "kg", "2026-03-26T07:00:00", "InBody H40 Home Scale", ""])
    return output.getvalue()


def _normalize_key(value: str | None) -> str:
    if not value:
        return ""
    normalized = str(value).strip().lower()
    normalized = re.sub(r"[^\w]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def _normalize_metric_code(metric_code: str | None) -> tuple[str | None, bool]:
    code = _normalize_key(metric_code)
    if not code:
        return None, False
    if code in WEARABLE_METRIC_SPECS:
        return code, False
    alias = WEARABLE_METRIC_ALIASES.get(code)
    if alias:
        return alias, True
    return None, False


def _normalize_unit(unit: str | None) -> str:
    if not unit:
        return ""
    value = str(unit).strip().lower()
    value = value.replace("°", "")
    value = value.replace(" ", "")
    return value


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip()
    if not raw:
        return None
    # Accept decimal comma exports.
    raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _convert_value_to_canonical(metric_code: str, value: float, unit: str | None) -> tuple[float, bool]:
    normalized_unit = _normalize_unit(unit)
    converted = False
    out = float(value)

    if metric_code == "cgm_avg_glucose_mgdl":
        if normalized_unit in {"mmol/l", "mmoll", "mmol"}:
            out = out * 18.0182
            converted = True
    elif metric_code == "body_weight_kg":
        if normalized_unit in {"lb", "lbs", "pound", "pounds"}:
            out = out * 0.45359237
            converted = True
        elif normalized_unit in {"g", "gram", "grams"}:
            out = out / 1000.0
            converted = True
    elif metric_code == "kilojoule_expended":
        if normalized_unit in {"kcal", "calorie", "calories"}:
            out = out * 4.184
            converted = True
    elif metric_code in {"systolic_bp_mmhg", "diastolic_bp_mmhg"}:
        if normalized_unit in {"kpa"}:
            out = out * 7.50062
            converted = True
    elif metric_code == "body_temperature_deviation_c":
        if normalized_unit in {"f", "degf", "fahrenheit"}:
            # Delta/offset conversion (not absolute temperature).
            out = out * (5.0 / 9.0)
            converted = True
    elif metric_code in {"cgm_time_in_range_pct", "sleep_efficiency_pct", "sleep_consistency_pct", "sleep_performance_pct"}:
        if normalized_unit in {"fraction", "ratio"} and 0.0 <= out <= 1.2:
            out = out * 100.0
            converted = True
    elif metric_code in {"spo2_pct", "overnight_spo2_avg_pct", "overnight_spo2_nadir_pct"}:
        if normalized_unit in {"fraction", "ratio"} and 0.0 <= out <= 1.2:
            out = out * 100.0
            converted = True

    return out, converted


def _expand_bp_pair_row(row: dict[str, Any], metric_code: str | None) -> list[dict[str, Any]]:
    if metric_code != "blood_pressure_pair":
        return [row]
    raw_value = str(row.get("value") or "").strip()
    match = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*[/|]\s*([0-9]+(?:\.[0-9]+)?)\s*$", raw_value)
    if not match:
        return []
    systolic, diastolic = match.group(1), match.group(2)
    base = dict(row)
    return [
        {**base, "metric_code": "systolic_bp_mmhg", "value": systolic, "unit": base.get("unit") or "mmHg"},
        {**base, "metric_code": "diastolic_bp_mmhg", "value": diastolic, "unit": base.get("unit") or "mmHg"},
    ]


def save_measurements(user_id: int, rows: list[dict[str, Any]], default_source: str = "manual") -> dict:
    """Insert wearable measurements."""
    inserted = 0
    skipped_unknown = 0
    skipped_invalid = 0
    normalized_aliases = 0
    unit_converted = 0
    bp_split = 0

    conn = get_connection()
    try:
        _ensure_wearable_measurements_schema(conn)

        for raw_row in rows:
            raw_metric_code = raw_row.get("metric_code")
            normalized_code, alias_used = _normalize_metric_code(str(raw_metric_code or ""))
            if alias_used:
                normalized_aliases += 1

            expanded_rows = _expand_bp_pair_row(raw_row, normalized_code)
            if normalized_code == "blood_pressure_pair":
                if expanded_rows:
                    bp_split += 1
                else:
                    skipped_invalid += 1
                    continue

            if not expanded_rows:
                skipped_invalid += 1
                continue

            for row in expanded_rows:
                metric_code, alias_used_expanded = _normalize_metric_code(str(row.get("metric_code") or ""))
                if alias_used_expanded:
                    normalized_aliases += 1
                if not metric_code or metric_code not in WEARABLE_METRIC_SPECS:
                    skipped_unknown += 1
                    continue

                value = _to_float(row.get("value"))
                if value is None:
                    skipped_invalid += 1
                    continue

                converted_value, did_convert = _convert_value_to_canonical(
                    metric_code,
                    value,
                    row.get("unit"),
                )
                if did_convert:
                    unit_converted += 1

                measured_at = (row.get("measured_at") or "").strip()
                if not measured_at:
                    measured_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")

                source = (row.get("source") or default_source).strip() or default_source
                external_id = row.get("external_id")
                spec = WEARABLE_METRIC_SPECS[metric_code]

                conn.execute(
                    """INSERT OR REPLACE INTO wearable_measurements
                       (user_id, metric_code, metric_name, value, unit, measured_at, source, external_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        metric_code,
                        spec["label"],
                        float(converted_value),
                        spec.get("unit"),
                        measured_at,
                        source,
                        external_id,
                    ),
                )
                inserted += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "inserted": inserted,
        "skipped_unknown": skipped_unknown,
        "skipped_invalid": skipped_invalid,
        "normalized_aliases": normalized_aliases,
        "unit_converted": unit_converted,
        "bp_split": bp_split,
    }


def import_measurements_csv_text(user_id: int, csv_text: str, default_source: str = "csv_upload") -> dict:
    if not csv_text or not csv_text.strip():
        return {
            "inserted": 0,
            "skipped_unknown": 0,
            "skipped_invalid": 0,
            "normalized_aliases": 0,
            "unit_converted": 0,
            "bp_split": 0,
        }

    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for row in reader:
        metric_code = (
            row.get("metric_code")
            or row.get("metric")
            or row.get("parameter")
            or row.get("name")
        )
        value = row.get("value") or row.get("reading") or row.get("measurement")
        measured_at = (
            row.get("measured_at")
            or row.get("timestamp")
            or row.get("datetime")
            or row.get("date")
        )
        source = row.get("source") or row.get("device") or default_source

        rows.append(
            {
                "metric_code": metric_code,
                "value": value,
                "unit": row.get("unit") or row.get("units"),
                "measured_at": measured_at,
                "source": source,
                "external_id": row.get("external_id") or row.get("id"),
            }
        )
    return save_measurements(user_id, rows, default_source=default_source)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def get_latest_measurements(user_id: int) -> dict[str, dict]:
    """Return latest measurement per metric code."""
    conn = get_connection()
    try:
        _ensure_wearable_measurements_schema(conn)
        rows = conn.execute(
            """
            SELECT wm.metric_code, wm.value, wm.unit, wm.measured_at, wm.source
            FROM wearable_measurements wm
            JOIN (
                SELECT metric_code, MAX(measured_at) AS max_measured_at
                FROM wearable_measurements
                WHERE user_id = ?
                GROUP BY metric_code
            ) latest
              ON latest.metric_code = wm.metric_code
             AND latest.max_measured_at = wm.measured_at
            WHERE wm.user_id = ?
            """,
            (user_id, user_id),
        ).fetchall()
    finally:
        conn.close()

    out = {}
    for row in rows:
        out[row["metric_code"]] = dict(row)
    return out


def _get_measurement_history(user_id: int, lookback_days: int = 60) -> dict[str, list[dict]]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff_days = float(lookback_days)

    conn = get_connection()
    try:
        _ensure_wearable_measurements_schema(conn)
        rows = conn.execute(
            """
            SELECT metric_code, value, unit, measured_at, source
            FROM wearable_measurements
            WHERE user_id = ?
            ORDER BY measured_at DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    history: dict[str, list[dict]] = {code: [] for code in WEARABLE_METRIC_SPECS}
    for row in rows:
        metric_code = row["metric_code"]
        if metric_code not in history:
            continue
        parsed_dt = _parse_timestamp(row["measured_at"])
        if parsed_dt is None:
            continue
        age_days = max(0.0, (now - parsed_dt).total_seconds() / 86400.0)
        if age_days > cutoff_days:
            continue
        history[metric_code].append(
            {
                "value": float(row["value"]),
                "unit": row["unit"],
                "measured_at": row["measured_at"],
                "source": row["source"],
                "parsed_dt": parsed_dt,
                "age_days": age_days,
            }
        )
    return history


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _normalize(value: float, spec: dict, goal_weight_kg: float | None = None) -> float | None:
    mode = spec.get("score_mode")
    if mode is None:
        return None

    if spec.get("transform") == "abs":
        value = abs(value)

    if mode == "higher_better":
        low = float(spec["min_value"])
        high = float(spec["max_value"])
        if high <= low:
            return None
        return round(_clamp((value - low) / (high - low) * 100.0, 0.0, 100.0), 1)

    if mode == "lower_better":
        low = float(spec["min_value"])
        high = float(spec["max_value"])
        if high <= low:
            return None
        return round(_clamp((high - value) / (high - low) * 100.0, 0.0, 100.0), 1)

    if mode == "target_band":
        hard_min = float(spec["hard_min"])
        optimal_min = float(spec["optimal_min"])
        optimal_max = float(spec["optimal_max"])
        hard_max = float(spec["hard_max"])
        if not (hard_min < optimal_min <= optimal_max < hard_max):
            return None

        if optimal_min <= value <= optimal_max:
            return 100.0
        if value < optimal_min:
            return round(_clamp((value - hard_min) / (optimal_min - hard_min) * 100.0, 0.0, 100.0), 1)
        return round(_clamp((hard_max - value) / (hard_max - optimal_max) * 100.0, 0.0, 100.0), 1)

    if mode == "binary":
        healthy_value = int(spec.get("healthy_value", 0))
        return 100.0 if int(round(value)) == healthy_value else 0.0

    if mode == "goal_distance":
        if goal_weight_kg is None or goal_weight_kg <= 0:
            return 50.0
        distance_pct = abs(value - goal_weight_kg) / goal_weight_kg * 100.0
        # Every 1% away from goal drops score by 6 points.
        return round(_clamp(100.0 - (distance_pct * 6.0), 0.0, 100.0), 1)

    return None


def _exp_decay(age_days: float, half_life_days: float) -> float:
    if half_life_days <= 0:
        return 1.0
    return math.exp(-math.log(2.0) * age_days / half_life_days)


def _smoothed_value(rows: list[dict], half_life_days: float, max_age_days: float) -> float | None:
    valid = [r for r in rows if r["age_days"] <= max_age_days]
    if not valid:
        return None

    weighted_sum = 0.0
    total_weight = 0.0
    for row in valid:
        w = _exp_decay(row["age_days"], half_life_days)
        weighted_sum += float(row["value"]) * w
        total_weight += w
    if total_weight <= 0:
        return None
    return weighted_sum / total_weight


def _smoothed_value_between(
    rows: list[dict],
    half_life_days: float,
    min_age_days: float,
    max_age_days: float,
) -> float | None:
    valid = [r for r in rows if min_age_days <= r["age_days"] <= max_age_days]
    if not valid:
        return None
    weighted_sum = 0.0
    total_weight = 0.0
    for row in valid:
        # Re-center decay inside this window so nearer points in window weigh more.
        relative_age = max(0.0, row["age_days"] - min_age_days)
        w = _exp_decay(relative_age, half_life_days)
        weighted_sum += float(row["value"]) * w
        total_weight += w
    if total_weight <= 0:
        return None
    return weighted_sum / total_weight


def _trend_delta_abs_score(
    rows: list[dict],
    spec: dict,
    goal_weight_kg: float | None,
) -> float:
    recent_value = _smoothed_value(rows, half_life_days=3.0, max_age_days=7.0)
    prior_value = _smoothed_value_between(rows, half_life_days=7.0, min_age_days=7.0, max_age_days=30.0)
    if recent_value is None or prior_value is None:
        return 0.0
    recent_abs = _normalize(recent_value, spec, goal_weight_kg=goal_weight_kg)
    prior_abs = _normalize(prior_value, spec, goal_weight_kg=goal_weight_kg)
    if recent_abs is None or prior_abs is None:
        return 0.0
    return float(recent_abs - prior_abs)


def _percentile_rank(values: list[float], current: float) -> float:
    if not values:
        return 50.0
    less_or_equal = sum(1 for v in values if v <= current)
    return (less_or_equal / len(values)) * 100.0


def _freshness_factor(age_days: float) -> float:
    if age_days <= 3:
        return 1.0
    if age_days <= 7:
        return 0.9
    if age_days <= 14:
        return 0.8
    if age_days <= 30:
        return 0.65
    return 0.5


def _blend_personalized_score(abs_score: float, historical_abs_scores: list[float]) -> float:
    # Personal baseline blend activates when there is enough personal history.
    if len(historical_abs_scores) < 7:
        return abs_score
    relative_score = _percentile_rank(historical_abs_scores, abs_score)
    return _clamp((0.7 * abs_score) + (0.3 * relative_score), 0.0, 100.0)


def _weighted_average(items: list[tuple[float, float]]) -> float | None:
    if not items:
        return None
    total_weight = sum(weight for _, weight in items)
    if total_weight <= 0:
        return None
    return sum(score * weight for score, weight in items) / total_weight


def compute_wearable_wheel(user_id: int) -> dict:
    """Compute 5-domain wearable wheel with confidence and metric breakdown."""
    history = _get_measurement_history(user_id, lookback_days=60)
    goal_weight_kg = _get_goal_weight_kg(user_id)

    metric_scores: dict[str, dict] = {}
    for code, spec in WEARABLE_METRIC_SPECS.items():
        rows = history.get(code, [])
        if not rows:
            continue

        rows_sorted = sorted(rows, key=lambda r: r["age_days"])
        latest_row = rows_sorted[0]

        current_value = _smoothed_value(rows, half_life_days=7.0, max_age_days=30.0)
        readiness_value = _smoothed_value(rows, half_life_days=1.5, max_age_days=3.0)
        resilience_value = _smoothed_value(rows, half_life_days=14.0, max_age_days=30.0)

        if current_value is None:
            continue
        if readiness_value is None:
            readiness_value = current_value
        if resilience_value is None:
            resilience_value = current_value

        historical_abs_scores = []
        for row in rows:
            score = _normalize(float(row["value"]), spec, goal_weight_kg=goal_weight_kg)
            if score is not None:
                historical_abs_scores.append(float(score))

        current_abs = _normalize(float(current_value), spec, goal_weight_kg=goal_weight_kg)
        readiness_abs = _normalize(float(readiness_value), spec, goal_weight_kg=goal_weight_kg)
        resilience_abs = _normalize(float(resilience_value), spec, goal_weight_kg=goal_weight_kg)
        if current_abs is None or readiness_abs is None or resilience_abs is None:
            continue

        current_score = _blend_personalized_score(float(current_abs), historical_abs_scores)
        readiness_score = _blend_personalized_score(float(readiness_abs), historical_abs_scores)
        resilience_score = _blend_personalized_score(float(resilience_abs), historical_abs_scores)

        trend_delta = _trend_delta_abs_score(rows, spec, goal_weight_kg=goal_weight_kg)
        trend_adjust = _clamp(trend_delta * 0.25, -8.0, 8.0)
        current_score = _clamp(current_score + trend_adjust, 0.0, 100.0)

        freshness = _freshness_factor(latest_row["age_days"])
        base_weight = float(spec.get("weight", 1.0))
        effective_weight = base_weight * freshness

        metric_scores[code] = {
            "code": code,
            "label": spec["label"],
            "raw_value": float(current_value),
            "latest_raw_value": float(latest_row["value"]),
            "unit": spec.get("unit"),
            "score_100": round(current_score, 1),
            "readiness_score_100": round(readiness_score, 1),
            "resilience_score_100": round(resilience_score, 1),
            "measured_at": latest_row["measured_at"],
            "domain": spec["domain"],
            "weight": base_weight,
            "effective_weight": round(effective_weight, 4),
            "freshness_factor": round(freshness, 2),
            "trend_delta_100": round(trend_delta, 2),
            "trend_adjust_100": round(trend_adjust, 2),
            "optional": bool(spec.get("optional")),
        }

    domains = {}
    for domain_code in DOMAIN_ORDER:
        domain_spec = WEARABLE_WHEEL_DOMAINS[domain_code]
        is_proxy = bool(domain_spec.get("is_proxy"))

        if not is_proxy:
            codes = DIRECT_DOMAIN_METRICS.get(domain_code, [])
            required_codes = [c for c in codes if not WEARABLE_METRIC_SPECS.get(c, {}).get("optional")]
            total = len(required_codes)
            weighted_current_required = []
            weighted_readiness_required = []
            weighted_resilience_required = []
            weighted_current_optional = []
            weighted_readiness_optional = []
            weighted_resilience_optional = []
            available_codes = []
            freshness_values = []
            available_required_codes = []

            for code in codes:
                metric = metric_scores.get(code)
                if not metric:
                    continue
                available_codes.append(code)
                if code in required_codes:
                    available_required_codes.append(code)
                w = float(metric["effective_weight"])
                if code in required_codes:
                    weighted_current_required.append((metric["score_100"], w))
                    weighted_readiness_required.append((metric["readiness_score_100"], w))
                    weighted_resilience_required.append((metric["resilience_score_100"], w))
                else:
                    weighted_current_optional.append((metric["score_100"], w))
                    weighted_readiness_optional.append((metric["readiness_score_100"], w))
                    weighted_resilience_optional.append((metric["resilience_score_100"], w))
                freshness_values.append(float(metric["freshness_factor"]))

            optional_weight_scale = 1.0
            required_weight_total = sum(weight for _, weight in weighted_current_required)
            optional_weight_total = sum(weight for _, weight in weighted_current_optional)
            if required_weight_total > 0 and optional_weight_total > 0:
                max_optional_total = required_weight_total * (
                    MAX_OPTIONAL_DOMAIN_WEIGHT_SHARE / (1.0 - MAX_OPTIONAL_DOMAIN_WEIGHT_SHARE)
                )
                if optional_weight_total > max_optional_total > 0:
                    optional_weight_scale = max_optional_total / optional_weight_total

            weighted_current = list(weighted_current_required)
            weighted_readiness = list(weighted_readiness_required)
            weighted_resilience = list(weighted_resilience_required)

            for score, weight in weighted_current_optional:
                weighted_current.append((score, weight * optional_weight_scale))
            for score, weight in weighted_readiness_optional:
                weighted_readiness.append((score, weight * optional_weight_scale))
            for score, weight in weighted_resilience_optional:
                weighted_resilience.append((score, weight * optional_weight_scale))

            coverage = (len(available_required_codes) / total) if total else 1.0
            freshness_quality = (sum(freshness_values) / len(freshness_values)) if freshness_values else 0.0
            confidence = coverage * freshness_quality
            available_required = len(available_required_codes)
            optional_used = len([c for c in available_codes if c not in required_codes])
            total_all_metrics = len(codes)
            missing_required_codes = [c for c in required_codes if c not in available_required_codes]
        else:
            proxy_weights = PROXY_DOMAIN_WEIGHTS.get(domain_code, {})
            total = len(proxy_weights)
            weighted_current = []
            weighted_readiness = []
            weighted_resilience = []
            available_codes = []
            freshness_values = []

            for code, proxy_weight in proxy_weights.items():
                metric = metric_scores.get(code)
                if not metric:
                    continue
                available_codes.append(code)
                w = float(proxy_weight) * float(metric["freshness_factor"])
                weighted_current.append((metric["score_100"], w))
                weighted_readiness.append((metric["readiness_score_100"], w))
                weighted_resilience.append((metric["resilience_score_100"], w))
                freshness_values.append(float(metric["freshness_factor"]))

            coverage = (len(available_codes) / total) if total else 0.0
            freshness_quality = (sum(freshness_values) / len(freshness_values)) if freshness_values else 0.0
            confidence = coverage * freshness_quality * 0.7
            available_required = len(available_codes)
            optional_used = 0
            total_all_metrics = total
            optional_weight_scale = 1.0
            missing_required_codes = []

        score_100 = _weighted_average(weighted_current)
        readiness_100 = _weighted_average(weighted_readiness)
        resilience_100 = _weighted_average(weighted_resilience)

        if score_100 is None:
            score_100 = 50.0
        if readiness_100 is None:
            readiness_100 = score_100
        if resilience_100 is None:
            resilience_100 = score_100

        domains[domain_code] = {
            "code": domain_code,
            "name": domain_spec["name"],
            "short": domain_spec["short"],
            "color": domain_spec["color"],
            "icon": domain_spec["icon"],
            "is_proxy": is_proxy,
            "score_100": round(score_100, 1),
            "score_10": round(score_100 / 10.0, 1),
            "readiness_100": round(readiness_100, 1),
            "readiness_10": round(readiness_100 / 10.0, 1),
            "resilience_100": round(resilience_100, 1),
            "resilience_10": round(resilience_100 / 10.0, 1),
            "confidence": round(confidence, 2),
            "available_metrics": available_required,
            "total_metrics": total,
            "total_all_metrics": total_all_metrics,
            "optional_metrics_used": optional_used,
            "optional_weight_scale": round(optional_weight_scale, 2),
            "missing_required_codes": missing_required_codes,
            "metric_codes_used": available_codes,
        }

    domain_scores = [domains[d]["score_100"] for d in DOMAIN_ORDER]
    domain_readiness = [domains[d]["readiness_100"] for d in DOMAIN_ORDER]
    domain_resilience = [domains[d]["resilience_100"] for d in DOMAIN_ORDER]

    overall_score_100 = round(sum(domain_scores) / len(domain_scores), 1) if domain_scores else 0.0
    overall_readiness_100 = round(sum(domain_readiness) / len(domain_readiness), 1) if domain_readiness else 0.0
    overall_resilience_100 = round(sum(domain_resilience) / len(domain_resilience), 1) if domain_resilience else 0.0

    return {
        "domains": domains,
        "domain_order": list(DOMAIN_ORDER),
        "metrics": metric_scores,
        "overall_score_100": overall_score_100,
        "overall_score_10": round(overall_score_100 / 10.0, 1),
        "overall_readiness_100": overall_readiness_100,
        "overall_readiness_10": round(overall_readiness_100 / 10.0, 1),
        "overall_resilience_100": overall_resilience_100,
        "overall_resilience_10": round(overall_resilience_100 / 10.0, 1),
        "data_points_used": len(metric_scores),
    }
