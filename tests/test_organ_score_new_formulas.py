from services import organ_score_service as oss


def test_interpret_score_uses_non_overlapping_threshold_boundaries():
    definition = {
        "interpretation": {
            "ranges": [
                {"max": 5.0, "label": "Low", "severity": "optimal"},
                {"min": 5.0, "max": 7.5, "label": "Borderline", "severity": "normal"},
                {"min": 7.5, "label": "High", "severity": "high"},
            ]
        }
    }
    assert oss.interpret_score(4.99, definition)["label"] == "Low"
    assert oss.interpret_score(5.0, definition)["label"] == "Borderline"
    assert oss.interpret_score(7.5, definition)["label"] == "High"


def test_interpret_score_keeps_inclusive_upper_when_no_next_overlap():
    definition = {
        "interpretation": {
            "ranges": [
                {"max": 0, "label": "Zero", "severity": "optimal"},
                {"min": 1, "max": 2, "label": "OneToTwo", "severity": "normal"},
                {"min": 3, "label": "ThreePlus", "severity": "high"},
            ]
        }
    }
    assert oss.interpret_score(0, definition)["label"] == "Zero"
    assert oss.interpret_score(1, definition)["label"] == "OneToTwo"


def test_most_recent_iso_lab_date_ignores_unknown_and_invalid_entries():
    assert (
        oss._most_recent_iso_lab_date(
            ["unknown", "", "2025-01-15", "not-a-date", "2025-03-20"]
        )
        == "2025-03-20"
    )
    assert oss._most_recent_iso_lab_date(["unknown", "", "n/a"]) == "unknown"


def test_compute_all_scores_prefers_valid_iso_lab_date_when_some_inputs_unknown(monkeypatch):
    definitions = [
        {
            "id": 1,
            "code": "apri",
            "name": "APRI",
            "organ_system": "liver",
            "tier": "validated",
            "formula_key": "calc_apri",
            "required_biomarkers": ["ast", "platelets"],
            "required_clinical": [],
            "interpretation": {
                "ranges": [
                    {"max": 0.5, "label": "Low", "severity": "optimal"},
                    {"min": 0.5, "label": "Elevated", "severity": "elevated"},
                ]
            },
        }
    ]

    saved = {}

    monkeypatch.setattr(oss, "get_all_score_definitions", lambda: definitions)
    monkeypatch.setattr(
        oss,
        "_get_latest_biomarkers_as_dict",
        lambda _uid: {"ast": 40.0, "platelets": 200.0},
    )
    monkeypatch.setattr(
        oss,
        "_get_latest_biomarkers_with_dates",
        lambda _uid: {
            "ast": {"value": 40.0, "lab_date": "unknown"},
            "platelets": {"value": 200.0, "lab_date": "2026-01-05"},
        },
    )
    monkeypatch.setattr(oss, "_get_latest_dexa_inputs_with_dates", lambda _uid: {})
    monkeypatch.setattr(oss, "_get_clinical_data", lambda _uid: {})
    monkeypatch.setattr(
        oss,
        "save_score_result",
        lambda **kwargs: saved.update({"lab_date": kwargs["lab_date"]}),
    )

    out = oss.compute_all_scores(7)
    assert out and out[0]["code"] == "apri"
    assert saved["lab_date"] == "2026-01-05"
    assert out[0]["lab_date"] == "2026-01-05"


def test_albi_score_matches_reference_equation():
    value = oss.calc_albi_score(total_bilirubin_mgdl=0.8, albumin_gdl=4.5)
    assert value == -3.075


def test_fli_matches_reference_equation():
    value = oss.calc_fli(tg_mgdl=150, bmi=30, ggt_ul=30, waist_cm=100)
    assert value == 72.0


def test_bard_score_weighting():
    assert oss.calc_bard_score(bmi=31, ast=32, alt=30, diabetes=1) == 4
    assert oss.calc_bard_score(bmi=24, ast=24, alt=40, diabetes=0) == 0


