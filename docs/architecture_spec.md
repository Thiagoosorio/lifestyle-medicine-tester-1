# Architecture Specification — Organ-Level Composite Scoring Engine

**Status:** Build specification. Decisions, not options. Anchors `commitments_log.md` queue item #7 (Architecture spec for Claude Code).
**Sources of truth:** `merged_methodology_organ_composite_scores.md` (§1.3, §1.4, §1.5, §1.6, §1.7, §3.6, §4.5, §5.2, §5.3, §5.6) and `commitments_log.md` (4 May 2026 entries: aggregation specification, normalisation rule, ε floor, panel reductions, source-data panel audit Tier 1/2/3/4, regulatory positioning and launch jurisdiction; **plus three later entries from this conversation: anchor-source distinction, KFRE gate, aMAP compound gate**).
**Audience:** Claude Code, implementing the scoring core.
**Out of scope here:** UI/rendering, persistence, auth, the Sobol harness itself (see §12 for the seam only), cohort statistics, validation programme.

---

## 1. Language and runtime

**Language:** Python 3.12 (CPython, latest patch).
**Lockfile:** `pyproject.toml` + `uv.lock` (or `poetry.lock`); pinned exact versions, no floating ranges.

**Why Python over TypeScript.** The system's centre of gravity is numerical: piecewise-linear normalisation, weighted geometric means with an ε floor, Dirichlet weight sampling, Sobol variance decomposition, bootstrap, Spearman/Harrell's C. Every one is first-class in Python (`numpy`, `scipy`, `SALib`, `lifelines`) and second-class or absent in Node. The §4.5 Sobol harness alone settles the choice. The audit posture also favours a stack auditable by clinical biostatisticians.

**Core scoring dependencies (kept minimal — auditable surface):**

| Package | Version | Role |
|---|---|---|
| `pydantic` | `>=2.7,<3.0` | Config validation, type enforcement at module boundaries |
| `pyyaml` | `>=6.0` | YAML config loading (instruments, domain weights) |
| stdlib `dataclasses`, `decimal`, `math`, `typing`, `enum`, `logging`, `json` | — | Everything else |

**No** `numpy` / `pandas` in the scoring core. Aggregation is small-N (≤ 20 inputs per organ); stdlib `math` is sufficient and keeps the core dependency-light. Numpy/SALib live in the harness only.

**Validation/harness dependencies (separate package):** `numpy`, `scipy`, `SALib`, `lifelines`, `pytest`, `hypothesis`. These never import the scoring core's I/O layer.

**Test stack:** `pytest`, `pytest-cov`, `hypothesis`, `pytest-snapshot`. Coverage gate enforced in CI (§10).

---

## 2. Project structure

```
healthscore/                          # repository root
├── pyproject.toml
├── uv.lock
├── README.md
├── ARCHITECTURE.md                   # this document, copied in
│
├── src/healthscore/
│   ├── __init__.py
│   ├── types.py                      # ALL dataclasses (§3) — no logic
│   ├── enums.py                      # ScoreStatus, RedFlagSeverity, RiskBand, etc.
│   ├── errors.py                     # exception classes (§9)
│   │
│   ├── normalize.py                  # distance-to-cutoff, ε floor (pure)
│   ├── gates.py                      # gate-check engine (§6, pure)
│   ├── instruments.py                # MoCA/MMSE, STOP-BANG/NoSAS selector (§7)
│   ├── redflags.py                   # non-compensatory flag layer (pure)
│   ├── wording.py                    # risk-band template renderer (§8, pure)
│   │
│   ├── scores/                       # pure: input dict + config → ScoreResult
│   │   ├── __init__.py               # registry: name → callable
│   │   ├── liver.py                  # fib4, albi, amap, fli (+ confirmatory: nfs, apri, hsi)
│   │   ├── cvd.py                    # prevent, score2, qrisk3, apob, lpa, cha2ds2vasc
│   │   ├── metabolic.py              # homa_ir, mets_ir, tyg, tyg_bmi, vai, lap, findrisc
│   │   ├── kidney.py                 # egfr, kfre, kdigo_category
│   │   ├── brain.py                  # moca, mmse, phq9, gad7, caide, libra, homocysteine
│   │   ├── bone_muscle.py            # dxa_t, ewgsop2, qfracture, fnih_lean
│   │   ├── system_wide.py            # phenoage, sii, nlr, hb_rdw, thyroid_pattern, stop_bang, nosas
│   │   └── gut.py                    # fit, calprotectin, rome_iv (binary/symptom — flag only)
│   │
│   ├── aggregate/
│   │   ├── __init__.py
│   │   ├── common.py                 # ε-floor logging, weight normalisation, both specs share
│   │   ├── spec_a.py                 # α-blend (§5)
│   │   ├── spec_b.py                 # geometric + flag layer (§5)
│   │   └── compare.py                # |Spec A − Spec B| disagreement detector
│   │
│   ├── audit.py                      # structured audit log emitter (§11)
│   └── engine.py                     # orchestrator: ONLY public entry point
│
├── src/healthscore_io/               # I/O layer, separate package, depends on core
│   ├── config_loader.py              # JSON/YAML → pydantic models
│   ├── input_adapter.py              # external payloads → ScoreInput
│   ├── output_adapter.py             # AggregationOutput → API response
│   └── audit_writer.py               # audit.py emissions → durable storage
│
├── configs/
│   ├── scores/                       # one file per score
│   │   ├── fib4.json
│   │   ├── albi.json
│   │   ├── amap.json
│   │   ├── fli.json
│   │   ├── prevent.json
│   │   ├── cha2ds2vasc.json
│   │   ├── moca.json
│   │   ├── mmse.json
│   │   ├── stop_bang.json
│   │   ├── nosas.json
│   │   └── …                         # one per score in panel
│   ├── instruments.yaml              # MoCA↔MMSE, STOP-BANG↔NoSAS bindings
│   ├── domains.yaml                  # organ→domain weights, α default, ε default
│   └── wording.yaml                  # risk-band wording templates per score
│
├── tests/
│   ├── unit/
│   │   ├── test_normalize.py
│   │   ├── test_gates.py
│   │   ├── test_redflags.py
│   │   ├── test_wording.py
│   │   ├── test_instruments.py
│   │   └── scores/test_*.py          # one per score
│   ├── integration/
│   │   ├── test_engine_end_to_end.py
│   │   └── test_audit_emissions.py
│   ├── regression/
│   │   └── test_liver_worked_example.py   # §1.7 frozen test (§10)
│   ├── property/
│   │   └── test_aggregation_invariants.py # hypothesis-driven
│   └── linguistics/
│       └── test_forbidden_verbs.py        # §8 enforcement
│
└── harness/                          # separate, NOT imported by core
    ├── sobol_runner.py
    ├── perturbation_grid.py
    └── reports/
```

