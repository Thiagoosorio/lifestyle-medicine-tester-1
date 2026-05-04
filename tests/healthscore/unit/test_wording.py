"""Unit tests for wording.py: render() rules and forbidden-lemma scanner.

Per architecture_spec.md §8 (Output language constraints).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from healthscore.enums import RiskBand, ScoreStatus
from healthscore.types import ScoreResult
from healthscore.wording import (
    ALLOW_LIST,
    FORBIDDEN_LEMMAS,
    render_wording,
    scan_text_for_forbidden_lemmas,
)


# ──────────────────────────────────────────────────────────────────────────
# render_wording
# ──────────────────────────────────────────────────────────────────────────


def _result(status: ScoreStatus, band: RiskBand | None = None) -> ScoreResult:
    return ScoreResult(
        score_id="fib4",
        status=status,
        raw_value=Decimal("2.0") if status is ScoreStatus.OK else None,
        normalised_q=0.49 if status is ScoreStatus.OK else None,
        epsilon_applied=False,
        risk_band=band,
        anchors_used=None,
        anchor_sources=None,
        interpolation_mode=None,
        confidence="high" if status is ScoreStatus.OK else None,
        pmid=None,
        active_instrument=None,
        gate_failures=(),
        gate_evaluation_trace=(),
        reason=None,
        wording=None,
    )


@pytest.mark.parametrize(
    "status",
    [
        ScoreStatus.GATED,
        ScoreStatus.MISSING_INPUT,
        ScoreStatus.OUT_OF_RANGE,
        ScoreStatus.NORMALISATION_BREAKDOWN,
        ScoreStatus.UNAVAILABLE,
    ],
)
def test_non_ok_results_carry_no_wording(status):
    """Methodology §8 + §6: gated / missing / out-of-range scores carry
    NO user-facing wording. The renderer must enforce this regardless of
    what (if any) templates exist."""
    res = _result(status, band=None)
    assert render_wording(res, templates={"fib4": {"low": "x"}}) is None


def test_ok_result_with_no_templates_returns_none():
    res = _result(ScoreStatus.OK, band=RiskBand.INDETERMINATE)
    assert render_wording(res, templates=None) is None


def test_ok_result_with_no_score_template_returns_none():
    res = _result(ScoreStatus.OK, band=RiskBand.INDETERMINATE)
    assert render_wording(res, templates={"other_score": {"indeterminate": "x"}}) is None


def test_ok_result_with_no_band_returns_none():
    """Defensive: if for some reason the score is OK but risk_band is None,
    the renderer must not synthesise a default band."""
    res = _result(ScoreStatus.OK, band=None)
    assert render_wording(
        res, templates={"fib4": {"low": "x", "indeterminate": "y", "high": "z"}}
    ) is None


def test_ok_result_renders_matching_band_template():
    res = _result(ScoreStatus.OK, band=RiskBand.INDETERMINATE)
    templates = {"fib4": {
        "low": "Low likelihood band.",
        "indeterminate": "Intermediate band -- consider follow-up.",
        "high": "High band -- discuss with clinician.",
    }}
    assert render_wording(res, templates=templates) == (
        "Intermediate band -- consider follow-up."
    )


# ──────────────────────────────────────────────────────────────────────────
# scan_text_for_forbidden_lemmas
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "lemma",
    [
        "diagnose", "diagnosis", "diagnostic",
        "prognosis", "prognostic",
        "prescribe", "prescription",
        "cure", "curative",
    ],
)
def test_strict_forbidden_lemma_is_caught(lemma):
    text = f"This output should never {lemma} the user's condition."
    found = scan_text_for_forbidden_lemmas(text)
    assert lemma in found


@pytest.mark.parametrize(
    "lemma",
    ["predict", "predicts", "prediction", "recommend", "recommended", "treatment", "therapy"],
)
def test_context_aware_lemma_is_caught_in_word_boundary_match(lemma):
    text = f"The score will {lemma} disease."
    found = scan_text_for_forbidden_lemmas(text)
    assert lemma in found


def test_substrings_inside_innocuous_words_do_not_trigger():
    """'diagnostic' is forbidden but 'diagnosing' is a different lemma; we
    only enforce exact lemmas via word-boundary matching. Likewise 'cured'
    contains 'cure' but is bounded differently. Spot-check a few."""
    # 'cure' inside 'pedicure' must NOT trigger -- word boundary fails.
    assert "cure" not in scan_text_for_forbidden_lemmas("she had a pedicure today")
    # but plain 'cure' DOES trigger.
    assert "cure" in scan_text_for_forbidden_lemmas("the score will cure you")


@pytest.mark.parametrize(
    "phrase",
    [
        "lifestyle recommendations",
        "screening recommendations",
        "AHA PREVENT",
        "screening for liver fibrosis",
        "diagnostic accuracy",
    ],
)
def test_allow_listed_phrases_are_not_flagged(phrase):
    """A forbidden substring inside an allow-listed phrase must NOT trigger."""
    text = f"Score documentation discusses {phrase} for context."
    assert scan_text_for_forbidden_lemmas(text) == []


def test_allow_list_does_not_swallow_forbidden_lemma_outside_phrase():
    """If a forbidden lemma appears OUTSIDE an allow-listed phrase, it
    must still be caught even if the same string also includes the phrase."""
    text = "The diagnostic accuracy is high. The score will diagnose disease."
    # 'diagnostic' inside 'diagnostic accuracy' should be allow-listed.
    # 'diagnose' is a separate occurrence -- must trigger.
    found = scan_text_for_forbidden_lemmas(text)
    assert "diagnose" in found
    assert "diagnostic" not in found


def test_forbidden_lemmas_constant_includes_strict_set():
    """Sanity: the public FORBIDDEN_LEMMAS tuple must include the
    architecture_spec §8 strict-forbidden set so the linter at CI-time
    enforces the regulatory commitment, not just whatever happened to
    land in the implementation."""
    expected_strict = {
        "diagnose", "diagnosis", "diagnostic",
        "prognosis", "prognostic", "prognose",
        "prescribe", "prescription", "cure", "curative",
    }
    assert expected_strict <= set(FORBIDDEN_LEMMAS)


def test_allow_list_includes_aha_prevent_proper_noun():
    """AHA PREVENT must be allow-listed (proper noun, not a recommendation)."""
    assert any("aha prevent" in p.lower() for p in ALLOW_LIST)
