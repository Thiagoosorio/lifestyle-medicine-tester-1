"""Frozen regression: methodology §1.7 worked liver example.

This is the canary test that must fail loudly on any silent change to:
    * the FIB-4 anchors (1.30 / 1.985-constructed / 2.67) or two-anchor PWL
    * the geometric mean implementation in aggregate.common
    * the epsilon floor activation logic
    * the weight defaults (FIB-4 0.40, ALBI 0.20, aMAP 0.20, FLI 0.20)

Inputs (per methodology §1.7):
    FIB-4 = 2.0  -> two-anchor PWL because indeterminate is constructed_midpoint
                  -> q = 1 - (2.0 - 1.30) / (2.67 - 1.30) ~= 0.4891
    ALBI  = -2.5 -> q = 0.40 (stated by §1.7; per-score normalisation lives in Phase 3+)
    aMAP  = 55   -> q = 0.50 (stated by §1.7)
    FLI   = 70   -> q = 0.20 (stated by §1.7)

Cluster weights (methodology §1.7 reduced-panel composite):
    FIB-4 0.40, ALBI 0.20, aMAP 0.20, FLI 0.20

Expected organ score (Spec A and Spec B identical at organ level per
methodology §1.3): ~39.5 with absolute tolerance 0.5.

Phase 0 deliberately constructs ScoreResult objects directly with the
stated q values rather than driving the full engine.compute() path --
the engine, score modules, and per-score normalisation land in Phase 3+.
The full integration test using engine.compute() arrives in Phase 4
(architecture_spec.md Appendix A).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from healthscore.aggregate.spec_a import aggregate_organ_spec_a
from healthscore.aggregate.spec_b import aggregate_organ_spec_b
from healthscore.enums import (
    AnchorSource,
    InterpolationMode,
    RiskBand,
    ScoreStatus,
)
from healthscore.normalize import normalise_distance_to_cutoff
from healthscore.types import ScoreResult


# ── Helpers ────────────────────────────────────────────────────────────────


def _ok_score(score_id: str, q: float, raw: str) -> ScoreResult:
    """Build a ScoreResult with status OK and the given normalised q.

    Phase 0 doesn't yet ship the per-score normalisation pipeline, so the
    regression test populates q directly. ``anchors_used`` is not required
    for aggregation; the aggregate functions only read ``status``,
    ``score_id``, and ``normalised_q``.
    """
    return ScoreResult(
        score_id=score_id,
        status=ScoreStatus.OK,
        raw_value=Decimal(raw),
        normalised_q=q,
        epsilon_applied=False,
        risk_band=RiskBand.INDETERMINATE,
        anchors_used=None,
        anchor_sources=None,
        interpolation_mode=None,
        confidence="high",
        pmid=None,
        active_instrument=None,
        gate_failures=(),
        gate_evaluation_trace=(),
        reason=None,
        wording=None,
    )


# Methodology §1.7 reduced-panel weights (also frozen here -- a silent
# change to the methodology weights must also break this test).
_LIVER_WEIGHTS = {
    "fib4": 0.40,
    "albi": 0.20,
    "amap": 0.20,
    "fli": 0.20,
}

_EPSILON = 0.01


# ── The acceptance gate ────────────────────────────────────────────────────


def test_methodology_1_7_organ_score_spec_a():
    """Spec A organ score for §1.7 worked example must be 39.5 ± 0.5."""
    fib4_outcome = normalise_distance_to_cutoff(
        Decimal("2.0"),
        low_value=Decimal("1.30"),
        indeterminate_value=Decimal("1.985"),
        high_value=Decimal("2.67"),
        low_source=AnchorSource.PUBLISHED,
        indeterminate_source=AnchorSource.CONSTRUCTED_MIDPOINT,
        high_source=AnchorSource.PUBLISHED,
    )
    # Anchor-source guard: if this ever flips to three-anchor PWL, the
    # methodology document needs updating, not the test.
    assert fib4_outcome.interpolation_mode is InterpolationMode.TWO_ANCHOR_PWL
    assert fib4_outcome.q == pytest.approx(0.48905, abs=1e-4)

    score_results = (
        _ok_score("fib4", fib4_outcome.q, "2.0"),
        _ok_score("albi", 0.40, "-2.5"),
        _ok_score("amap", 0.50, "55"),
        _ok_score("fli",  0.20, "70"),
    )

    organ_score, eps_codes = aggregate_organ_spec_a(
        score_results=score_results,
        weights=_LIVER_WEIGHTS,
        epsilon=_EPSILON,
    )

    assert organ_score is not None
    assert eps_codes == ()                       # no q hits the epsilon floor
    assert organ_score == pytest.approx(39.5, abs=0.5), (
        f"Spec A organ score drifted from §1.7 worked example: got {organ_score!r}, "
        f"expected 39.5 ± 0.5"
    )


def test_methodology_1_7_organ_score_spec_b():
    """Spec B organ score for §1.7 worked example must be 39.5 ± 0.5,
    and must equal Spec A at organ level (methodology §1.3: same weighted
    geometric mean within organ)."""
    fib4_outcome = normalise_distance_to_cutoff(
        Decimal("2.0"),
        low_value=Decimal("1.30"),
        indeterminate_value=Decimal("1.985"),
        high_value=Decimal("2.67"),
        low_source=AnchorSource.PUBLISHED,
        indeterminate_source=AnchorSource.CONSTRUCTED_MIDPOINT,
        high_source=AnchorSource.PUBLISHED,
    )

    score_results = (
        _ok_score("fib4", fib4_outcome.q, "2.0"),
        _ok_score("albi", 0.40, "-2.5"),
        _ok_score("amap", 0.50, "55"),
        _ok_score("fli",  0.20, "70"),
    )

    organ_a, _ = aggregate_organ_spec_a(
        score_results=score_results, weights=_LIVER_WEIGHTS, epsilon=_EPSILON
    )
    organ_b, _ = aggregate_organ_spec_b(
        score_results=score_results, weights=_LIVER_WEIGHTS, epsilon=_EPSILON
    )

    assert organ_a is not None
    assert organ_b is not None
    assert organ_b == pytest.approx(39.5, abs=0.5), (
        f"Spec B organ score drifted from §1.7 worked example: got {organ_b!r}, "
        f"expected 39.5 ± 0.5"
    )
    # Methodology §1.3: Spec A and Spec B are *identical* at organ level.
    # If this ever drifts, either the methodology has changed or one of the
    # two organ functions has diverged silently.
    assert abs(organ_a - organ_b) < 0.01, (
        f"Spec A ({organ_a!r}) and Spec B ({organ_b!r}) diverged at organ "
        f"level; methodology §1.3 says they must be equal"
    )


def test_methodology_1_7_geometric_below_arithmetic():
    """Methodology §1.4 imbalance-penalisation property: weighted geometric
    mean (~39.5) sits below weighted arithmetic mean for this panel because
    the q values are imbalanced (FLI 0.20, FIB-4 0.49, ALBI 0.40, aMAP 0.50).
    Pin the inequality so anyone who silently swaps to arithmetic mean
    breaks this test.

    METHODOLOGY ERRATUM: §1.7 quotes the arithmetic mean as 45.2, but the
    arithmetic the methodology itself shows
    (0.40·0.49 + 0.20·0.40 + 0.20·0.50 + 0.20·0.20) sums to 0.416, not
    0.452 -- so the correct arithmetic mean is 41.6, not 45.2. Test pins
    the computed value; the quoted §1.7 number needs correcting in the
    methodology document.
    """
    fib4_outcome = normalise_distance_to_cutoff(
        Decimal("2.0"),
        low_value=Decimal("1.30"),
        indeterminate_value=Decimal("1.985"),
        high_value=Decimal("2.67"),
        low_source=AnchorSource.PUBLISHED,
        indeterminate_source=AnchorSource.CONSTRUCTED_MIDPOINT,
        high_source=AnchorSource.PUBLISHED,
    )
    qs = {
        "fib4": fib4_outcome.q,
        "albi": 0.40,
        "amap": 0.50,
        "fli":  0.20,
    }
    arithmetic = sum(qs[k] * _LIVER_WEIGHTS[k] for k in qs) * 100.0

    organ_a, _ = aggregate_organ_spec_a(
        score_results=tuple(_ok_score(k, qs[k], "0") for k in qs),
        weights=_LIVER_WEIGHTS,
        epsilon=_EPSILON,
    )

    assert organ_a is not None
    assert organ_a < arithmetic, (
        f"Geometric mean ({organ_a:.2f}) must sit below arithmetic mean "
        f"({arithmetic:.2f}) -- methodology §1.4 imbalance penalisation."
    )
    # Computed arithmetic from the §1.7 inputs (NOT the §1.7-quoted 45.2,
    # which is an arithmetic error in the methodology document).
    assert arithmetic == pytest.approx(41.6, abs=0.1)
