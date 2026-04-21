"""Tests for the Hb + RDW mortality-risk composite (replaces cbc_composite)."""

from services.organ_score_service import calc_cbc_mortality_risk


def test_healthy_female_returns_high_score():
    # Hb 13.5, RDW 12.2 -> lowest RDW quintile + normal Hb
    assert calc_cbc_mortality_risk(hemoglobin=13.5, rdw=12.2, sex="female") == 90


def test_healthy_male_returns_high_score():
    assert calc_cbc_mortality_risk(hemoglobin=15.0, rdw=12.4, sex="male") == 90


def test_mild_anemia_lowers_score():
    # Hb 11 (mild anemia F) with normal RDW -> mid-range
    value = calc_cbc_mortality_risk(hemoglobin=11.0, rdw=13.0, sex="female")
    assert 55 <= value <= 75


def test_elevated_rdw_lowers_score_even_with_normal_hb():
    # RDW 15.0 (Patel Q5) but Hb normal -> should fall below 60
    value = calc_cbc_mortality_risk(hemoglobin=14.0, rdw=15.2, sex="female")
    assert value < 60


def test_severe_anemia_plus_high_rdw_flags_high_risk():
    value = calc_cbc_mortality_risk(hemoglobin=7.5, rdw=16.0, sex="male")
    assert value <= 30


def test_returns_none_when_inputs_missing_or_nonpositive():
    assert calc_cbc_mortality_risk(hemoglobin=None, rdw=13.0, sex="male") is None
    assert calc_cbc_mortality_risk(hemoglobin=13.0, rdw=None, sex="male") is None
    assert calc_cbc_mortality_risk(hemoglobin=0, rdw=13.0, sex="male") is None
