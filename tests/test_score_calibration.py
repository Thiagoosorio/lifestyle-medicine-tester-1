"""Regression tests for organ-score parity and cross-score sanity.

Every entry in REFERENCE_CASES comes from a published source paper,
supplement, or authoritative reference implementation. A failure here
means a formula drifted from its source -- treat it as a clinical defect,
not a test to update.
"""

import pytest

from services.score_calibration import (
    REFERENCE_CASES,
    check_score,
    cross_check_cvd_10yr,
)


@pytest.mark.parametrize(
    "case",
    REFERENCE_CASES,
    ids=lambda c: f"{c.score_code}:{c.source[:30]}",
)
def test_reference_case_matches_published_value(case):
    result = check_score(case)
    assert result["status"] == "pass", (
        f"{case.score_code} drifted from {case.source}: expected "
        f"{case.expected}, got {result['computed']} "
        f"(diff={result['diff']}, tolerance={case.tolerance})"
    )


def test_cross_checker_runs_without_error_and_shows_all_five_patients():
    report = cross_check_cvd_10yr()
    assert len(report) == 5
    for row in report:
        assert "patient" in row
        assert "family" in row
        # Each patient must have at least one CVD score produced
        present = {k: v for k, v in row["family"].items() if v is not None}
        assert present, f"no CVD score computed for {row['patient']}"


def test_cross_checker_does_not_regress_healthy_young_female():
    """Healthy 45-year-old woman should show <5% family median.

    Regression guard for the ASCVD-PCE 100%-clamp bug (missing age-TC and
    age-HDL interaction terms in the female panel) that landed briefly in
    the codebase. Any return to that pathology would shoot this median
    far above 5%.
    """
    report = cross_check_cvd_10yr()
    healthy = next(r for r in report if "Healthy F45" in r["patient"])
    assert healthy["median"] is not None
    assert healthy["median"] < 5.0, (
        f"Healthy F45 family-median drifted to {healthy['median']}% "
        f"-- check ascvd_pce / prevent interaction terms. Full family: "
        f"{healthy['family']}"
    )
