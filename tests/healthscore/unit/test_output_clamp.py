"""Unit tests for the output_clamp mechanism (Phase 5; commitments_log #22).

Pins the architectural contract:
  - Formula output is clamped BEFORE distance-to-cutoff normalisation.
  - Audit log carries both unclamped and clamped values (raw_value vs
    raw_value_unclamped on ScoreResult).
  - Activation forces confidence: low and stamps reason
    "output_clamped:<rationale>".
  - Mid-band inputs (within [min, max]) produce no audit perturbation.

PhenoAge is the canonical clamped score; tests below also exercise the
mechanism with a synthetic ScoreConfig to keep the unit-test scope
narrow.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from healthscore.enums import ScoreStatus
from healthscore.score_config import load_score_config
from healthscore.score_eval import evaluate_score
from healthscore.scores import lookup_formula


_REPO_ROOT = Path(__file__).resolve().parents[3]
_PHENOAGE_CFG = _REPO_ROOT / "configs" / "scores" / "phenoage.json"


# ── PhenoAge canonical clamp regression ──────────────────────────────────


def _phenoage_inputs(**overrides):
    base = dict(
        age=55, albumin_gdl=4.2, creatinine_mgdl=1.0, fasting_glucose_mgdl=100,
        hs_crp_mgL=2.0, lymphocyte_pct=28, mcv_fL=90, rdw_pct=13.5,
        wbc_10e9L=6.5, alkaline_phosphatase_uL=70,
    )
    base.update(overrides)
    return base


@pytest.fixture(scope="module")
def phenoage_config():
    return load_score_config(_PHENOAGE_CFG)


def test_phenoage_config_carries_output_clamp_min_minus25_max_plus25(phenoage_config):
    """Config-level pin: PhenoAge has output_clamp[-25, 25, gompertz_tail].
    Any future config change that drops or relaxes this clamp breaks here."""
    assert phenoage_config.output_clamp is not None
    assert float(phenoage_config.output_clamp.min) == -25.0
    assert float(phenoage_config.output_clamp.max) == 25.0
    assert phenoage_config.output_clamp.rationale == "gompertz_tail"


def test_phenoage_negative_tail_is_clamped_to_minus25(phenoage_config):
    """A super-healthy user whose Gompertz output is well below -25
    must surface clamped raw_value=-25, unclamped raw_value preserved
    in audit, confidence demoted to low, reason stamped."""
    res = evaluate_score(
        phenoage_config,
        raw_inputs=_phenoage_inputs(
            age=50, albumin_gdl=5.2, creatinine_mgdl=0.6,
            fasting_glucose_mgdl=75, hs_crp_mgL=0.2, lymphocyte_pct=45,
            mcv_fL=82, rdw_pct=11.5, wbc_10e9L=4.0,
            alkaline_phosphatase_uL=40,
        ),
        prior_results={}, formula=lookup_formula(phenoage_config.formula),
        gate=None,
    )
    assert res.status is ScoreStatus.OK
    assert res.output_clamped is True
    assert float(res.raw_value) == -25.0
    assert res.raw_value_unclamped is not None
    assert float(res.raw_value_unclamped) < -25.0
    assert res.confidence == "low"
    assert res.reason == "output_clamped:gompertz_tail"


def test_phenoage_positive_tail_is_clamped_to_plus25(phenoage_config):
    """A very-sick user whose Gompertz output is above +25 must clamp."""
    res = evaluate_score(
        phenoage_config,
        raw_inputs=_phenoage_inputs(
            age=50, albumin_gdl=2.5, creatinine_mgdl=4.0,
            fasting_glucose_mgdl=350, hs_crp_mgL=50.0,
            lymphocyte_pct=8, mcv_fL=105, rdw_pct=22, wbc_10e9L=14,
        ),
        prior_results={}, formula=lookup_formula(phenoage_config.formula),
        gate=None,
    )
    assert res.status is ScoreStatus.OK
    assert res.output_clamped is True
    assert float(res.raw_value) == 25.0
    assert res.raw_value_unclamped is not None
    assert float(res.raw_value_unclamped) > 25.0
    assert res.confidence == "low"
    assert res.reason == "output_clamped:gompertz_tail"


def test_phenoage_clamp_drives_q_floor_and_ceiling(phenoage_config):
    """When the clamp activates, the q-mapping consumes the clamped
    raw_value. With anchors low=-10 / indeterm=0 / high=+10 (per the
    shipped phenoage.json), a clamped +25 sits well above 'high', so q
    must clamp to 0.0 (worst); a clamped -25 sits well below 'low', so
    q must clamp to 1.0 (best)."""
    high = evaluate_score(
        phenoage_config,
        raw_inputs=_phenoage_inputs(
            age=50, albumin_gdl=2.5, creatinine_mgdl=4.0,
            fasting_glucose_mgdl=350, hs_crp_mgL=50.0,
            lymphocyte_pct=8, mcv_fL=105, rdw_pct=22, wbc_10e9L=14,
        ),
        prior_results={}, formula=lookup_formula(phenoage_config.formula),
        gate=None,
    )
    low = evaluate_score(
        phenoage_config,
        raw_inputs=_phenoage_inputs(
            age=50, albumin_gdl=5.2, creatinine_mgdl=0.6,
            fasting_glucose_mgdl=75, hs_crp_mgL=0.2, lymphocyte_pct=45,
            mcv_fL=82, rdw_pct=11.5, wbc_10e9L=4.0,
            alkaline_phosphatase_uL=40,
        ),
        prior_results={}, formula=lookup_formula(phenoage_config.formula),
        gate=None,
    )
    assert high.normalised_q == 0.0
    assert low.normalised_q == 1.0


# ── Synthetic ScoreConfig: clamp does not activate when output is in band ─


def test_clamp_does_not_activate_when_value_is_inside_band(phenoage_config):
    """Sanity: when the clamp doesn't fire, raw_value and unclamped are
    equal, output_clamped is False, confidence is config.confidence."""
    # Manufacture a formula that returns exactly 0.0 (well within
    # [-25, +25]) so the clamp doesn't fire.
    def stub(_inputs):
        return Decimal("0")

    res = evaluate_score(
        phenoage_config,
        raw_inputs=_phenoage_inputs(),
        prior_results={},
        formula=stub,
        gate=None,
    )
    assert res.status is ScoreStatus.OK
    assert res.output_clamped is False
    assert res.raw_value == res.raw_value_unclamped == Decimal("0")
    assert res.confidence == phenoage_config.confidence
    assert res.reason is None