def test_mets_ir_matches_published_formula():
    value = oss.calc_mets_ir(glucose_mgdl=100, tg_mgdl=150, hdl_mgdl=45, bmi=30)
    assert value == 46.17


def test_tyg_bmi_matches_published_formula():
    value = oss.calc_tyg_bmi(glucose_mgdl=100, tg_mgdl=150, bmi=30)
    assert value == 267.68


def test_lap_index_matches_reference_equation():
    value = oss.calc_lap_index(waist_cm=100, tg_mgdl=150, sex="male")
    assert value == 59.28


def test_vai_matches_reference_equation():
    value = oss.calc_vai(waist_cm=100, bmi=30, tg_mgdl=150, hdl_mgdl=45, sex="male")
    assert value == 1.93


def test_apob_and_homocysteine_passthrough_scores():
    assert oss.calc_apob_risk(apob_mgdl=95.4) == 95.4
    assert oss.calc_homocysteine_neurovascular_risk(homocysteine_umol=11.2) == 11.2


def test_dxa_osteoporosis_who_thresholds():
    assert oss.calc_dxa_osteoporosis_who(dexa_t_score=-0.8) == 0.0
    assert oss.calc_dxa_osteoporosis_who(dexa_t_score=-1.8) == 1.0
    assert oss.calc_dxa_osteoporosis_who(dexa_t_score=-2.5) == 2.0
    assert oss.calc_dxa_osteoporosis_who(dexa_t_score=-3.1) == 3.0
    assert oss.calc_dxa_osteoporosis_who(dexa_t_score="-2,6") == 2.0


def test_fnih_low_lean_mass_cutpoints():
    assert oss.calc_fnih_low_lean_mass(dexa_alm_kg=23.0, bmi=27.0, sex="male") == 0.0
    assert oss.calc_fnih_low_lean_mass(dexa_alm_kg=18.0, bmi=28.0, sex="male") == 1.0
    assert oss.calc_fnih_low_lean_mass(dexa_alm_kg=16.0, bmi=29.0, sex="female") == 0.0
    assert oss.calc_fnih_low_lean_mass(dexa_alm_kg=13.0, bmi=28.0, sex="female") == 1.0


def test_ewgsop2_sarcopenia_staging():
    assert oss.calc_ewgsop2_sarcopenia(
        sex="male", grip_strength_kg=34.0, chair_stand_time_s=11.0, dexa_alm_h2=7.4, gait_speed_m_per_s=1.1
    ) == 0.0
    assert oss.calc_ewgsop2_sarcopenia(
        sex="male", grip_strength_kg=24.0, chair_stand_time_s=11.0, dexa_alm_h2=7.4, gait_speed_m_per_s=1.0
    ) == 1.0
    assert oss.calc_ewgsop2_sarcopenia(
        sex="female", grip_strength_kg=14.0, chair_stand_time_s=17.0, dexa_alm_h2=5.1, gait_speed_m_per_s=0.95
    ) == 2.0
    assert oss.calc_ewgsop2_sarcopenia(
        sex="female", grip_strength_kg=14.0, chair_stand_time_s=17.0, dexa_alm_h2=5.1, gait_speed_m_per_s=0.7
    ) == 3.0


def test_findrisc_matches_reference_point_bands():
    assert oss.calc_findrisc(
        age=42, bmi=23.0, waist_cm=78.0, sex="female", daily_activity_30min=True,
        daily_fruit_veg=True, on_bp_medication=False, history_high_glucose=False,
        family_history_diabetes="none",
    ) == 0
    assert oss.calc_findrisc(
        age=58, bmi=31.0, waist_cm=106.0, sex="male", daily_activity_30min=False,
        daily_fruit_veg=False, on_bp_medication=True, history_high_glucose=True,
        family_history_diabetes="first_degree",
    ) == 25


def test_nosas_thresholds():
    assert oss.calc_nosas(age=45, bmi=24.0, sex="female", neck_circumference_cm=35.0, loud_snoring=False) == 0
    assert oss.calc_nosas(age=60, bmi=31.0, sex="male", neck_circumference_cm=43.0, loud_snoring=True) == 17


