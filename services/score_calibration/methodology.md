# Composite-Score Weighting Methodology

Reference framework for the organ-composite weighting model in this app.
Every design decision below should be traceable to one of the sources in
the "References" section at the end.

## 1. Scope

Organ scores are aggregated in two steps:

1. **Within-organ**: a weighted mean of per-score severity-to-health values.
2. **Across-organ**: a mean of the per-organ composites.

This document covers the weighting at step 1 only; step 2 currently uses
equal organ weights (domain weighting is a separate Delphi-driven effort —
see `delphi_protocol.md`).

## 2. Weighting-method choice

Following Nardo et al. OECD/JRC Handbook on Constructing Composite
Indicators (2008) §6 and the contemporary review by Greco S et al.,
Soc Indic Res 2019;141:61–94 (DOI: 10.1007/s11205-017-1832-9, Q1), five
weighting families are recognised:

| Family | Data need | Scientific rigor | This app |
|---|---|---|---|
| Equal weights | None | Low; assumes all indicators equivalent | shipped as baseline |
| Statistical (PCA, EFA, entropy) | Cross-sectional sample | Moderate; inappropriate for formative composites (Bruzzese 2024) | not used |
| Outcome-anchored (Cox / elastic-net) | Longitudinal + outcomes | Highest; used by PhenoAge and GrimAge | **Phase 2 target** |
| Expert (Delphi, AHP, BWS) | Expert panel | Moderate | see `delphi_protocol.md` |
| Hybrid Bayesian | Mixed | High; complex | Phase 3 research |

The app currently ships Phase 1 — hybrid hierarchical weights with
transparent multiplier tables — and exposes four strategies side-by-side
so the clinician can inspect sensitivity before trusting any single number.

### Formative vs reflective warning

PCA- and EFA-based weights silently assume a *reflective* model (the
underlying latent variable "liver health" causes HSI, FLI, and FIB-4 to
move together). Our composites are *formative*: HSI, FLI, FIB-4 **cause**
poor liver health, they do not reflect it. Applying PCA here would be
mathematically tidy but conceptually invalid — see Bruzzese D, Cazzola D,
Colicchia C. SN Social Sciences 2024 (DOI: 10.1007/s43545-024-00920-x) for
the full argument.

## 3. Phase-1 multipliers (shipped)

Each score's weight is the product of three multipliers.

### 3.1 Evidence tier

Mirrors `config/score_classification.py::lifecycle`.

| Tier | Multiplier | Basis |
|---|---|---|
| validated | 1.0 | Current clinical standard |
| derived | 0.6 | Emerging but used in practice |

### 3.2 Outcome proximity

Mirrors `OUTCOME_PROXIMITY_BY_CODE`. Reflects how close the score sits to
an outcome — closer = more weight. The multipliers are drawn from the
AHA PREVENT precedent of giving direct risk calculators primacy over
mechanistic markers over ratio derivatives.

| Proximity | Multiplier | Examples |
|---|---|---|
| risk_calculator | 1.5 | PREVENT, QRISK3, KFRE, QFracture |
| mechanistic | 1.0 | ApoB, HOMA-IR, FIB-4, eGFR, DXA T-score |
| derivative | 0.6 | AIP, TG/HDL, Castelli, TyG-BMI |
| exploratory | 0.4 | SPINA-GT, TFQI, PLR, Glasgow Prognostic |

### 3.3 Severity emphasis

Mirrors `_PREVENTION_SEVERITY_WEIGHTS` in `organ_score_service.py`. A
"critical" finding contributes more than an "optimal" one because a
single dangerous result should not be averaged away by many normals.

### 3.4 Composite weight

```
weight = tier_multiplier × outcome_proximity × severity_emphasis
```

This is the `hybrid_recommended` strategy in
`services/score_calibration/weighting_strategies.py`.

## 4. Normalization

Raw score values (e.g. HOMA-IR 3.52, ApoB 132 mg/dL, FIB-4 1.83) are on
incomparable scales. The app uses a **severity-bucket normalization**:
every score is classified into one of five bands (optimal → critical)
against its interpretation ranges, then mapped to a 0–100 health value
(`_SEVERITY_TO_HEALTH_100`). This is:

- auditable (clinician can see which band a value fell into),
- boundary-safe (the Codex patch in `interpret_score` ensures no score
  lands in two adjacent bands),
- **opinionated** — different normalizations (z-scores against NHANES,
  percentiles, min-max) would produce measurably different composites.

