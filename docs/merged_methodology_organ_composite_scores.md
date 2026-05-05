# Evidence-Based Methodology for Organ-Level Composite Scoring in a 5-Domain Health App

*Merged methodology document, prepared May 2026. Synthesises findings from two independent deep-research runs (Claude Research, ChatGPT Deep Research), audited against OECD/JRC 2008, Greco et al. 2019, Paruolo/Saisana/Saltelli 2013, and primary clinical guidelines (AASLD 2023, EASL-EASD-EASO 2024, KDIGO 2024, ESC 2021, AHA 2023 PREVENT). Per OECD/JRC §1.5 multi-modelling recommendation, the document carries two parallel aggregation specifications and reports both as the headline output.*

---

## TL;DR

1. **Run two aggregation specifications in parallel and report both.** Spec A (α-blend: partial-min mixed with weighted geometric, α=0.5, Sobol-perturbed) and Spec B (weighted geometric + separate non-compensatory red-flag layer). Disagreement between them is the user-visible uncertainty; convergence is the headline. This is OECD/JRC §1.5 multi-modelling, not a hedge.
2. **Normalise every score to a 0–1 health metric using distance-to-published-clinical-cutoff**, not population percentiles. Three anchor points (low / indeterminate / high) per score, piecewise linear, capped at [0,1].
3. **Reduce the panel to remove redundancy.** Liver: FIB-4 + ALBI + aMAP + FLI (drop NAFLD-FS, APRI, HSI from the composite; retain as confirmatory display). CVD: one regional 10-year score + ApoB + Lp(a) + one diabetes risk score (drop AIP, remnant cholesterol, non-HDL, TG/HDL from the composite).
4. **Domain taxonomy:** Liver → Heart & Metabolism (MASLD is cardiometabolic by AASLD 2023 / EASL-EASD-EASO 2024 definition). Kidney → Heart & Metabolism (KDIGO 2024 + AHA 2023 CKM). Inflammatory, biological age, hematologic, sleep, thyroid → System-Wide. Disclose explicitly that the 5-domain frame is a product taxonomy informed by López-Otín 2023 hallmarks + ICD-11, not itself a peer-reviewed ontology.
5. **Validate locally first.** Al-Shamsi & Govender 2025 (BMC Cardiovasc Disord) provides UAE-specific PREVENT calibration showing good discrimination in Emirati women, moderate in men. UK Biobank is the methodology benchmark, not the primary cohort, for a UAE-deployed app.
6. **Pre-register** the validation protocol on OSF before any cohort touches the model. Required: Harrell's C ≥ 0.02 above best comparator AND rank-stability ρ ≥ 0.95 in Sobol perturbation as the launch decision rule.
7. **Defensible regulatory positioning is wellness/general-fitness, not SaMD.** Use risk-of-screening-positive language, never diagnostic language. Engage MOHAP early.

---

## 1. Methodology

### 1.1 Pipeline

```
Validated score (PMID-anchored)
  ↓
Orient direction: higher value = worse health
  ↓
Map to harm hᵢ ∈ [0,1] using published guideline cutoffs (distance-to-target)
  ↓
Convert to health qᵢ = 1 − hᵢ
  ↓
Group redundant scores into construct clusters; pick anchor per cluster
  ↓
Aggregate clinically distinct constructs to organ score using BOTH:
  - Spec A: α-blended partial-min × weighted geometric
  - Spec B: weighted geometric only
  ↓
Aggregate organ scores to domain score using BOTH:
  - Spec A: α-blended partial-min × weighted geometric (α tunable)
  - Spec B: weighted geometric + separate non-compensatory red-flag layer
  ↓
Display both specs in parallel; flag user-level disagreement
```

### 1.2 Normalisation rule (single, both specs use this)

**Distance-to-clinical-cutoff with three anchor points per score** (OECD/JRC 2008 §6.3 distance-to-target tradition; clinically anchored to guideline thresholds).

For each validated score, define:
- `0.0` = published low-risk cutoff (e.g. FIB-4 ≤ 1.3; eGFR ≥ 90; ASCVD 10-yr < 5%)
- `0.5` = indeterminate / borderline anchor (e.g. FIB-4 midpoint; eGFR 60–89 boundary; ASCVD 5–7.5%)
- `1.0` = published high-risk cutoff (e.g. FIB-4 ≥ 2.67; eGFR < 30; ASCVD ≥ 20%)

#### Anchor-source distinction (committed 4 May 2026 per architecture-spec patches)

Each anchor carries a `source` flag with one of two values:

- **`published`** — the value is an explicitly defined cutoff in the source guideline.
- **`constructed_midpoint`** — the value is the arithmetic midpoint of the indeterminate zone, computed by us, not found in any guideline.

The interpolation rule depends on the anchor sources:

- **All three anchors `published`** → three-anchor piecewise-linear interpolation through all three. Example: ASCVD 10-year risk has published cutoffs at 5%, 7.5%, and 20%, all three of which carry guideline weight.
- **Indeterminate anchor `constructed_midpoint`** → two-anchor piecewise-linear interpolation between `low` and `high` only. The constructed midpoint is recorded in audit logs and may be displayed for transparency, but is not used in the interpolation maths. Example: FIB-4 has two published cutoffs (1.30 and 2.67 per AASLD 2023 / EASL-EASD-EASO 2024) and an indeterminate *zone* between them; the midpoint 1.985 is constructed, not published.

**Rationale for the distinction:** marking an anchor "constructed" but then interpolating through it as if it were a calibration anchor would contradict the marking. Two-anchor PWL is the honest fallback when no midpoint cutoff exists. Three-anchor PWL is appropriate only when the guideline gives three real anchors.

Piecewise-linear interpolation between the active anchors; capped at [0, 1]. `qᵢ = 1 − hᵢ`.

| Score type | Normalisation |
|---|---|
| Absolute risk % (e.g. PREVENT 10-yr ASCVD) | Three-anchor PWL using guideline treatment thresholds (e.g. 5%, 7.5%, 20% — all published) |
| Ordinal category (e.g. KDIGO green/yellow/orange/red) | Fixed harm levels per category; later recalibrate to observed event rates |
| Continuous score with two published cutoffs (FIB-4, FLI) | Two-anchor PWL between published low and high; indeterminate anchor flagged `constructed_midpoint`, recorded in audit, not used in maths |
| Continuous score with three published cutoffs (eGFR 30/60/90, ASCVD 5/7.5/20) | Three-anchor PWL through all three published anchors |
| Binary screen (FIT, calprotectin) | **Do not aggregate as a numeric score.** Treat as a clinical flag / pathway trigger only |
| Symptom score (PHQ-9, GAD-7, CAT) | Map to validated severity bands |

**Why not min-max / z-score / percentile:** these make the score population-relative. A "70th percentile" liver health among UAE users may still be clinically abnormal; the user's score should not change because the user base demographic shifted. OECD/JRC 2008 §6.3 lists all four methods; clinical apps need anchored cutoffs.

**Floor handling:** geometric mean breaks at zero. Apply ε = 0.01 floor on `qᵢ` before logarithm. ε is itself a Sobol-perturbed parameter in robustness analysis (do not treat ε as a free constant).

### 1.3 Aggregation: two parallel specifications

#### Spec A — α-blend (sourced from Claude Research run)

Within organ, weighted geometric mean of construct healths:

```
OrganScore_A = 100 × exp(Σ wᵢ × ln(max(qᵢ, ε)))
```

Between organ → domain, blend partial-min with weighted geometric:

```
DomainScore_A = α × min(OrganScore_j) + (1 − α) × Π OrganScore_j^(w_j)
```

Default α = 0.5. α treated as Sobol-perturbed parameter, not a fixed constant.

**Strength:** mathematically elegant; one number captures "worst-organ-matters" and "everything-matters" jointly.
**Weakness:** harder to explain to users; α is arbitrary without a calibration target.

#### Spec B — geometric + non-compensatory flag layer (sourced from ChatGPT run)

Within organ, same weighted geometric mean as Spec A. Between organ → domain, weighted geometric only:

```
OrganScore_B = 100 × exp(Σ wᵢ × ln(max(qᵢ, ε)))
DomainScore_B = 100 × exp(Σ w_j × ln(OrganScore_j / 100))
```

**Separately** (not blended into the score), maintain a non-compensatory red-flag layer: if any input score crosses its published clinical action threshold, the user sees an explicit red flag alongside the composite — never folded into the number.

**Strength:** matches how clinical guidelines actually operate (scores are scores; flags are flags). Easier user explanation. Closer to AASLD 2023 / KDIGO 2024 sequential-testing logic.
**Weakness:** loses some signal in the headline number; users might focus on the score and ignore the flag.

#### What gets displayed

The user sees both:

| | Heart & Metabolism | Gut & Digestion | Brain Health | Muscle & Bones | System-Wide |
|---|---|---|---|---|---|
| Spec A | … | … | … | … | … |
| Spec B + flags | … | … | … | … | … |

If `|Spec A − Spec B| > 5 points`: surface "your scores point in different directions" + show contributing organs. This **is** the user-visible sensitivity analysis.

### 1.4 Compensability rule