def test_qfracture_risk_increases_with_more_risk_factors():
    lower = oss.calc_qfracture_major(
        age=60, sex="female", bmi=24.0, ethrisk=1, smoke_cat=0, alcohol_cat6=0,
        b_antidepressant=0, b_anycancer=0, b_asthmacopd=0, b_carehome=0,
        b_corticosteroids=0, b_cvd=0, b_dementia=0, b_endocrine=0, b_epilepsy2=0,
        b_falls=0, b_hrt_oest=0, b_liver=0, b_malabsorption=0, b_parkinsons=0,
        b_ra_sle=0, b_renal=0, b_type1=0, b_type2=0, fh_osteoporosis=0,
    )
    higher = oss.calc_qfracture_major(
        age=78, sex="female", bmi=19.5, ethrisk=1, smoke_cat=4, alcohol_cat6=4,
        b_antidepressant=1, b_anycancer=1, b_asthmacopd=1, b_carehome=0,
        b_corticosteroids=1, b_cvd=1, b_dementia=1, b_endocrine=1, b_epilepsy2=1,
        b_falls=1, b_hrt_oest=0, b_liver=1, b_malabsorption=1, b_parkinsons=1,
        b_ra_sle=1, b_renal=1, b_type1=0, b_type2=1, fh_osteoporosis=1,
    )
    hip = oss.calc_qfracture_hip(
        age=78, sex="male", bmi=20.0, ethrisk=1, smoke_cat=4, alcohol_cat6=5,
        b_antidepressant=1, b_anycancer=1, b_asthmacopd=1, b_carehome=1,
        b_corticosteroids=1, b_cvd=1, b_dementia=1, b_endocrine=0, b_epilepsy2=1,
        b_falls=1, b_fracture4=1, b_hrt_oest=0, b_liver=1, b_parkinsons=1,
        b_ra_sle=1, b_renal=1, b_type1=0, b_type2=1, fh_osteoporosis=1,
    )
    assert lower is not None and higher is not None and hip is not None
    assert higher > lower
    assert hip > 0


def test_get_latest_dexa_inputs_with_dates_coerces_numeric_text(monkeypatch):
    import services.body_metrics_service as body_metrics_service

    monkeypatch.setattr(
        body_metrics_service,
        "get_latest_dexa",
        lambda _uid: {
            "scan_date": "2026-03-01",
            "t_score": "-2,6",
            "z_score": "-1.3",
            "bmd_g_cm2": "0,912",
            "alm_kg": "17,4",
            "alm_h2": "6,2",
            "ffmi": "18,1",
        },
    )

    out = oss._get_latest_dexa_inputs_with_dates(1)
    assert out["dexa_t_score"]["value"] == -2.6
    assert out["dexa_z_score"]["value"] == -1.3
    assert out["dexa_bmd_g_cm2"]["value"] == 0.912
    assert out["dexa_alm_kg"]["value"] == 17.4
    assert out["dexa_alm_h2"]["value"] == 6.2
    assert out["dexa_ffmi"]["value"] == 18.1
    assert out["dexa_t_score"]["lab_date"] == "2026-03-01"


def test_save_dexa_scan_derives_alm_h2_and_ffmi_from_direct_inputs(db_conn, monkeypatch):
    import services.body_metrics_service as body_metrics_service

    monkeypatch.setattr(body_metrics_service, "get_connection", db_conn)
    monkeypatch.setattr(body_metrics_service, "_get_reference_height_cm", lambda _uid: 170.0)

    conn = db_conn()
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, display_name, email) VALUES (?, ?, ?, ?)",
        ("dexa.user", "fakehash", "DEXA User", "dexa@example.com"),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    body_metrics_service.save_dexa_scan(
        user_id,
        "2026-03-02",
        alm_kg=18.5,
        lean_mass_g=50000.0,
        t_score=-1.7,
    )

    latest = body_metrics_service.get_latest_dexa(user_id)
    assert latest["alm_kg"] == 18.5
    assert latest["alm_h2"] == 6.4
    assert latest["ffmi"] == 17.3


