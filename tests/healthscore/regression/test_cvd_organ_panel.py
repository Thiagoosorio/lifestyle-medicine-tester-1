"""§1.5 weight-redistribution regression for the cardiovascular organ panel.

Composite members (architecture_spec.md §4 Default weights, adjusted for
the Phase 3 panel with FINDRISC deferred to a later phase):

    prevent  weight 0.55
    apob     weight 0.30
    lpa      weight 0.15

CHA₂DS₂-VASc is not a composite member (gated on AF documented; Tier 1
clinical-safety score that displays separately).

This regression verifies:
  1. Healthy user with all three composite scores OK: aggregator uses
     all three with the configured weights.
  2. CHA₂DS₂-VASc gates correctly (no AF documented) without affecting
     the CVD composite score (it is non-composite, so its gating is
     orthogonal).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from healthscore.aggregate.common import weighted_geomean
from healthscore.aggregate.spec_a import aggregate_organ_spec_a
from healthscore.aggregate.spec_b import aggregate_organ_spec_b
from healthscore.enums import ScoreStatus
from healthscore.score_config import load_score_config, parse_gate_spec
from healthscore.score_eval import evaluate_score
from healthscore.scores import lookup_formula


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"
_WORDING_YAML = _REPO_ROOT / "configs" / "wording.yaml"


@pytest.fixture(scope="module")
def wording_templates():
    return yaml.safe_load(_WORDING_YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cvd_configs():
    return {
        sid: load_score_config(_SCORE_CONFIGS / f"{sid}.json")
        for sid in ("prevent", "apob", "lpa", "cha2ds2vasc")
    }


def _evaluate(cfg, raw_inputs, templates):
    return evaluate_score(
        cfg,
        raw_inputs=raw_inputs,
        prior_results={},
        formula=lookup_formula(cfg.formula),
        gate=parse_gate_spec(cfg.gate_requirements),
        templates=templates,
    )


def test_cvd_composite_weights_sum_to_one(cvd_configs):
    composite = [c for c in cvd_configs.values() if c.composite_member]
    total = sum(c.composite_weight for c in composite)
    assert total == pytest.approx(1.0, abs=1e-6)


def test_cvd_panel_typical_user_uses_all_composite_members(
    cvd_configs, wording_templates
):
    """55-year-old male with normal lipids; all three composite scores OK."""
    raw_inputs = {
        "age": 55, "sex": "male",
        "total_chol_mgdl": 200, "hdl_c_mgdl": 45,
        "sbp_mmhg": 130, "bmi": 27, "egfr": 90,
        "diabetes": False, "smoking": False,
        "bp_treatment": False, "statin": False,
        "apob_mgdl": 95,
        "lpa_mgdl": 25,
    }
    results = [
        _evaluate(cvd_configs["prevent"], raw_inputs, wording_templates),
        _evaluate(cvd_configs["apob"],    raw_inputs, wording_templates),
        _evaluate(cvd_configs["lpa"],     raw_inputs, wording_templates),
    ]
    for r in results:
        assert r.status is ScoreStatus.OK
        assert r.normalised_q is not None

    weights = {sid: cvd_configs[sid].composite_weight for sid in ("prevent", "apob", "lpa")}

    spec_a, _ = aggregate_organ_spec_a(
        score_results=results, weights=weights, epsilon=0.01,
    )
    spec_b, _ = aggregate_organ_spec_b(
        score_results=results, weights=weights, epsilon=0.01,
    )
    assert spec_a is not None and spec_b is not None
    # methodology §1.3: spec A == spec B at organ level.
    assert abs(spec_a - spec_b) < 0.01

    expected, _ = weighted_geomean(
        [(r.normalised_q, weights[r.score_id]) for r in results], epsilon=0.01,
    )
    assert spec_a == pytest.approx(expected, abs=1e-6)


def test_cha2ds2_vasc_gated_without_af_does_not_affect_cvd_composite(
    cvd_configs, wording_templates
):
    """CHA₂DS₂-VASc has composite_member=false. A user without
    documented AF gates CHA₂DS₂-VASc (correctly) but the CVD composite
    score is unaffected because CHA₂DS₂-VASc is not in the composite."""
    raw_inputs = {
        "age": 55, "sex": "male",
        "atrial_fibrillation_status": None,
        "total_chol_mgdl": 200, "hdl_c_mgdl": 45,
        "sbp_mmhg": 130, "bmi": 27, "egfr": 90,
        "diabetes": False, "smoking": False,
        "bp_treatment": False, "statin": False,
        "apob_mgdl": 95,
        "lpa_mgdl": 25,
    }
    cha = _evaluate(cvd_configs["cha2ds2vasc"], raw_inputs, wording_templates)
    assert cha.status is ScoreStatus.GATED
    assert cha.gate_failures == ("af_not_documented",)

    # Composite ignores cha2ds2vasc (non-member); aggregator processes only
    # the three composite members.
    results = [
        _evaluate(cvd_configs["prevent"], raw_inputs, wording_templates),
        _evaluate(cvd_configs["apob"],    raw_inputs, wording_templates),
        _evaluate(cvd_configs["lpa"],     raw_inputs, wording_templates),
    ]
    weights = {sid: cvd_configs[sid].composite_weight for sid in ("prevent", "apob", "lpa")}
    spec_a, _ = aggregate_organ_spec_a(
        score_results=results, weights=weights, epsilon=0.01,
    )
    assert spec_a is not None
    assert 0.0 <= spec_a <= 100.0


def test_documented_af_user_passes_cha2ds2_vasc_gate(cvd_configs, wording_templates):
    raw_inputs = {
        "age": 78, "sex": "female",
        "atrial_fibrillation_status": True,
        "chf_or_lv_dysfunction": False,
        "hypertension": True,
        "diabetes": False,
        "stroke_tia_thromboembolism": False,
        "vascular_disease": False,
    }
    res = _evaluate(cvd_configs["cha2ds2vasc"], raw_inputs, wording_templates)
    assert res.status is ScoreStatus.OK
    assert res.gate_failures == ()
    # 78F + AF + HTN = 1(female) + 2(>=75) + 1(HTN) = 4
    assert res.raw_value is not None and float(res.raw_value) == 4.0