| Level | Compensability | Rationale |
|---|---|---|
| Within construct (e.g. APRI vs FIB-4 for fibrosis) | **No** — pick anchor + use others as discordance check | Same construct, redundant inputs; averaging double-counts shared drivers |
| Within organ (fibrosis + steatosis + synthetic function) | **Partial** (geometric mean, not arithmetic) | Constructs are partial substitutes; geometric penalises imbalance per OECD/JRC §6.11 |
| Between organs in a domain | **Partial** (Spec A) or **none** (Spec B + flag layer) | Good liver does not compensate bad kidney; both specs preserve this |
| Clinical action thresholds | **Never compensatory** | A red flag is a flag regardless of other scores |

OECD/JRC 2008 §6.11: *linear aggregation imposes constant compensability; geometric reduces compensability for low values; non-compensatory MCDA preserves rank but loses cardinal information.* Greco et al. 2019 §3.3 places geometric mean below arithmetic on the compensability spectrum and recommends it when "indicators represent essentials," which clinical organ function is.

### 1.5 Redundancy detection and handling

Four-layer audit per organ:

1. **Clinical construct map** — classify each score by intended outcome and inputs.
2. **Input-overlap matrix** — flag shared variables (AST, platelets, age, BP, lipids).
3. **Empirical redundancy** — Spearman correlation matrix; flag |ρ| > 0.7 pairs; VIF > 5 on linear regression of mortality on all scores; PCA — if PC1 explains > 70% of variance, panel is essentially one-dimensional.
4. **Outcome redundancy** — incremental ΔC-index, calibration, NRI/IDI (cautiously per Kerr et al. 2014 critique), decision-curve net benefit.

Handling hierarchy:

| Situation | Action |
|---|---|
| Same construct, same endpoint, heavy input overlap | Pick best-validated anchor; demote others to confirmatory display |
| Same construct, different calibration population | Pick by target population calibration |
| Same construct, modest overlap, complementary endpoint | Keep, single cluster weight |
| Distinct construct | Keep as separate input |
| No local calibration | Use as provisional; flag calibration uncertainty |

**Do not** equal-weight redundant scores. AST appears in FIB-4, NAFLD-FS, and APRI; equal-weighting weights AST 3× anything orthogonal.

### 1.6 Score discordance (Q3)

When two scores cover the **same construct** and disagree:

```
Do not average.
Apply guideline-endorsed gate → confirmer pathway.
If no confirmer: show "discordant / uncertain" flag and reduce composite confidence.
```

| Organ | Gate | Confirmer / next step | Composite handling |
|---|---|---|---|
| Liver MASLD | FIB-4 | VCTE or ELF (per AASLD 2023, EASL-EASD-EASO 2024 stepwise approach) | FIB-4 anchors; NFS/APRI discordance triggers uncertainty flag |
| Kidney | eGFR + UACR (KDIGO heatmap) | Repeat abnormal labs; KFRE for kidney-failure horizon | Heatmap is categorical; KFRE is endpoint-specific; do not average |
| CVD | Regionally calibrated 10-yr score | Risk enhancers, CAC if clinically appropriate | Pick one calculator by population; do not average across calculators |
| Gut / CRC | FIT | Colonoscopy if positive | FIT is a pathway trigger, not an averageable score |
| Mental health | PHQ-9 / GAD-7 | Diagnostic clinical interview if positive | Severity bands; flag positive screen; never label diagnosis |

### 1.7 Worked liver example

**User inputs (calibrated to produce the stated q values via standard published anchors per §1.2):** FIB-4 = 2.0, NAFLD-FS = indeterminate (confirmatory display only), APRI = normal (confirmatory display only), FLI = 54, HSI = high (confirmatory display only), ALBI = −1.874, aMAP = 55.

**Reduced panel for composite:** FIB-4 (anchor for fibrosis, w=0.40), ALBI (synthetic function, w=0.20), aMAP (HCC risk, w=0.20), FLI (steatosis anchor, w=0.20). NFS, APRI, HSI shown as confirmatory display only.

**Normalisation (distance-to-cutoff, with anchor-source rules per §1.2):**
- FIB-4 = 2.0. Indeterminate anchor (1.985) is `constructed_midpoint`, so two-anchor PWL is used between 1.30 (q=1.0) and 2.67 (q=0.0). Computation: `q = 1 − (2.0 − 1.30)/(2.67 − 1.30) ≈ 0.489 → 0.49`
- ALBI = −1.874. Two-anchor PWL between −2.60 (q=1.0) and −1.39 (q=0.0). Computation: `q = 1 − (−1.874 − (−2.60))/(−1.39 − (−2.60)) = 1 − 0.726/1.21 ≈ 0.40`
- aMAP = 55 in intermediate band (50–60 maps to q = 1.0–0.5) → q = 0.50
- FLI = 54. Two-anchor PWL between 30 (q=1.0) and 60 (q=0.0). Computation: `q = 1 − (54 − 30)/(60 − 30) = 1 − 0.80 = 0.20`

> **Note on the calibrated raws.** Earlier drafts of this example used ALBI = −2.5 and FLI = 70, which under standard distance-to-cutoff anchors actually produce q ≈ 0.92 and q = 0 (clamped) respectively, not the stated 0.40 and 0.20. The 39.5 organ-score target referenced in this document was based on q values, not raw inputs, and was preserved when the regression test in `architecture_spec.md §10` and `tests/healthscore/regression/test_liver_worked_example_full_pipeline.py` was implemented. To make the worked example self-consistent end-to-end, the raws shown above are the values that actually produce the stated q values via the published-anchor PWL. This is methodology erratum #2 (caught during Phase 2 implementation, 4 May 2026); see commitments_log.md for full discussion.
>
> **Note on per-formula calibration vs single-user fixture.** The four scores in this example (FIB-4, ALBI, aMAP, FLI) share input variables — FIB-4 and aMAP both depend on age and platelets, and the constraints they impose on those inputs are mutually inconsistent. There is no single physiologically-coherent user whose lab values simultaneously produce FIB-4 = 2.0, ALBI = −1.874, aMAP = 55, and FLI = 54 via the published formulae. This worked example is therefore **a per-score calibration set, not a unified user fixture**. The integration test suite in `tests/healthscore/integration/test_canonical_fixtures.py` reproduces this honestly by calling `evaluate_score` per-score with the per-formula raws. The 39.46 organ-score target is preserved at the q-aggregation level. This is methodology erratum #4 (caught during Phase 4 integration testing, 4 May 2026); future worked examples that need to be reproducible from a single user fixture must be derived backward from a coherent set of raw labs through every formula simultaneously.

**Spec A organ score:**
```
OrganScore_A = 100 × exp(0.40·ln(0.49) + 0.20·ln(0.40) + 0.20·ln(0.50) + 0.20·ln(0.20))
             ≈ 100 × exp(−0.285 − 0.183 − 0.139 − 0.322)
             ≈ 100 × exp(−0.929)
             ≈ 39.5
```

**Spec B organ score:** identical at organ level (same geometric mean within organ). Difference appears at domain level.

**Equivalent arithmetic (for sensitivity):**
```
0.40·0.49 + 0.20·0.40 + 0.20·0.50 + 0.20·0.20
= 0.196 + 0.080 + 0.100 + 0.040
= 0.416 → 41.6
```

Geometric (39.5) is lower than arithmetic (41.6) because the panel has imbalance — high steatosis and intermediate fibrosis cannot be fully offset by good synthetic function. This is the *intended* behaviour: an arithmetic mean would let normal ALBI hide the steatosis + fibrosis signal.

**User-facing display:**
> Liver composite: 39.5 (Spec A) / 39.5 (Spec B). Indeterminate steatosis signal (FLI 54). Intermediate fibrosis by FIB-4; NAFLD-FS indeterminate (discordance flag). Synthetic function preserved (ALBI Grade 1, near Grade 1/2 boundary). **Action:** if cardiometabolic risk factors present, follow MASLD stepwise pathway (FIB-4 → VCTE/ELF per AASLD 2023 / EASL-EASD-EASO 2024).

### 1.8 Score eligibility gates (committed 4 May 2026)

Some scores are clinically meaningful only for users who meet eligibility conditions defined by the score's derivation cohort. Computing such a score for an ineligible user produces a number with no clinical meaning. Three gates are committed; the architecture spec implements them as a recursive predicate engine with topological execution order so cross-score gates work correctly.

| Score | Eligibility condition | Rationale |
|---|---|---|
| **CHA₂DS₂-VASc** | Documented atrial fibrillation (`atrial_fibrillation_status == true`) | The score is a stratifier *within* AF, not a population stroke-risk score. Computing for non-AF users and producing "anticoagulation recommended" output is iatrogenic harm risk. (commitments_log Tier 1, methodology §3.6) |
| **KFRE** | `eGFR ≤ 60` (i.e. CKD stage G3a or worse) | Tangri 2011 (PMID 21482743) derived KFRE in CKD G3a–G5 cohorts. Computing for healthy kidneys produces a "5-year risk of kidney failure" output that is meaningless because the input population is healthy. (commitments_log decision 4 May 2026) |
| **aMAP** | Documented chronic liver disease **OR** (FIB-4 ≥ 1.3 AND FLI ≥ 60) | Original Liu 2020 (PMID 32707225) validated in chronic liver disease patients. The compound rule extends to MASLD users with elevated screening markers, who are at HCC risk despite no formal CLD diagnosis. The FIB-4 + FLI second branch references *other scores' computed values*, requiring topological execution order in the implementation. (commitments_log decision 4 May 2026) |

**Failed gates do not contribute to organ aggregation.** The score returns `status=GATED` with the failure reason; its weight is redistributed across surviving cluster members per §1.5 redundancy handling. The user-facing display does not show a number, only an explanation that the score does not apply to the user's profile.

