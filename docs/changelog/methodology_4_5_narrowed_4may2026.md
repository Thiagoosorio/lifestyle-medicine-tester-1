# Methodology §4.5 Sobol Perturbation — Narrowed Scope (4 May 2026)

> **Patch superseded by methodology master commit; retained for audit history.**
> The §4.5 narrowing described below was folded into the methodology master at
> `docs/merged_methodology_organ_composite_scores.md` in commit `c8d5678` (4 May 2026).
> This file is preserved in `docs/changelog/` as a self-contained audit record of
> the Phase 6 distribution-finding → §4.5 narrowing decision chain. Do not apply
> the patch a second time — the master already carries the narrowed text.

*Patch-document for `merged_methodology_organ_composite_scores.md` §4.5. Apply by replacing the existing "Pre-registered Monte Carlo robustness protocol" block in §4.5 with the narrowed protocol below. The change is committed in parallel with the OSF pre-registration draft (`docs/osf_prereg_draft.md`); the pre-registration's Sobol perturbation scope must match the methodology document's pre-registered protocol verbatim.*

---

## Why §4.5 narrows

The original §4.5 listed seven uncertainty dimensions, including aggregation perturbations across `weighted-arithmetic`, `partial-min`, and `OWA` alternatives in addition to the parallel Spec A (α-blend) / Spec B (geometric + flag) primaries.

Two findings during the Phase 6 review prompted the narrowing:

1. **Spec A vs Spec B paired-spec convergence (H5, ρ ≥ 0.90) already provides the methodologically substantive aggregation-perturbation result.** The two pre-registered specifications differ in compensability behaviour (α-blend with partial-min vs pure geometric + non-compensatory red-flag layer), and convergence between them under the same per-organ weighted-geometric is the test that matters for the OECD/JRC §1.5 multi-modelling stance. Adding `weighted-arithmetic`, `partial-min`, and `OWA` perturbations marginally strengthens the result without changing a passing launch decision into a failing one.

2. **The aggregation alternatives are not built and not in scope for validation execution.** `engine.compute()` raises `NotImplementedError` on `aggregation in ("weighted_arithmetic", "partial_min", "owa")` (architecture_spec §12; Phase 6 loud-failure decision). Pre-registering them would commit to building them before validation runs — an implementation prerequisite that adds effort without changing the launch-decision conclusion.

The narrowing keeps perturbation across the dimensions where the methodological commitment is strongest (weights, the Spec A blend parameter α, normalisation choice, ε floor, indicator inclusion, cohort bootstrap) and removes the dimensions where the marginal information value does not justify the implementation effort. The aggregation alternatives remain available for future research use; if a future pre-registration finds value in them, that pre-registration can re-include them.

---

## Replacement §4.5 block (paste verbatim)

> ### 4.5 Pre-registered Monte Carlo robustness protocol
>
> Pre-register on OSF **before** any cohort touches the model.
>
> ```
> Inputs (fixed):
>   - validated score panel (after redundancy reduction per §1.5)
>   - clinical cutoff mappings (three anchor points per score; §1.2 anchor-source rule)
>   - construct clusters
>   - both Spec A (α-blend) and Spec B (geometric + flag) pre-registered as parallel primaries
>
> Uncertainty dimensions (six; aggregation alternatives narrowed out 4 May 2026):
>   1. Weight uncertainty:
>        Dirichlet(α_concentration · w_nominal); α_concentration ∈ {2, 10}.
>   2. Spec A blend parameter α:
>        α ~ Uniform(0.3, 0.7).
>   3. Normalisation uncertainty:
>        primary: distance-to-cutoff
>        sensitivity: z-score, min-max, ordinal-ranked
>   4. Indicator inclusion:
>        leave-one-score-out and leave-one-cluster-out.
>   5. ε floor uncertainty:
>        ε ∈ {0.005, 0.01, 0.02, 0.05}
>   6. Cohort uncertainty:
>        bootstrap n=1,000 individuals per cohort; replicate across cohorts.
>
> Aggregation perturbation deliberately narrowed (4 May 2026):
>   - weighted-arithmetic, partial-min, OWA aggregations are NOT pre-registered.
>   - Spec A vs Spec B paired-spec convergence (Spearman ρ ≥ 0.90 per domain)
>     is the methodologically substantive aggregation-perturbation result.
>   - architecture_spec.md §12 / engine.compute() raise NotImplementedError on
>     these branches; they remain available for future research use but are
>     out of scope for the pre-registered validation.
>
> Simulation:
>   - 10,000 Monte Carlo draws minimum per organ/domain
>   - Bootstrap 1,000 resamples for performance metrics
>
> Reporting:
>   - Median, IQR, 95% simulation interval per score
>   - Spearman ρ rank correlation between user composite under nominal and
>     perturbed configurations
>   - First-order Sobol indices for each design choice (which choice drives
>     variance in user rank?)
>   - Probability of crossing clinical-action thresholds
>   - Spec A vs Spec B agreement: paired Spearman ρ per domain;
>     flag any user where |Spec_A − Spec_B| > 5 points
>   - Variance attribution by weights, normalisation, indicator inclusion,
>     ε, α (the six pre-registered perturbation dimensions)
> ```
>
> Per Paruolo / Saisana / Saltelli 2013 ("Voodoo or Science?"): every release
> reports first-order Sobol main-effect contributions alongside nominal weights,
> never nominal weights alone.

---

## Cross-references

- **Pre-registration:** `docs/osf_prereg_draft.md` §7 (Sobol perturbation protocol — narrowed) carries the matching narrowed perturbation set. The pre-registration's perturbation scope must equal the methodology's for the OSF submission to be coherent.
- **Architecture spec:** `docs/architecture_spec.md` §12 (Sobol harness — the seam) describes the `AggregationOverrides` type. The `aggregation in ("weighted_arithmetic", "partial_min", "owa")` branches raise `NotImplementedError` in `engine.compute()`; this is the loud-failure pattern that surfaced the implementation-vs-pre-registration question.
- **Commitments log:** `commitments_log.md` Phase 6 implementation entry, Engineering decision #3 ("`NotImplementedError` for unbuilt aggregation branches is the right pattern") and the Option C reweighting decision both anchor the narrowing.

---

*This patch document is a transitional artifact. Once the methodology master is checked into the repo (mirroring the architecture_spec.md precedent, commit 2763955), this patch is folded into the master at §4.5 and this document is retired or moved to a `docs/changelog/` archive.*
