"""Tests for outcome_proximity coverage + pluggable weighting strategies."""

import pytest

from config.organ_scores_data import ORGAN_SCORE_DEFINITIONS
from config.score_classification import (
    OUTCOME_PROXIMITY_BY_CODE,
    OUTCOME_PROXIMITY_CODES,
    get_classification,
)
from services.score_calibration.weighting_strategies import (
    DEFAULT_STRATEGY,
    STRATEGIES,
    get_strategy,
    list_strategies,
)


# ── Outcome proximity coverage ──────────────────────────────────────────────


def test_every_score_has_an_outcome_proximity_tag():
    all_codes = {d["code"] for d in ORGAN_SCORE_DEFINITIONS}
    tagged = set(OUTCOME_PROXIMITY_BY_CODE.keys())
    assert all_codes == tagged, (
        f"missing={sorted(all_codes - tagged)}, extra={sorted(tagged - all_codes)}"
    )


@pytest.mark.parametrize("code, proximity", sorted(OUTCOME_PROXIMITY_BY_CODE.items()))
def test_proximity_values_are_valid(code, proximity):
    assert proximity in OUTCOME_PROXIMITY_CODES, f"{code} has invalid proximity {proximity}"


def test_get_classification_returns_proximity_field():
    info = get_classification("prevent_10yr")
    assert info["outcome_proximity"] == "risk_calculator"


# ── Strategy behaviour ──────────────────────────────────────────────────────


def test_all_four_strategies_are_registered():
    assert set(STRATEGIES.keys()) == {
        "equal", "evidence_tier", "outcome_proximity", "hybrid_recommended",
    }
    assert DEFAULT_STRATEGY == "hybrid_recommended"


def test_list_strategies_returns_strategies_in_display_order():
    codes = [s.code for s in list_strategies()]
    assert codes == ["equal", "evidence_tier", "outcome_proximity", "hybrid_recommended"]


def test_equal_strategy_returns_one_for_every_score():
    strategy = get_strategy("equal")
    for code in OUTCOME_PROXIMITY_BY_CODE:
        weight = strategy.compute_weight({"code": code, "tier": "validated", "severity": "optimal"})
        assert weight == 1.0


def test_evidence_tier_strategy_downweights_derived():
    strategy = get_strategy("evidence_tier")
    validated = strategy.compute_weight({"code": "fib4", "tier": "validated", "severity": "elevated"})
    derived = strategy.compute_weight({"code": "tyg_bmi", "tier": "derived", "severity": "elevated"})
    assert validated > derived
    assert validated == pytest.approx(1.0)
    assert derived == pytest.approx(0.6)


def test_outcome_proximity_strategy_prefers_risk_calculators():
    strategy = get_strategy("outcome_proximity")
    risk_calc = strategy.compute_weight({"code": "prevent_10yr", "tier": "validated", "severity": "elevated"})
    mechanistic = strategy.compute_weight({"code": "apob_risk", "tier": "validated", "severity": "elevated"})
    derivative = strategy.compute_weight({"code": "aip", "tier": "validated", "severity": "elevated"})
    exploratory = strategy.compute_weight({"code": "plr", "tier": "derived", "severity": "elevated"})
    assert risk_calc > mechanistic > derivative > exploratory


def test_hybrid_strategy_responds_to_all_three_axes():
    """Hybrid weight should change when tier, proximity, OR severity changes."""
    strategy = get_strategy("hybrid_recommended")
    base = strategy.compute_weight({"code": "apob_risk", "tier": "validated", "severity": "optimal"})
    harder_severity = strategy.compute_weight({"code": "apob_risk", "tier": "validated", "severity": "critical"})
    lower_tier = strategy.compute_weight({"code": "apob_risk", "tier": "derived", "severity": "optimal"})
    higher_proximity = strategy.compute_weight({"code": "prevent_10yr", "tier": "validated", "severity": "optimal"})

    assert harder_severity > base        # severity drives weight up
    assert lower_tier < base             # derived tier drives weight down
    assert higher_proximity > base       # risk-calculator proximity drives weight up


def test_research_and_exploratory_combination_yields_lowest_weight():
    strategy = get_strategy("hybrid_recommended")
    # A derived-tier + exploratory score should end up near the bottom.
    exploratory_derived = strategy.compute_weight(
        {"code": "plr", "tier": "derived", "severity": "optimal"}
    )
    validated_risk_calc = strategy.compute_weight(
        {"code": "prevent_10yr", "tier": "validated", "severity": "optimal"}
    )
    assert exploratory_derived < validated_risk_calc / 4


# ── End-to-end: compare_weighting_strategies against a real user ────────────


def test_compare_weighting_strategies_returns_all_four_for_a_seeded_user(monkeypatch):
    """Headless replay of compare_weighting_strategies against a mocked cohort."""
    from services import organ_score_service as oss

    sample_scores = [
        {"code": "prevent_10yr", "organ_system": "cardiovascular",
         "tier": "validated", "severity": "elevated"},
        {"code": "apob_risk", "organ_system": "cardiovascular",
         "tier": "validated", "severity": "elevated"},
        {"code": "aip", "organ_system": "cardiovascular",
         "tier": "validated", "severity": "normal"},
        {"code": "fib4", "organ_system": "liver",
         "tier": "validated", "severity": "optimal"},
        {"code": "plr", "organ_system": "inflammatory",
         "tier": "derived", "severity": "elevated"},
    ]
    monkeypatch.setattr(oss, "get_latest_scores", lambda _uid: sample_scores)

    comparison = oss.compare_weighting_strategies(user_id=1)
    assert comparison is not None
    assert set(comparison.keys()) == {
        "equal", "evidence_tier", "outcome_proximity", "hybrid_recommended",
    }
    for payload in comparison.values():
        assert 0 <= payload["overall_score_10"] <= 10
        assert payload["organ_breakdown"]

    # The four strategies should not all return exactly the same number --
    # if they did, the sensitivity tab would be pointless.
    distinct_values = {c["overall_score_10"] for c in comparison.values()}
    assert len(distinct_values) >= 2
