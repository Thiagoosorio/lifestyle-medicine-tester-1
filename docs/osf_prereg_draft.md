# OSF Pre-Registration: Organ-Level Composite Scoring Engine — Validation Plan

*Draft for review prior to OSF submission. Format: AsPredicted-style template. Source documents: `merged_methodology_organ_composite_scores.md` (methodology), `docs/architecture_spec.md` (architecture), `commitments_log.md` (decision history including all errata, Phase 0–6 acceptance gates, Option B → Option C reweighting).*

---

## 0. Reproducibility anchor (codebase commitment)

This pre-registration commits to validating the scoring engine **at a specific codebase state**. The state is identified by `config_hash`, the SHA-256 of a canonical-serialised concatenation of all per-score JSON configs and `configs/domains.yaml` as defined in `src/healthscore/engine.py::compute_config_hash`.

| Anchor | Value |
|---|---|
| `config_hash` | `sha256:5fa815d214f1c1a8e8a79c24a4f33657a47769c05493190879ecaed831deb1dc` |
| Repository commit | `6b047dc` (Option C reweighting; PhenoAge `composite_member: false`) |
| Number of score configs | 35 |
| Number of domains | 5 |
| Methodology document version | merged_methodology_organ_composite_scores.md as of 4 May 2026 |

**Replay rule.** Any rerun against a different `config_hash` invalidates this pre-registration. A new pre-registration is required if any score config, weight, anchor, gate, instrument-slot resolution, or domain-weight changes.

**Determinism.** `engine.compute()` is deterministic given `(raw_inputs, config_hash, instruments.yaml)`; `run_id` and `timestamp_utc` are the only fields permitted to vary across reruns.

---

## 1. Hypotheses

The composite scoring engine produces calibrated, discriminating, rank-stable risk-stratification across five health domains for the deployed cohort. We test:

**H1 (discrimination).** Both the Spec A α-blend and Spec B weighted-geometric domain composites discriminate the domain-specific endpoint with Harrell's C ≥ 0.02 above the best single guideline-score comparator for that domain's primary endpoint, as enumerated in §6 comparator #2, with non-overlapping confidence intervals, in **both** the UAE primary cohort and the UK Biobank methodology benchmark.

**H2 (calibration).** Calibration slope ∈ [0.85, 1.15] and calibration-in-the-large within ±10% for each domain composite, in each cohort.

**H3 (clinical net benefit).** Decision-curve net benefit is positive at clinically reasonable thresholds (per §4.6) for at least one endpoint per domain, in each cohort.

**H4 (Sobol rank stability).** Spearman ρ ≥ 0.95 between user composite ranks under nominal config and ranks under Sobol-perturbed config (per §4.5 perturbation protocol).

**H5 (Spec A vs Spec B convergence).** Spearman ρ ≥ 0.90 between paired user scores under Spec A and Spec B, per domain. If ρ < 0.90, no single headline is published; both specs are surfaced to users with the §1.3 "scores point in different directions" framing.

**H6 (UAE-cohort calibration parity).** Per methodology §4.4 decision rule: if UAE-cohort Harrell's C is more than 0.05 below UK Biobank C for any domain composite, the model is **not deployment-ready in the UAE without local recalibration**. This is a launch-blocker.

**Scope of validation: organ + domain levels only.** This pre-registration validates at organ + domain level only. Methodology §4.1 listed three composite levels (organ → domain → headline) as a possibility, but no headline-aggregation rule has been committed in the methodology, no headline-weights table exists, and the codebase does not implement a headline aggregator. Pre-registering against a non-existent function would commit to building it before validation; we deliberately scope the pre-registration to what the engine actually computes. A headline aggregator is left for a future pre-registration if a UX requirement materialises.

---

## 2. Specifications pre-registered (parallel primaries, not primary-vs-sensitivity)

Per OECD/JRC §1.5 multi-modelling guidance, both specifications are pre-registered as **parallel primary** specifications. This is the user-visible sensitivity analysis, not a hedge.