**Hard separation rule:** `src/healthscore/` (core) imports nothing from `src/healthscore_io/` or `harness/`. The core is a pure function `(inputs, config) → AggregationOutput`. I/O, persistence, networking, time-of-day, and randomness (other than what's passed in explicitly) are forbidden inside the core. This is what makes the core Sobol-perturbable without modification (§12).

---

## 3. Type definitions

All types live in `src/healthscore/types.py`. Pydantic v2 `BaseModel` for anything that crosses a config or API boundary; plain `@dataclass(frozen=True, slots=True)` for internal-only structures. `Decimal` for any value displayed to a user; `float` is acceptable inside aggregation maths but the boundary back to the user re-quantises.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Literal, Mapping, Sequence
from pydantic import BaseModel, Field

# ── enums ────────────────────────────────────────────────────────────────────

class ScoreStatus(str, Enum):
    OK              = "ok"
    GATED           = "gated"               # gate-check failed; not computed
    MISSING_INPUT   = "missing_input"       # required input absent
    OUT_OF_RANGE    = "out_of_range"        # input outside physiological bounds
    NORMALISATION_BREAKDOWN = "normalisation_breakdown"  # ε floor activated
    UNAVAILABLE     = "unavailable"         # instrument not selected for this run

class RiskBand(str, Enum):
    LOW             = "low"
    INDETERMINATE   = "indeterminate"
    HIGH            = "high"

class RedFlagSeverity(str, Enum):
    INFO            = "info"
    ATTENTION       = "attention"
    URGENT_REVIEW   = "urgent_review"       # never "urgent" alone (§8 wording)

class ScoreKind(str, Enum):
    CONTINUOUS_3ANCHOR  = "continuous_3anchor"
    ABSOLUTE_RISK_PCT   = "absolute_risk_pct"
    ORDINAL_CATEGORY    = "ordinal_category"
    SYMPTOM_BAND        = "symptom_band"
    BINARY_SCREEN       = "binary_screen"   # FIT, calprotectin — flag only

class AnchorSource(str, Enum):
    PUBLISHED            = "published"
    CONSTRUCTED_MIDPOINT = "constructed_midpoint"

class InterpolationMode(str, Enum):
    THREE_ANCHOR_PWL = "three_anchor_pwl"   # all three anchors published
    TWO_ANCHOR_PWL   = "two_anchor_pwl"     # midpoint constructed; skipped in interpolation

# ── leaf input/result ────────────────────────────────────────────────────────

class ScoreInput(BaseModel):
    """User-side inputs for a single score computation."""
    score_id: str
    raw_inputs: Mapping[str, Decimal | str | bool | None]
    locale: Literal["en", "ar"] = "en"     # drives Arabic-cutoff selection (§7 / §5.5)
    population: str | None = None          # e.g. "uae_emirati"; None = derivation-cohort default

@dataclass(frozen=True, slots=True)
class ScoreResult:
    score_id: str
    status: ScoreStatus
    raw_value: Decimal | None              # the score's native units (e.g. FIB-4 = 2.0)
    normalised_q: float | None             # health value in [0,1] AFTER ε floor
    epsilon_applied: bool                  # True if ε floor activated
    risk_band: RiskBand | None
    anchors_used: tuple[Decimal, Decimal, Decimal] | None  # (low, indet, high)
    anchor_sources: tuple[AnchorSource, AnchorSource, AnchorSource] | None
    interpolation_mode: InterpolationMode | None
    confidence: Literal["high", "moderate", "low", "single_source"] | None
    pmid: str | None
    active_instrument: str | None          # e.g. "moca" if this slot resolved to MoCA
    gate_failures: tuple[str, ...]         # empty if gates passed; failure_reason_code values if not
    gate_evaluation_trace: tuple[str, ...] # ordered audit trace of gate node evaluations
    reason: str | None                     # for non-OK statuses; not user-facing
    wording: str | None                    # rendered, regulator-safe; user-facing

@dataclass(frozen=True, slots=True)
class RedFlag:
    score_id: str
    severity: RedFlagSeverity
    threshold_label: str                   # e.g. "FIB-4 ≥ 2.67"
    actual_value: Decimal
    wording: str                           # rendered, regulator-safe (§8)
    pmid: str

# ── organ / domain ───────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class OrganScore:
    organ_id: str                          # "liver", "kidney", "cvd", …
    domain_id: str                         # "heart_metab", "brain", …
    inputs: tuple[ScoreResult, ...]        # the contributing ScoreResults
    spec_a_value: float | None             # 0–100; None if all inputs failed
    spec_b_value: float | None             # 0–100; identical to A at organ level
    epsilon_activations: tuple[str, ...]   # score_ids where ε fired
    weights_used: Mapping[str, float]      # nominal cluster weights; sums to 1
    red_flags: tuple[RedFlag, ...]         # collected from inputs
    confidence: Literal["high", "moderate", "low"]

@dataclass(frozen=True, slots=True)
class DomainScore:
    domain_id: str                         # one of the 5
    organs: tuple[OrganScore, ...]
    spec_a_value: float | None             # α-blend per §1.3
    spec_b_value: float | None             # weighted geometric per §1.3
    disagreement: float | None             # |spec_a - spec_b|; None if either missing
    disagreement_flag: bool                # True if disagreement > 5 (per §1.3)
    red_flags: tuple[RedFlag, ...]         # rolled up from organs
    alpha_used: float                      # the α actually used in this run
    epsilon_used: float                    # the ε actually used in this run

class AggregationOutput(BaseModel):
    """Top-level result from engine.compute()."""
    schema_version: str = "1.0.0"
    run_id: str                            # ULID; ties to audit log
    config_hash: str                       # SHA-256 of resolved config
    locale: Literal["en", "ar"]
    population: str | None
    domains: Sequence[DomainScore]
    score_results: Sequence[ScoreResult]   # all per-score computations, including gated/missing
    red_flags: Sequence[RedFlag]           # union across all organs
    active_instruments: Mapping[str, str]  # {"cognitive": "moca", "osa": "stop_bang"}
    timestamp_utc: str                     # ISO-8601, fixed by caller (not core)
```

**`Decimal` vs `float`.** Inputs and raw values use `Decimal` to avoid display-rounding (`1.30` should not show as `1.2999…`). Aggregation maths use `float` — `math.log` and `math.exp` are double-precision. The boundary back to the user re-quantises with `Decimal.quantize`.

**No `None` ambiguity.** Every nullable field is typed `T | None`. Missing scores arrive as `ScoreResult` with `status != OK` and a populated `reason` — never silently dropped.

---

## 4. Score config schema

One JSON file per score in `configs/scores/<score_id>.json`. Loaded into a pydantic `ScoreConfig` model at engine startup; engine refuses to start if any config fails validation.

```json
{
  "score_id": "fib4",
  "display_name": "FIB-4",
  "kind": "continuous_3anchor",
  "pmid_primary": "16729309",
  "pmid_supporting": ["32946642", "36727674"],
  "guideline_anchor": "AASLD 2023 / EASL-EASD-EASO 2024",
  "input_variables": [
    { "name": "ast",       "unit": "U/L",         "physio_min": 0,   "physio_max": 5000 },
    { "name": "alt",       "unit": "U/L",         "physio_min": 0,   "physio_max": 5000 },
    { "name": "platelets", "unit": "10^9/L",      "physio_min": 1,   "physio_max": 1500 },
    { "name": "age",       "unit": "years",       "physio_min": 18,  "physio_max": 120 }
  ],
  "formula": "fib4",
  "anchors": {
    "low":           { "value": 1.30,  "q": 1.0, "source": "published" },
    "indeterminate": { "value": 1.985, "q": 0.5, "source": "constructed_midpoint" },
    "high":          { "value": 2.67,  "q": 0.0, "source": "published" }
  },
  "anchors_unit": "fib4_units",
  "interpolation": "piecewise_linear",
  "clamp": [0.0, 1.0],
  "applicable_population": {
    "min_age": 35,
    "max_age": 79,
    "exclusions": ["acute_hepatitis", "pregnancy"],
    "calibration_caveat": "AASLD 2023 cutoffs may misclassify ~25% of MASLD cirrhosis (PMC12269257); UAE calibration unverified."
  },
  "derivation_cohort": {
    "study": "Sterling 2006",
    "n": 832,
    "geography": "USA",
    "ethnicity": "mixed",
    "outcome": "advanced fibrosis (Ishak 4-6) by biopsy"
  },
  "epsilon_override": null,
  "red_flag": {
    "trigger": ">=",
    "threshold": 2.67,
    "severity": "attention",
    "wording_key": "fib4_high_band"
  },
  "gate_requirements": [],
  "confidence": "high",
  "instrument_slot": null,
  "version": "2025.1"
}
```

Key per-score fields:

| Field | Required | Notes |
|---|---|---|
| `score_id` | yes | snake_case; primary registry key |
| `kind` | yes | drives normalisation routine |
| `pmid_primary` | yes | derivation paper. The four corrections in `commitments_log.md` "Source-data panel audit committed" Tier 2 are mandatory: Hb+RDW = `19880817`; QFracture (both endpoints) = `22619194`; clinical-chemistry PhenoAge = `30596641` (**not** the DNAm `29676998`). Suboptimal-citation upgrades (Tier 3) are config-only changes deferred to Phase 5. |
| `input_variables[]` | yes | each with `name`, `unit`, `physio_min`, `physio_max` |
| `anchors.{low,indeterminate,high}` | yes for `continuous_3anchor` | values in score's native units; q values normally 1.0 / 0.5 / 0.0. Each anchor carries `source: "published" | "constructed_midpoint"`. **Interpolation rule:** if all three anchors are `published`, use three-anchor piecewise-linear; if `indeterminate.source == "constructed_midpoint"`, use two-anchor piecewise-linear between `low` and `high` only (the midpoint is recorded in audit but not used in interpolation maths). FIB-4, NAFLD-FS, and most other guideline-cutoff scores have constructed midpoints; ASCVD 10-year (5% / 7.5% / 20%) has three published anchors. **Methodology clarification needed:** §1.2 currently treats all three anchors uniformly; it must be updated to describe the constructed-midpoint case and the two-anchor fallback. §1.7 worked example uses two-anchor interpolation for FIB-4 (q≈0.49) — this becomes explicit when §1.2 is clarified. |
| `anchors_unit` | yes | the unit; never assume |
| `applicable_population` | yes | drives gate-check + calibration banner |
| `derivation_cohort` | yes | for audit + UI calibration banner per §5.5 |
| `epsilon_override` | optional | per-score override of global ε; null means inherit |
| `red_flag` | optional | trigger comparator + threshold + severity; null means no flag |
| `gate_requirements[]` | optional | see §6 |
| `instrument_slot` | optional | for MoCA/MMSE, STOP-BANG/NoSAS rows; see §7 |
| `confidence` | yes | one of `high`, `moderate`, `low`, `single_source` (e.g. PHQ-9 Arabic cutoff) |

Global defaults live in `configs/domains.yaml`:

```yaml
epsilon_default: 0.01
alpha_default: 0.5
disagreement_threshold: 5.0
domains:
  heart_metab:
    weight: 0.30
    organs:
      liver:   { weight: 0.20, scores: { fib4: 0.40, albi: 0.20, amap: 0.20, fli: 0.20 } }
      kidney:  { weight: 0.20, scores: { egfr: 0.50, kfre: 0.30, kdigo_category: 0.20 } }
      cvd:     { weight: 0.40, scores: { prevent: 0.50, apob: 0.25, lpa: 0.15, findrisc: 0.10 } }
      metabolic: { weight: 0.20, scores: { homa_ir: 0.40, mets_ir: 0.30, tyg: 0.30 } }
  brain:        { weight: 0.20, organs: { … } }
  muscle_bones: { weight: 0.15, organs: { … } }
  gut:          { weight: 0.10, organs: { … } }
  system_wide:  { weight: 0.25, organs: { … } }
```

Weights summing to 1.0 within each level is checked at config load; engine refuses to start otherwise.

---

## 5. Aggregation function signatures

Both specs are pure functions with **identical** input and output types. The engine runs both and stores both into `DomainScore`. Spec A and Spec B never call each other.

```python
# src/healthscore/aggregate/common.py

def normalise_for_geomean(q: float, epsilon: float) -> tuple[float, bool]:
    """Apply ε floor before log. Returns (q_floored, epsilon_was_applied)."""

def weighted_geomean(values: Sequence[tuple[float, float]], epsilon: float) -> tuple[float, list[bool]]:
    """values: [(q_i, w_i), ...]. Returns (organ_score_0_100, [epsilon_flags_per_input])."""

# src/healthscore/aggregate/spec_a.py

def aggregate_organ_spec_a(
    *,
    score_results: Sequence[ScoreResult],
    weights: Mapping[str, float],
    epsilon: float,
) -> tuple[float | None, tuple[str, ...]]:
    """
    Spec A organ-level: weighted geometric mean.
    Returns (organ_score_0_100 | None, tuple_of_score_ids_where_epsilon_applied).
    None if every input is non-OK. Skips gated/missing inputs and renormalises weights.
    """

def aggregate_domain_spec_a(
    *,
    organs: Sequence[OrganScore],
    organ_weights: Mapping[str, float],
    alpha: float,        # exposed for Sobol perturbation (§12)
    epsilon: float,      # exposed for Sobol perturbation (§12)
) -> float | None:
    """
    Spec A domain-level (§1.3):
        DomainScore_A = α · min(OrganScore_j) + (1 − α) · Π OrganScore_j ^ w_j
    Returns 0–100 or None if every organ is None.
    """

# src/healthscore/aggregate/spec_b.py

def aggregate_organ_spec_b(
    *,
    score_results: Sequence[ScoreResult],
    weights: Mapping[str, float],
    epsilon: float,
) -> tuple[float | None, tuple[str, ...]]:
    """
    Spec B organ-level: identical to Spec A at organ level by methodology §1.3
    (same weighted geometric mean within organ). Implemented as a separate
    function so the two specs remain swappable without coupling — if a future
    methodology revision diverges them at organ level, only this signature changes.
    """

def aggregate_domain_spec_b(
    *,
    organs: Sequence[OrganScore],
    organ_weights: Mapping[str, float],
    epsilon: float,      # exposed for Sobol perturbation (§12)
) -> float | None:
    """
    Spec B domain-level (§1.3):
        DomainScore_B = 100 · exp(Σ w_j · ln(OrganScore_j / 100))
    Red flags are NOT folded into this number — they are returned separately
    by redflags.collect() and surfaced on DomainScore.red_flags.
    """

# src/healthscore/aggregate/compare.py

def disagreement(spec_a: float | None, spec_b: float | None, threshold: float) -> tuple[float | None, bool]:
    """Returns (|a - b|, exceeded). If either is None, returns (None, False)."""
```

**ε floor handling.** `normalise_for_geomean` is the *only* place ε is applied. It returns whether activation occurred, and that boolean propagates up into `OrganScore.epsilon_activations` and the audit log (§11). ε is a parameter, never a constant — see §12.

**α exposure.** `aggregate_domain_spec_a` takes `alpha` as a keyword-only parameter. The default value is read from `configs/domains.yaml` at engine startup; the harness overrides it without touching the function.

**Weight renormalisation when an input is missing/gated.** If a score is `MISSING_INPUT`, `OUT_OF_RANGE`, or `GATED`, both specs skip it and renormalise the surviving weights to sum to 1. This is logged. If fewer than 2 scores survive within an organ, the organ returns `None` and the audit log records a `degenerate_organ` event.

---

## 6. Gate-check logic

Three concrete gates are committed (`commitments_log.md` 4 May 2026 entries: CHA₂DS₂-VASc clinical-safety gate; KFRE clinically-correct gate; aMAP compound MASLD-evidence gate). The aMAP gate references **other scores' computed values**, not just raw inputs, which forces a recursive predicate type and dependency-ordered execution.

**Predicate type (recursive).** A `GatePredicate` is one of:
- a `GateLeaf` — a single condition on a field
- a `GateAllOf` — every child must pass
- a `GateAnyOf` — at least one child must pass

**Missing policy (leaf):**

- **`"fail"`** — unresolvable field ⇒ leaf is a decisive **FAIL**.
- **`"skip"`** — unresolvable field ⇒ leaf is **NON-DECISIVE** (3-state: PASS / FAIL / SKIP). A skip leaf neither satisfies an `any_of` branch nor violates an `all_of` constraint — the gate falls through to the next branch / next constraint.

```python
@dataclass(frozen=True, slots=True)
class GateLeaf:
    field: str                          # dotted path: "raw_inputs.<name>" OR "score_results.<id>.<field>"
    predicate: Literal["equals", "in", "ge", "le", "gt", "lt", "truthy"]
    expected: object | None
    missing_policy: Literal["fail", "skip"]   # "skip" = non-decisive (does not satisfy any_of, does not violate all_of)
    failure_reason_code: str

@dataclass(frozen=True, slots=True)
class GateAllOf:
    all_of: tuple["GatePredicate", ...]

@dataclass(frozen=True, slots=True)
class GateAnyOf:
    any_of: tuple["GatePredicate", ...]

GatePredicate = GateLeaf | GateAllOf | GateAnyOf
```

**Field path semantics.** A leaf's `field` is a dotted path:
- `raw_inputs.<name>` — looks up the value in `ScoreInput.raw_inputs`. If absent and `missing_policy == "fail"`, the leaf fails.
- `score_results.<score_id>.<field>` — looks up a previously computed `ScoreResult` for `<score_id>`. If that score has `status != OK`, the leaf evaluates per `missing_policy`. The dependency is recorded for topological sort.

**Three-state combinator semantics (non-decisive `skip`).** Combinators evaluate every child (no short-circuit, for audit fidelity), classify each as PASS / FAIL / SKIP, and propagate as follows:

| Pattern | Result |
|---|---|
| `any_of(skip, pass)` | **pass** |
| `any_of(skip, fail)` | **fail** |
| `any_of(skip)` | **skip** (fully non-decisive) |
| `any_of()` | fail (vacuous existential) |
| `all_of(skip, pass)` | **pass** |
| `all_of(skip, fail)` | **fail** |
| `all_of(skip)` | **skip** |
| `all_of()` | pass (vacuous truth) |

The public `evaluate_predicate` API returns a 2-state `(passed: bool, …)`; a top-level SKIP maps to `passed=True` because no decisive failure was found. The trace records `leaf:<code>:skip` and `any_of:skip` / `all_of:skip` so audit can distinguish "the gate passed because every constraint was applicable and satisfied" from "the gate passed because no constraint was applicable in the first place."

The aMAP gate is the canonical case: the CLD-status leaf carries `missing_policy: "skip"` so a user without a documented CLD answer is non-decisive on that branch — the engine then evaluates the FIB-4 + FLI second branch, and `any_of` resolves on whichever branch is decisive. Without `skip`, missing CLD would force the first branch to FAIL and the `any_of` would resolve on the second branch's outcome alone (no fall-through semantics). The fall-through behaviour is what the architecture spec's narrative example required all along; this subsection is the formal definition that catches the spec up to the Phase 2 implementation.

**Dependency DAG and topological execution.**

1. At engine startup, walk every score's gate tree. Collect `score_results.<id>` references as edges: `<id>` → this score (this score depends on `<id>`).
2. Topologically sort the score registry. Cycle → `RegistryConflictError` at startup.
3. At runtime, `engine.compute()` evaluates scores in topological order. A score's gate evaluates only after all referenced scores have computed.
4. If a referenced score is `GATED`, `MISSING_INPUT`, or `OUT_OF_RANGE`, the dependent leaf treats the field as unresolvable and applies `missing_policy`.

**Engine module** `src/healthscore/gates.py`:

```python
def evaluate_predicate(
    predicate: GatePredicate,
    raw_inputs: Mapping[str, object],
    prior_results: Mapping[str, ScoreResult],
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    """
    Evaluate a (possibly nested) predicate.
    Returns (passed, failure_reason_codes, evaluation_trace).
    `evaluation_trace` is an ordered list like
        ("any_of:start", "leaf:cld_documented:fail", "all_of:start",
         "leaf:fib4_ge_1.3:pass", "leaf:fli_ge_60:pass", "all_of:pass", "any_of:pass")
    suitable for audit logging (§11).
    """
```

A score whose gate fails is **never computed**: it returns `ScoreResult(status=GATED, gate_failures=(<failure_reason_codes>,), gate_evaluation_trace=(<trace>,), risk_band=None, raw_value=None, normalised_q=None, wording=None)`. The gated score does not contribute to organ aggregation, and its weight is redistributed across surviving cluster members per §5.

**Pre-launch gate registry (must ship blocking the score's compute path):**

| Score | Gate (config form) | Source |
|---|---|---|
| `cha2ds2vasc` | `leaf{ field=raw_inputs.atrial_fibrillation_status, equals true, missing=fail }` | commitments_log Tier 1; methodology §3.6 |
| `kfre` | `leaf{ field=raw_inputs.egfr, le 60, missing=fail }` | commitments_log decision (this conversation): KFRE is clinically meaningful only for diagnosed CKD (G3a–G5) |
| `amap` | `any_of[ leaf{ field=raw_inputs.chronic_liver_disease_status, equals true, missing=skip }, all_of[ leaf{ field=score_results.fib4.raw_value, ge 1.3, missing=fail }, leaf{ field=score_results.fli.raw_value, ge 60, missing=fail } ] ]` | commitments_log decision (this conversation): aMAP computes for documented CLD users **or** for users with FIB-4 ≥ 1.3 AND FLI ≥ 60 (MASLD screening evidence); avoids over-restriction without dropping the gate |
| `qfracture_*` | `leaf{ field=raw_inputs.age, ge 30, missing=fail }` | derivation cohort (Hippisley-Cox 2012) |

**`missing_policy` choice:** prefer `"fail"` for clinical-safety gates (e.g. CHA₂DS₂-VASc / atrial-fibrillation: missing = decisive fail, no score). Prefer `"skip"` only when the leaf is one branch of an `any_of` and another branch must be evaluated independently (e.g. aMAP / chronic-liver-disease-status: missing = non-decisive on this branch, evaluate MASLD-screening branch).

**aMAP gate JSON form** (illustrative for the schema):

```json
"gate_requirements": {
  "any_of": [
    {
      "field": "raw_inputs.chronic_liver_disease_status",
      "predicate": "equals", "expected": true,
      "missing_policy": "skip", "failure_reason_code": "cld_not_documented"
    },
    {
      "all_of": [
        { "field": "score_results.fib4.raw_value", "predicate": "ge", "expected": 1.3,
          "missing_policy": "fail", "failure_reason_code": "fib4_unavailable_or_low" },
        { "field": "score_results.fli.raw_value", "predicate": "ge", "expected": 60,
          "missing_policy": "fail", "failure_reason_code": "fli_unavailable_or_low" }
      ]
    }
  ]
}
```

Note `missing_policy: "skip"` on the CLD-status leaf: a user who hasn't told us their CLD status simply doesn't trigger the first branch — the engine falls through to the screening-evidence branch. Without `skip`, missing CLD status would short-circuit the whole `any_of` to fail.

**Adding a future conditional score** is purely a config change (add `gate_requirements` to the JSON). Adding a new field path or predicate type requires a code change. The four predicate kinds and two combinators above are exhaustive for this build; if a future need arises (e.g. `not_of`, time-windowed predicates), extend the schema deliberately, not silently.

**Test obligations:**
- Every score with non-empty `gate_requirements` has unit tests for each branch: gate-pass, gate-fail-by-each-leaf-reason-code, gate-fail-by-missing-input, gate-fail-by-dependency-not-OK.
- aMAP-specific: tests cover (i) CLD documented → pass, (ii) CLD null + FIB-4 ≥ 1.3 + FLI ≥ 60 → pass via second branch, (iii) CLD null + FIB-4 < 1.3 → fail, (iv) CLD null + FLI missing → fail with `fli_unavailable_or_low`, (v) CLD null + FIB-4 GATED itself → fail with `fib4_unavailable_or_low`.
- Engine-startup test: a config with circular dependencies (score A's gate references B, B's gate references A) raises `RegistryConflictError` before any computation runs.
- CHA₂DS₂-VASc remains the canonical Phase-1 fixture (§10).

**Source attribution.** Erratum #3, `commitments_log.md` (4 May 2026): the original §6 wording defined `"skip"` literally as "leaf passes," which contradicts the spec's own narrative example ("falls through to the screening-evidence branch"). Phase 2 implementation surfaced the inconsistency; the formal 3-state semantics above resolve it. Phase 1's CHA₂DS₂-VASc canonical fixture continues to pass under either reading because it uses `missing_policy: "fail"` only.

---

## 7. Runtime instrument selection

Per §5.6, two instrument slots have committed primary + fallback pairs:

| Slot | Primary | Fallback | Trigger |
|---|---|---|---|
| `cognitive` | `moca` | `mmse` | MoCA Cognition Inc. licensing terms |
| `osa` | `stop_bang` | `nosas` | UHN/Frances Chung licensing terms |

Selection is **runtime config**, not code. `configs/instruments.yaml`:

```yaml
slots:
  cognitive:
    primary: moca
    fallback: mmse
    active: moca           # the only field the deployment env changes
    fallback_reason: null  # populated if active != primary
  osa:
    primary: stop_bang
    fallback: nosas
    active: stop_bang
    fallback_reason: null
```

**Engine startup:**

1. Load `instruments.yaml`.
2. For each slot, resolve `active` to a `score_id`.
3. Verify the resolved `score_id` has a config in `configs/scores/`.
4. Build a `slot → active_score_id` map; freeze it for the run.
5. The non-active instrument's score is registered with `status=UNAVAILABLE` for any input that arrives. It does **not** contribute to aggregation, does not emit a wording, and is logged once at startup, not per-call.

**Propagation:**

- `ScoreResult.active_instrument` carries the resolved `score_id` for any score in an instrument slot.
- `AggregationOutput.active_instruments` carries the full slot-to-score map.
- The audit log entry per computation includes `active_instruments` (§11).
- The user-facing wording template includes the instrument name when in an instrument slot (e.g. "*Cognitive screening (MoCA)*"), so a fallback activation is always visible to the user.

**Fallback activation propagates a confidence demotion.** When `active = fallback`, the score's `confidence` field in the resulting `ScoreResult` is forced to `low` regardless of the underlying config, with `reason="fallback_active:<primary>→<fallback>"`. This implements the §5.6 trade-off note ("MMSE in place of MoCA: lower MCI sensitivity (~80% vs ~90%); known education/culture bias amplified in UAE/MENA user base. Add explicit confidence-flag in user-facing display").

**Test obligation:** integration tests run the full engine twice — once with primary active, once with fallback active — asserting (a) the right score executes, (b) `confidence` is demoted on fallback, (c) audit log records the active instrument, (d) the inactive instrument returns `UNAVAILABLE` for any input.

---

## 8. Output language constraints

**Authority:** `commitments_log.md`, 4 May 2026 entry "Regulatory positioning and launch jurisdiction." Reproduced verbatim:

> *Code constraints (binding for architecture spec and Claude Code implementation): no "diagnose," "predict disease," "prognosis," or treatment-recommendation language in any output string, function name, API response, or UI label. Risk-band language only. CHA₂DS₂-VASc gate (§3.6 Tier 1) is a specific instance of this rule.*

**Launch jurisdiction:** UAE MOHAP / DoH Abu Dhabi only. EU MDR and FDA frameworks are **deferred** per the same commitments_log entry; the architecture spec does not constrain output for those jurisdictions because they are not in scope at launch. If/when expansion is on the table, this section is re-opened.

**Forbidden lemmas in any output string, function name, public API field, or UI label** (anchored to the commitments_log wording, not broadened):

```
diagnose, diagnosis, diagnostic
predict, prediction, predicts          (when paired with a disease/condition object)
prognosis, prognostic, prognose
recommend                              (in treatment-direction sense)
prescribe, prescription
treatment, therapy                     (when paired with action verbs: start, begin, initiate, stop)
cure, curative
```

**Exceptions** (allow-listed; linter accepts):

- "lifestyle recommendations" / "screening recommendations" → allowed (wellness sense, not treatment-direction).
- "AHA PREVENT equation" / "AHA PREVENT score" → allowed (proper noun).
- "screening for ..." → allowed (descriptive of the score's purpose, not diagnostic claim).
- "diagnostic accuracy" inside an internal `confidence` field's prose justification → allowed only in non-user-visible audit fields.

**Note on `predict`.** The verb is forbidden when its grammatical object is a disease or future condition ("predicts diabetes," "predicts mortality"). It is permissible in narrow technical references that do not address the user's future state (e.g., score documentation describing a derivation cohort: "the FIB-4 derivation paper assessed predictive performance against biopsy-proven fibrosis"). The linter (below) treats `predict*` followed within five tokens by a disease noun, "risk," "future," "outcome," "mortality," or any input-variable name as a violation.

**Risk-band wording template (per score, per band) lives in `configs/wording.yaml`:**

```yaml
fib4:
  low:           "Low likelihood of advanced liver fibrosis on this screen."
  indeterminate: "Indeterminate result on liver fibrosis screen — consider follow-up testing per AASLD 2023 stepwise pathway."
  high:          "High-risk band on liver fibrosis screen. Discuss with a clinician for confirmatory testing (VCTE or ELF)."

cha2ds2vasc:
  low:           "Within lower stroke-risk band among people with documented atrial fibrillation."
  indeterminate: "Within intermediate stroke-risk band among people with documented atrial fibrillation. Discuss with a clinician."
  high:          "Within higher stroke-risk band among people with documented atrial fibrillation. Discuss with a clinician."
  # NOTE: no "anticoagulation recommended" anywhere — §3.6 / commitments_log Tier 1 fix.
```

**Linter (`tests/linguistics/test_forbidden_verbs.py`):** at CI time, walks `configs/wording.yaml`, all `*.json` configs, all string literals returned from public functions in `src/healthscore/` (via AST inspection of return values and public function names), and the `wording` field of every `ScoreResult` produced by the regression test suite. Fails on any forbidden lemma. Exception list is itself version-controlled.

**Disclaimer.** Every `AggregationOutput` carries the §5.3 baseline disclaimer string in a `disclaimer` field (TBD on `AggregationOutput` — Claude Code to add). I/O layer is responsible for surfacing it; core is responsible for guaranteeing the field is populated.

---

## 9. Error handling

Three return modes, by severity, applied consistently:

| Condition | Behaviour | Audit log |
|---|---|---|
| Required input absent | `ScoreResult(status=MISSING_INPUT, reason="missing:<field>", raw_value=None, normalised_q=None, wording=None)`. Score skipped in aggregation; cluster weights renormalise. | INFO |
| Input present but outside `physio_min/max` | Same as MISSING_INPUT but `status=OUT_OF_RANGE`, `reason="out_of_range:<field>=<value>"`. Never silently clamp. | WARN |
| Gate-check fails | `status=GATED`, `gate_failures=(<fields>,)`, `wording=None`. Score never computed. | INFO |
| Normalisation produces `q < 0` or `q > 1` after clamp | Should be impossible by construction; if it happens, `status=NORMALISATION_BREAKDOWN`, `reason="anchor_inversion:<score_id>"`, score skipped. | ERROR |
| ε floor activated (`q < ε`) | `epsilon_applied=True`, score continues normally with `q := ε`. | INFO |
| Inactive instrument (per §7) | `status=UNAVAILABLE`. | INFO at startup, not per call |
| Engine-level config invalid (weights don't sum to 1, anchors out of order, missing PMID) | Raise `ConfigValidationError` at startup. **Engine refuses to start.** | ERROR |
| Engine-level dependency conflict (two scores claim same `score_id`) | Raise `RegistryConflictError` at startup. | ERROR |
| Aggregation receives zero valid inputs for an organ | `OrganScore.spec_a_value = OrganScore.spec_b_value = None`; domain aggregation skips this organ and renormalises. | WARN |
| Aggregation receives zero valid organs for a domain | `DomainScore.spec_a_value = DomainScore.spec_b_value = None`. | WARN |

**What never happens:**

- Silent type coercion. Inputs that fail pydantic validation raise `InputValidationError` at the I/O boundary, before the core sees them.
- Silent clamping. Out-of-range values are reported, not clipped.
- Default values for missing inputs. There is no "assume mean" path.
- Exceptions raised inside the scoring core. Errors are values (`ScoreResult.status`), not exceptions, except for engine-startup config errors.

**Exception classes (`src/healthscore/errors.py`):**

```python
class HealthScoreError(Exception): ...
class ConfigValidationError(HealthScoreError): ...
class RegistryConflictError(HealthScoreError): ...
class InputValidationError(HealthScoreError): ...   # raised by I/O layer only
```

The core never raises these on a per-computation call. The I/O layer may raise `InputValidationError` if a payload fails pydantic validation before it reaches `engine.compute()`.

---

## 10. Test framework

**Tooling:** `pytest` + `pytest-cov` + `hypothesis` + `pytest-snapshot`. CI runs `pytest --cov=src/healthscore --cov-report=term-missing --cov-fail-under=95`.

**Coverage targets:** `aggregate/*`, `normalize.py`, `gates.py`, `instruments.py`, `wording.py` — 100% line + branch. `redflags.py` — 100% line. `scores/*` — ≥ 95% line per file. `healthscore_io/*` — ≥ 90% line.

**Test categories:**

- **Unit:** every score, every gate, every wording template. One file per source file.
- **Property-based (hypothesis):** invariants — geometric mean ≤ arithmetic mean; output ∈ [0, 100]; ε activation never increases the score; renormalising weights after a missing input preserves sum = 1; idempotence (same input + same config = same output).
- **Integration:** full `engine.compute()` with fixture payloads (healthy, mid-band, high-risk, gated CHA₂DS₂-VASc, ε-activated edge case, fallback-instrument run).
- **Regression — §1.7 worked liver example, frozen golden test:**

```python
# tests/regression/test_liver_worked_example.py
def test_liver_worked_example_organ_score():
    """
    Methodology §1.7 worked example.
    Inputs: FIB-4=2.0, ALBI=-2.5, aMAP=55, FLI=70 (NFS/APRI/HSI as confirmatory only).
    Weights: FIB-4 0.40, ALBI 0.20, aMAP 0.20, FLI 0.20.

    Per the constructed-midpoint rule (§4): FIB-4 indeterminate anchor (1.985)
    is `constructed_midpoint`, so interpolation is two-anchor PWL between
    1.30/q=1.0 and 2.67/q=0.0. Same applies to other scores whose indeterminate
    anchors are constructed.

    Expected normalised q values (per §1.7):
        FIB-4 = 0.49 (two-anchor PWL: 1 - (2.0 - 1.30)/(2.67 - 1.30))
        ALBI  = 0.40
        aMAP  = 0.50
        FLI   = 0.20
    Expected organ score (Spec A and Spec B at organ level): ≈ 39.5 (±0.5 tolerance).
    """
    out = engine.compute(load_fixture("liver_worked_example.json"))
    liver = next(o for d in out.domains for o in d.organs if o.organ_id == "liver")
    assert 39.0 <= liver.spec_a_value <= 40.0
    assert 39.0 <= liver.spec_b_value <= 40.0
    assert abs(liver.spec_a_value - liver.spec_b_value) < 0.01
```

This test fails on any silent change to FIB-4 anchors, ALBI anchors, aMAP anchors, FLI anchors, the geometric mean implementation, the ε floor, or the weight defaults. It is the canary.

- **Linguistics:** the §8 forbidden-verb linter; runs in CI.
- **Audit-log shape:** snapshot tests on the JSON-serialised audit log for canonical fixtures. A change to the audit schema must be a deliberate snapshot update, not silent.

**Mutation testing (`mutmut`):** target ≥ 80% mutation kill rate on `aggregate/*` and `normalize.py`. Run weekly in CI, not per PR.

**No network in tests.** No file system writes outside `tmp_path`. No `time.time()` in core code — caller passes timestamps in.

---

## 11. Audit logging

Every call to `engine.compute()` emits **one** structured JSON object to the audit channel before returning. The audit channel is injected at engine construction (`AuditSink` protocol); the I/O layer wires it to durable storage. The core never opens files, sockets, or stdout.

**Schema (illustrative — full panel is per-score; trimmed here for brevity):**

```json
{
  "schema_version": "1.0.0",
  "run_id": "01HZ…ULID",
  "config_hash": "sha256:…",
  "timestamp_utc": "2026-05-04T12:34:56Z",
  "locale": "en",
  "population": "uae_emirati",
  "active_instruments": { "cognitive": "moca", "osa": "stop_bang" },
  "alpha_used": 0.50,
  "epsilon_used": 0.01,
  "overrides_applied": {},
  "score_eval_order": ["fib4", "albi", "fli", "amap", "egfr", "kfre", "cha2ds2vasc", "..."],
  "scores": [
    {
      "score_id": "fib4", "status": "ok",
      "raw_inputs": { "ast": 31, "alt": 36, "platelets": 258, "age": 43 },
      "raw_value": 0.86,
      "anchors_used": [1.30, 1.985, 2.67],
      "anchor_sources": ["published", "constructed_midpoint", "published"],
      "interpolation_mode": "two_anchor_pwl",
      "normalised_q": 1.00, "epsilon_applied": false, "risk_band": "low",
      "gate_failures": [], "gate_evaluation_trace": [],
      "active_instrument": null, "red_flag_triggered": false,
      "pmid_primary": "16729309"
    },
    {
      "score_id": "amap", "status": "ok",
      "raw_inputs": { "age": 43, "sex": "female", "albumin": 4.2, "bilirubin": 0.7, "platelets": 258, "chronic_liver_disease_status": null },
      "gate_evaluation_trace": [
        "any_of:start",
        "leaf:cld_not_documented:skip",
        "all_of:start",
        "leaf:fib4_unavailable_or_low:pass",
        "leaf:fli_unavailable_or_low:pass",
        "all_of:pass",
        "any_of:pass"
      ],
      "raw_value": 55, "anchor_sources": ["published","constructed_midpoint","published"],
      "interpolation_mode": "two_anchor_pwl",
      "normalised_q": 0.50, "risk_band": "indeterminate",
      "gate_failures": [], "red_flag_triggered": false
    },
    {
      "score_id": "cha2ds2vasc", "status": "gated",
      "raw_inputs": { "age": 43, "sex": "female", "atrial_fibrillation_status": null },
      "gate_evaluation_trace": ["leaf:af_not_documented:fail"],
      "gate_failures": ["af_not_documented"],
      "raw_value": null, "normalised_q": null, "red_flag_triggered": false
    }
  ],
  "organs": [
    { "organ_id": "liver", "domain_id": "heart_metab",
      "spec_a": 39.5, "spec_b": 39.5,
      "weights_used": { "fib4": 0.40, "albi": 0.20, "amap": 0.20, "fli": 0.20 },
      "epsilon_activations": [], "weight_renormalisations": [] }
  ],
  "domains": [
    { "domain_id": "heart_metab", "spec_a": 52.1, "spec_b": 51.8,
      "disagreement": 0.3, "disagreement_flag": false }
  ],
  "red_flags": [
    { "score_id": "lpa", "severity": "attention", "threshold_label": "Lp(a) ≥ 50 mg/dL", "actual_value": 70 }
  ]
}
```

**Required fields per computation, enumerated:**

- run_id, config_hash, timestamp, locale, population
- α and ε actually used; overrides applied (§12)
- score_eval_order — the topological sort the engine used (§6)
- For every score in the panel: score_id, status, raw_inputs (redaction policy is I/O layer's concern), raw_value, anchors_used, anchor_sources, interpolation_mode, normalised_q, epsilon_applied, risk_band, gate_failures, gate_evaluation_trace, active_instrument, red_flag_triggered
- For every organ: spec_a, spec_b, weights actually used after renormalisation, epsilon_activations, weight_renormalisations (which scores dropped out and why)
- For every domain: spec_a, spec_b, disagreement, disagreement_flag
- All red flags

**Retention.** The core has no opinion on retention. The I/O layer's `AuditSink` is responsible for durability, retention, redaction, and PII handling. The core's contract: emit-once, structured, deterministic given inputs.

**Determinism.** Given the same `(inputs, config, instruments_yaml)`, the audit log is byte-identical except for `run_id` and `timestamp_utc`, both passed in by the caller. This is what makes the log reproducible by the harness (§12).

---

## 12. Sobol perturbation harness — the seam

The harness lives in `harness/`, imports `src/healthscore/`, never the inverse. Per §4.5, the harness perturbs:

1. Score weights *w* (Dirichlet around nominal)
2. Domain compensability α (U(0.3, 0.7))
3. Normalisation choice {distance-to-cutoff, min–max, ordinal-ranked}
4. Aggregation {weighted geometric, weighted arithmetic, partial-min, OWA}
5. Indicator inclusion (leave-one-out)
6. ε floor (∈ {0.005, 0.01, 0.02, 0.05})
7. Cohort bootstrap (n=1,000)

The architecture exposes these without core modification through one mechanism: `engine.compute()` accepts an optional `overrides: AggregationOverrides` argument.

```python
class AggregationOverrides(BaseModel):
    """All Sobol-perturbable parameters, optional. None means use config default."""
    score_weights: Mapping[str, Mapping[str, float]] | None = None   # organ_id → score_id → weight
    organ_weights: Mapping[str, Mapping[str, float]] | None = None   # domain_id → organ_id → weight
    alpha: float | None = None
    epsilon: float | None = None
    epsilon_per_score: Mapping[str, float] | None = None
    normalisation: Literal["distance_to_cutoff", "min_max", "ordinal_ranked"] | None = None
    aggregation: Literal["weighted_geometric", "weighted_arithmetic", "partial_min", "owa"] | None = None
    score_inclusion: Mapping[str, bool] | None = None     # score_id → included (leave-one-out)

def engine.compute(
    inputs: Mapping[str, ScoreInput],
    config: ResolvedConfig,
    *,
    overrides: AggregationOverrides | None = None,
    audit_sink: AuditSink,
) -> AggregationOutput: ...
```

**Rules the seam enforces:**

- Overrides do not mutate config; they shadow it for the call.
- Every override that fires is recorded in the audit log under `overrides_applied`, by name and value. A Sobol run is fully reconstructable from logs.
- Normalisation and aggregation alternatives ({min–max, ordinal} and {arithmetic, partial-min, OWA}) are implemented in `aggregate/spec_a.py` and `aggregate/spec_b.py` as named branches selected by `overrides.aggregation`. They are not pluggable strategy classes — the four named alternatives in §4.5 are exhaustive and frozen.
- Score-inclusion overrides flow through the same skip/renormalise path as missing inputs (§5, §9). Leave-one-out is not a special case in the core.
- The harness sets `run_id` per draw and writes audit logs to a separate sink. Rank-stability and Sobol indices are computed offline from the log corpus.

**What the harness does NOT get to do:**

- Modify anchors, PMIDs, gate requirements, instrument mappings, or wording templates. Anchor uncertainty is out of scope per §4.5; if added later it goes through this same overrides interface, not config mutation.
- Bypass gates. A perturbed run with `cha2ds2vasc` weighted heavily still gates on `atrial_fibrillation_status`. This is the safety property the gate-check pattern is enforcing.
- Disable the forbidden-verb linter. Wording templates do not vary across perturbations.

This is the boundary that makes the validation programme in §4.5 / §4.6 executable without a single line change in the scoring core when the harness is added.

---

## Appendix A — implementation order for Claude Code

Anchored to `commitments_log.md` 4 May 2026 entry "Source-data panel audit committed" (Tier structure) and outstanding action item #8 ("ship Tier 1 + Tier 2 panel fixes; verify CHA₂DS₂-VASc gating in running app before any further validation work").

**Phase 0 — scaffolding:** `types.py`, `enums.py`, `errors.py`; then `normalize.py` + tests (covering §1.7 anchor arithmetic); then `aggregate/common.py`, `spec_a.py`, `spec_b.py` + tests including the §1.7 organ-score regression (target ≈ 39.5 ± 0.5).

**Phase 1 — Tier 1 (clinical-safety blocker; must ship and be verified in the running app before Phase 2):** `gates.py` with full recursive `GatePredicate` type and leaf evaluation (`all_of` / `any_of` combinators implemented but no compound gates wired up yet); `wording.py` + §8 forbidden-verb linter; `configs/scores/cha2ds2vasc.json` with leaf-only gate (`atrial_fibrillation_status equals true`) and risk-band wording only (no "anticoagulation recommended"). Verify end-to-end: a 43-year-old female with `atrial_fibrillation_status: null` returns `ScoreResult(status=GATED, wording=None, gate_failures=("af_not_documented",), gate_evaluation_trace=("leaf:af_not_documented:fail",))`.

**Phase 2 — Tier 2 (PMID replacements):** `configs/scores/hb_rdw.json` (`pmid_primary: "19880817"` Patel 2010); `qfracture_hip.json` and `qfracture_major.json` (`"22619194"` Hippisley-Cox & Coupland 2012); `phenoage.json` (`"30596641"` Liu 2018, clinical-chemistry — **not** DNAm `29676998`). Snapshot test: no config in `configs/scores/` carries the four superseded PMIDs (`20921437`, `22941793`, or `29676998` in the panel's clinical-chemistry PhenoAge slot).

**Phase 3 — instruments, dependency-ordered scoring, and remaining scores:** add the engine-startup topological sort + cycle-detection over `score_results.<id>` cross-references in gate trees; `redflags.py`; `instruments.py` + tests (primary-vs-fallback for cognitive: MoCA/MMSE, OSA: STOP-BANG/NoSAS); then `scores/*` in order: liver four (FIB-4, ALBI, **FLI before aMAP** — aMAP's gate depends on FIB-4 and FLI per §6), CVD anchor scores (PREVENT, ApoB, Lp(a), regional alternates), metabolic, kidney (eGFR before KFRE — KFRE's gate depends on eGFR), brain, bone/muscle, system-wide, gut. aMAP and KFRE configs land in this phase with their committed gates wired.

**Phase 4 — orchestration and audit:** `audit.py` + snapshot tests; `engine.py` + integration tests with canonical fixtures (healthy, mid-band, high-risk, gated CHA₂DS₂-VASc, ε-activated, fallback-instrument); `AggregationOverrides` + harness seam tests (§12).

**Phase 5 — Tier 3 (citation hygiene upgrades; engineering-bandwidth dependent per commitments_log; non-blocking):** apply the suboptimal-citation upgrades from `score_panel_pmid_audit_log.md` (FIB-4 → 16729309; APRI → 12883497; AIP → 11738396; TyG → 19067533; SII → 25271081; KFRE → 21482743; Thyroid primary patterns → 23246686). Config-only changes.

**Phase 6 — Tier 4 (CHA₂DS₂-VASc calculation bug; blocked behind Phase 1 per commitments_log):** audit and fix the calculation logic where SBP 134 mmHg is scored as hypertension (correct cutoff is ≥ 140/90 or on treatment).

**Phase 7 — I/O layer:** `healthscore_io/` last. Core ships before I/O.

## Appendix B — implementation-level details Claude Code may choose

ULID library; JSON serialisation library (`json` sufficient, `orjson` acceptable in I/O); `AuditSink` logging-framework wiring; whether `ResolvedConfig` is frozen-at-startup (recommended) or rebuilt per request; audit-log file naming.

Everything else above is a decision, not a suggestion.
