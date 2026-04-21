"""Tests for age/sex-specific reference range resolution."""

from config.biomarkers_data import BIOMARKER_DEFINITIONS, resolve_reference_range


_BY_CODE = {b["code"]: b for b in BIOMARKER_DEFINITIONS}


def test_hemoglobin_resolves_sex_specific_ranges():
    hb = _BY_CODE["hemoglobin"]
    female = resolve_reference_range(hb, age=35, sex="female")
    male = resolve_reference_range(hb, age=35, sex="male")
    # WHO 2011: female anemia cutoff 12.0, male 13.0
    assert female["standard_low"] == 12.0
    assert male["standard_low"] == 13.5
    # Upper limits differ by sex
    assert female["standard_high"] == 15.5
    assert male["standard_high"] == 17.5


def test_creatinine_uses_sex_specific_range():
    creat = _BY_CODE["creatinine"]
    female = resolve_reference_range(creat, sex="female")
    male = resolve_reference_range(creat, sex="male")
    assert female["standard_low"] == 0.5
    assert male["standard_low"] == 0.7


def test_ferritin_premenopausal_vs_postmenopausal():
    fer = _BY_CODE["ferritin"]
    premen = resolve_reference_range(fer, age=30, sex="female")
    postmen = resolve_reference_range(fer, age=60, sex="female")
    # Premenopausal women run lower
    assert premen["standard_high"] < postmen["standard_high"]


def test_testosterone_female_range_is_much_lower_than_male():
    t = _BY_CODE["testosterone_total"]
    fem = resolve_reference_range(t, age=35, sex="female")
    mal = resolve_reference_range(t, age=35, sex="male")
    assert fem["standard_high"] <= 100
    assert mal["standard_low"] >= 300


def test_testosterone_male_declines_with_age_band():
    t = _BY_CODE["testosterone_total"]
    young = resolve_reference_range(t, age=30, sex="male")
    older = resolve_reference_range(t, age=65, sex="male")
    assert young["optimal_low"] > older["optimal_low"]


def test_biomarker_without_variants_returns_base_range_unchanged():
    tc = _BY_CODE["total_cholesterol"]
    ranges = resolve_reference_range(tc, age=40, sex="female")
    assert ranges["standard_low"] == tc["standard_low"]
    assert ranges["standard_high"] == tc["standard_high"]


def test_resolver_handles_missing_sex_gracefully():
    # Without sex we should still get a usable range (falls back to base).
    hb = _BY_CODE["hemoglobin"]
    ranges = resolve_reference_range(hb)
    assert ranges["standard_low"] is not None
    assert ranges["standard_high"] is not None