### Spec A — α-blend (committed default α = 0.5)

```
OrganScore_A = 100 × exp(Σ wᵢ × ln(max(qᵢ, ε)))
DomainScore_A = α × min(OrganScore_j) + (1 − α) × Π OrganScore_j^(w_j)
```

α is Sobol-perturbed under Uniform(0.3, 0.7) per §4.5.

### Spec B — geometric + non-compensatory red-flag layer

```
OrganScore_B = 100 × exp(Σ wᵢ × ln(max(qᵢ, ε)))
DomainScore_B = 100 × exp(Σ w_j × ln(OrganScore_j / 100))
```

Red flags maintained as a separate non-compensatory display layer; never folded into the score.

### Composite-member configuration (System-Wide §3.7 Option C)

PhenoAge is **non-composite display** (`composite_member: false`) per the Phase 6 distribution finding (100% clamp activation; methodology §3.7). System-Wide composite weights:

| Component | Weight | Tier |
|---|---:|:---:|
| Frailty (FRAIL scale) | 0.35 | A |
| Hb + RDW Mortality Risk | 0.25 | B |
| OSA (STOP-BANG primary, NoSAS fallback) | 0.25 | B |
| SII | 0.15 | B |
| PhenoAge | — *(non-composite display only)* | B |

PhenoAge remains a **published comparator** (per §4.3 comparator #5) but does not contribute to the composite. The audit log records `composite_member: false` so forensic replay distinguishes "computed but excluded by policy" from "not computed."

All other organ-panel composite weights are encoded in `configs/domains.yaml` and locked by `config_hash`.

---

## 3. Instrument-slot substitution rules (pre-registered, not post-hoc)

Per methodology §5.6, two instrument slots have committed primary + fallback pairs. Both substitution rules are pre-registered as **conditional substitutions**, not as analyst-discretion choices made during validation:

| Slot | Primary | Fallback | Pre-registered substitution rule |
|---|---|---|---|
| `cognitive` | MoCA (PMID 15817019) | MMSE (PMID 1202204) | Substitute MMSE for MoCA **iff** MoCA Cognition Inc. commercial licensing is unavailable or uneconomic in the deployment jurisdiction at validation time. Substitution is documented in `configs/instruments.yaml::cognitive.active`; the active instrument propagates through `ScoreResult.active_instrument` and is recorded in every audit log entry. |
| `osa` | STOP-BANG (PMID 18431116) | NoSAS (PMID 27306675) | Substitute NoSAS for STOP-BANG **iff** UHN/Frances Chung commercial licensing is unavailable or uneconomic. Substitution mechanism and audit recording identical to the cognitive slot. |

**Fallback methodology trade-off (pre-registered, not decided during validation):**

- **MMSE in place of MoCA:** lower MCI sensitivity (~80% vs ~90%); known education/culture bias amplified in UAE/MENA users. The `ScoreResult.confidence` field is forced to `low` and `reason = "fallback_active:moca->>mmse"` per architecture_spec §7.
- **NoSAS in place of STOP-BANG:** loses the Alhouqani 2015 UAE direct-validation anchor (PMID 25758298). Same confidence demotion + audit reason mechanism.

Pre-registration covers **both** MoCA-active and MMSE-active branches. Whichever is active at validation time is the version that ships; the alternative is documented as the pre-registered fallback chain, not as a robustness check.

---

## 4. Validation cohorts (priority and decision rule)

Per methodology §4.4:

| Priority | Cohort | Use |
|---|---|---|
| **Primary** | UAE Healthy Future Study + Tawam Hospital cohort (Al-Shamsi 2025) + Qatar Biobank | Local calibration, UAE-specific cutoff verification, equity calibration. Primary because the user base is Emirati / GCC. |
| **Methodology benchmark** | UK Biobank (n ≈ 500,000) | Methodology benchmark, **not primary**, because its 95%+ white European composition is not representative of the UAE deployed user base. |
| Secondary validation | NHANES + linked mortality (US) | PhenoAge anchor (comparator #5); mortality linkage. |
| Multi-ethnic validation | All of Us (US) + MESA (CVD/CAC) | Diversity replication. |
| European replication | Rotterdam Study, Whitehall II | Aging / dementia / cardiometabolic replication. |

**Cohort filter criteria (exclusions; applied before any score is computed):**

- Age outside score's `applicable_population.min_age` ÷ `max_age` (per-config).
- Pregnancy.
- Acute illness within 14 days of biomarker draw (excludes inflammatory-marker confounding for SII / NLR / hs-CRP).
- Score-specific exclusions encoded in each `applicable_population.exclusions` field (e.g. KFRE: `["acute_kidney_injury", "pregnancy", "kidney_transplant"]`).
- Type-1 diabetes for HOMA-IR / METS-IR (per config).
- Active malignancy + chemotherapy for SII (per config).

**Outcome ascertainment** is by cohort registry / linked mortality file as specified in each cohort's data dictionary; harmonised to the per-domain endpoints listed in §5 below.

**Decision rule on UAE-cohort calibration (methodology §4.4):** if UAE Harrell's C is more than 0.05 below UK Biobank C for any domain composite, the model is not deployment-ready in the UAE without local recalibration. This rule is pre-registered: failure triggers a recalibration cycle, not a publication.

---

## 5. Outcomes (one primary + secondaries per composite level)

Per methodology §4.1:

| Composite | Primary endpoint | Secondary endpoints |
|---|---|---|
| **Liver organ** | Advanced fibrosis (VCTE / MRE / ELF confirmed) | Cirrhosis, decompensation, HCC, liver mortality |
| **Kidney organ** | 40% eGFR decline | KRT initiation, CKD hospitalisation, mortality |
| **CVD organ** | MACE | ASCVD, HF hospitalisation, CVD mortality |
| **Metabolic organ** | Incident T2DM | Insulin therapy initiation, cardiometabolic hospitalisation |
| **Brain Health domain** | Incident dementia / MCI | Depression / anxiety diagnosis, sleep apnoea confirmation |
| **Muscle & Bones domain** | Fragility fracture | Falls, sarcopenia confirmation, disability |
| **System-Wide domain** | All-cause mortality | Hospitalisation, frailty progression |

Endpoints are time-to-event; censoring at last follow-up or competing-risk death (where applicable). Cox-regression / Harrell's C with Uno's C as a robustness check.

---

## 6. Comparators (per methodology §4.3 — every composite must beat these)

Each domain composite is benchmarked against the eight comparators below. The launch threshold (H1) requires the composite to beat the **best single guideline score per endpoint** (#2) by Harrell's C ≥ 0.02 with non-overlapping CIs.

1. **Equal-weighted arithmetic mean** of the same normalised inputs (trivial baseline).
2. **Best single guideline score per endpoint** (one per composite; enumerated verbatim so the §8 condition #1 launch decision has no analyst-discretion gap at validation time):
    - **Liver organ** (advanced fibrosis): **FIB-4 alone** (Sterling 2006, PMID 16729309).
    - **Kidney organ** (40% eGFR decline): **eGFR alone** (CKD-EPI 2021, Inker 2021, PMID 34554658).
    - **CVD organ** (MACE): **AHA PREVENT alone** (Khan 2024, PMID 37947085).
    - **Metabolic organ** (incident T2DM): **FINDRISC alone** (Lindström & Tuomilehto 2003, PMID 12610029); Tier A; methodology §3.1.
    - **Brain Health domain** (incident dementia / MCI): **CAIDE alone** for dementia; **PHQ-9 alone** for the depression component.
    - **Muscle & Bones domain** (fragility fracture): **QFracture alone** (Hippisley-Cox & Coupland 2012, PMID 22619194; Tier 2 PMID-corrected per `pmid_verification_log.md`).
    - **System-Wide domain** (all-cause mortality): **Fried Frailty Phenotype alone** (Fried 2001, PMID 11253156); **STOP-BANG alone** is the OSA-component anchor.
3. **Evidence-tier-only weighting** (Tier A = 1.0; Tier B = 0.5; Tier C = 0.25; Tier D = 0.0; renormalised).
4. **Outcome-proximity-only weighting.**
5. **PhenoAge alone** (Liu 2018 PMID 30596641, clinical-chemistry form). PhenoAge is `composite_member: false` per Option C, but is retained here as a **published comparator** representing the canonical "biological age" benchmark.
6. **Frailty index (deficit accumulation, Rockwood form)** — System-Wide and headline.
7. **Clift et al. 2021 C-Score smartphone composite** (Clift AK et al., *JMIR mHealth uHealth* 9(2):e25655; PMID 33591285; PMC7925156; n=420,560 UK Biobank; 4,526,452 person-years; 16,188 deaths; points-based C=0.66, age-adjusted Cox C=0.74). Published anchor for "consumer app composite" performance. *(Note: this comparator was previously misattributed as "Foster 2021" in earlier project drafts; corrected per `pmid_verification_log.md`.)*
8. **Null / age-sex-only model.**

---

## 7. Statistical analysis

Per methodology §4.2:

| Outcome class | Required metrics |
|---|---|
| Time-to-event | Harrell's C / Uno's C; time-dependent AUROC; calibration slope and intercept; Brier score; decision-curve analysis (Vickers & Elkin 2006, *Med Decis Making* 26:565-574). |
| Binary diagnosis | AUROC; PR-AUC where event rare; sens/spec at pre-specified thresholds; calibration. |
| Ordinal severity | Calibration by category; weighted kappa; ordinal C-index. |
| Reclassification | NRI / IDI **only for pre-specified clinically meaningful categories** per Kerr et al. 2014 critique. No analyst-chosen thresholds. |
| Clinical utility | Decision-curve analysis at guideline thresholds. |
| Robustness | Sobol variance-based sensitivity on weights, normalisation, aggregation, ε floor, indicator inclusion. **Rank-stability** (Spearman ρ) reported alongside score-stability per Paruolo / Saisana / Saltelli 2013. |

### Sobol perturbation protocol (narrowed)

Pre-registered; implemented via `AggregationOverrides` per architecture_spec §12. Perturbation dimensions:

1. **Weight uncertainty:** Dirichlet(α_concentration · w_nominal); α_concentration ∈ {2, 10}.
2. **Spec A blend parameter α:** α ~ Uniform(0.3, 0.7).
3. **Normalisation uncertainty:** primary distance-to-cutoff; sensitivity z-score, min-max, ordinal-ranked.
4. **Indicator inclusion:** leave-one-score-out and leave-one-cluster-out.
5. **ε floor:** ε ∈ {0.005, 0.01, 0.02, 0.05}.
6. **Cohort uncertainty:** bootstrap n=1,000 per cohort; replicate across cohorts.

Simulation: ≥ 10,000 Monte Carlo draws per organ / domain. Bootstrap 1,000 resamples for performance metrics.

**Aggregation perturbation deliberately narrowed.** Methodology §4.5 originally listed `weighted-arithmetic`, `partial-min`, and `OWA` as additional aggregation perturbations. These are **not** pre-registered for validation execution. Rationale: Spec A vs Spec B paired-spec convergence (H5, ρ ≥ 0.90) already provides the methodologically substantive aggregation-perturbation result — the two pre-registered specifications differ in compensability behaviour (α-blend vs pure geometric + flag layer) and convergence between them is the test that matters. Additional perturbation across weighted-arithmetic, partial-min, and OWA would marginally strengthen the result but would not change a passing launch decision into a failing one. The harness branches that currently raise `NotImplementedError` in `engine.compute()` are not in scope for validation execution and remain available for future research use. Methodology document §4.5 updated in parallel to match this narrowed perturbation set.

### Multiple-testing adjustment plan (hierarchical)

H1–H3 are tested independently per `(cohort × spec)` cell. The launch decision rule (§8) requires the test to pass in **both** cohorts under **both** specs, so each `(cohort × spec)` cell is treated as its own family for the family-wise error-rate adjustment. There are four cells: `(UAE × Spec A)`, `(UAE × Spec B)`, `(UK Biobank × Spec A)`, `(UK Biobank × Spec B)`.

Within each cell, **Holm-Bonferroni** adjusts across the seven composites (organ-level: liver, kidney, CVD, metabolic; domain-level: Brain, Muscle & Bones, System-Wide). The launch decision (§8) requires every cell to clear its Holm-adjusted threshold for a composite to be publishable; partial-cell failures invalidate the composite for launch.

H4 (rank-stability) and H5 (spec convergence) are not subject to multiple-testing adjustment — they are reproducibility / convergence checks, not inferential hypothesis tests.

### Reporting

Per §4.5: median, IQR, 95% simulation interval per score; first-order Sobol indices for each design choice (which choice drives variance in user rank?); probability of crossing clinical-action thresholds; Spec A vs Spec B agreement Spearman ρ; variance attribution by weights / normalisation / aggregation / indicator inclusion / ε.

### Reporting alongside nominal weights

Per Paruolo / Saisana / Saltelli 2013 ("Voodoo or Science?"): every release reports **first-order Sobol main-effect contributions alongside nominal weights**, never nominal weights alone. This is a binding pre-registration commitment.

---

## 8. Launch decision rule (per methodology §4.6)

A specification is publishable for deployment **only if all five conditions hold**:

| # | Condition |
|---|---|
| 1 | **Discrimination:** Harrell's C ≥ 0.02 above the best single comparator with non-overlapping CIs in **both** the UAE primary cohort **and** the UK Biobank benchmark. |
| 2 | **Calibration:** calibration slope ∈ [0.85, 1.15]; calibration-in-the-large within ±10%. |
| 3 | **Net benefit:** positive in decision-curve analysis at clinically reasonable thresholds for **at least one endpoint per domain**. |
| 4 | **Rank-stability:** Spearman ρ ≥ 0.95 across Sobol perturbation. |
| 5 | **Spec A vs Spec B agreement:** Spearman ρ ≥ 0.90 between paired user scores. If lower, do **not** publish a single headline; display both with the §1.3 disagreement framing. |

If any condition fails for any domain composite, the affected composite is not launched for that domain. Pre-registered remediation: simplify, recalibrate, or remove the affected domain. Publication of a partial set of launched composites is permissible provided each launched composite has cleared all five conditions independently.

---

## 9. Negative-result publication commitment

Per methodology §4.7, this pre-registration carries a **binding negative-result publication commitment**. We commit to publishing the validation results **regardless of outcome**, including:

- All-domain failure (no composite meets the launch decision rule).
- Per-domain failure (subset of composites fails).
- Spec A vs Spec B divergence below ρ = 0.90 (no single headline published).
- UAE / UK Biobank C-statistic divergence above 0.05 (deployment-not-ready finding).
- Sobol rank-instability ρ < 0.95 in any domain.
- Calibration slope outside [0.85, 1.15] in any cohort.

Negative results will be submitted to a peer-reviewed journal that publishes negative findings (e.g. *PLOS ONE*, *F1000Research*, *BMC Cardiovascular Disorders*) within 12 months of validation completion, regardless of whether positive results from the same study are published elsewhere.

This commitment is binding on the principal investigator and is recorded as part of the OSF pre-registration so a third-party audit can verify compliance.

---

## 10. AsPredicted-style summary (paste-ready for OSF intake form)

> **1. Have any data been collected for this study already?**
>
> No, no data have been collected. The composite scoring engine is locked at `config_hash sha256:5fa815d214f1c1a8e8a79c24a4f33657a47769c05493190879ecaed831deb1dc` (repository commit `6b047dc`); validation cohorts are pending data-access agreements (UAE Healthy Future Study, Qatar Biobank, Tawam Hospital cohort).
>
> ---
>
> **2. What's the main question being asked or hypothesis being tested in this study?**
>
> Do the Spec A (α-blend) and Spec B (geometric + flag) per-domain composite scores discriminate, calibrate, and show clinical net benefit for their pre-registered domain endpoints in the UAE primary cohort, with parity (within 0.05 Harrell's C) against the UK Biobank methodology benchmark?
>
> ---
>
> **3. Describe the key dependent variable(s) specifying how they will be measured.**
>
> Per-domain time-to-event endpoints harmonised across cohorts: liver (advanced fibrosis confirmed by VCTE / MRE / ELF); kidney (40% eGFR decline); CVD (MACE); metabolic (incident T2DM); brain (incident dementia / MCI); muscle & bones (fragility fracture); system-wide (all-cause mortality). Ascertained from cohort registries / linked mortality files per each cohort's data dictionary.
>
> ---
>
> **4. How many and which conditions will participants be assigned to?**
>
> Not applicable (observational). Cohort filtering by exclusions (age outside score `applicable_population` range; pregnancy; acute illness within 14 days; per-score exclusions per config) applies before scoring.
>
> ---
>
> **5. Specify exactly which analyses you will conduct to examine the main question/hypothesis.**
>
> H1 (discrimination): Cox-regression Harrell's C / Uno's C per composite; comparator hierarchy per §4.3 (8 comparators including Clift 2021 C-Score). Threshold: ΔC ≥ 0.02 with non-overlapping CI vs best single guideline score, in both UAE and UK Biobank cohorts.
>
> H2 (calibration): calibration slope ∈ [0.85, 1.15]; calibration-in-the-large ±10%.
>
> H3 (net benefit): decision-curve analysis at guideline thresholds.
>
> H4 (rank stability): Sobol perturbation per §4.5; Spearman ρ ≥ 0.95.
>
> H5 (Spec A vs Spec B convergence): paired Spearman ρ ≥ 0.90 per domain.
>
> H6 (UAE-cohort parity): if UAE Harrell's C > 0.05 below UK Biobank C, deployment blocked pending recalibration.
>
> Multiple-testing correction: Holm-Bonferroni across the seven composites for H1–H3.
>
> ---
>
> **6. Describe exactly how outliers will be defined and handled.**
>
> No outlier exclusion. Physiologically implausible inputs are blocked at the per-score `physio_min` / `physio_max` level encoded in each `input_variables` config; values outside these bounds return `ScoreStatus.OUT_OF_RANGE` and are documented in the per-score audit blob. PhenoAge values exceeding ±25 years acceleration are **clamped** at the formula output (config `output_clamp` per Phase 5; activates 100% of the time per Phase 6 distribution check) — clamped values are recorded alongside unclamped values in the audit log so forensic replay can recover both.
>
> ---
>
> **7. How many observations will be collected or what will determine sample size?**
>
> UAE Healthy Future Study: target n ≈ 5,000 subset with the lab panel required by the score configs (full UAEHFS enrolment is larger, n ≈ 20,000+; subset reflects users for whom all eight committed PMID-corrected scores can be computed). Final n at validation time is documented in the cohort-extraction script and surfaced in the audit log. UK Biobank: full cohort (n ≈ 500,000) with the methodology-document age and exclusion filters applied (typically reducing to n ≈ 350,000–400,000). Bootstrap n=1,000 resamples per cohort per metric; ≥ 10,000 Monte Carlo draws per organ / domain in the Sobol harness.
>
> ---
>
> **8. Anything else you would like to pre-register?**
>
> - **Codebase reproducibility anchor:** `config_hash sha256:5fa815d214f1c1a8e8a79c24a4f33657a47769c05493190879ecaed831deb1dc` (repository commit `6b047dc`). Any rerun against a different `config_hash` invalidates this pre-registration.
> - **Two specifications pre-registered as parallel primaries** (Spec A α-blend, Spec B geometric + flag), per OECD/JRC §1.5 multi-modelling guidance.
> - **Licensing-fallback substitution rules pre-registered:** MoCA → MMSE if MoCA Cognition Inc. licensing unavailable; STOP-BANG → NoSAS if UHN/Frances Chung licensing unavailable. Substitutions documented in `configs/instruments.yaml::*.active`; both branches covered by this pre-registration.
> - **System-Wide composite reweighting (Option C, methodology §3.7, 4 May 2026):** Frailty 0.35, Hb+RDW 0.25, OSA 0.25, SII 0.15. PhenoAge `composite_member: false` (research-grade display only) following the Phase 6 distribution check (100% clamp activation).
> - **Wellness positioning:** the engine is positioned as a wellness / general-fitness tool per UAE MOHAP framing, not as Software-as-Medical-Device. No diagnostic / prognostic / treatment-recommendation language is permitted in any user-visible string per `commitments_log.md` "Regulatory positioning and launch jurisdiction." The §5.3 disclaimer appears verbatim on every `AggregationOutput` per Phase 4 acceptance gate.
> - **Negative-result publication commitment.** Binding. See §9.
> - **Audit-log determinism.** Every `engine.compute()` call emits one structured JSON record per architecture_spec §11. Records are reproducible byte-for-byte given identical `(raw_inputs, config_hash, instruments.yaml)`, modulo `run_id` and `timestamp_utc`.
>
> ---

---

## Appendix A — Items intentionally not pre-registered

The following are **not** pre-registered and remain analyst-discretion:

- **UI copy** for Spec A vs Spec B disagreement surfaces (Conv 9 in the conversation queue; runs after lawyer review).
- **Disclaimer wording beyond §5.3 baseline** (Conv 6; deferred to UAE-licensed regulatory counsel).
- **Final per-cohort filter sample size** (depends on data-access agreement specifics).
- **Thresholds for "clinically reasonable" in DCA** (specified per endpoint at validation time using guideline-thresholds where available, e.g. ASCVD 7.5% / 20%; FIB-4 1.30 / 2.67; KFRE 5% / 20%).

These are documented as analyst-discretion to make the boundary between pre-registered and post-hoc explicit.

---

## Appendix B — Source documents at the time of pre-registration

| Document | Repo path | Role |
|---|---|---|
| Methodology | `merged_methodology_organ_composite_scores.md` | The "why" — design rationale, evidence sourcing, redundancy analysis, regulatory positioning. |
| Architecture spec | `docs/architecture_spec.md` | The "what" — type signatures, gate-engine grammar, audit log schema, Sobol harness seam. |
| Commitments log | `commitments_log.md` | Decision history including all four errata, six build phases (Phase 0–6), Option B → Option C reweighting. |
| PMID verification | `pmid_verification_log.md` | Citation hygiene; Foster→Clift correction; PhenoAge PMID 29676998 → 30596641 correction. |
| Source-data audit | `score_panel_pmid_audit_log.md` | Tier 1–4 audit findings; CHA₂DS₂-VASc gating safety issue. |
| Arabic / UAE validation | `arabic_uae_validation_log.md` | Source for §3 panel rows and §5.6 instrument-fallback decisions. |
| Disclaimer pre-legal-review | `disclaimer_draft_pre_legal_review.md` | Pre-launch disclaimer draft awaiting UAE-licensed regulatory counsel review (Conv 6). |

---

*Draft authored by Claude Code on behalf of the principal investigator. Review and refinement of the two `[REVIEWER:]` flags above is expected before OSF submission. Once those are resolved and the document is final, the principal investigator submits to OSF with the supporting documents listed in Appendix B as ancillary attachments.*
