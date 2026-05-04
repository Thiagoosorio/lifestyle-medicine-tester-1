"""Frozen regression: the Phase 1 CHA2DS2-VASc canonical fixture.

architecture_spec.md Appendix A, Phase 1, end-to-end verification:

    Verify end-to-end: a 43-year-old female with
    atrial_fibrillation_status: null returns

        ScoreResult(
            status=GATED,
            wording=None,
            gate_failures=("af_not_documented",),
            gate_evaluation_trace=("leaf:af_not_documented:fail",),
        )

This test pins the entire shape of that GATED ScoreResult so any future
change that loosens the gate -- e.g. defaulting AF status to False,
producing a wording for a gated score, computing a value for a gated
score -- breaks loudly.

Phase 1 has no engine.compute() yet; the fixture exercises
``evaluate_gate_to_result`` directly. Phase 4 will rerun the same
assertions through the full engine.compute() path.
"""

from __future__ import annotations

from healthscore.enums import ScoreStatus
from healthscore.gates import GateLeaf, evaluate_gate_to_result


# Phase 1 canonical CHA2DS2-VASc gate (per architecture_spec.md §6,
# commitments_log Tier 1). Only AF-documented users pass; everyone else
# is gated.
_CHA2DS2VASC_GATE = GateLeaf(
    field="raw_inputs.atrial_fibrillation_status",
    predicate="equals",
    expected=True,
    missing_policy="fail",
    failure_reason_code="af_not_documented",
)


def test_43yo_female_with_null_af_status_returns_canonical_gated_result():
    """The audited example from commitments_log Tier 1 Source-data panel audit.

    A 43-year-old healthy woman with no documented atrial fibrillation
    must NOT receive a CHA2DS2-VASc score and must NOT receive any
    'anticoagulation recommended' text. Architecture spec §6 enforces
    this via the gate; this test pins the precise shape of the GATED
    result.
    """
    raw_inputs = {
        "age": 43,
        "sex": "female",
        "atrial_fibrillation_status": None,
        "systolic_bp": 134,
    }
    result = evaluate_gate_to_result(
        score_id="cha2ds2vasc",
        predicate=_CHA2DS2VASC_GATE,
        raw_inputs=raw_inputs,
        prior_results={},
    )

    # Must produce a GATED ScoreResult (not a number, not a wording, not
    # a None; the GATED status is itself the audit signal).
    assert result is not None
    assert result.score_id == "cha2ds2vasc"
    assert result.status is ScoreStatus.GATED
    assert result.gate_failures == ("af_not_documented",)
    assert result.gate_evaluation_trace == ("leaf:af_not_documented:fail",)

    # Architecture spec §6 + §8: gated score carries no number, no band,
    # no wording. The "anticoagulation recommended" output that triggered
    # commitments_log Tier 1 cannot reappear -- there's no wording slot
    # populated for the UI to render.
    assert result.wording is None
    assert result.raw_value is None
    assert result.normalised_q is None
    assert result.risk_band is None
    assert result.epsilon_applied is False
    assert result.anchors_used is None
    assert result.anchor_sources is None
    assert result.interpolation_mode is None
    assert result.confidence is None
    assert result.active_instrument is None
    assert result.reason is None


def test_explicitly_false_af_status_also_fails_the_gate():
    """A user who explicitly answered 'no' to the AF question must also
    be gated -- 'no AF' is not the same as 'AF documented'."""
    result = evaluate_gate_to_result(
        score_id="cha2ds2vasc",
        predicate=_CHA2DS2VASC_GATE,
        raw_inputs={
            "atrial_fibrillation_status": False,
            "age": 43,
            "sex": "female",
        },
        prior_results={},
    )
    assert result is not None
    assert result.status is ScoreStatus.GATED
    assert result.gate_failures == ("af_not_documented",)


def test_documented_af_user_passes_the_gate():
    """A user with documented atrial fibrillation passes the gate. Phase 1
    has no scoring formula yet, so the helper returns None to signal
    'compute the score' -- Phase 3 will wire that path."""
    result = evaluate_gate_to_result(
        score_id="cha2ds2vasc",
        predicate=_CHA2DS2VASC_GATE,
        raw_inputs={
            "atrial_fibrillation_status": True,
            "age": 75,
            "sex": "female",
        },
        prior_results={},
    )
    # Gate passes -> caller should compute the score normally. Per the
    # contract in gates.py, that's signalled by None.
    assert result is None
