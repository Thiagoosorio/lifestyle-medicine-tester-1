from datetime import datetime, timezone

import services.critical_lab_policy_service as clps


def test_build_critical_communication_plan_only_uses_approved_analytes():
    rows = [
        {
            "code": "potassium",
            "name": "Potassium",
            "value": 6.2,
            "unit": "mmol/L",
            "classification": "critical_high",
            "critical_low": 3.0,
            "critical_high": 6.0,
            "lab_date": "2026-04-01",
        },
        {
            "code": "hs_crp",
            "name": "hs-CRP",
            "value": 40.0,
            "unit": "mg/L",
            "classification": "critical_high",
            "critical_low": None,
            "critical_high": 30.0,
            "lab_date": "2026-04-01",
        },
    ]

    plan = clps.build_critical_communication_plan(rows)
    assert plan["has_critical"] is True
    assert len(plan["alerts"]) == 1

    potassium = next(r for r in plan["alerts"] if r["code"] == "potassium")
    assert potassium["notify_within_minutes"] == 15
    assert potassium["urgency_level"] == "immediate"
    assert potassium["critical_threshold"].startswith(">")
    assert "emergency care" in potassium["patient_action"].lower()
    assert "chest pain" in potassium["red_flag_symptoms"]


def test_chronic_diagnostic_thresholds_do_not_create_urgent_workflows():
    results = [
        {
            "code": "ldl_cholesterol",
            "name": "LDL Cholesterol",
            "value": 191,
            "unit": "mg/dL",
            "standard_low": None,
            "standard_high": 130,
            "critical_low": None,
            "critical_high": 190,
            "lab_date": "2026-04-01",
        },
        {
            "code": "fasting_glucose",
            "name": "Fasting Glucose",
            "value": 127,
            "unit": "mg/dL",
            "standard_low": 70,
            "standard_high": 100,
            "critical_low": 50,
            "critical_high": 126,
            "lab_date": "2026-04-01",
        },
        {
            "code": "hba1c",
            "name": "HbA1c",
            "value": 6.6,
            "unit": "%",
            "standard_low": 4.0,
            "standard_high": 5.7,
            "critical_low": None,
            "critical_high": 6.5,
            "lab_date": "2026-04-01",
        },
    ]

    plan = clps.build_critical_communication_plan_from_results(results)

    assert plan["has_critical"] is False
    assert plan["immediate_count"] == 0
    assert plan["alerts"] == []


def test_build_critical_communication_plan_from_results_detects_critical():
    results = [
        {
            "code": "sodium",
            "name": "Sodium",
            "value": 121,
            "unit": "mmol/L",
            "standard_low": 135,
            "standard_high": 145,
            "critical_low": 125,
            "critical_high": 155,
            "lab_date": "2026-04-01",
        },
        {
            "code": "hdl_cholesterol",
            "name": "HDL Cholesterol",
            "value": 50,
            "unit": "mg/dL",
            "standard_low": 40,
            "standard_high": 60,
            "critical_low": 20,
            "critical_high": 100,
            "lab_date": "2026-04-01",
        },
    ]

    plan = clps.build_critical_communication_plan_from_results(results)
    assert plan["has_critical"] is True
    assert len(plan["alerts"]) == 1
    sodium = plan["alerts"][0]
    assert sodium["code"] == "sodium"
    assert sodium["classification"] == "critical_low"
    assert sodium["notify_within_minutes"] == 15


def test_alert_includes_detection_and_deadline_timestamps():
    rows = [
        {
            "code": "potassium",
            "name": "Potassium",
            "value": 6.8,
            "unit": "mmol/L",
            "classification": "critical_high",
            "critical_low": 3.0,
            "critical_high": 6.0,
            "lab_date": "2020-01-01T14:30:00",  # old date -> overdue
        }
    ]
    plan = clps.build_critical_communication_plan(rows)
    alert = plan["alerts"][0]
    assert "detected_at_iso" in alert
    assert "notify_by_iso" in alert
    assert "escalate_by_iso" in alert
    assert alert["notify_overdue"] is True
    # Deadline = detection + 15 min for potassium
    detected = datetime.fromisoformat(alert["detected_at_iso"])
    notify_by = datetime.fromisoformat(alert["notify_by_iso"])
    assert (notify_by - detected).total_seconds() == 15 * 60


def test_alert_not_overdue_for_fresh_detection():
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [
        {
            "code": "potassium",
            "name": "Potassium",
            "value": 6.8,
            "unit": "mmol/L",
            "classification": "critical_high",
            "critical_low": 3.0,
            "critical_high": 6.0,
            "lab_date": now_iso,
        }
    ]
    plan = clps.build_critical_communication_plan(rows)
    alert = plan["alerts"][0]
    assert alert["notify_overdue"] is False
    assert alert["minutes_until_notify"] >= 0


def test_historical_date_only_uses_workflow_receipt_time():
    before = datetime.now(timezone.utc)
    rows = [
        {
            "code": "potassium",
            "name": "Potassium",
            "value": 6.8,
            "unit": "mmol/L",
            "classification": "critical_high",
            "critical_low": 3.0,
            "critical_high": 6.0,
            "lab_date": "2020-01-01",
        }
    ]

    alert = clps.build_critical_communication_plan(rows)["alerts"][0]
    after = datetime.now(timezone.utc)
    detected = datetime.fromisoformat(alert["detected_at_iso"])

    assert before.replace(second=0, microsecond=0) <= detected <= after
    assert alert["notify_overdue"] is False
    assert alert["minutes_until_notify"] >= 0


def test_durable_receipt_keeps_deadline_stable_across_later_renders(monkeypatch):
    class RenderClock(datetime):
        current = datetime(2026, 4, 1, 12, 5, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr(clps, "datetime", RenderClock)
    rows = [
        {
            "code": "potassium",
            "name": "Potassium",
            "value": 6.8,
            "unit": "mmol/L",
            "classification": "critical_high",
            "critical_low": 3.0,
            "critical_high": 6.0,
            "lab_date": "2026-03-31",
            "created_at": "2026-04-01 12:00:00",
        }
    ]

    first_alert = clps.build_critical_communication_plan(rows)["alerts"][0]
    RenderClock.current = datetime(2026, 4, 1, 12, 20, tzinfo=timezone.utc)
    later_alert = clps.build_critical_communication_plan(rows)["alerts"][0]

    assert first_alert["detected_at_iso"] == "2026-04-01T12:00+00:00"
    assert first_alert["notify_by_iso"] == "2026-04-01T12:15+00:00"
    assert later_alert["notify_by_iso"] == first_alert["notify_by_iso"]
    assert first_alert["notify_overdue"] is False
    assert later_alert["notify_overdue"] is True


def test_explicit_detection_timestamp_overrides_collection_date():
    rows = [
        {
            "code": "potassium",
            "name": "Potassium",
            "value": 6.8,
            "unit": "mmol/L",
            "classification": "critical_high",
            "critical_low": 3.0,
            "critical_high": 6.0,
            "lab_date": "2026-04-01",
            "detected_at": "2020-01-02T14:30:00+00:00",
        }
    ]

    alert = clps.build_critical_communication_plan(rows)["alerts"][0]

    assert alert["detected_at_iso"] == "2020-01-02T14:30+00:00"
    assert alert["notify_overdue"] is True

