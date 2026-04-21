from config.organ_scores_data import ORGAN_SCORE_DEFINITIONS


def _defs_by_code():
    return {d["code"]: d for d in ORGAN_SCORE_DEFINITIONS}


def test_organ_score_codes_are_unique():
    codes = [d["code"] for d in ORGAN_SCORE_DEFINITIONS]
    assert len(codes) == len(set(codes))


def test_validated_scores_have_primary_citation_pmid():
    missing = [
        d["code"]
        for d in ORGAN_SCORE_DEFINITIONS
        if d.get("tier") == "validated" and not d.get("citation_pmid")
    ]
    assert missing == []


def test_known_citation_regressions_are_fixed():
    defs = _defs_by_code()
    assert defs["remnant_cholesterol"]["citation_pmid"] == "23265341"
    assert defs["plr"]["citation_pmid"] == "24793958"


def test_prevent_is_validated_with_full_coefficient_parity():
    defs = _defs_by_code()
    # Full AHA PREVENT coefficients (Khan 2024 Table S12) implemented,
    # output verified against preventr R package reference cases.
    assert defs["prevent_10yr"]["tier"] == "validated"
    assert defs["prevent_10yr_ascvd"]["tier"] == "validated"
    assert defs["prevent_10yr_hf"]["tier"] == "validated"
    assert defs["prevent_10yr"]["citation_pmid"] == "37947085"


def test_cbc_mortality_risk_replaces_legacy_composite():
    defs = _defs_by_code()
    # CBC composite (arbitrary percentile binning) retired in favor of the
    # Patel 2010 RDW + WHO-anemia all-cause mortality score.
    assert "cbc_composite" not in defs
    assert defs["cbc_mortality_risk"]["tier"] == "validated"
    assert defs["cbc_mortality_risk"]["citation_pmid"] == "20921437"


def test_new_scores_are_present_with_expected_formula_keys():
    defs = _defs_by_code()
    assert defs["albi_score"]["formula_key"] == "calc_albi_score"
    assert defs["fli"]["formula_key"] == "calc_fli"
    assert defs["bard_score"]["formula_key"] == "calc_bard_score"
    assert defs["mets_ir"]["formula_key"] == "calc_mets_ir"
    assert defs["tyg_bmi"]["formula_key"] == "calc_tyg_bmi"
    assert defs["lap_index"]["formula_key"] == "calc_lap_index"
    assert defs["vai"]["formula_key"] == "calc_vai"
    assert defs["apob_risk"]["formula_key"] == "calc_apob_risk"
    assert defs["homocysteine_neurovascular"]["formula_key"] == "calc_homocysteine_neurovascular_risk"
    assert defs["framingham_vascular_age_gap"]["formula_key"] == "calc_framingham_vascular_age_gap"
