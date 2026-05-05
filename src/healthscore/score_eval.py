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

from healthscore.calibration_banners import calibration_banner_for
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
from healthscore.instruments import InstrumentRegistry
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
    instrument_registry: InstrumentRegistry | None = None,
) -> ScoreResult:
    """Evaluate a single score end-to-end. See module docstring for the pipeline."""
    # 0. Instrument-slot routing (architecture_spec.md §7).
    #    When this score is the inactive member of an instrument slot, it
    #    returns UNAVAILABLE without touching gate / formula / normaliser.
    if instrument_registry is not None and instrument_registry.is_inactive_instrument(
        config.score_id
    ):
        slot = instrument_registry.resolution_for_score(config.score_id)
        return ScoreResult(
            score_id=config.score_id,
            status=ScoreStatus.UNAVAILABLE,
            raw_value=None,
            normalised_q=None,
            epsilon_applied=False,
            risk_band=None,
            anchors_used=None,
            anchor_sources=None,
            interpolation_mode=None,
            confidence=None,
            pmid=config.pmid_primary,
            active_instrument=slot.active if slot else None,
            gate_failures=(),
            gate_evaluation_trace=(),
            reason=(
                f"inactive_instrument:{slot.slot}->>{slot.active}"
                if slot else "inactive_instrument"
            ),
            wording=None,
        )

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

    # 3b. Output clamp (commitments_log #22, 4 May 2026). Applied BEFORE
    # normalisation so the q-mapping operates on the clamped value; the
    # unclamped value is preserved for audit. Activation forces
    # confidence=low and stamps reason="output_clamped:<rationale>".
    raw_value_unclamped = raw_value
    output_clamped = False
    clamp_reason: str | None = None
    if config.output_clamp is not None:
        clamp_min = config.output_clamp.min
        clamp_max = config.output_clamp.max
        if raw_value < clamp_min:
            raw_value = clamp_min
            output_clamped = True
        elif raw_value > clamp_max:
            raw_value = clamp_max
            output_clamped = True
        if output_clamped:
            clamp_reason = f"output_clamped:{config.output_clamp.rationale}"

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

    # 4a. Language-anchor override (Phase 5; methodology §5.5).
    # If the user's locale matches a configured language override, use
    # those anchors and stamp the audit field. Confidence may be
    # overridden (e.g. Arabic single-source -> "single_source" tag).
    locale_raw = raw_inputs.get("locale")
    locale_for_anchors = (
        locale_raw.strip().lower()
        if isinstance(locale_raw, str) and locale_raw.strip()
        else "en"
    )
    active_anchors = config.anchors
    language_cutoff_active: str | None = None
    language_confidence_override: str | None = None
    if (
        config.language_anchor_overrides is not None
        and locale_for_anchors in config.language_anchor_overrides
    ):
        override = config.language_anchor_overrides[locale_for_anchors]
        active_anchors = override.anchors
        language_cutoff_active = locale_for_anchors
        language_confidence_override = override.confidence_override
    elif config.language_anchor_overrides is not None:
        # User has a configured override set but a locale outside it
        # (e.g. "fr" when only "ar" is configured): default to "en"
        # anchors; record "en" so the audit log shows the anchor set
        # was deliberately the English default.
        language_cutoff_active = "en"

    outcome = normalise_distance_to_cutoff(
        raw_value,
        low_value=active_anchors.low.value,
        indeterminate_value=active_anchors.indeterminate.value,
        high_value=active_anchors.high.value,
        low_source=active_anchors.low.source,
        indeterminate_source=active_anchors.indeterminate.source,
        high_source=active_anchors.high.source,
    )

    risk_band = _risk_band_from_q(outcome.q)
    anchors_used = (
        active_anchors.low.value,
        active_anchors.indeterminate.value,
        active_anchors.high.value,
    )
    anchor_sources = (
        active_anchors.low.source,
        active_anchors.indeterminate.source,
        active_anchors.high.source,
    )

    # 5. Wording
    from healthscore.wording import render_wording

    # Resolve instrument-slot metadata (active instrument label,
    # fallback confidence demotion per architecture_spec §7).
    active_instrument: str | None = None
    confidence_for_result = config.confidence
    reason_for_result: str | None = None
    if instrument_registry is not None:
        slot = instrument_registry.resolution_for_score(config.score_id)
        if slot is not None:
            active_instrument = slot.active
            if slot.fallback_active:
                confidence_for_result = "low"
                reason_for_result = slot.fallback_reason

    # Output-clamp confidence demotion (commitments_log #22). When the
    # formula output was clamped, drop confidence to "low" and stamp the
    # reason. If a fallback already lowered confidence, the clamp reason
    # supersedes (more specific). Both states never co-occur in practice
    # (instrument-slot scores are not Gompertz-tail-prone).
    if output_clamped:
        confidence_for_result = "low"
        reason_for_result = clamp_reason

    # Language-anchor confidence override (Phase 5). Applies when the
    # locale-specific override carried a confidence_override (e.g.
    # Arabic single-source PHQ-9 / GAD-7 cutoffs). Output-clamp takes
    # precedence if both fire (only an extreme tail score can cause
    # both, and "output_clamped" is the more specific failure mode).
    if language_confidence_override is not None and not output_clamped:
        confidence_for_result = language_confidence_override  # type: ignore[assignment]

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
        confidence=confidence_for_result,
        pmid=config.pmid_primary,
        active_instrument=active_instrument,
        gate_failures=(),
        gate_evaluation_trace=(),
        reason=reason_for_result,
        wording=None,
        raw_value_unclamped=raw_value_unclamped,
        output_clamped=output_clamped,
        language_cutoff_active=language_cutoff_active,
    )
    wording = render_wording(pre_render_result, templates=templates)
    banner = calibration_banner_for(config.score_id, raw_inputs)

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
        confidence=confidence_for_result,
        pmid=config.pmid_primary,
        active_instrument=active_instrument,
        gate_failures=(),
        gate_evaluation_trace=(),
        reason=reason_for_result,
        wording=wording,
        calibration_banner=banner,
        raw_value_unclamped=raw_value_unclamped,
        output_clamped=output_clamped,
        language_cutoff_active=language_cutoff_active,
    )
