"""PhenoAge clamp distribution check (commitments_log action item #26).

Phase 5 surfaced an open question: does the [-25, +25] output_clamp on
PhenoAge fire for outliers (5-10% activation, healthy bounds) or for
the median user (80%+ activation, signalling the bounds are too narrow
or the formula is fundamentally low-confidence)?

This script answers the question by feeding PhenoAge a population of
1,000 simulated healthy adults whose biomarker values are drawn from
NHANES-like normal distributions, then reporting:

    * activation rate (fraction of users where output_clamp fires)
    * mean / median / 5th / 95th percentile of the unclamped output
    * a histogram of the unclamped distribution

Decision rule per action item #26:
    >= 80% activation     -> bounds too narrow OR PhenoAge always low-conf
    5%-10% activation     -> bounds correctly tuned for outliers
    something between     -> document explicitly, revisit weight in §3.7
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
from statistics import mean, median, quantiles
from typing import Iterable

# Make the script runnable from the repo root.
import sys
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from healthscore.score_config import load_score_config       # noqa: E402
from healthscore.score_eval import evaluate_score             # noqa: E402
from healthscore.scores import lookup_formula                 # noqa: E402


# NHANES-like normal-distribution parameters (mean, sd) for healthy
# adults aged 35-75. These are not exact NHANES values but are
# representative of the central tendency reported across NHANES IV
# tables for non-pregnant, non-acute-illness adults.
_NHANES_BIOMARKER_DISTRIBUTIONS: dict[str, tuple[float, float, float, float]] = {
    # name: (mean, sd, lower_clip, upper_clip)
    "albumin_gdl":              (4.30, 0.30, 3.00, 5.20),
    "creatinine_mgdl":          (0.95, 0.20, 0.50, 2.00),
    "fasting_glucose_mgdl":     (95.0, 12.0, 65.0, 180.0),
    "hs_crp_mgL":               (2.00, 2.50, 0.10, 20.00),
    "lymphocyte_pct":           (30.0, 6.0,  10.0, 50.0),
    "mcv_fL":                   (89.0, 4.0,  75.0, 105.0),
    "rdw_pct":                  (13.0, 0.9,  11.5, 17.0),
    "alkaline_phosphatase_uL":  (75.0, 20.0, 30.0, 200.0),
    "wbc_10e9L":                (6.5,  1.5,  3.0,  15.0),
}


def _draw_inputs(rng: random.Random, age: int) -> dict[str, object]:
    inputs: dict[str, object] = {"age": age}
    for name, (mu, sd, lo, hi) in _NHANES_BIOMARKER_DISTRIBUTIONS.items():
        v = rng.gauss(mu, sd)
        v = max(lo, min(hi, v))
        inputs[name] = round(v, 3)
    return inputs


def _summarise(values: Iterable[float]) -> dict[str, float]:
    vals = list(values)
    quants = quantiles(vals, n=20)        # 5%, 10%, ..., 95%
    return {
        "n": len(vals),
        "mean": mean(vals),
        "median": median(vals),
        "p5": quants[0],
        "p25": quants[4],
        "p75": quants[14],
        "p95": quants[18],
        "min": min(vals),
        "max": max(vals),
    }


def _ascii_histogram(values: list[float], bins: int = 20, width: int = 40) -> str:
    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    counts = [0] * bins
    for v in values:
        idx = min(bins - 1, int((v - lo) / span * bins))
        counts[idx] += 1
    peak = max(counts) or 1
    out: list[str] = []
    for i, c in enumerate(counts):
        edge_lo = lo + i * span / bins
        bar = "#" * int(c / peak * width)
        out.append(f"  {edge_lo:7.2f} | {bar} ({c})")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=1000, help="number of simulated users")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument(
        "--ages", default="35-75",
        help="age range as 'lo-hi' (uniform draw)",
    )
    args = parser.parse_args()

    age_lo, age_hi = (int(x) for x in args.ages.split("-"))
    rng = random.Random(args.seed)

    config = load_score_config(_REPO_ROOT / "configs" / "scores" / "phenoage.json")
    formula = lookup_formula(config.formula)

    unclamped: list[float] = []
    clamped_count = 0
    clamped_low = 0
    clamped_high = 0

    for _ in range(args.n):
        age = rng.randint(age_lo, age_hi)
        inputs = _draw_inputs(rng, age)
        result = evaluate_score(
            config, raw_inputs=inputs, prior_results={},
            formula=formula, gate=None,
        )
        if result.raw_value_unclamped is None:
            continue
        unclamped_value = float(result.raw_value_unclamped)
        unclamped.append(unclamped_value)
        if result.output_clamped:
            clamped_count += 1
            if unclamped_value < float(config.output_clamp.min):  # type: ignore[union-attr]
                clamped_low += 1
            else:
                clamped_high += 1

    activation_rate = clamped_count / max(1, len(unclamped))
    summary = _summarise(unclamped)

    print()
    print(f"PhenoAge clamp distribution check  (n={len(unclamped)}, ages {args.ages})")
    print(f"  output_clamp: [{float(config.output_clamp.min)}, {float(config.output_clamp.max)}]")  # type: ignore[union-attr]
    print(f"  activation rate: {activation_rate*100:.1f}% ({clamped_count} / {len(unclamped)})")
    print(f"     low-tail   ({clamped_low} clamped to min)")
    print(f"     high-tail  ({clamped_high} clamped to max)")
    print()
    print(f"Unclamped distribution (years of acceleration):")
    for k, v in summary.items():
        print(f"  {k:>8s}: {v:8.3f}")
    print()
    print("Histogram (unclamped):")
    print(_ascii_histogram(unclamped))
    print()
    print("Decision rule (action #26):")
    if activation_rate >= 0.80:
        print(f"  -> {activation_rate*100:.0f}% activation: BOUNDS TOO NARROW or PhenoAge always low-confidence.")
        print("     Recommend either widening the clamp band or documenting that PhenoAge")
        print("     is always low-confidence and revisiting its weight in methodology Section 3.7.")
    elif activation_rate <= 0.10:
        print(f"  -> {activation_rate*100:.0f}% activation: bounds correctly tuned for outliers.")
        print("     Existing weight allocation stands; no further reweight needed.")
    else:
        print(f"  -> {activation_rate*100:.0f}% activation: between thresholds. Document explicitly")
        print("     in methodology Section 3.7 and revisit Option B reweighting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
