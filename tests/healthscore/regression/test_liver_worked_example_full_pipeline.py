"""§1.7 worked liver example -- driven through the full Phase 2 pipeline.

config -> formula -> normaliser -> Spec A & Spec B aggregators

The Phase 0 regression test pinned the same target (39.46 ± 0.05) using
hand-constructed ScoreResults bypassing the formulae. Phase 2 reproduces
that target end-to-end through the JSON configs, the per-score formulae
in src/healthscore/scores/liver.py, the normaliser, and both aggregators.

§1.7 ERRATUM #2 (logged in commitments_log.md):

The methodology document §1.7 quotes raw values FIB-4=2.0, ALBI=-2.5,
aMAP=55, FLI=70 producing q=0.49 / 0.40 / 0.50 / 0.20 respectively.
Under the standard published anchors:

    score   §1.7 raw   §1.7 q   q under standard anchors at §1.7 raw
    FIB-4    2.0       0.49     0.489  ✓ (matches)
    ALBI    -2.5       0.40     0.917  ✗ (mismatch -- §1.7 hand-waves)
    aMAP    55         0.50     0.500  ✓ (matches)
    FLI     70         0.20     0.000  ✗ (clamps to high)

To preserve §1.7's q values via standard anchors, the regression test
uses adjusted raw values for ALBI and FLI: ALBI=-1.874 and FLI=54.
This is the third §1.7 erratum (after the 45.2/41.6 arithmetic typo
caught in Phase 0 and the constructed_midpoint clarification). The
methodology document needs a follow-up update; the codebase remains the
source of truth on the math (per the Phase 0 erratum precedent).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from healthscore.aggregate.spec_a import aggregate_organ_spec_a
from healthscore.aggregate.spec_b import aggregate_organ_spec_b
from healthscore.enums import InterpolationMode, ScoreStatus
from healthscore.score_config import load_score_config, parse_gate_spec
from healthscore.score_eval import evaluate_score
from healthscore.scores import lookup_formula


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"
_WORDING_YAML = _REPO_ROOT / "configs" / "wording.yaml"


# Raw inputs chosen so each formula produces a raw_value that, under the
# score's published anchors, gives the §1.7 q value:
#     FIB-4 raw=2.0    -> q = 0.489 (matches §1.7 EXACTLY)
#     ALBI  raw=-1.874 -> q = 0.40  (deviates from §1.7's -2.5; same q)
#     aMAP  raw=55     -> q = 0.50  (matches §1.7 EXACTLY)
#     FLI   raw=54     -> q = 0.20  (deviates from §1.7's 70; same q)
_FIB4_RAW = {
    # FIB-4 = (50 * 43.818) / (200 * sqrt(30)) = 2.0000 exactly
    "age": 50,
    "ast": 43.818,
    "alt": 30.0,
    "platelets": 200,
}

_ALBI_RAW = {
    # bilirubin 1.0 mg/dL (=17.1 umol/L) + albumin 3.162 g/dL (=31.62 g/L)
    # -> 0.66*log10(17.1) - 0.085*31.62 = 0.8138 - 2.6877 = -1.8739
    # -> q = 1 - (-1.8739 + 2.60)/(-1.39 + 2.60) = 1 - 0.7261/1.21 = 0.4000
    "total_bilirubin_mgdl": 1.0,
    "albumin_gdl": 3.162,
}

_AMAP_RAW = {
    # Liu 2020 simplified form, solved for aMAP = 55.0 exactly:
    # inner = 65*0.06 + 1*0.89 + ln(34.2)*0.48 + 38.05*-0.01 = 6.1050
    # intermediate = 6.1050*0.86 + 150*-0.01 = 3.7503
    # aMAP = 3.7503*100/7.5 + 5 = 55.004
    "age": 65,
    "sex": "male",
    "total_bilirubin_mgdl": 2.0,
    "albumin_gdl": 3.805,
    "platelets": 150,
    "chronic_liver_disease_status": True,        # gate first-branch passes
}

_FLI_RAW = {
    # TG=138 + BMI=28 + GGT=30 + WC=92 -> FLI = 54.02 -> q = 0.1993 ~= 0.20
    "tg_mgdl": 138,
    "bmi": 28,
    "ggt_ul": 30,
    "waist_cm": 92,
}


_TOLERANCE = 0.05


@pytest.fixture(scope="module")
def wording_templates() -> dict[str, dict[str, str]]:
    return yaml.safe_load(_WORDING_YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def liver_configs():
    return {
        "fib4": load_score_config(_SCORE_CONFIGS / "fib4.json"),
        "albi": load_score_config(_SCORE_CONFIGS / "albi.json"),
        "amap": load_score_config(_SCORE_CONFIGS / "amap.json"),
        "fli":  load_score_config(_SCORE_CONFIGS / "fli.json"),
    }


# ──────────────────────────────────────────────────────────────────────────
# Per-score sanity checks (each formula's raw_value matches the target)
# ──────────────────────────────────────────────────────────────────────────


def test_fib4_raw_value_at_section_1_7_inputs(liver_configs, wording_templates):
    cfg = liver_configs["fib4"]
    res = evaluate_score(
        cfg,
        raw_inputs=_FIB4_RAW,
        prior_results={},
        formula=lookup_formula(cfg.formula),
        gate=parse_gate_spec(None),
        templates=wording_templates,
    )
    assert res.status is ScoreStatus.OK
    assert float(res.raw_value) == pytest.approx(2.0, abs=0.005)
    assert res.interpolation_mode is InterpolationMode.TWO_ANCHOR_PWL
    assert res.normalised_q == pytest.approx(0.48905, abs=1e-3)


def test_albi_raw_value_at_section_1_7_inputs(liver_configs, wording_templates):
    cfg = liver_configs["albi"]
    res = evaluate_score(
        cfg,
        raw_inputs=_ALBI_RAW,
        prior_results={},
        formula=lookup_formula(cfg.formula),
        gate=parse_gate_spec(None),
        templates=wording_templates,
    )
    assert res.status is ScoreStatus.OK
    assert float(res.raw_value) == pytest.approx(-1.874, abs=0.01)
    assert res.normalised_q == pytest.approx(0.40, abs=1e-2)


def test_amap_raw_value_at_section_1_7_inputs(liver_configs, wording_templates):
    cfg = liver_configs["amap"]
    res = evaluate_score(
        cfg,
        raw_inputs=_AMAP_RAW,
        prior_results={},
        formula=lookup_formula(cfg.formula),
        gate=parse_gate_spec(cfg.gate_requirements),
        templates=wording_templates,
    )
    assert res.status is ScoreStatus.OK
    assert float(res.raw_value) == pytest.approx(55.0, abs=0.05)
    assert res.normalised_q == pytest.approx(0.50, abs=1e-2)


def test_fli_raw_value_at_section_1_7_inputs(liver_configs, wording_templates):
    cfg = liver_configs["fli"]
    res = evaluate_score(
        cfg,
        raw_inputs=_FLI_RAW,
        prior_results={},
        formula=lookup_formula(cfg.formula),
        gate=parse_gate_spec(None),
        templates=wording_templates,
    )
    assert res.status is ScoreStatus.OK
    assert float(res.raw_value) == pytest.approx(54.0, abs=0.5)
    assert res.normalised_q == pytest.approx(0.20, abs=2e-2)


# ──────────────────────────────────────────────────────────────────────────
# THE acceptance gate: organ score 39.46 ± 0.05 via Spec A and Spec B
# ──────────────────────────────────────────────────────────────────────────


def test_section_1_7_organ_score_via_full_phase2_pipeline(
    liver_configs, wording_templates
):
    """End-to-end: configs -> formulae -> normaliser -> spec_a + spec_b
    aggregators must produce the §1.7 organ score 39.46 ± 0.05 with both
    specs identical at the organ level (per methodology §1.3)."""

    score_results = []
    for score_id, raw_inputs in (
        ("fib4", _FIB4_RAW),
        ("albi", _ALBI_RAW),
        ("amap", _AMAP_RAW),
        ("fli",  _FLI_RAW),
    ):
        cfg = liver_configs[score_id]
        res = evaluate_score(
            cfg,
            raw_inputs=raw_inputs,
            prior_results={},
            formula=lookup_formula(cfg.formula),
            gate=parse_gate_spec(cfg.gate_requirements),
            templates=wording_templates,
        )
        assert res.status is ScoreStatus.OK, (
            f"{score_id} failed pipeline: {res.status} reason={res.reason}"
        )
        score_results.append(res)

    weights = {cfg.score_id: cfg.composite_weight for cfg in liver_configs.values()}

    spec_a, eps_a = aggregate_organ_spec_a(
        score_results=score_results, weights=weights, epsilon=0.01,
    )
    spec_b, eps_b = aggregate_organ_spec_b(
        score_results=score_results, weights=weights, epsilon=0.01,
    )

    assert spec_a is not None
    assert spec_b is not None
    assert spec_a == pytest.approx(39.46, abs=_TOLERANCE), (
        f"Spec A organ score drifted from §1.7 worked example: got {spec_a:.4f}, "
        f"expected 39.46 ± {_TOLERANCE}"
    )
    assert spec_b == pytest.approx(39.46, abs=_TOLERANCE), (
        f"Spec B organ score drifted from §1.7: got {spec_b:.4f}, "
        f"expected 39.46 ± {_TOLERANCE}"
    )
    assert abs(spec_a - spec_b) < 0.01, (
        f"Methodology §1.3: Spec A and Spec B identical at organ level. "
        f"got Spec A={spec_a:.4f}, Spec B={spec_b:.4f}"
    )
    # No epsilon activations expected for these q values (all > 0.01).
    assert eps_a == ()
    assert eps_b == ()
