import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from config.sibo_data import SIBO_DIET_TYPES, SIBO_EVIDENCE
import services.sibo_service as sibo_service


SAFE_ELIMINATION_SCREEN = {
    "acknowledged": True,
    "red_flags": [],
    "nutrition_risks": [],
    "clinician_reviewed": False,
}


@pytest.mark.parametrize(
    ("screen", "expected_code"),
    [
        (None, "acknowledgement_required"),
        (
            {**SAFE_ELIMINATION_SCREEN, "red_flags": ["Unintentional weight loss"]},
            "red_flag",
        ),
        (
            {
                **SAFE_ELIMINATION_SCREEN,
                "nutrition_risks": ["Current or past eating disorder"],
            },
            "nutrition_review_required",
        ),
    ],
)
def test_elimination_safety_failure_precedes_database_access(
    monkeypatch, screen, expected_code
):
    def unexpected_connection():
        raise AssertionError("safety failure must occur before database access")

    monkeypatch.setattr(sibo_service, "get_connection", unexpected_connection)

    with pytest.raises(sibo_service.RestrictiveDietSafetyError) as exc_info:
        sibo_service.start_fodmap_phase(1, "elimination", safety_screen=screen)

    assert exc_info.value.code == expected_code


def test_elimination_phase_starts_after_safety_acknowledgement(
    db_conn, test_user, monkeypatch
):
    monkeypatch.setattr(sibo_service, "get_connection", db_conn)

    sibo_service.start_fodmap_phase(
        test_user, "elimination", safety_screen=SAFE_ELIMINATION_SCREEN
    )

    phase = sibo_service.get_current_phase(test_user)
    assert phase["phase"] == "elimination"


def test_sibo_evidence_copy_separates_ibs_symptoms_from_sibo_eradication():
    low_fodmap = SIBO_DIET_TYPES["low_fodmap"]
    assert "first-line" not in low_fodmap["note"].lower()
    assert "ibs symptom" in low_fodmap["note"].lower()
    assert "not established as sibo eradication" in low_fodmap["note"].lower()

    elemental = SIBO_DIET_TYPES["elemental"]
    elemental_study = next(row for row in SIBO_EVIDENCE if row["pmid"] == "14992438")
    assert elemental["confidence"] == "C"
    assert elemental_study["evidence_grade"] == "C"
    assert "uncontrolled" in elemental_study["summary"].lower()
    limitations = elemental_study["causation_note"].lower()
    assert "very low-certainty" in limitations
    assert "without a control group" in limitations
    assert "chart review" in limitations


def test_spearman_rejects_non_variable_comparisons():
    assert sibo_service._spearman_rho([1] * 10, list(range(10))) == (None, None)
    assert sibo_service._spearman_rho(list(range(10)), [4] * 10) == (None, None)


def test_benjamini_hochberg_adjustment_is_monotone_in_rank():
    adjusted = sibo_service._benjamini_hochberg([0.01, 0.04, 0.03])
    assert adjusted == pytest.approx([0.03, 0.04, 0.04])


def test_correlation_results_are_exploratory_adjusted_and_drop_constant_groups(
    db_conn, test_user, monkeypatch
):
    monkeypatch.setattr(sibo_service, "get_connection", db_conn)
    conn = db_conn()
    for index in range(12):
        log_date = (date.today() - timedelta(days=11 - index)).isoformat()
        symptom = index % 10
        conn.execute(
            """INSERT INTO sibo_symptom_logs
               (user_id, log_date, bloating, abdominal_pain, gas, nausea, fatigue, overall_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (test_user, log_date, symptom, symptom, symptom, symptom, symptom, symptom),
        )
        conn.execute(
            """INSERT INTO sibo_food_logs
               (user_id, log_date, meal_type, food_name, serving_size, fodmap_groups)
               VALUES (?, ?, 'lunch', 'Test food', ?, ?)""",
            (test_user, log_date, index + 1, json.dumps(["fructans"])),
        )
    conn.commit()
    conn.close()

    results = sibo_service.compute_correlations(test_user)

    assert results
    assert {result["group"] for result in results} == {"fructans"}
    assert all(result["exploratory"] is True for result in results)
    assert all(result["p"] == result["p_adjusted"] for result in results)
    assert all(result["p_adjusted"] >= result["p_raw"] for result in results)
    assert all(
        result["multiplicity_method"] == "Benjamini-Hochberg FDR"
        for result in results
    )


def test_correlation_page_removes_significance_claim():
    page = Path("pages/sibo_tracker.py").read_text(encoding="utf-8").lower()
    assert "likely a significant pattern" not in page
    assert "exploratory fodmap-symptom correlations" in page
    assert "benjamini-hochberg" in page
