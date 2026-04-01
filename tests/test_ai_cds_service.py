import services.ai_cds_service as ai_cds


def test_catalogs_are_available():
    benchmarks = ai_cds.get_institution_emr_benchmarks()
    use_cases = ai_cds.get_ai_cds_use_cases()
    github_patterns = ai_cds.get_github_lifestyle_patterns()
    evidence = ai_cds.get_lifestyle_evidence_base()

    assert len(benchmarks) >= 3
    assert len(use_cases) >= 3
    assert len(github_patterns) >= 3
    assert len(evidence) >= 4
    assert all("institution" in row for row in benchmarks)
    assert all("use_case" in row for row in use_cases)
    assert all("repo" in row for row in github_patterns)
    assert all("topic" in row for row in evidence)


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
    assert modules["Lifestyle Intervention Opportunity Finder"]["priority"] == "P1"
    assert modules["Lifestyle Intervention Opportunity Finder"]["status"] == "Activate now"
    assert modules["Wearable Adherence & Recovery Drift Detector"]["status"] == "Pilot now"


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
    assert modules["Wearable Adherence & Recovery Drift Detector"]["status"] == "Backlog"


def test_lifestyle_intervention_support_returns_domain_cards():
    snapshot = {
        "wearable": {"overall_readiness_10": 6.0},
        "counts": {"labs_flagged": 2},
        "organ_domain_categories": [
            {"domain_code": "heart_metabolism", "score_10": 6.1, "elevated_or_worse": 1},
            {"domain_code": "gut_digestion", "score_10": 6.7, "elevated_or_worse": 1},
            {"domain_code": "brain_health", "score_10": 6.4, "elevated_or_worse": 1},
        ],
    }

    cards = ai_cds.build_lifestyle_intervention_support(snapshot)
    domains = {row["domain"] for row in cards}
    assert "Heart & Metabolism" in domains
    assert "Gut & Digestion" in domains
    assert "Brain Health" in domains
