"""Integrity tests for score lifecycle + domain classification."""

import pytest

from config.organ_scores_data import ORGAN_SCORE_DEFINITIONS
from config.score_classification import (
    DOMAIN_CODES,
    LIFECYCLE_CODES,
    SCORE_CLASSIFICATION,
    active_scores,
    get_classification,
    research_scores,
    scores_for_domain,
    superseded_scores,
)


def test_every_defined_score_has_a_classification_entry():
    all_codes = {d["code"] for d in ORGAN_SCORE_DEFINITIONS}
    classified = set(SCORE_CLASSIFICATION.keys())
    assert all_codes == classified, (
        f"missing={sorted(all_codes - classified)}, "
        f"extra={sorted(classified - all_codes)}"
    )


@pytest.mark.parametrize("code, info", sorted(SCORE_CLASSIFICATION.items()))
def test_classification_entry_fields_are_valid(code, info):
    assert info["lifecycle"] in LIFECYCLE_CODES, f"{code} has invalid lifecycle {info['lifecycle']}"
    assert info["primary_domain"] in DOMAIN_CODES, (
        f"{code} has invalid primary_domain {info['primary_domain']}"
    )
    for dom in info.get("secondary_domains") or []:
        assert dom in DOMAIN_CODES, f"{code} has invalid secondary_domain {dom}"
    assert info.get("lifecycle_note"), f"{code} missing lifecycle_note rationale"
    if info["lifecycle"] == "superseded":
        assert info.get("superseded_by"), f"{code} marked superseded but missing superseded_by"
        assert info["superseded_by"] in SCORE_CLASSIFICATION, (
            f"{code} superseded_by={info['superseded_by']} which is not itself classified"
        )


def test_active_scores_cover_every_primary_cvd_and_liver_workhorse():
    actives = set(active_scores())
    must_be_active = {
        "prevent_10yr", "prevent_10yr_ascvd", "prevent_10yr_hf",
        "qrisk3", "ascvd_pce",
        "fib4", "apri", "hsi", "fli",
        "homa_ir", "tyg_index", "mets_ir",
        "dxa_osteoporosis_who", "ewgsop2_sarcopenia",
        "cbc_mortality_risk", "phenoage",
    }
    missing = must_be_active - actives
    assert not missing, f"expected these to be lifecycle=active: {sorted(missing)}"


def test_superseded_scores_point_to_a_valid_replacement():
    for code in superseded_scores():
        info = get_classification(code)
        assert info["superseded_by"] in SCORE_CLASSIFICATION
        # The replacement should not itself be superseded.
        assert get_classification(info["superseded_by"])["lifecycle"] != "superseded"


def test_heart_metabolism_is_densest_primary_domain():
    # Sanity: cardiovascular + metabolic risk scores dominate the panel.
    primary_counts = {
        dom: len(scores_for_domain(dom, primary_only=True))
        for dom in DOMAIN_CODES
    }
    assert primary_counts["heart_metabolism"] >= primary_counts["brain_health"]
    assert primary_counts["heart_metabolism"] >= primary_counts["muscle_bones"]
    assert primary_counts["heart_metabolism"] >= primary_counts["gut_digestion"]


def test_dxa_and_sarcopenia_are_primary_muscle_bones():
    assert get_classification("dxa_osteoporosis_who")["primary_domain"] == "muscle_bones"
    assert get_classification("ewgsop2_sarcopenia")["primary_domain"] == "muscle_bones"


def test_phenoage_is_primary_system_wide():
    assert get_classification("phenoage")["primary_domain"] == "system_wide"


def test_research_scores_are_flagged_not_deleted():
    # Research-tier formulas must still exist in FORMULA_DISPATCH so they keep
    # computing for clinicians who explicitly opt in to the research filter.
    from services.organ_score_service import FORMULA_DISPATCH

    defined_codes = {d["code"]: d for d in ORGAN_SCORE_DEFINITIONS}
    for code in research_scores():
        formula_key = defined_codes[code]["formula_key"]
        assert formula_key in FORMULA_DISPATCH, (
            f"research-tier score {code} missing dispatch entry"
        )
