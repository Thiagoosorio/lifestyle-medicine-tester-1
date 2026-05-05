"""Phase 5 organ-panel regressions: metabolic + brain composites.

Composite-member groupings:

    metabolic:  homa_ir 0.20, mets_ir 0.20, tyg 0.15, findrisc 0.20,
                vai 0.15, lap 0.10           sum 1.00

    brain:      moca/mmse-cognitive-slot 0.30, caide 0.25, phq9 0.20,
                gad7 0.15, homocysteine 0.10  sum 1.00

The brain panel pulls one of {moca, mmse} from the cognitive instrument
slot. The inactive instrument returns UNAVAILABLE and the aggregator
drops it (per Phase 4 instrument-fallback machinery), so only the
active instrument's 0.30 weight ends up in the renormalised pool.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from healthscore.aggregate.common import weighted_geomean
from healthscore.aggregate.spec_a import aggregate_organ_spec_a
from healthscore.engine import evaluate_all_scores
from healthscore.enums import ScoreStatus
from healthscore.instruments import load_instrument_registry
from healthscore.score_config import load_score_configs


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"
_WORDING_YAML = _REPO_ROOT / "configs" / "wording.yaml"
_INSTRUMENTS_YAML = _REPO_ROOT / "configs" / "instruments.yaml"


_METABOLIC_MEMBERS = ("homa_ir", "mets_ir", "tyg", "findrisc", "vai", "lap")
_BRAIN_MEMBERS = ("moca", "caide", "phq9", "gad7", "homocysteine")


@pytest.fixture(scope="module")
def configs():
    return load_score_configs(_SCORE_CONFIGS)


@pytest.fixture(scope="module")
def wording_templates():
    return yaml.safe_load(_WORDING_YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def instrument_registry():
    return load_instrument_registry(_INSTRUMENTS_YAML)


def _metabolic_inputs() -> dict[str, object]:
    """A 50yo male with mid-band metabolic profile."""
    return {
        "age": 50, "sex": "male", "bmi": 28, "waist_cm": 96,
        "fasting_insulin_uIUmL": 12, "fasting_glucose_mgdl": 105,
        "tg_mgdl": 160, "hdl_c_mgdl": 42,
        "daily_activity_30min": True, "daily_fruit_veg": True,
        "on_bp_medication": False, "history_high_glucose": False,
        "family_history_diabetes": "second_degree",
    }


def _brain_inputs(locale: str = "en") -> dict[str, object]:
    """A 60yo male with mild depression + intermediate cognitive profile."""
    base: dict[str, object] = {
        "age": 60, "sex": "male", "bmi": 26, "education_years": 14,
        "sbp_mmhg": 128, "total_chol_mgdl": 200,
        "physically_active": True,
        "moca_score": 26, "mmse_score": 27,
        "homocysteine_umol_L": 11.0,
        "locale": locale,
    }
    # PHQ-9 sums to 7 (mild range, English low band).
    for i in range(1, 10):
        base[f"phq9_q{i}"] = 1 if i <= 7 else 0
    # GAD-7 sums to 5 (subthreshold).
    for i in range(1, 8):
        base[f"gad7_q{i}"] = 1 if i <= 5 else 0
    return base


# ──────────────────────────────────────────────────────────────────────────
# Metabolic organ panel
# ──────────────────────────────────────────────────────────────────────────


def test_system_wide_composite_weights_after_option_b_reweighting(configs):
    """Phase 5 Option B (methodology §3.7): Frailty 0.30 + Hb+RDW 0.20 +
    OSA-slot 0.20 + PhenoAge 0.15 + SII 0.15 = 1.00. PhenoAge demoted from
    0.35 per persistent-low-confidence + cross-panel input redundancy."""
    assert configs["frail_scale"].composite_weight == 0.30
    assert configs["hb_rdw"].composite_weight == 0.20
    assert configs["stop_bang"].composite_weight == 0.20
    assert configs["phenoage"].composite_weight == 0.15
    assert configs["sii"].composite_weight == 0.15
    total = (
        configs["frail_scale"].composite_weight
        + configs["hb_rdw"].composite_weight
        + configs["stop_bang"].composite_weight
        + configs["phenoage"].composite_weight
        + configs["sii"].composite_weight
    )
    assert total == pytest.approx(1.0, abs=1e-6)
    # OSA fallback (NoSAS) carries the same 0.20 weight so a fallback
    # activation does not silently change the panel total.
    assert configs["nosas"].composite_weight == 0.20


def test_metabolic_composite_weights_sum_to_one(configs):
    members = [configs[sid] for sid in _METABOLIC_MEMBERS]
    total = sum(c.composite_weight or 0.0 for c in members)
    assert total == pytest.approx(1.0, abs=1e-6)


def test_metabolic_panel_runs_for_typical_user(
    configs, wording_templates, instrument_registry,
):
    raw_inputs = _metabolic_inputs()
    results = evaluate_all_scores(
        configs=configs, raw_inputs=raw_inputs,
        instrument_registry=instrument_registry, templates=wording_templates,
    )
    for sid in _METABOLIC_MEMBERS:
        assert results[sid].status is ScoreStatus.OK, (
            f"{sid}: {results[sid].status} ({results[sid].reason})"
        )

    weights = {sid: configs[sid].composite_weight for sid in _METABOLIC_MEMBERS}
    spec_a, _ = aggregate_organ_spec_a(
        score_results=[results[s] for s in _METABOLIC_MEMBERS],
        weights=weights, epsilon=0.01,
    )
    assert spec_a is not None
    assert 0.0 <= spec_a <= 100.0


# ──────────────────────────────────────────────────────────────────────────
# Brain organ panel: cognitive slot routing + Arabic-cutoff override
# ──────────────────────────────────────────────────────────────────────────


def test_brain_composite_weights_sum_to_one_with_active_cognitive(configs):
    """When MoCA is active (shipped instruments.yaml), brain weights:
    moca 0.30 + caide 0.25 + phq9 0.20 + gad7 0.15 + homocysteine 0.10 = 1.0."""
    members = [configs[sid] for sid in _BRAIN_MEMBERS]
    total = sum(c.composite_weight or 0.0 for c in members)
    assert total == pytest.approx(1.0, abs=1e-6)


def test_brain_panel_runs_for_typical_user_english_locale(
    configs, wording_templates, instrument_registry,
):
    raw_inputs = _brain_inputs(locale="en")
    results = evaluate_all_scores(
        configs=configs, raw_inputs=raw_inputs,
        instrument_registry=instrument_registry, templates=wording_templates,
    )
    for sid in _BRAIN_MEMBERS:
        assert results[sid].status is ScoreStatus.OK, (
            f"{sid}: {results[sid].status} ({results[sid].reason})"
        )
    # Inactive cognitive instrument is UNAVAILABLE.
    assert results["mmse"].status is ScoreStatus.UNAVAILABLE

    # Active MoCA carries no language override (locale=en).
    assert results["moca"].language_cutoff_active in (None, "en")
    # PHQ-9 at locale=en uses English anchors (no confidence override).
    assert results["phq9"].language_cutoff_active == "en"
    assert results["phq9"].confidence == configs["phq9"].confidence

    weights = {sid: configs[sid].composite_weight for sid in _BRAIN_MEMBERS}
    spec_a, _ = aggregate_organ_spec_a(
        score_results=[results[s] for s in _BRAIN_MEMBERS],
        weights=weights, epsilon=0.01,
    )
    assert spec_a is not None


def test_brain_panel_arabic_locale_demotes_phq9_and_gad7_confidence(
    configs, wording_templates, instrument_registry,
):
    """User with locale=ar: PHQ-9 and GAD-7 anchors switch to the Arabic
    overrides (Hammoudeh 2020 single-source cutoffs); confidence is
    demoted to 'single_source' on those scores. CAIDE / homocysteine /
    cognitive carry no Arabic confidence demotion."""
    raw_inputs = _brain_inputs(locale="ar")
    results = evaluate_all_scores(
        configs=configs, raw_inputs=raw_inputs,
        instrument_registry=instrument_registry, templates=wording_templates,
    )

    assert results["phq9"].language_cutoff_active == "ar"
    assert results["phq9"].confidence == "single_source"
    assert results["gad7"].language_cutoff_active == "ar"
    assert results["gad7"].confidence == "single_source"
    # MoCA Arabic override carries no confidence demotion (multi-site
    # convergence, not single-source).
    assert results["moca"].language_cutoff_active == "ar"
    assert results["moca"].confidence == configs["moca"].confidence


def test_brain_composite_renormalises_weight_when_cognitive_inactive(
    configs, wording_templates, instrument_registry,
):
    """The aggregator drops UNAVAILABLE scores per §1.5. With MMSE
    UNAVAILABLE in the shipped config, the brain composite renormalises
    over the remaining 5 members. This pins weight redistribution."""
    raw_inputs = _brain_inputs(locale="en")
    results = evaluate_all_scores(
        configs=configs, raw_inputs=raw_inputs,
        instrument_registry=instrument_registry, templates=wording_templates,
    )
    weights = {sid: configs[sid].composite_weight for sid in _BRAIN_MEMBERS}
    # mmse is UNAVAILABLE; aggregator drops it.
    spec_a, _ = aggregate_organ_spec_a(
        score_results=[results[s] for s in _BRAIN_MEMBERS] + [results["mmse"]],
        weights={**weights, "mmse": 0.30},
        epsilon=0.01,
    )
    expected, _ = weighted_geomean(
        [(results[s].normalised_q, weights[s]) for s in _BRAIN_MEMBERS],
        epsilon=0.01,
    )
    assert spec_a == pytest.approx(expected, abs=1e-6)
