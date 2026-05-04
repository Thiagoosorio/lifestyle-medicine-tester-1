"""§1.5 weight-redistribution regression for the kidney organ panel.

The kidney panel carries three composite members:

    egfr           weight 0.50
    kfre           weight 0.30   (gated when eGFR > 60)
    kdigo_category weight 0.20

When KFRE is gated (the architecturally common case for non-CKD users),
methodology §1.5 requires its weight to be redistributed across the
surviving cluster members. ``weighted_geomean`` renormalises weights
internally, so the aggregator's output for a healthy user with eGFR > 60
should reflect eGFR (renormalised to 0.50/0.70) and KDIGO (renormalised
to 0.20/0.70) only, with KFRE absent.

This regression pins both halves:

  1. Healthy user (eGFR > 60): KFRE GATED, kidney score = weighted geomean
     of eGFR + KDIGO with renormalised weights.
  2. CKD user (eGFR ≤ 60): KFRE OK, kidney score uses all three.
"""

from __future__ import annotations

import math
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
def kidney_configs():
    return {
        "egfr":           load_score_config(_SCORE_CONFIGS / "egfr.json"),
        "kfre":           load_score_config(_SCORE_CONFIGS / "kfre.json"),
        "kdigo_category": load_score_config(_SCORE_CONFIGS / "kdigo_category.json"),
    }


def _evaluate_panel(configs, raw_inputs, templates):
    """Run the three kidney scores in dependency order (eGFR first; KFRE
    references raw_inputs.egfr but the test passes the eGFR value directly
    via raw_inputs, so no cross-score wiring is needed at this level)."""
    results = []
    for sid in ("egfr", "kfre", "kdigo_category"):
        cfg = configs[sid]
        res = evaluate_score(
            cfg,
            raw_inputs=raw_inputs,
            prior_results={r.score_id: r for r in results},
            formula=lookup_formula(cfg.formula),
            gate=parse_gate_spec(cfg.gate_requirements),
            templates=templates,
        )
        results.append(res)
    return {r.score_id: r for r in results}


# ──────────────────────────────────────────────────────────────────────────
# Healthy user: KFRE gated, weight redistributed
# ──────────────────────────────────────────────────────────────────────────


def test_healthy_user_kfre_gated_kidney_panel_uses_egfr_and_kdigo_only(
    kidney_configs, wording_templates
):
    """Healthy 50yo male with eGFR=100 and trace albuminuria. KFRE must be
    GATED (egfr_above_ckd_threshold). Kidney organ score must compute from
    eGFR + KDIGO only with weights renormalised per methodology §1.5."""
    raw_inputs = {
        "age": 50,
        "sex": "male",
        "serum_creatinine_mgdl": 0.9,         # -> eGFR ~104
        "egfr": 100,                           # presented directly to KFRE / KDIGO
        "uacr": 10,                            # A1 (normal)
    }
    results = _evaluate_panel(kidney_configs, raw_inputs, wording_templates)

    # Gate verification.
    assert results["egfr"].status is ScoreStatus.OK
    assert results["kfre"].status is ScoreStatus.GATED
    assert results["kfre"].gate_failures == ("egfr_above_ckd_threshold",)
    assert results["kdigo_category"].status is ScoreStatus.OK

    weights = {
        sid: kidney_configs[sid].composite_weight
        for sid in ("egfr", "kfre", "kdigo_category")
    }

    spec_a, _ = aggregate_organ_spec_a(
        score_results=list(results.values()), weights=weights, epsilon=0.01,
    )
    spec_b, _ = aggregate_organ_spec_b(
        score_results=list(results.values()), weights=weights, epsilon=0.01,
    )

    # Methodology §1.3: spec A == spec B at organ level.
    assert spec_a is not None and spec_b is not None
    assert abs(spec_a - spec_b) < 0.01

    # Direct expected: weighted geomean of (eGFR_q, KDIGO_q) with weights
    # renormalised from (0.50, 0.20) -> (5/7, 2/7). KFRE drops out entirely.
    egfr_q = results["egfr"].normalised_q
    kdigo_q = results["kdigo_category"].normalised_q
    assert egfr_q is not None and kdigo_q is not None
    expected_score, _ = weighted_geomean(
        [(egfr_q, 0.50), (kdigo_q, 0.20)], epsilon=0.01,
    )
    assert spec_a == pytest.approx(expected_score, abs=1e-6)


# ──────────────────────────────────────────────────────────────────────────
# CKD user: all three scores contribute
# ──────────────────────────────────────────────────────────────────────────


def test_ckd_user_kfre_active_kidney_panel_uses_all_three(
    kidney_configs, wording_templates
):
    """65yo male with G3b CKD (eGFR=40) + A2 albuminuria (UAC R=120).
    KFRE gate passes (eGFR ≤ 60); all three scores contribute."""
    raw_inputs = {
        "age": 65,
        "sex": "male",
        "serum_creatinine_mgdl": 1.85,        # -> eGFR ~40
        "egfr": 40,                            # explicit value passed to KFRE / KDIGO
        "uacr": 120,
    }
    results = _evaluate_panel(kidney_configs, raw_inputs, wording_templates)

    # All three OK.
    assert results["egfr"].status is ScoreStatus.OK
    assert results["kfre"].status is ScoreStatus.OK
    assert results["kdigo_category"].status is ScoreStatus.OK
    assert results["kfre"].normalised_q is not None
    assert results["kdigo_category"].normalised_q is not None

    weights = {
        sid: kidney_configs[sid].composite_weight
        for sid in ("egfr", "kfre", "kdigo_category")
    }

    spec_a, _ = aggregate_organ_spec_a(
        score_results=list(results.values()), weights=weights, epsilon=0.01,
    )
    expected, _ = weighted_geomean(
        [
            (results["egfr"].normalised_q,           0.50),
            (results["kfre"].normalised_q,           0.30),
            (results["kdigo_category"].normalised_q, 0.20),
        ],
        epsilon=0.01,
    )
    assert spec_a is not None
    assert spec_a == pytest.approx(expected, abs=1e-6)


def test_kidney_composite_weights_sum_to_one(kidney_configs):
    total = sum(c.composite_weight for c in kidney_configs.values())
    assert total == pytest.approx(1.0, abs=1e-6)
