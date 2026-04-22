# Delphi Protocol for Expert-Based Weight Elicitation

Structured panel protocol for eliciting **domain-level weights** (how much
does "Heart & Metabolism" count toward the overall composite vs. "Brain
Health" vs. "Muscle & Bones" etc.) when outcome-calibration data is not
yet available.

This document is a **pre-specified protocol**, not a ranking of scores —
the protocol is what gets executed; the output is a signed weight vector
stored in `services/score_calibration/delphi_runs/<date>.json`.

## 1. Panel design (Schippers 2025, Arthroscopy, PMID 40157555)

| Parameter | Target |
|---|---|
| Panel size | 20–30 clinicians |
| Rounds | 3 maximum |
| Consensus threshold | ≥ 80% agreement on final round |
| Anonymity | Enforced between rounds |
| Dropout tolerance | ≤ 20% round-to-round |

Panel composition (heterogeneous per Barrios 2025, BMC Med Res Methodol):

- 4–6 primary-care / internal-medicine clinicians (generalist view)
- 3–4 cardiometabolic specialists (lipid, diabetes, hypertension)
- 2–3 hepatology / gastroenterology
- 2–3 geriatrics / healthspan focus
- 2–3 sports / musculoskeletal medicine
- 2–3 neurology / cognitive health
- 1–2 clinical epidemiologists or biostatisticians (methodology guardrail)
- 1 patient advocate (non-weight-producing observer)

## 2. Round 1 — silent elicitation

Each panelist, independently and anonymously:

1. Reviews the five-domain description (see `score_classification.py`
   `DOMAIN_LABELS`).
2. Distributes 100 points across the five domains to reflect their
   clinical weight toward 10-year all-cause mortality in a
   hypothetical middle-aged adult without current diagnosis.
3. Provides a one-paragraph rationale per domain.
4. Flags disagreements with the domain boundaries.

Summary metric for Round 1: median and IQR of each domain's points.

## 3. Round 2 — feedback-anchored revision

Panelists see:

- Group median + IQR per domain from Round 1 (no individual attribution).
- Anonymised rationales, grouped by domain.
- A minority-view summary for domains where at least one panelist
  differed from the median by > 2× IQR.

Panelists re-rank with visible ability to move points between domains.
Required: a one-sentence justification whenever a Round-2 score differs
from the same panelist's Round-1 score by more than 5 points.

## 4. Round 3 — confirmation

Panelists see Round-2 consensus and indicate agree / disagree with each
domain's point allocation. Consensus is achieved when ≥ 80% of panelists
agree on all five domains. If consensus is NOT reached on one or more
domains, the protocol documents the disagreement; the affected domains
keep equal weights until a future calibration.

## 5. Robustness checks

Before the weight vector is accepted:

- **Sensitivity**: the final composite score for ten representative
  patient profiles (e.g. "Maria Silva demo", "Healthy F45", etc. from
  `services/score_calibration/cross_checker.py`) is computed under (a)
  the Delphi weights and (b) equal weights. If the two disagree by more
  than one health band for any patient, the Delphi weights are held for
  re-review.
- **Composition dependency**: the Delphi weights are re-run with one
  panelist removed at a time (leave-one-out) to verify no single voice
  dominates.

## 6. Output artifact

Each completed Delphi cycle produces a JSON file:

```json
{
  "run_id": "uuid4",
  "conducted_on": "2026-05-15",
  "panel_size": 27,
  "rounds_completed": 3,
  "consensus_achieved": true,
  "domain_weights": {
    "heart_metabolism": 0.34,
    "brain_health": 0.18,
    "muscle_bones": 0.13,
    "gut_digestion": 0.12,
    "system_wide": 0.23
  },
  "robustness": {
    "sensitivity_vs_equal_band_exceeded_count": 1,
    "leave_one_out_max_shift": 0.04
  },
  "methodology_ref": "methodology.md section 2"
}
```

## 7. Review cadence

Delphi weights expire 18 months from the conducted_on date, or earlier if:

- Guideline bodies release a materially new risk model affecting any
  domain (e.g. a PREVENT successor).
- An outcome-calibrated run becomes available (Phase 2 supersedes Phase 1).
- The panel composition materially changes (e.g. new UAE clinical
  guidance, institutional rotation).

## 8. References

- Schippers C et al. *Arthroscopy* 2025. PMID 40157555 — best-practice
  Delphi parameters (20–30 panelists, 3 rounds, 80% consensus).
- Barrios M et al. *BMC Med Res Methodol* 2025. PMID 39815180 — scoping
  review of consensus Delphi design.
- Lancsar E et al. *Value Health* review. PMID 34166149 — AHP / MCDA
  landscape for healthcare decision-making.
- Marsh K et al. *J Comp Eff Res* 2019. DOI 10.2217/cer-2018-0102 — SMART
  swing-weighting alternative for resource-limited settings.

Nothing in this document is clinical advice; it specifies how to
legitimately derive weights when outcome data is unavailable, not how
those weights should be used in individual patient care.
