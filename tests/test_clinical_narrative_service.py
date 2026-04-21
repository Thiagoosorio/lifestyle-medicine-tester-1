"""Tests for cross-domain pattern detection."""

from services.clinical_narrative_service import detect_cross_domain_patterns


def _score(code, severity, name=None):
    return {"code": code, "name": name or code, "severity": severity, "label": ""}


def test_no_patterns_when_scores_are_normal():
    scores = [
        _score("hsi", "normal"),
        _score("homa_ir", "normal"),
        _score("prevent_10yr", "normal"),
    ]
    assert detect_cross_domain_patterns(scores) == []


def test_masld_pattern_activates_with_fatty_liver_plus_insulin_resistance():
    scores = [
        _score("hsi", "elevated", "Hepatic Steatosis Index"),
        _score("homa_ir", "high", "HOMA-IR"),
    ]
    out = detect_cross_domain_patterns(scores)
    codes = {p["code"] for p in out}
    assert "masld_metabolic" in codes
    masld = next(p for p in out if p["code"] == "masld_metabolic")
    # Severity rolls up to the highest triggering score
    assert masld["severity"] == "high"
    trigger_codes = {t["code"] for t in masld["triggering_scores"]}
    assert trigger_codes == {"hsi", "homa_ir"}


def test_masld_requires_both_groups():
    # Only liver triggers, no insulin-resistance match -> inactive
    scores = [_score("hsi", "elevated"), _score("prevent_10yr", "elevated")]
    codes = {p["code"] for p in detect_cross_domain_patterns(scores)}
    assert "masld_metabolic" not in codes


def test_ckm_syndrome_requires_all_three_axes():
    scores = [
        _score("prevent_10yr_hf", "elevated"),
        _score("ckd_epi_egfr", "elevated"),
        _score("mets_ir", "elevated"),
    ]
    codes = {p["code"] for p in detect_cross_domain_patterns(scores)}
    assert "ckm_syndrome" in codes

    # Drop the kidney axis -> inactive
    scores2 = [s for s in scores if s["code"] != "ckd_epi_egfr"]
    codes2 = {p["code"] for p in detect_cross_domain_patterns(scores2)}
    assert "ckm_syndrome" not in codes2


def test_atherogenic_dyslipidemia_needs_two_particle_markers():
    one_marker = [_score("apob_risk", "elevated")]
    two_markers = [
        _score("apob_risk", "elevated"),
        _score("lpa_risk", "high"),
    ]
    assert "atherogenic_dyslipidemia" not in {p["code"] for p in detect_cross_domain_patterns(one_marker)}
    codes = {p["code"] for p in detect_cross_domain_patterns(two_markers)}
    assert "atherogenic_dyslipidemia" in codes


def test_patterns_sorted_by_descending_severity():
    scores = [
        # triggers masld_metabolic at 'elevated'
        _score("hsi", "elevated"), _score("homa_ir", "elevated"),
        # triggers inflammation at 'high'
        _score("nlr", "high"), _score("sii", "high"),
    ]
    out = detect_cross_domain_patterns(scores)
    assert out[0]["code"] == "chronic_inflammation"
    assert out[0]["severity"] == "high"


def test_elevated_threshold_excludes_merely_normal_scores():
    # Normal severity should not satisfy the default elevated floor.
    scores = [_score("hsi", "normal"), _score("homa_ir", "normal")]
    assert detect_cross_domain_patterns(scores) == []
