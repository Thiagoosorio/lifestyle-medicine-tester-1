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


def test_prevent_is_marked_directional_until_full_parity_validation():
    defs = _defs_by_code()
    assert defs["prevent_10yr"]["tier"] == "derived"
