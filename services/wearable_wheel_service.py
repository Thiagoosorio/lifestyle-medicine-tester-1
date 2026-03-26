"""Wearable-data ingestion and 5-domain wheel scoring."""

from __future__ import annotations

import csv
import io
from datetime import datetime
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
    """Insert wearable measurements.

    Expected row keys:
      - metric_code (required)
      - value (required)
      - measured_at (optional, ISO datetime; defaults now)
      - source (optional)
      - external_id (optional)
    """
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
                measured_at = datetime.utcnow().isoformat(timespec="seconds")

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


def _weighted_average(items: list[tuple[float, float]]) -> float | None:
    if not items:
        return None
    total_weight = sum(weight for _, weight in items)
    if total_weight <= 0:
        return None
    return sum(score * weight for score, weight in items) / total_weight


def compute_wearable_wheel(user_id: int) -> dict:
    """Compute 5-domain wearable wheel with confidence and metric breakdown."""
    latest = get_latest_measurements(user_id)

    metric_scores: dict[str, dict] = {}
    for code, spec in WEARABLE_METRIC_SPECS.items():
        row = latest.get(code)
        if not row:
            continue
        norm_score = _normalize(float(row["value"]), spec)
        if norm_score is None:
            continue
        metric_scores[code] = {
            "code": code,
            "label": spec["label"],
            "raw_value": float(row["value"]),
            "unit": spec.get("unit"),
            "score_100": norm_score,
            "measured_at": row["measured_at"],
            "domain": spec["domain"],
            "weight": float(spec.get("weight", 1.0)),
        }

    domains = {}
    for domain_code in DOMAIN_ORDER:
        domain_spec = WEARABLE_WHEEL_DOMAINS[domain_code]
        is_proxy = bool(domain_spec.get("is_proxy"))

        if not is_proxy:
            codes = DIRECT_DOMAIN_METRICS.get(domain_code, [])
            weighted_scores = []
            available_codes = []
            for code in codes:
                if code not in metric_scores:
                    continue
                available_codes.append(code)
                weighted_scores.append((metric_scores[code]["score_100"], metric_scores[code]["weight"]))

            score_100 = _weighted_average(weighted_scores)
            total = len(codes)
            available = len(available_codes)
            confidence = (available / total) if total else 0.0
        else:
            proxy_weights = PROXY_DOMAIN_WEIGHTS.get(domain_code, {})
            weighted_scores = []
            available_codes = []
            for code, proxy_weight in proxy_weights.items():
                if code not in metric_scores:
                    continue
                available_codes.append(code)
                weighted_scores.append((metric_scores[code]["score_100"], float(proxy_weight)))

            score_100 = _weighted_average(weighted_scores)
            total = len(proxy_weights)
            available = len(available_codes)
            confidence = ((available / total) if total else 0.0) * 0.7

        if score_100 is None:
            score_100 = 50.0

        domains[domain_code] = {
            "code": domain_code,
            "name": domain_spec["name"],
            "short": domain_spec["short"],
            "color": domain_spec["color"],
            "icon": domain_spec["icon"],
            "is_proxy": is_proxy,
            "score_100": round(score_100, 1),
            "score_10": round(score_100 / 10.0, 1),
            "confidence": round(confidence, 2),
            "available_metrics": available,
            "total_metrics": total,
            "metric_codes_used": available_codes,
        }

    domain_scores = [domains[d]["score_100"] for d in DOMAIN_ORDER]
    overall_score_100 = round(sum(domain_scores) / len(domain_scores), 1) if domain_scores else 0.0

    return {
        "domains": domains,
        "domain_order": list(DOMAIN_ORDER),
        "metrics": metric_scores,
        "overall_score_100": overall_score_100,
        "overall_score_10": round(overall_score_100 / 10.0, 1),
        "data_points_used": len(metric_scores),
    }
