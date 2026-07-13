import pytest

from services import organ_score_service as oss


_BIOMARKERS = {
    "total_bilirubin": 0.8,
    "albumin": 4.2,
    "platelets": 210.0,
    "creatinine": 1.0,
    "uacr": 100.0,
}

_CLINICAL = {
    "age": 65.0,
    "sex": "male",
    "diabetes_status": 0,
    "systolic_bp": 125.0,
    "chronic_liver_disease": 0,
    "chronic_kidney_disease": 1,
    "atrial_fibrillation": 0,
}


def _score_definitions(*codes):
    oss.seed_organ_score_definitions()
    by_code = {
        definition["code"]: definition
        for definition in oss.get_all_score_definitions()
    }
    return [by_code[code] for code in codes]


def _configure_score_inputs(monkeypatch, definitions, clinical=None):
    biomarkers = dict(_BIOMARKERS)
    profile = dict(_CLINICAL)
    if clinical:
        profile.update(clinical)

    monkeypatch.setattr(oss, "get_all_score_definitions", lambda: definitions)
    monkeypatch.setattr(
        oss, "_get_latest_biomarkers_as_dict", lambda _user_id: dict(biomarkers)
    )
    monkeypatch.setattr(
        oss,
        "_get_latest_biomarkers_with_dates",
        lambda _user_id: {
            code: {"value": value, "lab_date": "2026-07-01"}
            for code, value in biomarkers.items()
        },
    )
    monkeypatch.setattr(oss, "_get_latest_dexa_inputs_with_dates", lambda _user_id: {})
    monkeypatch.setattr(oss, "_get_clinical_data", lambda _user_id: dict(profile))


def _persist_stale_result(user_id, definition):
    oss.save_score_result(
        user_id=user_id,
        score_def_id=definition["id"],
        value=42.0,
        label="Stale",
        severity="high",
        input_snapshot={},
        lab_date="2026-06-01",
    )


@pytest.mark.parametrize(
    ("score_code", "profile_field", "reason_code", "reason_text"),
    [
        (
            "amap_hcc",
            "chronic_liver_disease",
            "cld_not_documented",
            "chronic liver disease",
        ),
        (
            "cha2ds2_vasc",
            "atrial_fibrillation",
            "af_not_documented",
            "atrial fibrillation",
        ),
    ],
)
def test_documented_condition_gate_removes_stale_score_and_exposes_reason(
    db_conn,
    test_user,
    monkeypatch,
    score_code,
    profile_field,
    reason_code,
    reason_text,
):
    definition = _score_definitions(score_code)[0]
    _persist_stale_result(test_user, definition)
    _configure_score_inputs(monkeypatch, [definition], {profile_field: 0})

    readiness = oss.get_computable_scores(test_user)
    assert readiness["computable"] == []
    assert len(readiness["inapplicable"]) == 1
    gated = readiness["inapplicable"][0]
    assert gated["reason"] == "inapplicable"
    assert gated["applicability_reason_code"] == reason_code
    assert reason_text in gated["applicability_reason"]

    assert oss.compute_all_scores(test_user) == []
    assert oss.get_latest_computed_scores(test_user) == []
    assert oss.compute_overall_organ_score(test_user) is None


@pytest.mark.parametrize(
    ("score_code", "profile_field"),
    [
        ("amap_hcc", "chronic_liver_disease"),
        ("cha2ds2_vasc", "atrial_fibrillation"),
    ],
)
def test_documented_condition_allows_legacy_score(
    db_conn, test_user, monkeypatch, score_code, profile_field
):
    definition = _score_definitions(score_code)[0]
    _configure_score_inputs(monkeypatch, [definition], {profile_field: 1})

    readiness = oss.get_computable_scores(test_user)
    assert [row["code"] for row in readiness["computable"]] == [score_code]
    assert readiness["inapplicable"] == []
    assert [row["code"] for row in oss.compute_all_scores(test_user)] == [score_code]


def test_kfre_gate_rejects_egfr_above_60_and_accepts_boundary(
    db_conn, test_user, monkeypatch
):
    definitions = _score_definitions("kfre_5yr", "kfre_2yr")
    for definition in definitions:
        _persist_stale_result(test_user, definition)
    _configure_score_inputs(monkeypatch, definitions)

    egfr = {"value": 60.1}
    monkeypatch.setattr(
        oss,
        "calc_ckd_epi_2021",
        lambda _creatinine, _age, _sex: egfr["value"],
    )

    readiness = oss.get_computable_scores(test_user)
    assert readiness["computable"] == []
    assert {
        row["applicability_reason_code"] for row in readiness["inapplicable"]
    } == {"egfr_above_ckd_threshold"}
    assert all(
        "eGFR <= 60" in row["applicability_reason"]
        for row in readiness["inapplicable"]
    )

    assert oss.compute_all_scores(test_user) == []
    assert oss.get_latest_computed_scores(test_user) == []
    assert oss.compute_overall_organ_score(test_user) is None

    egfr["value"] = 60.0
    readiness = oss.get_computable_scores(test_user)
    assert {row["code"] for row in readiness["computable"]} == {
        "kfre_5yr",
        "kfre_2yr",
    }
    assert readiness["inapplicable"] == []
    assert {row["code"] for row in oss.compute_all_scores(test_user)} == {
        "kfre_5yr",
        "kfre_2yr",
    }
