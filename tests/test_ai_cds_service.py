import services.ai_cds_service as ai_cds


def test_catalogs_are_available():
    benchmarks = ai_cds.get_institution_emr_benchmarks()
    use_cases = ai_cds.get_ai_cds_use_cases()

    assert len(benchmarks) >= 3
    assert len(use_cases) >= 3
    assert all("institution" in row for row in benchmarks)
    assert all("use_case" in row for row in use_cases)


def test_rollout_prioritizes_critical_events_when_present():
    snapshot = {
        "patient": {
            "age": 45,
            "sex": "female",
            "bmi": 29.1,
            "systolic_bp": 145,
            "diastolic_bp": 92,
        },
        "labs_attention": {"all": [{"code": "ldl"}], "critical": [{"code": "k"}]},
        "organ_overall": {"overall_score_10": 5.8},
        "wearable": {"overall_score_10": 6.0},
        "test_results": [{"test_type": "CPET"}],
        "interventions_active": [{"name": "Statin"}],
        "diagnoses_active": [{"diagnosis_name": "Hypertension"}],
        "organ_domain_categories": [
            {"domain_code": "heart_metabolism", "score_10": 6.2, "elevated_or_worse": 2}
        ],
        "counts": {"labs_critical": 1, "labs_flagged": 1, "organ_scores_high_risk": 2},
    }

    plan = ai_cds.build_ai_cds_rollout_plan(snapshot)
    modules = {row["module"]: row for row in plan["modules"]}

    assert plan["readiness_score_100"] >= 80
    assert modules["Critical Event Triage Copilot"]["priority"] == "P1"
    assert modules["Critical Event Triage Copilot"]["status"] == "Activate now"
    assert modules["Cardiometabolic Confirmatory-Test Trigger"]["status"] == "Pilot now"


def test_rollout_stays_conservative_for_low_data_profile():
    snapshot = {
        "patient": {"age": None, "sex": None, "bmi": None, "systolic_bp": None, "diastolic_bp": None},
        "labs_attention": {"all": [], "critical": []},
        "organ_overall": None,
        "wearable": None,
        "test_results": [],
        "interventions_active": [],
        "diagnoses_active": [],
        "organ_domain_categories": [],
        "counts": {"labs_critical": 0, "labs_flagged": 0, "organ_scores_high_risk": 0},
    }

    plan = ai_cds.build_ai_cds_rollout_plan(snapshot)
    modules = {row["module"]: row for row in plan["modules"]}

    assert plan["readiness_score_100"] <= 20
    assert plan["readiness_label"] == "Early readiness"
    assert modules["Cardiometabolic Confirmatory-Test Trigger"]["status"] == "Backlog"
