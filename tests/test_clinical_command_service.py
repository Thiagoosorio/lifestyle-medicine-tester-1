import models.clinical_registry as clinical_registry
import services.clinical_command_service as ccs


def _create_user(db_conn, username="clinical.user"):
    conn = db_conn()
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, display_name, email) VALUES (?, ?, ?, ?)",
        (username, "fakehash", "Clinical User", "clinical@example.com"),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def test_clinical_registry_crud(db_conn, monkeypatch):
    monkeypatch.setattr(clinical_registry, "get_connection", db_conn)
    user_id = _create_user(db_conn)

    clinical_registry.save_diagnosis(
        user_id=user_id,
        diagnosis_name="Hypertension",
        status="active",
        confirmed_date="2026-03-15",
        confirming_clinician="Dr A",
        source="Clinic Note",
    )
    active_dx = clinical_registry.list_diagnoses(user_id, active_only=True)
    assert len(active_dx) == 1
    assert active_dx[0]["diagnosis_name"] == "Hypertension"

    clinical_registry.update_diagnosis_status(user_id, active_dx[0]["id"], "resolved")
    assert clinical_registry.list_diagnoses(user_id, active_only=True) == []

    iv_id = clinical_registry.save_intervention(
        user_id=user_id,
        intervention_type="medication",
        name="Rosuvastatin",
        dose="10 mg",
        schedule="qHS",
        status="active",
    )
    active_iv = clinical_registry.list_interventions(user_id, active_only=True)
    assert len(active_iv) == 1
    assert active_iv[0]["id"] == iv_id
    assert active_iv[0]["name"] == "Rosuvastatin"

    clinical_registry.update_intervention_status(user_id, iv_id, "stopped")
    assert clinical_registry.list_interventions(user_id, active_only=True) == []

    clinical_registry.save_test_result(
        user_id=user_id,
        test_type="CPET",
        test_date="2026-03-20",
        summary="Reduced aerobic capacity",
        key_metrics={"vo2max_ml_kg_min": 31.4},
        risk_flag="moderate",
    )
    tests = clinical_registry.list_test_results(user_id, confirmed_only=True)
    assert len(tests) == 1
    assert tests[0]["test_type"] == "CPET"
    assert tests[0]["key_metrics"]["vo2max_ml_kg_min"] == 31.4


def test_get_labs_requiring_attention_groups_by_severity(monkeypatch):
    sample = [
        {"code": "a", "name": "A", "value": 1, "unit": "u", "lab_date": "2026-03-01"},
        {"code": "b", "name": "B", "value": 2, "unit": "u", "lab_date": "2026-03-01"},
        {"code": "c", "name": "C", "value": 3, "unit": "u", "lab_date": "2026-03-01"},
        {"code": "d", "name": "D", "value": 4, "unit": "u", "lab_date": "2026-03-01"},
    ]

    class_map = {
        "a": "critical_high",
        "b": "high",
        "c": "low",
        "d": "in_range",
    }

    monkeypatch.setattr(ccs, "get_latest_results", lambda _uid: sample)
    monkeypatch.setattr(ccs, "classify_result", lambda _v, row: class_map[row["code"]])

    out = ccs.get_labs_requiring_attention(1)
    assert len(out["critical"]) == 1
    assert len(out["abnormal"]) == 2
    assert [r["code"] for r in out["all"]] == ["a", "b", "c"]