OECD 2008 §5 considers all of the above acceptable, provided the choice
is documented and the same normalization is used across all scores. We
document the severity-bucket choice here; switching to z-scores would be
a Phase-2 change requiring re-calibration of `_SEVERITY_TO_HEALTH_100`.

## 5. Sensitivity analysis (non-negotiable)

Per OECD 2008 §7, every composite-index app MUST show users how the
result would change under alternative choices. We ship this as four
side-by-side strategies on the organ-health page:

1. `equal` — baseline
2. `evidence_tier` — app's historical default
3. `outcome_proximity` — closer-to-outcome scores count more
4. `hybrid_recommended` — (3.1)×(3.2)×(3.3) above

If the four composites disagree by more than 1.0 point on the 0–10 scale,
the page surfaces that as a "weighting-sensitivity warning" so the
clinician treats the headline number with appropriate caution.

## 6. Correlation / double-counting

FIB-4, HSI, FLI, and BARD all load onto the same "liver steatosis /
fibrosis" signal. Giving each an independent weight triple-counts that
signal. Current mitigation: organ-level averaging averages correlated
scores together within the liver organ, which naturally dampens the
triple-counting. Phase-2 work should collapse correlated scores into
sub-composites before the organ-level weighted mean — see Greco 2019
§4.2 on "linear-aggregation correlation assumptions".

## 7. Phase-2 roadmap (outcome calibration)

The `weight_calibration.py` skeleton is the staging ground. Required
inputs:

- A linked-outcome cohort: NHANES III + NDI mortality is the most
  accessible (public, US-wide), MESA for CV endpoints, UK Biobank once
  access is granted, and local EHR data once ≥3 years of follow-up has
  accumulated.
- Pre-specified endpoint per organ (MACE at 10 years for cardio, CKD
  progression for kidney, major osteoporotic fracture for bone, etc.).
- Cox elastic-net per organ producing interpretable non-negative weights
  that sum to one — same construction as PhenoAge (Levine 2018) and
  GrimAge 2 (Bortz 2023).

A calibration run produces an immutable `CalibrationRun` object (see
`weight_calibration.py`) carrying the dataset, endpoint, horizon, metric
results (C-statistic, Brier, calibration slope) and git commit SHA. No
calibrated weights reach production without clinician-statistician sign-off
and a diff of representative-patient composites before/after.

## 8. Governance

- Every multiplier change is versioned in git with rationale in the commit.
- A Phase-2 calibration run is a separate JSON artifact checked into
  `services/score_calibration/calibration_runs/` so the history is auditable.
- TRIPOD+AI 2024 reporting guideline applies for any outcome-calibrated
  weights; a model card with training/validation set metadata must ship
  alongside the weights file.

## References

1. Nardo M, Saisana M, Saltelli A, Tarantola S, Hoffman A, Giovannini E.
   *Handbook on Constructing Composite Indicators: Methodology and User
   Guide.* OECD Publishing, 2008. ISBN 978-92-64-04345-9.
2. Greco S, Ishizaka A, Tasiou M, Torrisi G. On the methodological
   framework of composite indices: a review of the issues of weighting,
   aggregation, and robustness. *Soc Indic Res* 2019;141:61–94.
   DOI: 10.1007/s11205-017-1832-9. Q1.
3. Bruzzese D, Cazzola D, Colicchia C. Measurement models in composite
   indicators: a critical review of PCA. *SN Soc Sci* 2024.
   DOI: 10.1007/s43545-024-00920-x.
4. Levine ME et al. An epigenetic biomarker of aging for lifespan and
   healthspan. *Aging* 2018;10(4):573–591. PMID 29676998.
5. Bortz J et al. Biological age estimation using circulating blood
   biomarkers. *npj Aging* 2023. DOI: 10.1038/s41514-023-00110-8. Q1.
6. Khan SS et al. Development and validation of the AHA PREVENT equations.
   *Circulation* 2024;149(6):430–449. PMID 37947085. Q1.
7. Barclay M et al. Systematic review of composite quality-of-care
   indicators. *PLOS ONE* 2022. PMID 35560126. Tier B.
8. Barrios M et al. Scoping review of consensus Delphi design. *BMC Med
   Res Methodol* 2025. PMID 39815180. Tier B.
9. Schippers C et al. Delphi methodology best practice. *Arthroscopy* 2025.
   PMID 40157555. Tier B.
