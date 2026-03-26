"""Wearable-data ingestion and 5-domain wheel scoring."""

from __future__ import annotations

import csv
import io
import math
from datetime import datetime, timezone
from typing import Any

from db.database import get_connection
from config.wearable_wheel_data import (
    CSV_TEMPLATE_HEADER,
    DIRECT_DOMAIN_METRICS,
    DOMAIN_ORDER,
    PROXY_DOMAIN_WEIGHTS,
    WEARABLE_METRIC_SPECS,
    WEARABLE_WHEEL_DOMAINS,
)


def get_metric_specs() -> dict[str, dict]:
    return WEARABLE_METRIC_SPECS


def get_domain_specs() -> dict[str, dict]:
    return WEARABLE_WHEEL_DOMAINS


def build_wearable_csv_template() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_TEMPLATE_HEADER)
    writer.writerow(["resting_heart_rate_bpm", "54", "2026-03-26T07:00:00", "wearable"])
    writer.writerow(["sleep_efficiency_pct", "92", "2026-03-26T07:00:00", "wearable"])
    writer.writerow(["recovery_score", "81", "2026-03-26T07:00:00", "wearable"])
    return output.getvalue()


def save_measurements(user_id: int, rows: list[dict[str, Any]], default_source: str = "manual") -> dict:
    """Insert wearable measurements."""
    inserted = 0
    skipped_unknown = 0
    skipped_invalid = 0

    conn = get_connection()
    try:
        for row in rows:
            metric_code = (row.get("metric_code") or "").strip()
            if metric_code not in WEARABLE_METRIC_SPECS:
                skipped_unknown += 1
                continue

            try:
                value = float(row.get("value"))
            except (TypeError, ValueError):
                skipped_invalid += 1
                continue

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
                    value,
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
    }


def import_measurements_csv_text(user_id: int, csv_text: str, default_source: str = "csv_upload") -> dict:
    if not csv_text or not csv_text.strip():
        return {"inserted": 0, "skipped_unknown": 0, "skipped_invalid": 0}

    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for row in reader:
        rows.append(
            {
                "metric_code": row.get("metric_code"),
                "value": row.get("value"),
                "measured_at": row.get("measured_at"),
                "source": row.get("source") or default_source,
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


def _normalize(value: float, spec: dict) -> float | None:
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
            score = _normalize(float(row["value"]), spec)
            if score is not None:
                historical_abs_scores.append(float(score))

        current_abs = _normalize(float(current_value), spec)
        readiness_abs = _normalize(float(readiness_value), spec)
        resilience_abs = _normalize(float(resilience_value), spec)
        if current_abs is None or readiness_abs is None or resilience_abs is None:
            continue

        current_score = _blend_personalized_score(float(current_abs), historical_abs_scores)
        readiness_score = _blend_personalized_score(float(readiness_abs), historical_abs_scores)
        resilience_score = _blend_personalized_score(float(resilience_abs), historical_abs_scores)

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
        }

    domains = {}
    for domain_code in DOMAIN_ORDER:
        domain_spec = WEARABLE_WHEEL_DOMAINS[domain_code]
        is_proxy = bool(domain_spec.get("is_proxy"))

        if not is_proxy:
            codes = DIRECT_DOMAIN_METRICS.get(domain_code, [])
            total = len(codes)
            weighted_current = []
            weighted_readiness = []
            weighted_resilience = []
            available_codes = []
            freshness_values = []

            for code in codes:
                metric = metric_scores.get(code)
                if not metric:
                    continue
                available_codes.append(code)
                w = float(metric["effective_weight"])
                weighted_current.append((metric["score_100"], w))
                weighted_readiness.append((metric["readiness_score_100"], w))
                weighted_resilience.append((metric["resilience_score_100"], w))
                freshness_values.append(float(metric["freshness_factor"]))

            coverage = (len(available_codes) / total) if total else 0.0
            freshness_quality = (sum(freshness_values) / len(freshness_values)) if freshness_values else 0.0
            confidence = coverage * freshness_quality
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
            "available_metrics": len(available_codes),
            "total_metrics": total,
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
