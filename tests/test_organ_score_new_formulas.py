from services import organ_score_service as oss


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


def test_new_formula_dispatch_entries_exist():
    for key in (
        "calc_albi_score",
        "calc_fli",
        "calc_bard_score",
        "calc_mets_ir",
        "calc_tyg_bmi",
    ):
        assert key in oss.FORMULA_DISPATCH


def test_get_clinical_data_includes_waist_from_body_metrics(monkeypatch):
    monkeypatch.setattr(oss, "get_profile", lambda _uid: {"sex": "female"})
    monkeypatch.setattr(oss, "get_age", lambda _uid: 43.0)
    monkeypatch.setattr(oss, "get_bmi", lambda _uid: 23.3)

    import services.body_metrics_service as body_metrics_service
    monkeypatch.setattr(body_metrics_service, "get_latest_metrics", lambda _uid: {"waist_cm": 72.0})

    clinical = oss._get_clinical_data(123)
    assert clinical["waist_cm"] == 72.0


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

    assert {"albi_score", "fli", "bard_score", "mets_ir", "tyg_bmi"}.issubset(codes)
