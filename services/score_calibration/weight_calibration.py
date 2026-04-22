"""Scaffolding for outcome-based calibration of the composite weighting model.

This module is intentionally NOT a working calibrator yet. Calibration
requires an outcomes dataset the application does not ship, and the
methodology choices (cohort, endpoint, horizon, discrimination metric)
should be reviewed by a clinician-statistician before any weights are
changed. The goal here is to make the path concrete enough that a future
contributor can execute it end-to-end without re-deriving the design.

──────────────────────────────────────────────────────────────────────────────
What needs to change

Three weighting layers currently live in services/organ_score_service.py and
are ALL hand-tuned today:

  _TIER_WEIGHTS               -- validated vs derived (evidence quality)
  _EVIDENCE_PRIORITY_SHARE    -- 80% evidence tier in composite blend
  _PREVENTION_PRIORITY_SHARE  -- 20% prevention-emphasis blend
  _SEVERITY_TO_HEALTH_100     -- optimal=100 ... critical=10 mapping

and the organ-level aggregation averages all contributing scores equally,
which means an organ with one critical score and four optimal ones looks
the same as an organ with five elevated scores -- clinically wrong.

──────────────────────────────────────────────────────────────────────────────
Recommended methodology

1. Dataset
   --------
   * NHANES III linked mortality (public; CDC NCHS) -- most of our scores
     can be computed on NHANES III participants, and linked NDI mortality
     through 2019 gives 10- and 30-year outcomes. Limitation: US cohort,
     genetic ancestry distribution differs from UAE.
   * MESA (Multi-Ethnic Study of Atherosclerosis) -- for CVD-specific
     endpoints.
   * UK Biobank -- richest phenotype, best for cross-score panel; requires
     application.
   * Optional: a local retrospective extract from the clinic EHR once
     sufficient follow-up is accumulated (>=3 years).

2. Endpoint
   --------
   For each organ, pre-specify the clinical endpoint calibration targets:
     cardiovascular   -> MACE (MI + stroke + CV death) at 10 years
     kidney           -> CKD progression to eGFR<60 or kidney failure
     liver            -> incident cirrhosis / liver-related death
     metabolic        -> incident T2DM
     musculoskeletal  -> major osteoporotic fracture at 10 years
     biological_age   -> all-cause mortality at 10 years

3. Two orthogonal calibrations
   ---------------------------
   A. Per-score severity->hazard ratio
      Replace the hand-tuned _SEVERITY_TO_HEALTH_100 map with empirical
      hazard ratios estimated from the reference cohort, converted to a
      0-100 health scale via HR -> 1 / (1+HR) * 100 or an equivalent.

   B. Organ-aggregation weights
      Fit an organ-level composite that best discriminates the organ's
      endpoint, using weighted logistic regression or Cox on the panel of
      scores. Evaluate with C-statistic, Brier score, and calibration slope.
      Keep the weights interpretable -- prefer elastic net over free
      regression so clinicians can still see what each score contributes.

4. Cross-organ composite
   ---------------------
   Optional last step: fit the all-cause-mortality composite once the
   per-organ composites are calibrated. Acceptable only if it beats
   PhenoAge alone (our current biological-age benchmark) on AUROC for
   all-cause mortality at 10 years in a held-out set.

5. Governance
   ----------
   * Freeze current weights as v0. Every calibration run produces a new
     immutable weight vector with its dataset + git-commit metadata.
   * Never roll new weights to production without:
       - review by a clinician-statistician
       - a CI run of the reference_cases + cross_checker harnesses
       - a before/after comparison of representative patient composites
   * Weights MUST be stored as data (JSON or Python dict), not as magic
     numbers in formula bodies, so this module can inject them.

──────────────────────────────────────────────────────────────────────────────
The code below provides only the structural skeleton. It intentionally
raises NotImplementedError so that no caller accidentally uses un-calibrated
numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CalibrationRun:
    dataset: str
    endpoint: str
    horizon_years: int
    cohort_size: int
    metric_cstat: float
    metric_brier: float
    git_commit: str
    severity_to_health_100: dict[str, float]
    tier_weights: dict[str, float]
    evidence_priority_share: float
    prevention_priority_share: float


def calibrate_severity_map(*_args: Any, **_kwargs: Any) -> dict[str, float]:
    """Estimate severity->0-100 health weights from outcomes data.

    Expected pipeline:
        1. Load cohort with per-patient score severity labels + outcome.
        2. Fit Cox proportional hazards across severity buckets per score.
        3. Aggregate to an average hazard ratio per severity label.
        4. Map HR -> health score on [0, 100] via a documented monotone
           transform (e.g. HR = 1 -> 85, HR = 3 -> 25).
    """
    raise NotImplementedError(
        "Outcome-calibration requires a linked cohort dataset. See module "
        "docstring for the recommended methodology and data sources."
    )


def calibrate_organ_weights(*_args: Any, **_kwargs: Any) -> dict[str, dict[str, float]]:
    """Learn per-organ aggregation weights that best predict the organ endpoint.

    Expected pipeline:
        1. For each organ, assemble the panel of per-patient score values.
        2. Fit elastic-net logistic (or Cox) against the pre-specified
           endpoint.
        3. Constrain weights to be non-negative and sum-to-one so the
           composite stays interpretable.
        4. Evaluate on a held-out fold -- C-statistic, Brier, calibration
           slope.
    """
    raise NotImplementedError(
        "Organ-weight calibration requires an outcomes dataset. See module "
        "docstring."
    )


def apply_calibration_run(run: CalibrationRun) -> None:
    """Persist a calibration run back into the service weight constants.

    Intended usage (once a validated run is available):
        run = CalibrationRun(...)
        apply_calibration_run(run)   # updates a JSON file the service reads

    Current implementation is a stub; the service still reads hand-tuned
    constants so no calibrated run can yet be applied.
    """
    raise NotImplementedError(
        "The service currently reads hand-tuned constants in "
        "services/organ_score_service.py. To consume calibrated weights, "
        "move those constants into a JSON file this function can write."
    )
