"""Unit tests for aggregate.common (epsilon floor + weighted geometric mean)."""

from __future__ import annotations

import math

import pytest

from healthscore.aggregate.common import normalise_for_geomean, weighted_geomean


# ── normalise_for_geomean (the only place epsilon is applied) ──────────────


def test_q_above_epsilon_passes_through_unchanged():
    q, applied = normalise_for_geomean(0.4, epsilon=0.01)
    assert q == 0.4
    assert applied is False


def test_q_below_epsilon_is_floored_and_flagged():
    q, applied = normalise_for_geomean(0.001, epsilon=0.01)
    assert q == 0.01
    assert applied is True


def test_q_at_epsilon_is_not_floored():
    """Exact equality is not below threshold; no activation."""
    q, applied = normalise_for_geomean(0.01, epsilon=0.01)
    assert q == 0.01
    assert applied is False


def test_q_zero_is_floored():
    q, applied = normalise_for_geomean(0.0, epsilon=0.01)
    assert q == 0.01
    assert applied is True


@pytest.mark.parametrize("bad_q", [-0.01, 1.01, 2.0])
def test_q_outside_unit_interval_raises(bad_q):
    with pytest.raises(ValueError):
        normalise_for_geomean(bad_q, epsilon=0.01)


@pytest.mark.parametrize("bad_eps", [-0.01, 0.0, 1.0, 1.5])
def test_epsilon_outside_open_unit_interval_raises(bad_eps):
    with pytest.raises(ValueError):
        normalise_for_geomean(0.5, epsilon=bad_eps)


# ── weighted_geomean ───────────────────────────────────────────────────────


def test_equal_weights_recover_unweighted_geomean():
    """Two q values, equal weights -> 100 * sqrt(q1 * q2)."""
    score, flags = weighted_geomean([(0.4, 1.0), (0.9, 1.0)], epsilon=0.01)
    assert score == pytest.approx(100.0 * math.sqrt(0.4 * 0.9))
    assert flags == [False, False]


def test_weights_are_renormalised_internally():
    """Weights summing to 0.5 give the same answer as weights summing to 1.0."""
    a = weighted_geomean([(0.4, 0.2), (0.9, 0.3)], epsilon=0.01)[0]
    b = weighted_geomean([(0.4, 0.4), (0.9, 0.6)], epsilon=0.01)[0]
    assert a == pytest.approx(b)


def test_zero_weight_inputs_are_skipped_via_renormalisation():
    """A zero-weight input contributes 0 to log_sum (because 0 * anything = 0).

    The remaining inputs' renormalised weights sum to 1; the result equals
    what we'd compute if the zero-weight input weren't present.
    """
    with_zero = weighted_geomean([(0.4, 0.5), (0.9, 0.5), (0.001, 0.0)], epsilon=0.01)[0]
    without = weighted_geomean([(0.4, 0.5), (0.9, 0.5)], epsilon=0.01)[0]
    assert with_zero == pytest.approx(without)


def test_below_epsilon_input_is_floored_and_flagged():
    score, flags = weighted_geomean([(0.4, 1.0), (0.001, 1.0)], epsilon=0.01)
    expected = 100.0 * math.sqrt(0.4 * 0.01)
    assert score == pytest.approx(expected)
    assert flags == [False, True]


def test_geometric_mean_le_arithmetic_mean_property():
    """Geometric mean is <= arithmetic mean (AM-GM inequality), strictly so
    when the values differ. This is the methodology §1.4 reason for using
    geometric: imbalance penalisation."""
    pairs = [(0.2, 0.25), (0.5, 0.25), (0.8, 0.25), (0.9, 0.25)]
    geo_score = weighted_geomean(pairs, epsilon=0.01)[0] / 100.0
    arith = sum(q * w for q, w in pairs)
    assert geo_score < arith


def test_empty_input_raises():
    with pytest.raises(ValueError):
        weighted_geomean([], epsilon=0.01)


def test_all_zero_weights_raises():
    with pytest.raises(ValueError):
        weighted_geomean([(0.4, 0.0), (0.5, 0.0)], epsilon=0.01)


def test_negative_weight_raises():
    with pytest.raises(ValueError):
        weighted_geomean([(0.4, 1.0), (0.5, -0.1)], epsilon=0.01)


def test_score_always_in_zero_to_one_hundred():
    """Property: with q in [0, 1] and epsilon > 0, output is in [0, 100]."""
    pairs_panels = [
        [(0.0, 1.0)],
        [(1.0, 1.0)],
        [(0.5, 1.0)],
        [(0.001, 0.4), (0.999, 0.6)],
    ]
    for pairs in pairs_panels:
        score, _ = weighted_geomean(pairs, epsilon=0.01)
        assert 0.0 <= score <= 100.0
