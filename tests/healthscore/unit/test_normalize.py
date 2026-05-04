"""Unit tests for healthscore.normalize.

Pins the §1.7 anchor arithmetic: FIB-4 with a constructed-midpoint
indeterminate anchor must use two-anchor PWL, not three-anchor PWL,
producing q ~= 0.489 for raw_value = 2.0.

Three-anchor PWL is exercised against the ASCVD 5/7.5/20% example
which methodology §1.2 cites as the canonical "all three published" case.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from healthscore.enums import AnchorSource, InterpolationMode
from healthscore.normalize import (
    NormalisationOutcome,
    normalise_distance_to_cutoff,
    select_interpolation_mode,
)


# ── Mode selection from anchor sources ──────────────────────────────────────


def test_three_published_anchors_yields_three_anchor_pwl():
    mode = select_interpolation_mode(
        AnchorSource.PUBLISHED, AnchorSource.PUBLISHED, AnchorSource.PUBLISHED
    )
    assert mode is InterpolationMode.THREE_ANCHOR_PWL


def test_constructed_midpoint_yields_two_anchor_pwl():
    mode = select_interpolation_mode(
        AnchorSource.PUBLISHED,
        AnchorSource.CONSTRUCTED_MIDPOINT,
        AnchorSource.PUBLISHED,
    )
    assert mode is InterpolationMode.TWO_ANCHOR_PWL


def test_constructed_low_or_high_anchor_is_rejected():
    """Low or high anchor with constructed_midpoint source is malformed config."""
    with pytest.raises(ValueError):
        select_interpolation_mode(
            AnchorSource.CONSTRUCTED_MIDPOINT,
            AnchorSource.PUBLISHED,
            AnchorSource.PUBLISHED,
        )
    with pytest.raises(ValueError):
        select_interpolation_mode(
            AnchorSource.PUBLISHED,
            AnchorSource.PUBLISHED,
            AnchorSource.CONSTRUCTED_MIDPOINT,
        )


# ── Two-anchor PWL: §1.7 FIB-4 worked example ──────────────────────────────


def _fib4_normalise(raw: str) -> NormalisationOutcome:
    """FIB-4 anchors per AASLD 2023 / EASL-EASD-EASO 2024.

    low=1.30 (q=1.0, published), indeterminate=1.985 (constructed_midpoint),
    high=2.67 (q=0.0, published). Two-anchor PWL applies.
    """
    return normalise_distance_to_cutoff(
        Decimal(raw),
        low_value=Decimal("1.30"),
        indeterminate_value=Decimal("1.985"),
        high_value=Decimal("2.67"),
        low_source=AnchorSource.PUBLISHED,
        indeterminate_source=AnchorSource.CONSTRUCTED_MIDPOINT,
        high_source=AnchorSource.PUBLISHED,
    )


def test_fib4_methodology_1_7_worked_example_two_anchor_pwl():
    """raw=2.0 -> q ~= 1 - 0.7/1.37 = 0.48905 (methodology §1.7)."""
    outcome = _fib4_normalise("2.0")
    assert outcome.interpolation_mode is InterpolationMode.TWO_ANCHOR_PWL
    assert outcome.q == pytest.approx(0.48905, abs=1e-4)
    assert not outcome.clamped_high
    assert not outcome.clamped_low


def test_fib4_at_low_anchor_is_q_equals_one():
    outcome = _fib4_normalise("1.30")
    assert outcome.q == 1.0
    assert outcome.clamped_high


def test_fib4_below_low_anchor_clamps_at_one():
    outcome = _fib4_normalise("0.50")
    assert outcome.q == 1.0
    assert outcome.clamped_high


def test_fib4_at_high_anchor_is_q_equals_zero():
    outcome = _fib4_normalise("2.67")
    assert outcome.q == 0.0
    assert outcome.clamped_low


def test_fib4_above_high_anchor_clamps_at_zero():
    outcome = _fib4_normalise("4.5")
    assert outcome.q == 0.0
    assert outcome.clamped_low


def test_fib4_two_anchor_pwl_does_not_pass_through_constructed_midpoint():
    """At the constructed midpoint (1.985), two-anchor PWL gives q ~= 0.5
    coincidentally because the midpoint is the arithmetic mean of low+high.
    But the *interpolation mode* must remain TWO_ANCHOR_PWL -- the midpoint
    is recorded for audit but not used as a calibration anchor."""
    outcome = _fib4_normalise("1.985")
    assert outcome.interpolation_mode is InterpolationMode.TWO_ANCHOR_PWL
    # 1 - (1.985 - 1.30)/(2.67 - 1.30) = 1 - 0.685/1.37 = 0.5
    assert outcome.q == pytest.approx(0.5, abs=1e-9)


# ── Three-anchor PWL: ASCVD 5/7.5/20% example ──────────────────────────────


def _ascvd_normalise(raw: str) -> NormalisationOutcome:
    """ASCVD 10-yr: low=5%, indeterminate=7.5%, high=20% — all published."""
    return normalise_distance_to_cutoff(
        Decimal(raw),
        low_value=Decimal("5.0"),
        indeterminate_value=Decimal("7.5"),
        high_value=Decimal("20.0"),
        low_source=AnchorSource.PUBLISHED,
        indeterminate_source=AnchorSource.PUBLISHED,
        high_source=AnchorSource.PUBLISHED,
    )


def test_ascvd_three_anchor_lower_segment():
    """6.25% sits at the midpoint of the lower segment 5 -> 7.5 -> q goes 1.0 -> 0.5
    -> at 6.25% q = 0.75."""
    outcome = _ascvd_normalise("6.25")
    assert outcome.interpolation_mode is InterpolationMode.THREE_ANCHOR_PWL
    assert outcome.q == pytest.approx(0.75, abs=1e-6)


def test_ascvd_three_anchor_at_indeterminate_anchor():
    outcome = _ascvd_normalise("7.5")
    assert outcome.q == pytest.approx(0.5, abs=1e-9)


def test_ascvd_three_anchor_upper_segment():
    """13.75% sits at the midpoint of 7.5 -> 20 -> q goes 0.5 -> 0.0
    -> at 13.75% q = 0.25."""
    outcome = _ascvd_normalise("13.75")
    assert outcome.q == pytest.approx(0.25, abs=1e-6)


def test_ascvd_three_anchor_clamps_at_anchors():
    assert _ascvd_normalise("3.0").q == 1.0
    assert _ascvd_normalise("25.0").q == 0.0


# ── Defensive checks ────────────────────────────────────────────────────────


def test_anchors_must_be_strictly_increasing_two_anchor():
    with pytest.raises(ValueError):
        normalise_distance_to_cutoff(
            Decimal("2.0"),
            low_value=Decimal("3.0"),
            indeterminate_value=Decimal("2.5"),
            high_value=Decimal("2.0"),
            low_source=AnchorSource.PUBLISHED,
            indeterminate_source=AnchorSource.CONSTRUCTED_MIDPOINT,
            high_source=AnchorSource.PUBLISHED,
        )


def test_anchors_must_be_strictly_increasing_three_anchor():
    with pytest.raises(ValueError):
        normalise_distance_to_cutoff(
            Decimal("8.0"),
            low_value=Decimal("5.0"),
            indeterminate_value=Decimal("4.0"),
            high_value=Decimal("20.0"),
            low_source=AnchorSource.PUBLISHED,
            indeterminate_source=AnchorSource.PUBLISHED,
            high_source=AnchorSource.PUBLISHED,
        )


def test_q_is_always_in_zero_one_inclusive():
    """Property: any in-range raw value produces q in [0, 1]."""
    for raw in ("1.0", "1.30", "1.65", "1.985", "2.30", "2.67", "3.0"):
        outcome = _fib4_normalise(raw)
        assert 0.0 <= outcome.q <= 1.0
