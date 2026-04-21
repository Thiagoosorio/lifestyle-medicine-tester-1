"""Critical lab communication planning helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config.critical_lab_policy_data import (
    CRITICAL_ANALYTE_PROTOCOL,
    CRITICAL_COMMUNICATION_POLICY,
    DEFAULT_CRITICAL_PROTOCOL,
)
from services.biomarker_service import classify_result


def _parse_detection_time(raw: str | None) -> datetime:
    """Best-effort parse of lab_date. Returns current UTC time on failure."""
    if not raw:
        return datetime.now(timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        except ValueError:
            continue
    return datetime.now(timezone.utc)


def _critical_threshold_text(row: dict) -> str:
    unit = row.get("unit") or ""
    cls = row.get("classification")
    if cls == "critical_low" and row.get("critical_low") is not None:
        return f"< {row.get('critical_low')} {unit}".strip()
    if cls == "critical_high" and row.get("critical_high") is not None:
        return f"> {row.get('critical_high')} {unit}".strip()
    return "Configured critical threshold"


def _alert_protocol_for_code(code: str | None) -> dict:
    if not code:
        return dict(DEFAULT_CRITICAL_PROTOCOL)
    return {
        **DEFAULT_CRITICAL_PROTOCOL,
        **CRITICAL_ANALYTE_PROTOCOL.get(code, {}),
    }


def build_critical_communication_plan(critical_rows: list[dict]) -> dict:
    """Build communication actions for already-classified critical rows.

    Each alert carries an absolute ``notify_by_iso`` / ``escalate_by_iso``
    deadline computed from the detection time and the analyte-specific
    notification window, so clinicians see exactly when each critical result
    must be handled.
    """
    now = datetime.now(timezone.utc)
    alerts = []
    for row in critical_rows:
        protocol = _alert_protocol_for_code(row.get("code"))
        detected_at = _parse_detection_time(row.get("lab_date"))
        notify_minutes = int(protocol["notify_within_minutes"])
        escalate_minutes = int(protocol["escalate_after_minutes"])
        notify_by = detected_at + timedelta(minutes=notify_minutes)
        escalate_by = notify_by + timedelta(minutes=escalate_minutes)
        alerts.append(
            {
                "code": row.get("code"),
                "name": row.get("name"),
                "value": row.get("value"),
                "unit": row.get("unit"),
                "classification": row.get("classification"),
                "critical_threshold": _critical_threshold_text(row),
                "urgency_level": protocol["urgency_level"],
                "notify_within_minutes": notify_minutes,
                "escalate_after_minutes": escalate_minutes,
                "recommended_action": protocol["recommended_action"],
                "lab_date": row.get("lab_date"),
                "detected_at_iso": detected_at.isoformat(timespec="minutes"),
                "notify_by_iso": notify_by.isoformat(timespec="minutes"),
                "escalate_by_iso": escalate_by.isoformat(timespec="minutes"),
                "notify_overdue": notify_by < now,
                "minutes_until_notify": int((notify_by - now).total_seconds() // 60),
            }
        )

    alerts.sort(
        key=lambda r: (
            int(r.get("notify_within_minutes") or 999),
            str(r.get("name") or ""),
        )
    )

    immediate_count = sum(1 for row in alerts if row.get("urgency_level") == "immediate")

    return {
        "has_critical": bool(alerts),
        "immediate_count": immediate_count,
        "policy": CRITICAL_COMMUNICATION_POLICY,
        "alerts": alerts,
    }


def build_critical_communication_plan_from_results(results: list[dict]) -> dict:
    """Classify raw results and build critical communication actions."""
    critical_rows: list[dict] = []
    for row in results:
        cls = classify_result(row.get("value"), row)
        if cls not in {"critical_low", "critical_high"}:
            continue
        critical_rows.append(
            {
                "code": row.get("code"),
                "name": row.get("name"),
                "value": row.get("value"),
                "unit": row.get("unit"),
                "classification": cls,
                "critical_low": row.get("critical_low"),
                "critical_high": row.get("critical_high"),
                "lab_date": row.get("lab_date"),
            }
        )
    return build_critical_communication_plan(critical_rows)

