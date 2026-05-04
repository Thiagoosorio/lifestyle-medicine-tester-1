"""Per-score evaluation pipeline.

Per architecture_spec.md §6 + §9:

    raw_inputs  -- gate -- formula -- normalise -- interpret -- ScoreResult

The full ``engine.compute()`` orchestration (registry topo sort,
multi-score wiring, audit log) lands in Phase 4. ``evaluate_score``
implements the per-score core that engine.compute will call inside its
topologically ordered loop.

Behaviour:
    1. Apply gate. If gate fails -> GATED ScoreResult; stop.
    2. Validate every required input is present and within physio bounds.
       Missing -> MISSING_INPUT; out-of-range -> OUT_OF_RANGE.
    3. Run formula. None back -> MISSING_INPUT.
    4. Map raw -> q via normalise_distance_to_cutoff (using config anchors).
    5. Bucket the q value into a RiskBand (low / indeterminate / high)
       using the q anchors (>= 0.5 -> low; <= 0.0 -> high; otherwise indet).
    6. Render wording from templates (None for non-OK; templates land in
       Phase 2+ with configs/wording.yaml).
    7. Assemble ScoreResult with status OK.

Pure function: no I/O, no time, no state. Errors are *values*
(ScoreResult.status), never exceptions, except for ConfigValidationError
when the config itself is malformed.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable, Mapping

from healthscore.enums import (
    AnchorSource,
    InterpolationMode,
    RiskBand,
    ScoreStatus,
)
from healthscore.gates import (
    GatePredicate,
    evaluate_gate_to_result,
)
from healthscore.normalize import normalise_distance_to_cutoff
from healthscore.score_config import ScoreConfig
from healthscore.types import ScoreResult


def _validate_input_bounds(
    config: ScoreConfig,
    raw_inputs: Mapping[str, Any],
) -> tuple[ScoreStatus | None, str | None]:
    """Return (status, reason) for the first missing or OOR input, else (None, None)."""
    for ivar in config.input_variables:
        value = raw_inputs.get(ivar.name)
        if value is None:
            return ScoreStatus.MISSING_INPUT, f"missing:{ivar.name}"
        try:
            num = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            # non-numeric inputs (e.g. sex string) skip the bounds check.
            continue
        if ivar.physio_min is not None and num < float(ivar.physio_min):
            return (
                ScoreStatus.OUT_OF_RANGE,
                f"out_of_range:{ivar.name}={value}<{ivar.physio_min}",
            )
        if ivar.physio_max is not None and num > float(ivar.physio_max):
            return (
                ScoreStatus.OUT_OF_RANGE,
                f"out_of_range:{ivar.name}={value}>{ivar.physio_max}",
            )
    return None, None


def _risk_band_from_q(q: float) -> RiskBand:
    """Map a q in [0, 1] to a 3-band risk classification.

    Using q's anchor positions (1.0 = low risk, 0.5 = indeterminate, 0.0 = high
    risk) the natural buckets are:
        q >  0.5    LOW
        q == 0.5    INDETERMINATE
        q <  0.5    INDETERMINATE  if q > 0.0
        q == 0.0    HIGH

    The methodology §1.2 leaves "indeterminate" as the broad middle band;
    HIGH is reserved for the rule-in cutoff. We follow that.
    """
    if q >= 0.75:
        return RiskBand.LOW
    if q <= 0.25:
        return RiskBand.HIGH
    return RiskBand.INDETERMINATE


def evaluate_score(
    config: ScoreConfig,
    *,
    raw_inputs: Mapping[str, Any],
    prior_results: Mapping[str, ScoreResult],
    formula: Callable[[Mapping[str, Any]], Decimal | None],
    gate: GatePredicate | None,
    epsilon: float = 0.01,
    templates: Mapping[str, Mapping[str, str]] | None = None,
) -> ScoreResult:
    """Evaluate a single score end-to-end. See module docstring for the pipeline."""
    # 1. Gate
    gated = evaluate_gate_to_result(
        config.score_id, gate, raw_inputs, prior_results,
    )
    if gated is not None:
        return gated

    # 2. Input validation
    status, reason = _validate_input_bounds(config, raw_inputs)
    if status is not None:
        return ScoreResult(
            score_id=config.score_id,
            status=status,
            raw_value=None,
            normalised_q=None,
            epsilon_applied=False,
            risk_band=None,
            anchors_used=None,
            anchor_sources=None,
            interpolation_mode=None,
            confidence=config.confidence,
            pmid=config.pmid_primary,
            active_instrument=None,
            gate_failures=(),
            gate_evaluation_trace=(),
            reason=reason,
            wording=None,
        )

    # 3. Formula
    raw_value = formula(raw_inputs)
    if raw_value is None:
        return ScoreResult(
            score_id=config.score_id,
            status=ScoreStatus.MISSING_INPUT,
            raw_value=None,
            normalised_q=None,
            epsilon_applied=False,
            risk_band=None,
            anchors_used=None,
            anchor_sources=None,
            interpolation_mode=None,
            confidence=config.confidence,
            pmid=config.pmid_primary,
            active_instrument=None,
            gate_failures=(),
            gate_evaluation_trace=(),
            reason="formula_returned_none",
            wording=None,
        )

    # 4. Normalise
    if config.anchors is None:
        # Non-continuous-3anchor kinds aren't implemented in Phase 2.
        return ScoreResult(
            score_id=config.score_id,
            status=ScoreStatus.NORMALISATION_BREAKDOWN,
            raw_value=raw_value,
            normalised_q=None,
            epsilon_applied=False,
            risk_band=None,
            anchors_used=None,
            anchor_sources=None,
            interpolation_mode=None,
            confidence=config.confidence,
            pmid=config.pmid_primary,
            active_instrument=None,
            gate_failures=(),
            gate_evaluation_trace=(),
            reason="normalisation_unsupported_kind",
            wording=None,
        )

    outcome = normalise_distance_to_cutoff(
        raw_value,
        low_value=config.anchors.low.value,
        indeterminate_value=config.anchors.indeterminate.value,
        high_value=config.anchors.high.value,
        low_source=config.anchors.low.source,
        indeterminate_source=config.anchors.indeterminate.source,
        high_source=config.anchors.high.source,
    )

    risk_band = _risk_band_from_q(outcome.q)
    anchors_used = (
        config.anchors.low.value,
        config.anchors.indeterminate.value,
        config.anchors.high.value,
    )
    anchor_sources = (
        config.anchors.low.source,
        config.anchors.indeterminate.source,
        config.anchors.high.source,
    )

    # 5. Wording
    from healthscore.wording import render_wording

    pre_render_result = ScoreResult(
        score_id=config.score_id,
        status=ScoreStatus.OK,
        raw_value=raw_value,
        normalised_q=outcome.q,
        epsilon_applied=False,                  # eps is applied during aggregation
        risk_band=risk_band,
        anchors_used=anchors_used,
        anchor_sources=anchor_sources,
        interpolation_mode=outcome.interpolation_mode,
        confidence=config.confidence,
        pmid=config.pmid_primary,
        active_instrument=None,
        gate_failures=(),
        gate_evaluation_trace=(),
        reason=None,
        wording=None,
    )
    wording = render_wording(pre_render_result, templates=templates)

    return ScoreResult(
        score_id=config.score_id,
        status=ScoreStatus.OK,
        raw_value=raw_value,
        normalised_q=outcome.q,
        epsilon_applied=False,
        risk_band=risk_band,
        anchors_used=anchors_used,
        anchor_sources=anchor_sources,
        interpolation_mode=outcome.interpolation_mode,
        confidence=config.confidence,
        pmid=config.pmid_primary,
        active_instrument=None,
        gate_failures=(),
        gate_evaluation_trace=(),
        reason=None,
        wording=wording,
    )
