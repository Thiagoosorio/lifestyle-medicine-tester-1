import services.critical_lab_policy_service as clps


def test_build_critical_communication_plan_applies_analyte_protocol():
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
    assert len(plan["alerts"]) == 2

    potassium = next(r for r in plan["alerts"] if r["code"] == "potassium")
    assert potassium["notify_within_minutes"] == 15
    assert potassium["urgency_level"] == "immediate"
    assert potassium["critical_threshold"].startswith(">")

    hs_crp = next(r for r in plan["alerts"] if r["code"] == "hs_crp")
    assert hs_crp["notify_within_minutes"] == 60
    assert hs_crp["urgency_level"] == "urgent_review"


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