**Adding future gates** is purely a config change in the architecture spec (`gate_requirements` field in the per-score JSON). Adding new predicate types or field paths requires a code change in the gate engine.

---

## 2. Domain taxonomy

### 2.1 Disclosure language (mandatory)

> "We adopt a 5-domain user-facing taxonomy (Heart & Metabolism, Gut & Digestion, Brain Health, Muscle & Bones, System-Wide) constructed by mapping organ systems (ICD-11 chapters) onto integrative healthspan dimensions, informed by López-Otín et al. (Cell 2023) hallmarks of aging. We acknowledge this taxonomy is a product simplification, not an externally validated medical ontology."

### 2.2 Final mapping

| Organ system | Primary domain | Cross-tag | Rationale | Tier |
|---|---|---|---|---|
| Liver (FIB-4, ALBI, aMAP, FLI) | **Heart & Metabolism** | Gut & Digestion (anatomical); System-Wide in cirrhosis/HCC | MASLD is **defined** as cardiometabolic disease (AASLD 2023 *Hepatology*; EASL-EASD-EASO 2024 *J Hepatol* 81:492–542). Name change NAFLD→MASLD reflects this. | A |
| Kidney (eGFR, KFRE, KDIGO category) | **Heart & Metabolism** | System-Wide | KDIGO 2024 (Kidney Int 105(4S):S117–S314) + AHA 2023 Presidential Advisory frame CKD inside cardio-kidney-metabolic (CKM) syndrome. eGFR is in PREVENT. | A |
| CVD (one regional + ApoB + Lp(a)) | **Heart & Metabolism** | — | Self-evident | A |
| Metabolic (HOMA-IR, METS-IR, TyG, FINDRISC) | **Heart & Metabolism** | System-Wide | Same domain as CVD/liver/kidney per CKM | A |
| Thyroid (TSH+FT4 pattern) | **System-Wide** | Heart & Metabolism | Affects metabolism, cardiac, neuro, mood, bone — does not sit in one organ silo | B |
| Inflammatory (SII, NLR) | **System-Wide** | — | López-Otín 2023 explicitly adds chronic inflammation as integrative hallmark | A |
| Biological age (PhenoAge) | **System-Wide** | All domains | Integrates 9 biomarkers across organs by construction | A |
| Sleep (NoSAS, +STOP-BANG) | **System-Wide** | Brain Health | OSA affects CV, metabolism, cognition; integrative hallmark | B |
| Hematologic (Hb + RDW) | **System-Wide** | — | RDW is non-specific mortality integrator (Patel 2010 PMID 19880817 — see §6 caveat) | B |
| Neuro (CAIDE, homocysteine, +MoCA, PHQ-9, GAD-7, LIBRA) | **Brain Health** | System-Wide | Cognition + mental-health screens map to ICD-11 nervous system + WHO ICOPE cognitive/psychological capacity | A |
| Bone/musculoskeletal (DXA T-score, EWGSOP2, QFracture, FNIH lean, +FRAX, SARC-F, SPPB, gait speed) | **Muscle & Bones** | System-Wide | Self-evident; EWGSOP2 is established standard | A |
| Frailty (Fried, Rockwood CFS) | **System-Wide** | Muscle & Bones; Brain Health | Frailty integrates mobility + exhaustion + function + mortality risk | A |
| Respiratory (GOLD spirometry, mMRC, CAT) | **System-Wide** | (future "Lungs & Oxygenation") | ICD-11 has respiratory chapter; 5-domain frame lacks natural respiratory home | A |
| Vision/hearing (future) | **Brain Health** or **System-Wide** | Healthy-aging cross-tag | WHO ICOPE treats vision and hearing as intrinsic-capacity domains | B |
| Gut & Digestion (FIT, calprotectin, GERD-Q, Bristol/Rome IV, IBD activity) | **Gut & Digestion** | System-Wide | Currently empty; populate per §3 | A |

### 2.3 Diff vs original draft

- **Liver moves out of any "gut/digestion" framing.** MASLD is metabolic. Anatomical mapping in ICD-11 is preserved as cross-tag.
- **Kidney stays inside Heart & Metabolism**, not its own domain (per CKM 2023).
- **System-Wide becomes the home for cross-cutting integrators:** inflammatory, biological age, hematologic, sleep, thyroid, frailty.
- **Two product domains the 5-domain frame cannot cleanly hold:** respiratory and senses (vision/hearing). Tag internally for future expansion.

---

## 3. Panel additions per domain

Tier code: **A** = guideline; **B** = systematic review / large cohort; **C** = single derivation cohort; **D** = preprint/expert opinion.
**NEW since 2023** = source < 36 months old.

### 3.1 Heart & Metabolism

| Score | PMID / source | Cohort | Performance | Tier |
|---|---|---|---|---|
| ESC SCORE2 / SCORE2-OP | EHJ 2021;42:2439-2454 | 12 EU cohorts, n=677,684 | Region-calibrated; ESC 2021 prevention recommendation | A |
| AHA PREVENT (already in panel) | PMID 37947085 | Pooled contemporary US cohorts | C-stat improved over PCE; **Spec recommends as primary for non-UAE users** | A (NEW since Dec 2023) |
| **Al-Shamsi & Govender 2025 — UAE PREVENT validation** | DOI 10.1186/s12872-025-05211-8; PMID 41073890 | n=897 Emiratis, 12-yr follow-up | **Effective in Emirati women; recalibration needed in men** | B (NEW since Oct 2025) — **PRIMARY for UAE users** |
| Al-Shamsi 2022 — UAE 10-yr CVD nomogram | BMJ Open 2022; PMID 36581433 | UAE national cohort | UAE-specific derivation | B |
| Abushanab et al. 2025 — three CVD scores in Emiratis | Am J Prev Cardiol 2025; PMID 40236788 | Emirati cohort | Head-to-head head | B (NEW) |
| ELF test (sequential confirmer for FIB-4 ≥ 1.3) | AASLD 2023 + EASL-EASD-EASO 2024 | Multiple cohorts | AASLD/EASL endorsed at 9.8 cutoff | A |
| ADA 2024 T2D risk (alternative to FINDRISC for non-Finnish) | ADA Standards of Care 2024 | — | Region-agnostic | A |

**Consolidation:** drop AIP, remnant cholesterol, non-HDL, TG/HDL from composite. All redundant with ApoB. Keep one anchor 10-yr score (region-specific) + ApoB + Lp(a) (one-time per EAS 2022 PMID 36036785) + one diabetes risk score + FIB-4 + eGFR.

### 3.2 Gut & Digestion (currently empty)