def test_build_clinical_snapshot_aggregates_sections(monkeypatch):
    monkeypatch.setattr(ccs, "get_user", lambda _uid: {"display_name": "Maria Silva", "email": "maria@example.com"})
    monkeypatch.setattr(ccs, "get_profile", lambda _uid: {"sex": "female", "systolic_bp": 122, "diastolic_bp": 76, "smoking_status": "never", "diabetes_status": 0})
    monkeypatch.setattr(ccs, "get_age", lambda _uid: 44.0)
    monkeypatch.setattr(ccs, "get_bmi", lambda _uid: 23.8)
    monkeypatch.setattr(ccs, "get_latest_metrics", lambda _uid: {"weight_kg": 66.2, "height_cm": 167.0})
    monkeypatch.setattr(ccs, "get_latest_dexa", lambda _uid: {"scan_date": "2026-02-20", "total_fat_pct": 29.1, "lean_mass_g": 46200, "bmd_g_cm2": 1.06})
    monkeypatch.setattr(ccs, "list_diagnoses", lambda _uid, active_only=False: [{"diagnosis_name": "Prediabetes", "status": "active"}] if active_only else [{"diagnosis_name": "Prediabetes", "status": "active"}])
    monkeypatch.setattr(ccs, "list_interventions", lambda _uid, active_only=True: [{"id": 1, "intervention_type": "medication", "name": "Metformin", "status": "active"}])
    monkeypatch.setattr(ccs, "get_user_protocols", lambda _uid: [])
    monkeypatch.setattr(ccs, "get_saved_program", lambda _uid: None)
    monkeypatch.setattr(ccs, "get_cycling_profile", lambda _uid: None)
    monkeypatch.setattr(ccs, "get_active_plan", lambda _uid: None)
    monkeypatch.setattr(ccs, "get_labs_requiring_attention", lambda _uid: {"critical": [], "abnormal": [{"code": "ldl"}], "all": [{"code": "ldl"}]})
    monkeypatch.setattr(ccs, "list_test_results", lambda _uid, confirmed_only=True, limit=50: [{"test_type": "CPET", "test_date": "2026-03-10", "summary": "Moderate impairment", "risk_flag": "moderate"}])
    monkeypatch.setattr(ccs, "get_latest_computed_scores", lambda _uid: [{"severity": "high"}, {"severity": "normal"}])
    monkeypatch.setattr(ccs, "compute_overall_organ_score", lambda _uid: {"overall_score_10": 6.3, "overall_label": "Watchlist", "overall_confidence_pct": 78, "score_coverage_pct": 82})
    monkeypatch.setattr(ccs, "compute_wearable_wheel", lambda _uid: {"overall_score_10": 6.9, "overall_readiness_10": 7.2, "overall_resilience_10": 6.6})
    monkeypatch.setattr(ccs, "get_lab_dates", lambda _uid: [])
    monkeypatch.setattr(ccs, "get_results_by_date", lambda _uid, _lab_date: [])

    snap = ccs.build_clinical_snapshot(7)
    assert snap["patient"]["display_name"] == "Maria Silva"
    assert snap["counts"]["diagnoses_active"] == 1
    assert snap["counts"]["interventions_active"] == 1
    assert snap["counts"]["labs_flagged"] == 1
    assert snap["counts"]["organ_scores_high_risk"] == 1
    assert snap["organ_overall"]["overall_score_10"] == 6.3
    assert snap["wearable"]["overall_score_10"] == 6.9


def test_evidence_trace_keeps_validated_scores_with_q_or_org_guideline_sources():
    trace = ccs._build_evidence_trace(
        [
            {
                "code": "fib4",
                "name": "FIB-4",
                "organ_system": "liver",
                "tier": "validated",
                "citation_pmid": "38851997",
                "citation_text": "EASL guideline [Q1]",
            },
            {
                "code": "q2_item",
                "name": "Q2 Score",
                "organ_system": "kidney",
                "tier": "validated",
                "citation_pmid": "12345",
                "citation_text": "Some study [Q2]",
            },
            {
                "code": "aha_score",
                "name": "ApoB Risk Category",
                "organ_system": "cardiovascular",
                "tier": "validated",
                "citation_pmid": "30586774",
                "citation_text": "ACC/AHA Cholesterol Guideline statement.",
            },
            {
                "code": "derived_item",
                "name": "Derived Score",
                "organ_system": "metabolic",
                "tier": "derived",
                "citation_pmid": "67890",
                "citation_text": "Some study [Q1]",
            },
            {
                "code": "no_pmid",
                "name": "Missing PMID",
                "organ_system": "metabolic",
                "tier": "validated",
                "citation_pmid": None,
                "citation_text": "AHA statement",
            },
        ]
    )

    assert trace["counts"]["allowed"] == 3
    assert trace["counts"]["excluded"] == 2
    allowed_codes = {row["code"] for row in trace["allowed_sources"]}
    assert allowed_codes == {"fib4", "q2_item", "aha_score"}


def test_organ_domain_categories_include_requested_five_domains():
    overall = {
        "organ_breakdown": [
            {"organ_system": "cardiovascular", "name": "Cardio", "score_10": 7.5, "confidence_0_1": 0.8, "elevated_or_worse": 1},
            {"organ_system": "metabolic", "name": "Metabolic", "score_10": 6.5, "confidence_0_1": 0.7, "elevated_or_worse": 2},
            {"organ_system": "liver", "name": "Liver", "score_10": 8.0, "confidence_0_1": 0.9, "elevated_or_worse": 0},
            {"organ_system": "neurological", "name": "Neuro", "score_10": 7.0, "confidence_0_1": 0.6, "elevated_or_worse": 1},
            {"organ_system": "thyroid", "name": "Thyroid", "score_10": 5.5, "confidence_0_1": 0.5, "elevated_or_worse": 1},
        ]
    }

    categories = ccs._build_organ_domain_categories(overall, latest_dexa={"scan_date": "2026-01-01"})
    by_code = {row["domain_code"]: row for row in categories}

    assert set(by_code.keys()) == {"heart_metabolism", "muscle_bones", "gut_digestion", "brain_health", "system_wide"}
    assert by_code["heart_metabolism"]["score_10"] == 7.0
    assert by_code["gut_digestion"]["score_10"] == 8.0
    assert by_code["brain_health"]["score_10"] == 7.0
    assert by_code["muscle_bones"]["score_10"] is None
    assert "DEXA present" in by_code["muscle_bones"]["note"]