def test_compute_all_scores_uses_dexa_t_score_inputs(monkeypatch):
    definitions = [
        {
            "id": 1,
            "code": "dxa_osteoporosis_who",
            "name": "DXA Osteoporosis Classification (WHO/ISCD)",
            "organ_system": "musculoskeletal",
            "tier": "validated",
            "formula_key": "calc_dxa_osteoporosis_who",
            "required_biomarkers": ["dexa_t_score"],
            "required_clinical": [],
            "interpretation": {
                "ranges": [
                    {"max": 0.49, "label": "Normal", "severity": "optimal"},
                    {"min": 0.5, "max": 1.49, "label": "Osteopenia", "severity": "elevated"},
                    {"min": 1.5, "max": 2.49, "label": "Osteoporosis", "severity": "high"},
                    {"min": 2.5, "label": "Severe", "severity": "critical"},
                ]
            },
            "citation_pmid": "18180210",
        }
    ]
    saved = {}

    monkeypatch.setattr(oss, "get_all_score_definitions", lambda: definitions)
    monkeypatch.setattr(oss, "_get_latest_biomarkers_as_dict", lambda _uid: {})
    monkeypatch.setattr(oss, "_get_latest_biomarkers_with_dates", lambda _uid: {})
    monkeypatch.setattr(
        oss,
        "_get_latest_dexa_inputs_with_dates",
        lambda _uid: {"dexa_t_score": {"value": -2.7, "lab_date": "2026-02-20"}},
    )
    monkeypatch.setattr(oss, "_get_clinical_data", lambda _uid: {})
    monkeypatch.setattr(oss, "save_score_result", lambda **kwargs: saved.update(kwargs))

    out = oss.compute_all_scores(42)
    assert out and out[0]["code"] == "dxa_osteoporosis_who"
    assert out[0]["value"] == 2.0
    assert out[0]["severity"] == "high"
    assert out[0]["lab_date"] == "2026-02-20"
    assert saved["lab_date"] == "2026-02-20"
    assert saved["input_snapshot"]["dexa_t_score"] == -2.7


def test_thyroid_guideline_pattern_covers_key_clinical_states():
    assert oss.calc_thyroid_guideline_pattern(tsh=2.0, free_t4_ngdl=1.2) == 0.0
    assert oss.calc_thyroid_guideline_pattern(tsh=6.2, free_t4_ngdl=1.1) == 2.0
    assert oss.calc_thyroid_guideline_pattern(tsh=12.0, free_t4_ngdl=1.1) == 3.0
    assert oss.calc_thyroid_guideline_pattern(tsh=9.0, free_t4_ngdl=0.7) == 4.0
    assert oss.calc_thyroid_guideline_pattern(tsh=1.2, free_t4_ngdl=0.7) == 3.0
    assert oss.calc_thyroid_guideline_pattern(tsh=0.02, free_t4_ngdl=1.1) == 3.0
    assert oss.calc_thyroid_guideline_pattern(tsh=0.03, free_t4_ngdl=2.1) == 4.0


def test_framingham_vascular_age_gap_basics():
    baseline_gap = oss.calc_framingham_vascular_age_gap(
        age=55,
        sex="female",
        total_chol=150,
        hdl=60,
        systolic_bp=110,
        on_bp_med=False,
        smoking=False,
        diabetes=False,
    )
    assert abs(baseline_gap) <= 0.2

    high_risk_gap = oss.calc_framingham_vascular_age_gap(
        age=55,
        sex="female",
        total_chol=260,
        hdl=35,
        systolic_bp=160,
        on_bp_med=True,
        smoking=True,
        diabetes=True,
    )
    assert high_risk_gap > 0


