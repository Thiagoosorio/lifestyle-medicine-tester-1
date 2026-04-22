"""Tools for validating organ-score numerical outputs and composite weights.

Three layers:

reference_cases
    Registry of published "example patients" with expected outputs per score.
    Drives parity regression tests against the source paper / supplement.

cross_checker
    Runs standard test patients through overlapping score families (CVD,
    metabolic, liver, bone) to catch divergence that usually means a bug.

weight_calibration
    Scaffolding + methodology for calibrating the composite weighting
    model against outcomes data (NHANES-linked mortality, etc.). Does not
    run calibration itself; documents what data + method would be needed.
"""

from services.score_calibration.reference_cases import (
    REFERENCE_CASES,
    ReferenceCase,
    check_score,
    iter_reference_cases,
)
from services.score_calibration.cross_checker import (
    STANDARD_PATIENTS,
    cross_check_cvd_10yr,
)

__all__ = [
    "REFERENCE_CASES",
    "ReferenceCase",
    "STANDARD_PATIENTS",
    "check_score",
    "iter_reference_cases",
    "cross_check_cvd_10yr",
]
