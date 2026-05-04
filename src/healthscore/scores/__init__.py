"""Per-score formula registry.

Each score's formula is a pure function:
    (raw_inputs: Mapping[str, Decimal | str | bool | None]) -> Decimal | None

It returns None when one or more required inputs are absent or invalid;
the per-score-evaluation pipeline (score_eval.py) translates None into a
ScoreResult with status MISSING_INPUT or OUT_OF_RANGE.

Sub-modules group formulae by organ (matching architecture_spec.md §2):
    liver        fib4, albi, amap, fli, nafld_fs, apri, hsi
    cvd          (Phase 3+)
    metabolic    (Phase 3+)
    kidney       (Phase 3+)
    brain        (Phase 3+)
    bone_muscle  (Phase 3+)
    system_wide  (Phase 3+)

The registry maps the ``formula`` field in a score config (a dispatch
key like ``"fib4"``) to the corresponding callable.
"""

from __future__ import annotations

from typing import Callable, Mapping

from healthscore.scores import kidney as _kidney
from healthscore.scores import liver as _liver

#: ``ScoreConfig.formula`` -> formula callable.
#: New scores append entries here; the engine refuses to start if a
#: config references an unknown formula key.
FORMULA_REGISTRY: dict[str, Callable[..., object]] = {
    # liver
    "fib4": _liver.calc_fib4,
    "albi": _liver.calc_albi,
    "amap": _liver.calc_amap,
    "fli": _liver.calc_fli,
    "nafld_fs": _liver.calc_nafld_fs,
    "apri": _liver.calc_apri,
    "hsi": _liver.calc_hsi,
    # kidney
    "egfr_deficit": _kidney.calc_egfr_deficit,
    "kfre_5yr": _kidney.calc_kfre_5yr,
    "kdigo_category": _kidney.calc_kdigo_category,
}


def lookup_formula(formula_key: str) -> Callable[..., object]:
    if formula_key not in FORMULA_REGISTRY:
        raise KeyError(
            f"unknown formula key {formula_key!r}; registered keys: "
            f"{sorted(FORMULA_REGISTRY.keys())}"
        )
    return FORMULA_REGISTRY[formula_key]
