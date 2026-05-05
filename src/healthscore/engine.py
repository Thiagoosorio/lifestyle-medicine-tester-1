"""Engine orchestrator (architecture_spec.md §11 + §12).

The Phase 4 ``evaluate_all_scores`` + ``aggregate_organ`` helpers are
preserved as the integration-test seam. Phase 6 adds:

    * ``compute_config_hash``  -- SHA-256 of a deterministic dump of all
                                  loaded configs; written to the audit log
                                  under ``config_hash``.
    * ``new_run_id``           -- ULID-shaped time-ordered identifier for
                                  the audit-log ``run_id`` field. Falls
                                  back to a UUID4-derived form if no
                                  ULID library is available.
    * ``compute()``            -- full orchestration. Topologically
                                  sorts the score graph, evaluates each
                                  score (with output_clamp + language
                                  override + instrument routing), groups
                                  results by organ via domains.yaml,
                                  aggregates Spec A and Spec B per organ
                                  AND per domain, emits one audit blob
                                  to the supplied ``AuditSink``, and
                                  returns ``AggregationOutput``.

The ``AggregationOverrides`` parameter implements the Sobol seam (§12).
Two named branches are currently honoured: ``aggregation`` and ``epsilon``;
the others are validated and recorded but not yet wired into the
aggregator bodies (parked for the harness-mode work).

Pure: no I/O beyond what the supplied AuditSink chooses to perform.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from healthscore.aggregate.spec_a import (
    aggregate_domain_spec_a,
    aggregate_organ_spec_a,
)
from healthscore.aggregate.spec_b import (
    aggregate_domain_spec_b,
    aggregate_organ_spec_b,
)
from healthscore.aggregate.compare import disagreement
from healthscore.audit import AuditSink
from healthscore.domain_config import DomainsConfig
from healthscore.enums import ScoreStatus
from healthscore.gates import GatePredicate
from healthscore.instruments import InstrumentRegistry
from healthscore.overrides import AggregationOverrides
from healthscore.registry import topological_sort
from healthscore.score_config import ScoreConfig, parse_gate_spec
from healthscore.score_eval import evaluate_score
from healthscore.scores import lookup_formula
from healthscore.types import (
    AggregationOutput,
    DomainScore,
    OrganScore,
    ScoreResult,
)


# ── Helpers ─────────────────────────────────────────────────────────────


def _gate_for(config: ScoreConfig) -> GatePredicate | None:
    return parse_gate_spec(config.gate_requirements)


def _resolve_eval_order(configs: Mapping[str, ScoreConfig]) -> tuple[str, ...]:
    score_gates: dict[str, GatePredicate | None] = {
        sid: _gate_for(cfg) for sid, cfg in configs.items()
    }
    return tuple(topological_sort(score_gates))


def evaluate_all_scores(
    *,
    configs: Mapping[str, ScoreConfig],
    raw_inputs: Mapping[str, object],
    instrument_registry: InstrumentRegistry | None = None,
    epsilon: float = 0.01,
    templates: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, ScoreResult]:
    """Phase 4 seam. Run every score in topological order, return the
    per-score results map. Preserved for the integration test suite."""
    eval_order = _resolve_eval_order(configs)
    results: dict[str, ScoreResult] = {}
    for sid in eval_order:
        cfg = configs[sid]
        result = evaluate_score(
            cfg,
            raw_inputs=raw_inputs,
            prior_results=results,
            formula=lookup_formula(cfg.formula),
            gate=_gate_for(cfg),
            epsilon=epsilon,
            templates=templates,
            instrument_registry=instrument_registry,
        )
        results[sid] = result
    return results


def aggregate_organ(
    *,
    organ_id: str,
    domain_id: str,
    member_results: Sequence[ScoreResult],
    weights: Mapping[str, float],
    epsilon: float = 0.01,
    confidence: str = "moderate",
) -> OrganScore:
    """Phase 4 seam. Bundle Spec A + Spec B aggregation into an OrganScore."""
    spec_a, eps_a = aggregate_organ_spec_a(
        score_results=list(member_results), weights=weights, epsilon=epsilon,
    )
    spec_b, _ = aggregate_organ_spec_b(
        score_results=list(member_results), weights=weights, epsilon=epsilon,
    )
    return OrganScore(
        organ_id=organ_id,
        domain_id=domain_id,
        inputs=tuple(member_results),
        spec_a_value=spec_a,
        spec_b_value=spec_b,
        epsilon_activations=eps_a,
        weights_used={sid: w for sid, w in weights.items() if w > 0.0},
        red_flags=(),
        confidence=confidence,  # type: ignore[arg-type]
    )


# ── Audit helpers ───────────────────────────────────────────────────────


def compute_config_hash(
    score_configs: Mapping[str, ScoreConfig],
    domains_config: DomainsConfig,
) -> str:
    """SHA-256 of a deterministic JSON dump of every config loaded.

    The hash covers ``configs/scores/*.json`` (via ScoreConfig.model_dump)
    and ``configs/domains.yaml`` (via DomainsConfig.model_dump). Sort
    keys for determinism. Two computes with identical configs produce
    the same hash; any config edit changes it.
    """
    payload = {
        "scores": {
            sid: cfg.model_dump(mode="json")
            for sid, cfg in sorted(score_configs.items())
        },
        "domains": domains_config.model_dump(mode="json"),
    }
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_run_id() -> str:
    """Generate a time-ordered identifier for the run.

    Uses a 26-character ULID-shaped form: 10-char base32 timestamp +
    16-char base32 randomness. No external dependency on the ``ulid``
    package -- the format is conformant for downstream parsers but the
    randomness is from ``os.urandom``.
    """
    _ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")

    def _b32(value: int, length: int) -> str:
        out: list[str] = []
        for _ in range(length):
            out.append(_ALPHABET[value & 0x1F])
            value >>= 5
        return "".join(reversed(out))

    return _b32(ts_ms, 10) + _b32(rand, 16)


# ── compute() ───────────────────────────────────────────────────────────


def _score_to_audit(result: ScoreResult, raw_inputs: Mapping[str, object]) -> dict[str, Any]:
    return {
        "score_id": result.score_id,
        "status": result.status.value,
        "raw_inputs": dict(raw_inputs),
        "raw_value": str(result.raw_value) if result.raw_value is not None else None,
        "raw_value_unclamped": (
            str(result.raw_value_unclamped)
            if result.raw_value_unclamped is not None
            else None
        ),
        "output_clamped": result.output_clamped,
        "anchors_used": (
            [str(v) for v in result.anchors_used]
            if result.anchors_used is not None else None
        ),
        "anchor_sources": (
            [s.value for s in result.anchor_sources]
            if result.anchor_sources is not None else None
        ),
        "interpolation_mode": (
            result.interpolation_mode.value
            if result.interpolation_mode is not None else None
        ),
        "normalised_q": result.normalised_q,
        "epsilon_applied": result.epsilon_applied,
        "risk_band": result.risk_band.value if result.risk_band is not None else None,
        "gate_failures": list(result.gate_failures),
        "gate_evaluation_trace": list(result.gate_evaluation_trace),
        "active_instrument": result.active_instrument,
        "language_cutoff_active": result.language_cutoff_active,
        "calibration_banner": result.calibration_banner,
        "confidence": result.confidence,
        "pmid_primary": result.pmid,
        "reason": result.reason,
    }


def compute(
    *,
    score_configs: Mapping[str, ScoreConfig],
    domains_config: DomainsConfig,
    instrument_registry: InstrumentRegistry,
    raw_inputs: Mapping[str, object],
    audit_sink: AuditSink,
    templates: Mapping[str, Mapping[str, str]] | None = None,
    overrides: AggregationOverrides | None = None,
    locale: str = "en",
    population: str | None = None,
) -> AggregationOutput:
    """Full engine orchestration.

    1. Resolve epsilon, alpha from overrides or domains_config.
    2. Topologically sort scores; evaluate each in order.
    3. For each organ in domains_config, aggregate surviving member
       results via Spec A and Spec B.
    4. For each domain, aggregate organ scores via Spec A
       (alpha-blend) and Spec B (weighted geometric).
    5. Emit the audit blob to ``audit_sink``.
    6. Return AggregationOutput.

    The ``aggregation`` override (weighted_arithmetic / partial_min /
    owa) is recorded in the audit log; the actual alternative-aggregator
    branches are stubs in this phase (parked for the harness-mode work).
    Calling compute() with an unimplemented aggregation override raises
    ``NotImplementedError`` rather than silently using the geometric
    default -- the failure mode for an unfinished harness branch should
    be loud, not silent.
    """
    epsilon = (
        overrides.epsilon if overrides and overrides.epsilon is not None
        else domains_config.epsilon_default
    )
    alpha = (
        overrides.alpha if overrides and overrides.alpha is not None
        else domains_config.alpha_default
    )
    if overrides is not None:
        if overrides.aggregation not in (None, "weighted_geometric"):
            raise NotImplementedError(
                f"aggregation={overrides.aggregation!r} is a Phase 6+ "
                "harness-mode branch; not yet implemented in compute()"
            )
        if overrides.normalisation not in (None, "distance_to_cutoff"):
            raise NotImplementedError(
                f"normalisation={overrides.normalisation!r} is a Phase 6+ "
                "harness-mode branch; not yet implemented in compute()"
            )

    # Apply score_inclusion: any score with inclusion=False is removed
    # from the eval pool entirely. (Leave-one-out per §4.5.)
    inclusion = {} if overrides is None or overrides.score_inclusion is None else dict(overrides.score_inclusion)
    active_configs = {
        sid: cfg for sid, cfg in score_configs.items()
        if inclusion.get(sid, True)
    }

    # 1+2. Per-score evaluation.
    eval_order = _resolve_eval_order(active_configs)
    results: dict[str, ScoreResult] = {}
    for sid in eval_order:
        cfg = active_configs[sid]
        # Per-score epsilon override (Sobol seam) takes precedence.
        per_score_eps = epsilon
        if (
            overrides is not None
            and overrides.epsilon_per_score is not None
            and sid in overrides.epsilon_per_score
        ):
            per_score_eps = overrides.epsilon_per_score[sid]
        result = evaluate_score(
            cfg,
            raw_inputs=raw_inputs,
            prior_results=results,
            formula=lookup_formula(cfg.formula),
            gate=_gate_for(cfg),
            epsilon=per_score_eps,
            templates=templates,
            instrument_registry=instrument_registry,
        )
        results[sid] = result

    organ_to_domain = domains_config.organ_to_domain()
    organs: list[OrganScore] = []

    # 3. Per-organ aggregation.
    for domain_id, domain_spec in domains_config.domains.items():
        for organ_id, organ_spec in domain_spec.organs.items():
            # Resolved (post-instrument-resolution) score weights.
            weights = domains_config.resolved_score_weights(
                organ_id, instrument_registry
            )
            # Apply override score_weights for this organ if provided.
            if (
                overrides is not None
                and overrides.score_weights is not None
                and organ_id in overrides.score_weights
            ):
                weights = dict(overrides.score_weights[organ_id])
            if not weights:
                continue
            member_results = [
                results[sid] for sid in weights if sid in results
            ]
            if not member_results:
                continue
            organ_score = aggregate_organ(
                organ_id=organ_id,
                domain_id=domain_id,
                member_results=member_results,
                weights=weights,
                epsilon=epsilon,
            )
            organs.append(organ_score)

    # 4. Per-domain aggregation.
    domain_scores: list[DomainScore] = []
    for domain_id, domain_spec in domains_config.domains.items():
        domain_organs = [o for o in organs if o.domain_id == domain_id]
        if not domain_organs:
            continue
        organ_weights = {
            organ_id: spec.weight for organ_id, spec in domain_spec.organs.items()
        }
        if (
            overrides is not None
            and overrides.organ_weights is not None
            and domain_id in overrides.organ_weights
        ):
            organ_weights = dict(overrides.organ_weights[domain_id])

        spec_a_val = aggregate_domain_spec_a(
            organs=domain_organs, organ_weights=organ_weights,
            alpha=alpha, epsilon=epsilon,
        )
        spec_b_val = aggregate_domain_spec_b(
            organs=domain_organs, organ_weights=organ_weights,
            epsilon=epsilon,
        )
        diff_value, diff_flag = disagreement(
            spec_a_val, spec_b_val,
            threshold=domains_config.disagreement_threshold,
        )
        domain_scores.append(DomainScore(
            domain_id=domain_id, organs=tuple(domain_organs),
            spec_a_value=spec_a_val, spec_b_value=spec_b_val,
            disagreement=diff_value,
            disagreement_flag=diff_flag,
            red_flags=(),
            alpha_used=alpha, epsilon_used=epsilon,
        ))

    # Active-instrument map.
    active_instruments = {
        slot: res.active for slot, res in instrument_registry.by_slot.items()
    }

    # 5. Build AggregationOutput + audit blob.
    run_id = new_run_id()
    config_hash = compute_config_hash(score_configs, domains_config)
    timestamp_utc = datetime.now(UTC).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )

    output = AggregationOutput(
        run_id=run_id,
        config_hash=config_hash,
        locale=locale,  # type: ignore[arg-type]
        population=population,
        domains=domain_scores,
        score_results=list(results.values()),
        red_flags=[],
        active_instruments=active_instruments,
        timestamp_utc=timestamp_utc,
    )

    audit_record: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "config_hash": config_hash,
        "timestamp_utc": timestamp_utc,
        "locale": locale,
        "population": population,
        "active_instruments": dict(active_instruments),
        "alpha_used": alpha,
        "epsilon_used": epsilon,
        "overrides_applied": overrides.applied_summary() if overrides else {},
        "score_eval_order": list(eval_order),
        "scores": [_score_to_audit(r, raw_inputs) for r in results.values()],
        "organs": [
            {
                "organ_id": o.organ_id,
                "domain_id": o.domain_id,
                "spec_a": o.spec_a_value,
                "spec_b": o.spec_b_value,
                "weights_used": dict(o.weights_used),
                "epsilon_activations": list(o.epsilon_activations),
            }
            for o in organs
        ],
        "domains": [
            {
                "domain_id": d.domain_id,
                "spec_a": d.spec_a_value,
                "spec_b": d.spec_b_value,
                "disagreement": d.disagreement,
                "disagreement_flag": d.disagreement_flag,
            }
            for d in domain_scores
        ],
        "red_flags": [],
        "disclaimer": output.disclaimer,
    }
    audit_sink.emit(audit_record)
    return output
