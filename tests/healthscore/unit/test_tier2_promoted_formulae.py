"""Unit tests for the Phase 3 Tier-2 PMID-replacement promotions.

Hb + RDW Mortality Risk (Patel 2010, PMID 19880817) — simplified Patel-
informed harm score with directional sanity checks.

QFracture-2012 hip + major (Hippisley-Cox & Coupland 2012, PMID
22619194) — bridges to the existing-app calculator; tests confirm the
greenfield wrapper produces identical numbers and gates correctly.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from healthscore.scores.bone_muscle import (
    calc_qfracture_hip,
    calc_qfracture_major,
)
from healthscore.scores.system_wide import calc_hb_rdw_mortality


# ── Hb + RDW ──────────────────────────────────────────────────────────────


def test_hb_rdw_zero_when_normal_for_female():
    """Female with Hb=14, RDW=12.5 (well within reference): no harm."""
    assert calc_hb_rdw_mortality(
        {"hemoglobin_gdl": 14, "rdw_pct": 12.5, "sex": "female"}
    ) == Decimal("0")


def test_hb_rdw_zero_when_normal_for_male():
    """Male with Hb=15, RDW=13.0: at reference, no harm."""
    assert calc_hb_rdw_mortality(
        {"hemoglobin_gdl": 15, "rdw_pct": 13.0, "sex": "male"}
    ) == Decimal("0")


def test_hb_rdw_anaemia_alone_raises_harm():
    """Female with Hb=10 (below WHO threshold 12), RDW normal."""
    val = calc_hb_rdw_mortality(
        {"hemoglobin_gdl": 10, "rdw_pct": 13.0, "sex": "female"}
    )
    assert val is not None and float(val) == pytest.approx(16.0, abs=0.01)
    # 12 - 10 = 2 g/dL deficit; 2 * 8 = 16


def test_hb_rdw_anisocytosis_alone_raises_harm():
    """Hb normal, RDW elevated to 16% (Patel 2010 high-mortality bin)."""
    val = calc_hb_rdw_mortality(
        {"hemoglobin_gdl": 14, "rdw_pct": 16.0, "sex": "female"}
    )
    assert val is not None and float(val) == pytest.approx(12.5, abs=0.01)
    # (16 - 13.5) * 5 = 12.5


def test_hb_rdw_combined_caps_at_100():
    val = calc_hb_rdw_mortality(
        {"hemoglobin_gdl": 5, "rdw_pct": 25, "sex": "female"}
    )
    assert val is not None and float(val) == 100.0


def test_hb_rdw_returns_none_on_missing_inputs():
    assert calc_hb_rdw_mortality({"rdw_pct": 14, "sex": "female"}) is None
    assert calc_hb_rdw_mortality({"hemoglobin_gdl": 14, "sex": "female"}) is None
    assert calc_hb_rdw_mortality({"hemoglobin_gdl": 14, "rdw_pct": 14}) is None


# ── QFracture-2012 ────────────────────────────────────────────────────────


def test_qfracture_hip_matches_existing_app_implementation():
    """The greenfield wrapper must produce the same number as the
    existing app's calc_qfracture_hip for the same inputs."""
    from services.organ_score_service import calc_qfracture_hip as app_calc

    args = dict(
        age=75.0, sex="female", bmi=24.0, ethrisk=1, smoke_cat=0,
        alcohol_cat6=0, b_antidepressant=0, b_anycancer=0, b_asthmacopd=0,
        b_carehome=0, b_corticosteroids=0, b_cvd=0, b_dementia=0,
        b_endocrine=0, b_epilepsy2=0, b_falls=0, b_fracture4=0, b_hrt_oest=0,
        b_liver=0, b_parkinsons=0, b_ra_sle=0, b_renal=0, b_type1=0,
        b_type2=0, fh_osteoporosis=0,
    )
    app_val = app_calc(**args)

    greenfield = calc_qfracture_hip({
        "age": 75, "sex": "female", "bmi": 24,
    })
    assert greenfield is not None and app_val is not None
    assert float(greenfield) == pytest.approx(app_val, abs=1e-3)


def test_qfracture_major_matches_existing_app_implementation():
    from services.organ_score_service import calc_qfracture_major as app_calc

    args = dict(
        age=75.0, sex="female", bmi=24.0, ethrisk=1, smoke_cat=0,
        alcohol_cat6=0, b_antidepressant=0, b_anycancer=0, b_asthmacopd=0,
        b_carehome=0, b_corticosteroids=0, b_cvd=0, b_dementia=0,
        b_endocrine=0, b_epilepsy2=0, b_falls=0, b_hrt_oest=0,
        b_liver=0, b_malabsorption=0, b_parkinsons=0, b_ra_sle=0,
        b_renal=0, b_type1=0, b_type2=0, fh_osteoporosis=0,
    )
    app_val = app_calc(**args)

    greenfield = calc_qfracture_major({
        "age": 75, "sex": "female", "bmi": 24,
    })
    assert greenfield is not None and app_val is not None
    assert float(greenfield) == pytest.approx(app_val, abs=1e-3)


def test_qfracture_hip_returns_none_on_missing_required_inputs():
    assert calc_qfracture_hip({"sex": "female", "bmi": 24}) is None         # age
    assert calc_qfracture_hip({"age": 75, "sex": "female"}) is None          # bmi
    assert calc_qfracture_hip({"age": 75, "bmi": 24}) is None                # sex


def test_qfracture_major_risk_climbs_with_age():
    """Same comorbidity profile, two ages: older person has higher risk."""
    young = float(calc_qfracture_major({"age": 50, "sex": "female", "bmi": 24}))
    old = float(calc_qfracture_major({"age": 80, "sex": "female", "bmi": 24}))
    assert old > young + 5.0