| Score | PMID / source | Cohort | Performance | Tier |
|---|---|---|---|---|
| FIT (CRC screening) | USPSTF 2021; Imperiale 2014 meta n>2 million | Pooled | Pooled sens 0.79, spec 0.94 | A |
| Faecal calprotectin | NICE DG11 (2013, reviewed 2017); van Rheenen meta-analysis | n>16,000 Edinburgh | Sens 93%, spec 96% IBD vs IBS at 50 µg/g (Kennedy 2014) | A |
| Bristol Stool / Rome IV (IBS) | Lacy 2016 *Gastroenterology* (Rome IV criteria); validation Palsson 2016 *Gastroenterology* 150:1481-91, PMID 27144634 | Sensitivity cohort n=843 multi-disorder GI clinic + specificity cohort n=5,931 population sample | Diagnostic criteria, not predictive AUC. Rome IV IBS Se 62.7% / Sp 97.1% | A |
| GERD-Q | PMID 19392863 (Jones 2009); meta-analysis PMID 37278156 | Multi-country n=308; meta n=11,166 | Sens 65%, spec 71% vs gastroscopy/pH | B |
| Harvey-Bradshaw Index (Crohn's) | PMID 6102236 (*Lancet* 1980 letter, no PubMed abstract) | Original derivation — cohort size pending full-text retrieval | r = 0.93 with full CDAI (claim from secondary literature; full-text confirmation pending) | B (use only in known IBD) |

**Stop condition:** until FIT and faecal calprotectin (or symptom-based validated GI instruments) are wired into the panel, **Gut & Digestion remains "not scored"** in the user-facing display. Do not use microbiome diversity indices (Shannon, alpha) — no Tier A/B individual-clinical-action validation as of May 2026.

### 3.3 Brain Health

| Score | PMID / source | Cohort | Performance | Tier |
|---|---|---|---|---|
| MoCA | English: PMID 15817019 (Nasreddine 2005, n=94 MCI / 93 mild AD / 90 controls). Arabic: convergent normative work — Egypt (Rahman 2009), Lebanon (Hayek 2020), Saudi Arabia (Muayqil 2021), Qatar (Amro 2025, PMC11807847) | English cohort 277; Arabic normative cohorts: Lebanon n=164, Qatar n=395 | English: sens 90% MCI, 100% AD; spec 87% (cutoff ≤25). **Arabic: cutoff ≤22 for MCI** (Qatar population-based 5th percentile; Lebanon ≤21; Saudi educational-stratified down to <9 for illiterate users) | A — **(1) MoCA Cognition Inc. licensing required for commercial deployment ($125/clinician training; commercial licence on top); (2) Arabic cutoff differs materially from English — apply language-specific threshold** |
| PHQ-9 | English: PMID 11556941 (Kroenke 2001); IPD meta PMID 30967483 (Levis 2019, BMJ; n=17,357). Arabic: Hammoudeh 2020, Eur J Oncol Nurs (Saudi cancer cohort, n=407, against MINI) | English: multi-site IPD meta. Arabic: single Saudi cancer cohort | English: cutoff ≥10, sens 0.88 / spec 0.85. **Arabic: cutoff ≥9, sens 88% / spec 80%, AUC 0.91** (single-source, cancer-specific — flag low confidence). No UAE primary-care validation. | A (English) / C (Arabic, single-source low-confidence). Pfizer/PRIME-MD: free for all use including commercial |
| GAD-7 | English: PMID 16717171 (Spitzer 2006). Arabic: Hammoudeh 2020 (companion analysis, same Saudi cancer cohort, n=407) | English: n=2,740 primary care. Arabic: n=407 Saudi cancer | English: cutoff ≥10, sens 89% / spec 82%. **Arabic: cutoff ≥6, sens 87% / spec 80%** (single-source, cancer-specific — flag low confidence). Lebanese psychiatric outpatient sample (Sawaya 2016, PMID 27031595): GAD-7 "neither sensitive nor specific" — concerning for high-anxiety populations. No UAE validation. | A (English) / C (Arabic, single-source low-confidence). Pfizer/PRIME-MD: free for all use |
| LIBRA | PMID 28247500 (Schiepers 2017); validation PMC11492037 (NEW since 2024) | Maastricht + ELSA + CAIDE 30-yr | Harrell's C 0.62–0.68 incident dementia | B |
| MMSE (alternative to MoCA) | PMID 1202204 (Folstein 1975); meta PMID 18579155 | Decades of validation | Memory clinic sens 79.8% / spec 81.3% | A — known education/culture bias |
| CogDrisk / ANU-ADRI | JAMA Netw Open 2023 (Huque); n=6,107 | 3 validation cohorts | Comparable AUC; CAIDE/LIBRA lower | B |

### 3.4 Muscle & Bones

| Score | PMID / source | Cohort | Performance | Tier |
|---|---|---|---|---|
| FRAX | Kanis 2008; UK validation n>878,000 | Global meta-cohorts | AUC 0.81 hip; QFracture slightly better in UK (BMJ 2017 PMID 28104610) | A |
| SARC-F | SR/MA PMID 29778639 | Meta-analysis | Low sens / high spec — case-finding only | B |
| Short Physical Performance Battery (SPPB) | SR/MA *BMC Med* | Meta-analysis | Linked to mortality + function | B |
| Timed Up and Go | Meta PMID 24484314 | Meta-analysis | Limited fall-prediction alone — use as component | B |
| Gait speed | ICOPE / geriatric literature | Broad validation | Mortality/frailty correlate | B |

### 3.5 System-Wide

| Score | PMID / source | Cohort | Performance | Tier |
|---|---|---|---|---|
| Fried Frailty Phenotype | PMID 11253156 (verified — both runs converged) | n=5,317 CHS | HR 1.82–4.46 mortality unadjusted; 1.29–2.24 adjusted | A |
| Clinical Frailty Scale (Rockwood) | PMID 16129869 | n=2,305 CSHA | AUC 0.87 mortality at 6 mo | A |
| FRAIL scale | PMID 22836700 | Multiple cohorts | Comparable to Fried in screening | B |
| STOP-BANG (cross-check NoSAS) | International SR/MA PMID 33515936 (n=26,547 across 47 studies); **UAE direct validation: Alhouqani et al. 2015, *Sleep Breath* 19(4):1235-40, PMID 25758298, DOI 10.1007/s11325-015-1150-x (Al Ain Sleep Disorders Specialised Clinic, n=193, Level I PSG)**; **deployment in UAE Healthy Future Study: PMC11286458 (Emirati adults, used for diabetes-risk cohort)** | International n=26,547; UAE Al Ain n=193 | Global: sens 93% / spec 43% at AHI ≥ 15. **UAE Al Ain: AUC 0.77; sens 90% (AHI≥5), 96.75% (≥15), 99.70% (≥30); cutoff ≥3 (standard)**. Specificity poor in clinic samples; consider ≥5 cutoff for general-population use | B; **UHN/Frances Chung licence required for commercial deployment** |
| GOLD COPD (FEV1/FVC < 0.70 + ABE) | GOLD 2025 report | Global | Diagnostic criterion, not AUC | A |
| GrimAge (DNAm) | PMID 30669119 (Lu 2019) | Multi-cohort | Strongest mortality association among epigenetic clocks | B — **requires methylation array** |
| DunedinPACE (DNAm) | PMID 35029144 (Belsky 2022) | Dunedin n=954 + 5 replication | Pace-of-aging metric | B — **requires methylation array** |
| Klemera-Doubal Biological Age | Klemera & Doubal 2006 | NHANES re-implementations | r = 0.20–0.32 with DunedinPACE | B |

### 3.6 Source-data corrections (mandatory)

**Source-data panel audit completed 4 May 2026** (see `score_panel_pmid_audit_log.md`). 39 unique PMIDs in the original panel verified live against PubMed. Four hard mismatches require panel updates before the scoring code is written or any cohort data is ingested. One additional finding is a clinical-safety issue, not a citation issue, and is the highest-priority item.

#### 🔴 Clinical-safety issue (highest priority)

**CHA₂DS₂-VASc must not be displayed to users without documented atrial fibrillation.** The current panel implementation displays the score with output text *"Moderate stroke risk — anticoagulation recommended"* for arbitrary users (audited example: 43-year-old healthy woman). This violates the methodology constraint in §1.5 (*"CHA₂DS₂-VASc only conditional on documented atrial fibrillation; it is a stratifier within AF, not a population CVD risk score"*) and is a clinical-safety concern: a user who reads "anticoagulation recommended" may seek anticoagulation they do not need (iatrogenic harm risk).

**Required panel logic before launch:**

1. **Gate the score behind a confirmed-AF input.** If `atrial_fibrillation_status` is absent, missing, or false, do not compute or display CHA₂DS₂-VASc.
2. **Remove "anticoagulation recommended" text** from the output template entirely. The score is a risk stratifier, not a treatment recommendation. Replace with risk-band language only.
3. **Audit the score's calculation logic separately** — the audit-flagged example computed 2 when the correct value for the inputs (sex-female only) is 1, suggesting SBP 134 mmHg is being scored as hypertension when the established cutoff is ≥140/90 or on treatment. Fix after the display gate is in place, not before.

#### 🔴 Hard PMID mismatches (panel-side replacements required)

| Score | Current panel PMID | Issue | Replacement |
|---|---|---|---|
| Hb + RDW Mortality Risk | PMID 20921437 | Points to Poole 2010 *Circulation* (pacemaker/ICD complications) — unrelated | **PMID 19880817** (Patel KV et al. 2010, *J Gerontol A* 65(3):258-265, DOI 10.1093/gerona/glp163) |
| QFracture 10-year Hip Fracture Risk | PMID 22941793 | Points to Webert 2012 *Semin Thromb Hemost* (acquired hemophilia A) — unrelated | **PMID 22619194** (Hippisley-Cox & Coupland 2012, *BMJ* 344:e3427, DOI 10.1136/bmj.e3427) — QFracture-2012 derivation/validation |
| QFracture 10-year Major Fracture Risk | PMID 22941793 | Same as above; same paper covers both endpoints | **PMID 22619194** (same paper) |
| Levine PhenoAge | PMID 29676998 | Points to the **DNA-methylation** PhenoAge (Levine 2018, *Aging*) — requires DNAm data, computationally different. Panel description ("9 blood biomarkers + chronological age") matches the **clinical-chemistry** PhenoAge, a different score | **PMID 30596641** (Liu Z et al. 2018, *PLoS Med* 15(12):e1002718, DOI 10.1371/journal.pmed.1002718) — clinical-chemistry PhenoAge with NHANES-IV validation. Optional alternative: PMID 23213031 (Levine 2013 original derivation) — not yet verified live |

#### ⚠️ Suboptimal-citation upgrades (recommended, not blocking)

Several scores currently cite a guideline, review, or outcome-validation paper instead of the score's derivation paper. These are not wrong but are weaker for citation hygiene:

| Score | Add as derivation citation | Keep current as |
|---|---|---|
| FIB-4 | PMID 16729309 (Sterling 2006, *Hepatology*) | EASL-EASD-EASO 2024 → MASLD-context citation |
| APRI | PMID 12883497 (Wai 2003, *Hepatology*) | WHO 2024 review → outcome endorsement |
| AIP | PMID 11738396 (Dobiášová & Frohlich 2001) | 2006 Czech-language review → drop or keep as supporting |
| TyG Index | PMID 19067533 (Simental-Mendía 2008) | PURE 2023 → outcome validation |
| SII | PMID 25271081 (Hu 2014, original HCC derivation) | Li 2024 meta → outcome evidence |
| KFRE | PMID 21482743 (Tangri 2011, original derivation) | Multinational validation 2016 → secondary |
| Thyroid Guideline Pattern | PMID 23246686 (Garber 2012 AACE/ATA) for primary-pattern arms | ETA 2018 → restrict to central-hypothyroidism arm only |

#### Outstanding (full-text retrieval pending)

- PMID 23213031 (Levine 2013 original blood-biomarker PhenoAge derivation) — recommended as alternative replacement for PhenoAge mismatch but **not verified live in the audit sweep**.
- PMID 14615253 (McLaughlin 2003, TG/HDL ratio) — referenced as derivation candidate but **not verified live**.
- See `score_panel_pmid_audit_log.md` for full audit detail.

---

### 3.7 System-Wide composite weighting (committed 4 May 2026; updated 4 May 2026 after Phase 6 distribution finding)

The System-Wide domain originally allocated PhenoAge 0.35 as the primary integrator on the rationale that PhenoAge integrates 9 multi-system biomarkers. Phase 5 implementation and Phase 6 distribution check together surfaced three concerns that change this allocation:

**Concern 1 — clamp activation is the centre of the distribution, not the tails.** Phase 6 closed action item #26 with a 1,000-simulated-user distribution check using NHANES-like biomarker distributions for healthy adults aged 35–75. **The PhenoAge `output_clamp` (±25 years) activates 100% of the time. Median unclamped output is −56 years. All clamp activations are low-tail; no high-tail activation observed.** This is not "the formula misbehaves at outliers"; it is "the formula's central tendency lies entirely outside the clinically meaningful range we committed to display." A clamp that always fires is no longer a clamp — it is a constant truncation that destroys the relative ordering between users.

**Concern 2 — persistent low-confidence flag.** Because the clamp activates 100% of the time, every user's PhenoAge component carries `confidence: low`. A flag that always fires is informational noise. Even at weight 0.15, this would mean every System-Wide score for every user always displays at least one low-confidence component flag — degrading the meaning of the flag for the panel's other components.

**Concern 3 — cross-panel input redundancy.** PhenoAge's nine inputs include albumin, creatinine, and RDW. Three of nine (33%) are already double-counted across other panel members:

- **Albumin:** ALBI (liver), aMAP (liver), NAFLD-FS (liver confirmatory)
- **Creatinine:** CKD-EPI eGFR (kidney), KFRE (kidney via eGFR), AHA PREVENT (CVD)
- **RDW:** Hb+RDW (System-Wide, in same panel)

OECD/JRC §6.4 explicitly warns that correlated indicators in a composite implicitly upweight their shared drivers. The methodology document's §1.5 four-layer redundancy audit was applied within organ panels but not at the System-Wide cross-panel integration level. PhenoAge as a composite contributor means the same lab values silently drive both Heart & Metabolism and System-Wide via PhenoAge.

**Decision (Option C, committed 4 May 2026 after Phase 6 distribution finding):** drop PhenoAge from the System-Wide composite. PhenoAge becomes `composite_member: false` — retained in the panel as a research-grade display score with explicit caveat language ("biological-age estimate from Liu 2018; clamp activates for typical healthy adults; treat as directional, not as a clinical anchor"), but does not contribute to System-Wide aggregation. Mirrors the NLR pattern (Phase 4): kept for user education, excluded from composite per §1.5 redundancy reduction.

**Final System-Wide composite weights (Option C):**

| Component | Weight | Tier | Rationale |
|---|---:|:---:|---|
| Frailty (FRAIL scale) | 0.35 | A | Primary integrator. Tier A evidence chain; direct mortality validation across multiple cohorts (Fried CHS n=5,317; Rockwood CSHA n=2,305); no clamp behaviour; no input overlap with other panels |
| Hb + RDW Mortality Risk | 0.25 | B | Strong mortality association (Patel 2010 PMID 19880817); simplified-form implementation per action item #19 |
| OSA (STOP-BANG primary) | 0.25 | B | Direct UAE validation (Alhouqani 2015 PMID 25758298) makes this disproportionately valuable for UAE-deployed app |
| SII (Systemic Immune-Inflammation Index) | 0.15 | B | Inflammation hallmark per López-Otín 2023 |
| PhenoAge (clinical-chemistry, Liu 2018) | — | B | **Non-composite display only.** `composite_member: false`. Shown to user with explicit caveat language; does not contribute to aggregation |

Sum: 0.35 + 0.25 + 0.25 + 0.15 = 1.00.

**Decision history:**

- **Phase 5 review (4 May 2026):** demoted PhenoAge from 0.35 → 0.15 as Option B. Concerns 2 and 3 were known; concern 1 (specific clamp activation rate) was pending action item #26.
- **Phase 6 distribution check (4 May 2026, action item #26 closed):** 100% clamp activation. Data supports Option C over Option B.
- **Phase 6 review (4 May 2026):** committed to Option C. PhenoAge becomes `composite_member: false`; weights of remaining four members renormalised to sum to 1.0.

**Reconsideration trigger.** Option C is committed for launch but explicitly revisitable in one scenario: if a future calibrated biological-age score (e.g. GrimAge or DunedinPACE with DNAm pipeline access, or a recalibrated clinical-chemistry PhenoAge with bounds derived from a UAE-specific reference distribution) becomes available and resolves both the clamp behaviour and the cross-panel redundancy, that score could be evaluated as a System-Wide composite member at Tier B weight. Restoring the current PhenoAge formula to composite contribution would require a different distribution check showing clamp activation rate falls into the 5–10% outlier range with bounds clinically defensible to a reviewer.

**Source:** Phase 5 implementation review (4 May 2026); Phase 6 implementation review (4 May 2026); Phase 6 distribution check (action item #26, 1,000-user NHANES-like simulation, 100% clamp activation, median unclamped −56); OECD/JRC §6.4 redundancy guidance; commitments_log.md.

---

## 4. Validation plan

### 4.1 Outcome anchoring (three levels)

| Composite level | Primary endpoint | Secondary endpoints |
|---|---|---|
| Organ composite | Organ-specific events | Specialist referral, imaging confirmation, hospitalisation |
| Domain composite | Domain-specific incidence/hospitalisation | Guideline risk-band crossing, medication initiation |
| Headline composite | All-cause mortality / hospitalisation | Frailty, incident multimorbidity, QoL decline |

Per organ:

| Organ | Primary endpoint |
|---|---|
| Liver | Advanced fibrosis (VCTE/MRE/ELF), cirrhosis, decompensation, HCC, liver mortality |
| Kidney | 40% eGFR decline, KRT initiation, CKD hospitalisation, mortality |
| CVD | MACE, ASCVD, HF hospitalisation, CVD mortality |
| Metabolic | Incident diabetes, insulin therapy, cardiometabolic hospitalisation |
| Brain | Incident dementia/MCI, depression/anxiety diagnosis, sleep apnoea confirmation |
| Muscle & Bones | Fragility fracture, falls, sarcopenia confirmation, disability |
| System-Wide | All-cause mortality, hospitalisation, frailty progression |

### 4.2 Statistical tests

| Outcome type | Required metrics |
|---|---|
| Time-to-event | Harrell's C / Uno's C, time-dependent AUROC, calibration slope/intercept, Brier score, decision-curve analysis (Vickers & Elkin 2006, *Med Decis Making* 26:565-574) |
| Binary diagnosis | AUROC, PR-AUC if rare, sens/spec at pre-specified thresholds, calibration |
| Ordinal severity | Calibration by category, weighted kappa, ordinal C-index |
| Reclassification | NRI/IDI **only for pre-specified clinically meaningful categories** (per Kerr et al. 2014 critique) |
| Clinical utility | Decision-curve analysis at guideline thresholds |
| Robustness | **Sobol variance-based sensitivity** on weights, normalisation, aggregation operator, ε floor; report **rank-stability** (Spearman ρ across perturbations), not just score-stability — per Paruolo, Saisana, Saltelli 2013, *JRSS A* 176:609-634, DOI 10.1111/j.1467-985X.2012.01059.x |

### 4.3 Comparators (every composite must beat)

1. Equal-weighted arithmetic mean of same normalised inputs (trivial baseline)
2. Best single guideline score per endpoint (FIB-4 alone for fibrosis; eGFR alone for kidney; regional CVD score alone)
3. Evidence-tier-only weighting
4. Outcome-proximity-only weighting
5. PhenoAge alone (System-Wide and headline)
6. Frailty index (deficit accumulation) — System-Wide and headline
7. Clift et al. 2021 C-Score smartphone composite (Clift AK et al., *JMIR mHealth uHealth* 9(2):e25655; PMID 33591285; PMC7925156; n=420,560 UK Biobank; 4,526,452 person-years; 16,188 deaths; points-based C=0.66, age-adjusted Cox C=0.74) — published anchor for "consumer app composite" performance
8. Null / age-sex-only model

### 4.4 Cohort priority (UAE deployment)

| Priority | Cohort | Use |
|---|---|---|
| **Primary** | UAE Healthy Future Study + Qatar Biobank + Tawam Hospital cohort (Al-Shamsi 2025) | Local calibration, UAE-specific cutoff verification, equity calibration |
| **Methodology benchmark** | UK Biobank (n≈500,000) | Methodology validation; published benchmark; not primary because 95%+ white European |
| Secondary validation | NHANES + linked mortality (US) | PhenoAge anchor; mortality linkage |
| Multi-ethnic validation | All of Us (US) + MESA (CVD/CAC) | Diversity replication |
| European replication | Rotterdam Study, Whitehall II | Aging, dementia, cardiometabolic |

**Decision rule:** if UAE-cohort Harrell's C is more than 0.05 below UK Biobank C, the model is not deployment-ready in the UAE and must be locally recalibrated before launch.

### 4.5 Pre-registered Monte Carlo robustness protocol

Pre-register on OSF **before** any cohort touches the model.

```
Inputs (fixed):
  - validated score panel (after redundancy reduction per §1.5)
  - clinical cutoff mappings (three anchor points per score; §1.2 anchor-source rule)
  - construct clusters
  - both Spec A (α-blend) and Spec B (geometric + flag) pre-registered as parallel primaries

Uncertainty dimensions (six; aggregation alternatives narrowed out 4 May 2026):
  1. Weight uncertainty:
       Dirichlet(α_concentration · w_nominal); α_concentration ∈ {2, 10}.
  2. Spec A blend parameter α:
       α ~ Uniform(0.3, 0.7).
  3. Normalisation uncertainty:
       primary: distance-to-cutoff
       sensitivity: z-score, min-max, ordinal-ranked
  4. Indicator inclusion:
       leave-one-score-out and leave-one-cluster-out.
  5. ε floor uncertainty:
       ε ∈ {0.005, 0.01, 0.02, 0.05}
  6. Cohort uncertainty:
       bootstrap n=1,000 individuals per cohort; replicate across cohorts.

Aggregation perturbation deliberately narrowed (4 May 2026; documented in
commitments_log.md and docs/methodology_4_5_narrowed_4may2026.md):
  - weighted-arithmetic, partial-min, OWA aggregations are NOT pre-registered.
  - Spec A vs Spec B paired-spec convergence (Spearman ρ ≥ 0.90 per domain)
    is the methodologically substantive aggregation-perturbation result.
  - architecture_spec.md §12 / engine.compute() raise NotImplementedError on
    these branches; they remain available for future research use but are
    out of scope for the pre-registered validation.

Simulation:
  - 10,000 Monte Carlo draws minimum per organ/domain
  - Bootstrap 1,000 resamples for performance metrics

Reporting:
  - Median, IQR, 95% simulation interval per score
  - Spearman ρ rank correlation between user composite under nominal and perturbed configurations
  - First-order Sobol indices for each design choice (which choice drives variance in user rank?)
  - Probability of crossing clinical-action thresholds
  - Spec A vs Spec B agreement: paired Spearman ρ per domain; flag any user where |Spec_A − Spec_B| > 5 points
  - Variance attribution by weights, normalisation, indicator inclusion, ε, α
    (the six pre-registered perturbation dimensions)
```

### 4.6 Launch decision rule

A spec is publishable **only if all conditions hold**:

1. **Discrimination:** Harrell's C ≥ 0.02 above the best single comparator with non-overlapping CIs in UAE cohort + UK Biobank.
2. **Calibration:** calibration slope ∈ [0.85, 1.15]; calibration-in-the-large within ±10%.
3. **Net benefit:** positive in decision-curve analysis at clinically reasonable thresholds for at least one endpoint.
4. **Rank-stability:** Spearman ρ ≥ 0.95 across Sobol perturbation.
5. **Spec A vs Spec B agreement:** Spearman ρ ≥ 0.90 between paired user scores; if lower, do not publish a single headline — display both with disagreement framing.

If any condition fails: do not launch. Simplify, recalibrate, or remove the affected domain.

### 4.7 Pre-registration document — required elements

- Hypotheses tested
- Cohort filter criteria (exclusions)
- Outcome ascertainment
- Comparator definitions (the 8 in §4.3)
- Threshold for "improvement" (ΔC ≥ 0.02; ρ ≥ 0.95)
- Multiple-testing adjustment plan
- **Negative result publication commitment**

---

## 5. Risks and regulatory

### 5.1 Where composites mislead

| Failure mode | Control |
|---|---|
| Hide severe abnormality behind good average values | Spec B's red-flag layer; Spec A's partial-min component |
| Double-count correlated inputs | Construct clustering (§1.5); redundancy audit |
| Imply false precision | Confidence labels; Sobol-based uncertainty intervals |
| Transfer poorly across populations | Local UAE calibration; subgroup performance reporting |
| Overweight easy-to-measure biomarkers | Pre-specified construct weights; missing-domain handling |
| User anxiety / inappropriate self-treatment | Conservative disclaimers; clinician-referral thresholds |

OECD/JRC 2008 §1.6 warns composites can send misleading messages if poorly constructed. Paruolo, Saisana, Saltelli 2013 ("Voodoo or Science?") demonstrate empirically that nominal weights almost never match main effects when variables are correlated and heteroscedastic — therefore **report Sobol main-effect contributions alongside nominal weights, every release**, not nominal weights alone.

### 5.2 Regulatory positioning

| Jurisdiction | Position |
|---|---|
| **FDA (US)** | General Wellness Guidance + 21st Century Cures Act CDS exemption. Outputs must not "drive clinical management" of serious conditions. Avoid acute/urgent framing. **Position as wellness self-management tool, not SaMD.** |
| **EU MDR** | Recital 19 excludes lifestyle/well-being software. MDCG 2019-11 + MDCG 2025 update. Rule 11 triggers Class IIa if app provides individualised disease-risk probabilities for clinical management. **Avoid disease-specific output language.** |
| **UAE (MOHAP / DoH)** | Federal Decree-Law No. 38 of 2024 (medical products); Federal Law No. 2 of 2019 (ICT in health). UAE largely mirrors EU MDR. **No UAE-specific SaMD guidance found in May 2026 search; engage MOHAP early.** Class IIa-equivalent assumed for any clinical recommendation. |

### 5.3 Disclaimer language (mandatory baseline)

> "This score is a wellness and risk-stratification aid based on published screening tools. It is not a diagnosis, does not rule disease in or out, and does not replace a clinician's judgment. Abnormal or high-risk results should be discussed with a licensed clinician. Do not change medications, start treatment, or delay medical care based on this score alone."

Plus disclose:

- Applicable age ranges
- Pregnancy exclusions
- Acute illness exclusions
- **Ethnicity/geography calibration uncertainty** (especially for non-Emirati users using UAE-calibrated scores, and vice versa)
- Missing-domain handling
- Whether the score has been locally validated
- Whether the score is intended for screening, monitoring, or disease management

### 5.4 Comparator landscape (descriptive only — not endorsements)

| Product | Evidence pattern |
|---|---|
| Cleerly | FDA-cleared SaMD (2020 De Novo); CT plaque AI; explicit medical-device positioning |
| Whoop "Recovery" | Wellness positioning; HRV-based; published evidence base mostly company-internal whitepapers |
| Oura "Readiness" | Wellness; sleep/HRV-based; limited clinical-endpoint validation |
| Function Health | Lab-test platform with proprietary "internal aggregates"; explicit "not for diagnosis" stance |
| InsideTracker InnerAge | Klemera-Doubal-style biomarker age; published evidence limited to company-affiliated derivation papers |
| Levine PhenoAge calculators (third-party) | Cite PMID 29676998; "for educational purposes"; no medical-device claim — **cleanest regulatory pattern to emulate** |

### 5.5 Equity / generalisability

| Score family | UAE / MENA evidence found | Action |
|---|---|---|
| WHO MENA CVD chart | Includes UAE explicitly (PMID 31488387) | Regional baseline; locally validate |
| AHA PREVENT | Al-Shamsi & Govender 2025 (PMID 41073890): good in Emirati women, moderate in men | Use with sex-specific calibration; report disagreement |
| QRISK3 / PCE / SCORE2 | Poor agreement among tools in UAE (PMC6980489) | Benchmark only; do not deploy uncalibrated |
| Liver FIB-4/NFS | UAE prevalence studies exist; no robust biopsy/VCTE-anchored validation | Use guideline pathway; flag UAE calibration uncertain |
| CKD / KFRE | Jordanian T2DM CKD-risk study (Aldosari 2024, *J Diabetes Complications* 38:108740, PMID 38581843, n=1,603) — single-country, not regional. No strong UAE-specific KFRE validation found | Validate locally before high-stakes use |
| STOP-BANG | **UAE direct validation: Alhouqani et al. 2015, Al Ain n=193 (PMID 25758298)** + UAE Healthy Future Study deployment (PMC11286458) | Adopt cutoff ≥3 as gate; consider ≥5 as confirmer for low-prevalence general-population screening; **UHN licensing required for commercial deployment** |
| PHQ-9 | Saudi cancer cohort (Hammoudeh 2020, n=407, AUC 0.91, cutoff ≥9) — **single-source low-confidence**. Lebanese psychiatric outpatient data (Sawaya 2016, PMID 27031595) raise concern. **No UAE primary-care validation found.** Closest UAE work (Daradkeh, Al Ain, n=571) used Arabic PRIME-MD/PHQ for prevalence description, not diagnostic-accuracy validation | Adopt Arabic cutoff ≥9 with low-confidence flag; commission UAE primary-care validation before deployment |
| GAD-7 | Saudi cancer cohort (Hammoudeh 2020, n=407, cutoff ≥6, sens 87%/spec 80%) — **single-source low-confidence**. **No UAE validation found.** | Adopt Arabic cutoff ≥6 with low-confidence flag; UAE pre-launch validation essential given Lebanese specialty-sample concern |
| MoCA | Multi-site Arabic normative convergence: Egypt (Rahman 2009, sens 92.3%/spec 85.7% vs CAMCOG), Lebanon (Hayek 2020, n=164, cutoff ≤21), Saudi (Muayqil 2021), Qatar (Amro 2025, n=395, cutoff ≤22). **No UAE validation found.** All Arabic studies are normative against screening tools, not diagnostic-accuracy against neuropsychological consensus | Adopt cutoff ≤22 (Qatari population-based) as default for Arabic users; add education-stratified Saudi thresholds for low-literacy users; **MoCA Cognition licensing required for commercial deployment ($125/clinician + commercial licence)** |

**Mandatory UI element:** for each score, show derivation cohort demographics and a calibration-uncertainty banner if user's demographics differ materially from derivation cohort.

### 5.6 Licensing constraints and committed instrument selection

Two instruments in the panel require commercial licensing for deployed wellness apps. The methodology document commits to specific primary and fallback instruments below. These are decisions made on **scientific grounds first, licensing cost second**, and they propagate into the OSF pre-registration (§4.7) as the committed validation panel.

#### Committed primary instruments and fallbacks

| Domain | Primary instrument | Fallback if licensing falls through | Scientific rationale for primary |
|---|---|---|---|
| **OSA screening (§3.5)** | **STOP-BANG** | **NoSAS** | Direct UAE peer-reviewed validation (Alhouqani et al. 2015, Al Ain n=193, PMID 25758298) + UAE Healthy Future Study deployment (PMC11286458) — strongest UAE-specific OSA evidence available. NoSAS has no UAE-specific validation. STOP-BANG primary for everyone; NoSAS retained as no-licence backup |
| **Cognitive screening (§3.3)** | **MoCA** | **MMSE** | MoCA memory-clinic sensitivity for MCI ~90% (PMID 15817019) vs MMSE ~79.8% (PMID 18579155 meta-analysis of 39 studies). MMSE has documented ceiling effect for MCI. For a healthspan app, missing MCI is the failure mode to avoid; MoCA's sensitivity advantage at the MCI threshold is the dispositive metric. Arabic evidence reinforces: multi-site MoCA convergence on cutoff ≤22 (Egypt, Lebanon, Saudi, Qatar) is the strongest Arabic cognitive-screening evidence base |
| **Depression screening (§3.3)** | **PHQ-9** | None needed (free) | No licensing constraint |
| **Anxiety screening (§3.3)** | **GAD-7** | None needed (free) | No licensing constraint |

#### Licensing budget items

| Instrument | Owner | Required for app deployment | Action item |
|---|---|---|---|
| **STOP-BANG** | University Health Network (Toronto) / Frances Chung | Commercial licence via stopbang.ca | Contact UHN for pricing; budget as launch-blocking line item |
| **MoCA** | MoCA Cognition Inc. (Nasreddine) | (1) $125 USD/clinician training & certification; (2) Commercial / pharma deployment licence | Contact MoCA Cognition Inc. for commercial licensing terms; budget per-user/per-deployment cost |

#### Fallback activation criteria

The fallback instruments (NoSAS, MMSE) are not deprecated — they remain validated alternatives. Methodology document maintains both primary and fallback validation chains so the OSF pre-registration can specify "MoCA primary, MMSE if MoCA licensing unavailable in deployment jurisdiction" as a pre-registered substitution rule rather than a post-hoc choice.

**Trigger conditions for fallback activation:**

- Licensing negotiation fails or terms become uneconomic for the deployment jurisdiction
- Licensing terms change post-launch in a way that disrupts continuity
- Deployment jurisdiction (e.g. specific MENA markets beyond UAE) has different licensing access
- Cost-per-user exceeds the budget threshold set by the product team

**If fallback activates,** the methodology trade-off is documented:
- **MMSE in place of MoCA:** lower MCI sensitivity (~80% vs ~90%); known education/culture bias amplified in UAE/MENA user base. Add explicit confidence-flag in user-facing display.
- **NoSAS in place of STOP-BANG:** loses direct UAE validation anchor; relies on international meta-analytic performance only. Add explicit confidence-flag.

#### Decisions logged

- **STOP-BANG primary, NoSAS fallback** — committed (4 May 2026).
- **MoCA primary, MMSE fallback** — committed (4 May 2026).
- **License negotiation responsibility** — assigned to product/business team; methodology document will be updated when licensing terms are confirmed or fallback is activated.

---

## 6. Source-to-Claim Audit (top 12)

| # | Claim | Supporting line (≤ 20 words) | Source | Verified |
|---|---|---|---|---|
| 1 | Linear aggregation imposes constant compensability | "In a linear aggregation, the compensability is constant…" | OECD 2008 §6.11 | ✓ |
| 2 | Geometric mean is less compensatory; appropriate for "essentials" | "geometric mean may sometimes be preferred when indicators represent 'essentials'" | Greco et al. 2019 §3.3, DOI 10.1007/s11205-017-1832-9 | ✓ |
| 3 | Nominal weights ≠ main effects in correlated composites | "relative nominal weights are hardly ever found to match relative main effects" | Paruolo, Saisana, Saltelli 2013, *JRSS A* 176:609-634 | ✓ |
| 4 | AASLD 2023 / EASL 2024 use sequential FIB-4 → ELF/VCTE | "A stepwise approach using blood-based scores [FIB-4]… and… transient elastography" | EASL-EASD-EASO 2024, *J Hepatol* 81:492-542 | ✓ |
| 5 | FIB-4 and NFS outperform APRI for mortality | "FIB-4 (AUC 0.67-0.82) and NFS (0.70-0.83) outperformed APRI (0.52-0.73) in all studies" | Lee et al. 2021, *Liver Int*, PMID 32946642 | ✓ |
| 6 | KDIGO 2024 is current CKD evaluation standard | "using both urine albumin measurement and assessment of glomerular filtration rate" | KDIGO 2024, *Kidney Int* 105(4S) | ✓ |
| 7 | López-Otín 2023 adds chronic inflammation and dysbiosis | "three new hallmarks: disabled macroautophagy, chronic inflammation and dysbiosis" | López-Otín et al. 2023, *Cell* 186:243-278, PMID 36599349 | ✓ |
| 8 | PREVENT effective in Emirati women; recalibration needed in men | "PREVENT equations predicted ASCVD risk effectively in Emirati women, recalibration is needed for better accuracy" | Al-Shamsi & Govender 2025, *BMC Cardiovasc Disord*, DOI 10.1186/s12872-025-05211-8 | ✓ NEW since Oct 2025 |
| 9 | MoCA detects MCI better than MMSE | "MoCA detected 90% of MCI subjects" | Nasreddine et al. 2005, PMID 15817019 | ✓ |
| 10 | GAD-7 sens/spec at cutoff ≥ 10 | "sensitivity 89% and specificity 82%" | Spitzer et al. 2006, PMID 16717171 | ✓ |
| 11 | EU MDR threshold for software-as-medical-device | "diagnosis, prevention, monitoring, prediction, prognosis, treatment or alleviation of disease" | MDCG 2019-11 | ✓ |
| 12 | ACCORD reporting guideline for Delphi panels | Modified Delphi reporting standard for biomedical consensus | Gattrell et al. 2024, *PLoS Med* 21:e1004326, PMID 38261576 | ✓ |

---

## 7. Caveats and Limitations

- **Two source PMIDs in user's original score panel could not be resolved as of audit date and require user-side verification:**
  - **PMID 20921437** (claimed for Hb + RDW Mortality Risk) — **does not resolve** to the Patel 2010 RDW meta-analysis. Actual content: Poole et al. 2010 *Circulation*, pacemaker/ICD replacement complications. **Replace with PMID 19880817** (Patel KV et al., *J Gerontol A* 2010, 65(3):258-265).
  - All other PMIDs in the user's panel were spot-checked; no further errors identified, but full PubMed resolution sweep with screenshot trail recommended before publication.
- **PMID/PMC verification sweep completed 4 May 2026** (see `pmid_verification_log.md`). Outcomes:
  - ✅ **Verified clean (no document changes):** PMID 18579155 (MMSE meta, sens 79.8%/spec 81.3% confirmed); PMID 17099194 (Vickers/Elkin DCA); PMC11108771 (QR4, PMID 38637635, n=16.77M); PMC12611636 (Hungarian FINDRISC recalibration, real — earlier suspicion about PMC ID format was wrong).
  - ⚠️ **Verified but mislabeled — relabel in §3:**
    - PMID 27144634 (Palsson et al. 2016, *Gastroenterology* 150:1481-91) — the n=843 cohort is a **multi-disorder GI clinic sample** (IBS, FC, FD), not IBS-specific; specificity (97.1%) comes from a separate 5,931-adult population sample. Relabel to: "Rome IV IBS Se 62.7% / Sp 97.1% (Palsson 2016, n=843 sensitivity cohort + n=5,931 specificity cohort)."
    - PMID 38581843 (Aldosari et al. 2024, *J Diabetes Complications* 38:108740) — single-country **Jordanian** T2DM cohort (n=1,603), not "Middle East" regional. Relabel.
    - PMID 36777063 (Lewis et al. 2021, *Crohn's & Colitis 360*, PMC9802037) — **ulcerative colitis only** (n=2,608), not IBD broadly. Mayo has never been a Crohn's instrument. Relabel.
  - ⚠️ **Outstanding — needs full-text retrieval:** PMID 6102236 (Harvey-Bradshaw 1980, *Lancet*) — citation correct but it is a one-page Lancet letter with no PubMed abstract; n and r=0.93 vs CDAI figure cannot be confirmed from PubMed metadata alone. Mark as "verified citation; cohort size and correlation coefficient pending full-text retrieval."
  - 🔴 **Source-data corrections required (apply throughout document and panel):**
    - **PMC10118750 → PMC10735173.** PMC10118750 does not resolve; the correct PMCID for AASLD 2023 (Rinella et al., *Hepatology* 77:1797-1835, DOI 10.1097/HEP.0000000000000323) is PMC10735173.
    - **"Foster 2021" → "Clift et al. 2021"** for the C-Score paper. Foster is **not on the author list at all**. Correct citation: Clift AK, Le Lannou E, Tighe CP, Shah SS, Beatty M, Hyvärinen A, et al. *JMIR mHealth uHealth* 2021;9(2):e25655; PMID 33591285; senior author Plans D (Huma Therapeutics).
- **The 5-domain taxonomy is not itself a peer-reviewed framework.** The most defensible published anchors are López-Otín 2023 (12 hallmarks) and ICD-11 organ chapters. Disclose this taxonomy as a hybrid product simplification, not a derivation.
- **Geometric mean breaks at zero.** ε = 0.01 floor is the default; ε is itself a Sobol-perturbed parameter, not a free constant.
- **Min-max alternative may be needed for any score lacking three published anchor cutoffs.** TyG-BMI, AIP, VAI have only population-specific decile cutoffs. Document this heterogeneity per score.
- **Wearable data exclusion is correct.** No consumer wearable metric (HRV, sleep stages, step count) has ≥ 2 Tier A/B validation studies tied to clinical mortality endpoints as of May 2026.
- **Spec A α = 0.5 default and ε = 0.01 default are pragmatic priors, not validated constants.** Both are Sobol-perturbed in §4.5.
- **Arabic / UAE validation sweep completed 4 May 2026** (see `arabic_uae_validation_log.md`). Outcomes:
  - ✅ **STOP-BANG: direct UAE validation found** — Alhouqani et al. 2015, Al Ain n=193 (PMID 25758298, DOI 10.1007/s11325-015-1150-x). Cutoff ≥3 confirmed. Plus deployment in UAE Healthy Future Study (PMC11286458) for diabetes-risk cohort.
  - ⚠️ **MoCA: multi-site Arabic normative convergence on cutoff ≤21–22** (Egypt, Lebanon, Saudi, Qatar) — meets soft two-source bar at population level. **No diagnostic-accuracy study against neuropsychological consensus in Arabic.** No UAE validation. Apply Arabic cutoff ≤22 for Arabic-language users.
  - 🔴 **PHQ-9 and GAD-7: single-source low-confidence Arabic cutoffs** (Hammoudeh 2020 Saudi cancer cohort suggests ≥9 and ≥6 respectively, both materially lower than English ≥10). **No UAE validation.** Two-source rule for high-impact threshold claims is **not met**. UAE primary-care diagnostic-accuracy study against MINI/SCID required before deployment.
  - 🔴 **Material licensing constraints discovered:** MoCA Cognition Inc. requires $125/clinician training + commercial licence for app deployment; STOP-BANG (UHN/Frances Chung) requires commercial licence via stopbang.ca. Documented in §5.6. **Decision committed (4 May 2026): STOP-BANG primary with NoSAS fallback; MoCA primary with MMSE fallback.** Licence negotiation assigned to product/business team; methodology document updated when terms confirmed.
- **EU MDR / FDA / MOHAP positioning is interpretive guidance based on regulator-published documents but is not legal advice.** Engage qualified regulatory counsel before launch.
- **Architecture spec ↔ methodology document sync (4 May 2026).** Three architecture-spec patches were committed (`commitments_log.md`) and propagated into this methodology document: (1) anchor-source distinction (§1.2 — `published` vs `constructed_midpoint`, two-anchor PWL fallback; §1.7 — FIB-4 example uses two-anchor PWL explicitly); (2) KFRE eligibility gate at eGFR ≤ 60 (§1.8); (3) aMAP compound eligibility gate (CLD OR MASLD-screening evidence; §1.8). The architecture spec at `architecture_spec.md` §6 is the implementation reference for the recursive predicate engine that enforces these.
- **Source-data panel audit completed 4 May 2026** (see `score_panel_pmid_audit_log.md`). 39 unique PMIDs in the original panel verified live against PubMed. Outcomes: 27 verified clean, 9 suboptimal-citation upgrades recommended, **3 hard mismatches requiring replacement** (Hb+RDW, QFracture×2 rows, Levine PhenoAge). Documented in §3.6. **One additional finding is a clinical-safety issue, not a citation issue:** the panel currently displays CHA₂DS₂-VASc with output text "anticoagulation recommended" for arbitrary users (not gated to documented atrial fibrillation as required by §1.5). This must be fixed before launch — it is iatrogenic harm risk.
- **Retraction-check is partial.** Primary methodology citations (OECD 2008; Greco 2019; Paruolo/Saisana/Saltelli 2013; Saisana/Saltelli/Tarantola 2005; Vickers/Elkin 2006; AASLD 2023; EASL-EASD-EASO 2024; KDIGO 2024; GOLD 2025; Liu 2018 clinical-chemistry PhenoAge PMID 30596641 — corrected from prior "Levine 2018" reference per panel audit; López-Otín 2023; Kivipelto 2006; Cruz-Jentoft 2019; Nasreddine 2005; Spitzer 2006; Kroenke 2001; Fried 2001; Imperiale 2014; Kennedy 2014; Liu 2020 aMAP; HEART UK 2019; EAS 2022; Clift 2021; Belsky 2022; Gattrell 2024; Al-Shamsi 2025) appear clean in PubMed retraction notices as of 4 May 2026 verification sweep. **Full Retraction Watch sweep recommended before publication.**

---

## 8. Evidence Coverage & Limitations

**Searched domains:** composite indicators methodology; OECD/JRC; weighting/aggregation/robustness; redundancy detection; liver MASLD/NAFLD pathways; CKD/KDIGO; CVD calculators (PCE, PREVENT, QRISK3, SCORE2, WHO MENA, regional UAE); UAE-specific validation; gut screening (FIT, calprotectin) + GI symptom scores; cognitive (MoCA, MMSE), depression (PHQ-9), anxiety (GAD-7); sleep apnoea (NoSAS, STOP-BANG); respiratory (GOLD); frailty (Fried, Rockwood); biological age (PhenoAge, GrimAge, DunedinPACE, KDM); validation statistics (Harrell's C, NRI/IDI, DCA, Sobol); FDA / EU MDR / UAE MOHAP regulatory guidance.

**Date range of sources cited:** 1975 (Folstein MMSE) through May 2026 (KDIGO 2024 commentaries; GOLD 2025; ACCORD 2024; PREVENT comparison studies 2024–25; LIBRA2 validation 2024; Al-Shamsi UAE PREVENT validation Oct 2025; Abushanab UAE three-score head-to-head 2025).

**NEW since 2023 sources (≤ 36 months old):**

- AHA PREVENT (Khan 2023, *Circulation*; PMID 37947085)
- AASLD 2023 NAFLD/MASLD Practice Guidance (Rinella 2023)
- EASL-EASD-EASO 2024 MASLD CPG (Tacke 2024, *J Hepatol* 81:492-542)
- KDIGO 2024 CKD Guideline (Apr 2024)
- López-Otín 2023 Hallmarks (Jan 2023)
- ACCORD reporting guideline (Gattrell 2024, *PLoS Med*; PMID 38261576)
- GOLD 2025 Report
- LIBRA2 validation (PMC11492037, 2024)
- PREVENT vs PCE comparison studies (*Atherosclerosis* 2024; *JACC Adv* 2025)
- Hungarian FINDRISC recalibration (Nov 2025) — **PMC ID needs verification**
- **Al-Shamsi & Govender 2025 UAE PREVENT validation** (BMC Cardiovasc Disord, Oct 2025) — primary UAE-specific evidence
- Abushanab et al. 2025 UAE three CVD scores head-to-head (Am J Prev Cardiol, Mar 2025)

**Known gaps:**

- No robust Gut & Digestion composite exists from current panel; domain remains "not scored" until FIT and calprotectin (or equivalent) are wired in.
- No respiratory domain in the 5-domain frame; map to System-Wide or add internal "Lungs & Oxygenation" tag for future expansion.
- No vision/hearing scoring; ICOPE intrinsic-capacity domains for future expansion.
- AUC/c-statistic values were not retrievable for every suggested score; "NR" entries should be filled in from source PDFs before publication.
- Journal SJR quartiles not fully verified live; conservative labelling used. No Q3/Q4 sources used as primary recommendations.
- Arabic / UAE language validation for PHQ-9, GAD-7, MoCA was not exhaustively searched — must be confirmed before deployment in Arabic-language UI.

**Two-source rule compliance:** all recommendations affecting score computation (Spec A and Spec B aggregation, distance-to-cutoff normalisation, redundancy reduction in liver and CVD, liver/kidney → Heart & Metabolism mapping, Sobol robustness protocol) have ≥ 2 Tier A or Tier B sources. Single-source recommendations explicitly flagged in §7.

**Bottom-line publication stance:** the defensible claim is **not** "this composite is clinically superior." The defensible claim is: *the composite is transparently constructed from validated inputs, redundancy-controlled, clinically anchored, runs two parallel aggregation specifications per OECD/JRC §1.5 multi-modelling guidance, robustness-tested via Sobol variance-based sensitivity, and pre-registered for outcome validation against equal-weight, best-single-score, PhenoAge, frailty, and Clift et al. 2021 C-Score comparators.*

---

*End of merged methodology document. For source data, audit trails, and prior research outputs, see Project files.*