def test_new_formula_dispatch_entries_exist():
    for key in (
        "calc_dxa_osteoporosis_who",
        "calc_fnih_low_lean_mass",
        "calc_ewgsop2_sarcopenia",
        "calc_findrisc",
        "calc_nosas",
        "calc_qfracture_major",
        "calc_qfracture_hip",
        "calc_thyroid_guideline_pattern",
        "calc_albi_score",
        "calc_fli",
        "calc_bard_score",
        "calc_mets_ir",
        "calc_tyg_bmi",
        "calc_lap_index",
        "calc_vai",
        "calc_apob_risk",
        "calc_homocysteine_neurovascular_risk",
        "calc_framingham_vascular_age_gap",
    ):
        assert key in oss.FORMULA_DISPATCH


def test_get_clinical_data_includes_waist_from_body_metrics(monkeypatch):
    monkeypatch.setattr(oss, "get_profile", lambda _uid: {"sex": "female"})
    monkeypatch.setattr(oss, "get_age", lambda _uid: 43.0)
    monkeypatch.setattr(oss, "get_bmi", lambda _uid: 23.3)

    import services.body_metrics_service as body_metrics_service
    monkeypatch.setattr(body_metrics_service, "get_latest_metrics", lambda _uid: {"waist_cm": 72.0})
    monkeypatch.setattr(body_metrics_service, "get_body_metrics_history", lambda _uid: [{"waist_cm": 72.0}])

    clinical = oss._get_clinical_data(123)
    assert clinical["waist_cm"] == 72.0


def test_get_clinical_data_falls_back_to_latest_non_null_waist(monkeypatch):
    monkeypatch.setattr(oss, "get_profile", lambda _uid: {"sex": "female"})
    monkeypatch.setattr(oss, "get_age", lambda _uid: 43.0)
    monkeypatch.setattr(oss, "get_bmi", lambda _uid: 23.3)

    import services.body_metrics_service as body_metrics_service
    monkeypatch.setattr(body_metrics_service, "get_latest_metrics", lambda _uid: {"waist_cm": None})
    monkeypatch.setattr(
        body_metrics_service,
        "get_body_metrics_history",
        lambda _uid: [{"waist_cm": 81.0}, {"waist_cm": None}, {"waist_cm": 79.0}],
    )

    clinical = oss._get_clinical_data(123)
    assert clinical["waist_cm"] == 79.0


def test_new_scores_compute_for_backfilled_demo_user(db_conn, monkeypatch):
    import models.clinical_profile as clinical_profile
    import models.organ_score as organ_score_model
    import seed_demo
    import services.biomarker_service as biomarker_service
    import services.body_metrics_service as body_metrics_service

    monkeypatch.setattr(seed_demo, "get_connection", db_conn)
    monkeypatch.setattr(clinical_profile, "get_connection", db_conn)
    monkeypatch.setattr(biomarker_service, "get_connection", db_conn)
    monkeypatch.setattr(body_metrics_service, "get_connection", db_conn)
    monkeypatch.setattr(organ_score_model, "get_connection", db_conn)
    monkeypatch.setattr(oss, "get_connection", db_conn)

    biomarker_service.seed_biomarker_definitions()
    oss.seed_organ_score_definitions()

    conn = db_conn()
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, display_name, email) VALUES (?, ?, ?, ?)",
        ("maria.silva", "fakehash", "Maria Silva", "maria.silva@demo.com"),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    seed_demo.ensure_demo_organ_score_prereqs(user_id)
    computed = oss.compute_all_scores(user_id)
    codes = {row["code"] for row in computed}

    assert {
        "fnih_low_lean_mass",
        "ewgsop2_sarcopenia",
        "qfracture_major",
        "qfracture_hip",
        "findrisc",
        "nosas",
        "thyroid_guideline_pattern",
        "albi_score",
        "fli",
        "bard_score",
        "mets_ir",
        "tyg_bmi",
        "lap_index",
        "vai",
        "apob_risk",
        "homocysteine_neurovascular",
        "framingham_vascular_age_gap",
    }.issubset(codes)
