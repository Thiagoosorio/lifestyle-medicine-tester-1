from services.organ_score_service import (
    calc_who_na_me_cvd_lab,
    calc_who_na_me_cvd_nonlab,
)


def test_who_na_me_lab_matches_official_low_risk_cell():
    risk = calc_who_na_me_cvd_lab(
        age=42,
        sex="male",
        total_chol=145,  # ~3.75 mmol/L -> <4 bin
        systolic_bp=118,
        smoking=False,
        diabetes=False,
    )
    assert risk == 2.0


def test_who_na_me_lab_matches_official_diabetes_smoker_cell():
    risk = calc_who_na_me_cvd_lab(
        age=42,
        sex="female",
        total_chol=280,  # ~7.24 mmol/L -> >=7 bin
        systolic_bp=118,
        smoking=True,
        diabetes=True,
    )
    assert risk == 19.0


def test_who_na_me_nonlab_matches_official_cell():
    risk = calc_who_na_me_cvd_nonlab(
        age=42,
        sex="male",
        bmi=36.0,  # >=35 bin
        systolic_bp=145,
        smoking=True,
    )
    assert risk == 18.0


def test_who_na_me_chart_rejects_age_outside_published_range():
    assert calc_who_na_me_cvd_lab(
        age=75,
        sex="male",
        total_chol=180,
        systolic_bp=130,
        smoking=False,
        diabetes=False,
    ) is None

    assert calc_who_na_me_cvd_nonlab(
        age=39,
        sex="female",
        bmi=24.0,
        systolic_bp=130,
        smoking=False,
    ) is None
