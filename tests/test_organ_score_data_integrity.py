from services import organ_score_service as oss


def _configure_apri_only(monkeypatch, values, lab_dates):
    oss.seed_organ_score_definitions()
    apri = next(
        definition
        for definition in oss.get_all_score_definitions()
        if definition["code"] == "apri"
    )

    monkeypatch.setattr(oss, "get_all_score_definitions", lambda: [apri])
    monkeypatch.setattr(
        oss,
        "_get_latest_biomarkers_as_dict",
        lambda _user_id: dict(values),
    )
    monkeypatch.setattr(
        oss,
        "_get_latest_biomarkers_with_dates",
        lambda _user_id: {
            code: {"value": value, "lab_date": lab_dates.get(code, "unknown")}
            for code, value in values.items()
        },
    )
    monkeypatch.setattr(oss, "_get_latest_dexa_inputs_with_dates", lambda _user_id: {})
    monkeypatch.setattr(oss, "_get_clinical_data", lambda _user_id: {})
    return apri


def _persisted_score_count(db_conn, user_id, score_def_id):
    conn = db_conn()
    try:
        return conn.execute(
            """SELECT COUNT(*)
               FROM organ_score_results
               WHERE user_id = ? AND score_def_id = ?""",
            (user_id, score_def_id),
        ).fetchone()[0]
    finally:
        conn.close()


def test_recompute_removes_stale_score_when_required_input_is_removed(
    db_conn, test_user, monkeypatch
):
    values = {"ast": 40.0, "platelets": 200.0}
    lab_dates = {"ast": "2026-04-01", "platelets": "2026-04-01"}
    apri = _configure_apri_only(monkeypatch, values, lab_dates)

    first = oss.compute_all_scores(test_user)
    assert [row["code"] for row in first] == ["apri"]
    assert _persisted_score_count(db_conn, test_user, apri["id"]) == 1

    values.pop("platelets")
    lab_dates.pop("platelets")

    assert oss.compute_all_scores(test_user) == []
    assert oss.get_latest_computed_scores(test_user) == []
    assert _persisted_score_count(db_conn, test_user, apri["id"]) == 0


def test_required_inputs_years_apart_do_not_form_a_synthetic_current_panel(
    db_conn, test_user, monkeypatch
):
    values = {"ast": 40.0, "platelets": 200.0}
    lab_dates = {"ast": "2026-04-01", "platelets": "2026-04-01"}
    apri = _configure_apri_only(monkeypatch, values, lab_dates)

    assert [row["code"] for row in oss.compute_all_scores(test_user)] == ["apri"]
    lab_dates["ast"] = "2018-04-01"

    readiness = oss.get_computable_scores(test_user)
    assert readiness["computable"] == []
    assert readiness["max_panel_date_gap_days"] == 30
    assert readiness["missing"][0]["reason"] == "required_biomarker_dates_exceed_max_gap"
    date_metadata = readiness["missing"][0]["date_metadata"]
    assert date_metadata["input_lab_dates"] == lab_dates
    assert date_metadata["panel_date_span_days"] > oss.MAX_PANEL_DATE_GAP_DAYS

    assert oss.compute_all_scores(test_user) == []
    assert oss.get_latest_computed_scores(test_user) == []
    assert _persisted_score_count(db_conn, test_user, apri["id"]) == 0


def test_panel_date_gap_policy_accepts_30_days_and_rejects_31_days():
    at_limit = oss._get_panel_date_metadata(
        ["ast", "platelets"],
        {
            "ast": {"value": 40.0, "lab_date": "2026-01-01"},
            "platelets": {"value": 200.0, "lab_date": "2026-01-31"},
        },
    )
    over_limit = oss._get_panel_date_metadata(
        ["ast", "platelets"],
        {
            "ast": {"value": 40.0, "lab_date": "2026-01-01"},
            "platelets": {"value": 200.0, "lab_date": "2026-02-01"},
        },
    )

    assert at_limit["panel_date_span_days"] == 30
    assert at_limit["date_coherent"] is True
    assert over_limit["panel_date_span_days"] == 31
    assert over_limit["date_coherent"] is False
