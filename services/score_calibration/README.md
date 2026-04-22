# Score Calibration

Three layers for validating organ-score numerical correctness and composite weighting.

## reference_cases.py

Registry of published "example patient → expected output" pairs per score.
Every entry cites the source paper, supplement, or authoritative reference
implementation. Runs as a regression harness — any code change that touches
`organ_score_service.py` or `organ_scores_data.py` should pass every case.

Run locally:

```
python -m services.score_calibration.reference_cases
```

Consumed by the `score-reference-validator` agent under `.codex/agents/`.

## cross_checker.py

Runs five representative patients across every CVD 10-year score and reports
family-median agreement. Intended to catch bugs (wrong units, coefficient
drift, age-band errors) rather than calibrate anything clinically.

Run locally:

```
python -m services.score_calibration.cross_checker
```

Consumed by the `score-cross-check` agent.

## weight_calibration.py

**Skeleton only — does not run.** Documents the methodology and dataset
choices required to replace the hand-tuned weighting constants with
outcome-calibrated values. The file intentionally raises
`NotImplementedError` so no caller accidentally uses un-calibrated numbers.

See the module docstring for:
- recommended datasets (NHANES III + NDI, MESA, UK Biobank, local EHR)
- per-organ endpoint definitions
- the two orthogonal calibrations (severity → health, organ aggregation)
- governance rules for rolling new weights to production

## Why this is in a separate package

- Keeps the audit / calibration surface area small and auditable.
- Gives the three `.codex/agents/` agents a stable entry point.
- Makes it easy to add a `pytest` marker that runs only these modules in
  CI when weights or formula files change.
