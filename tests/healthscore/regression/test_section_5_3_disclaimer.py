"""§5.3 disclaimer end-to-end output-string test (commitments_log #17).

The §5.3 disclaimer lives as a pydantic ``Field(default=...)`` on
``AggregationOutput.disclaimer``. The forbidden-verb linter narrowed
its scope (Phase 1 decision) to:
  - string literals returned from public functions
  - score JSON configs
  - configs/wording.yaml

The disclaimer therefore is NOT scanned by the linter even though it
contains the words "diagnosis" and "treatment" -- intentionally, because
it is regulator-mandated boilerplate that must appear verbatim in user
output (see commitments_log 4 May 2026 "Regulatory positioning and
launch jurisdiction"). This test pins:

  1. The disclaimer text appears verbatim on every ``AggregationOutput``
     instance (default value is correct + unchanged).
  2. The disclaimer's allow-list status is documented explicitly so a
     reviewer cannot mistake "the linter doesn't flag this" for "the
     linter is broken."
  3. If the disclaimer is ever changed, the change is visible here, in
     a regression-test diff, not silently in a pydantic Field default.
"""

from __future__ import annotations

import pytest

from healthscore.types import AggregationOutput
from healthscore.wording import scan_text_for_forbidden_lemmas


_EXPECTED_DISCLAIMER = (
    "This score is a wellness and risk-stratification aid based on published "
    "screening tools. It is not a diagnosis, does not rule disease in or out, "
    "and does not replace a clinician's judgment. Abnormal or high-risk results "
    "should be discussed with a licensed clinician. Do not change medications, "
    "start treatment, or delay medical care based on this score alone."
)


def _minimal_aggregation_output() -> AggregationOutput:
    return AggregationOutput(
        run_id="01J0000000000000000000000000",
        config_hash="0" * 64,
        locale="en",
        population=None,
        domains=[],
        score_results=[],
        red_flags=[],
        active_instruments={},
        timestamp_utc="2026-05-04T00:00:00Z",
    )


def test_disclaimer_default_is_the_section_5_3_boilerplate_verbatim():
    """The disclaimer text on a fresh AggregationOutput must equal the
    §5.3 boilerplate exactly. Any drift -- accidental edit, reformatting,
    a paraphrase -- breaks this test loudly."""
    out = _minimal_aggregation_output()
    assert out.disclaimer == _EXPECTED_DISCLAIMER


def test_disclaimer_appears_in_pydantic_model_dump():
    """Round-trips through model_dump() so I/O serialisations don't
    drop the disclaimer field."""
    out = _minimal_aggregation_output()
    payload = out.model_dump()
    assert "disclaimer" in payload
    assert payload["disclaimer"] == _EXPECTED_DISCLAIMER


def test_disclaimer_contains_the_three_regulator_mandated_phrases():
    """The §5.3 boilerplate is anchored on three regulator-mandated
    elements: (i) explicit non-diagnosis statement, (ii) explicit
    clinician-judgment statement, (iii) explicit do-not-change-care
    statement. If any of these drifts the test fails."""
    out = _minimal_aggregation_output()
    text = out.disclaimer.lower()
    assert "is not a diagnosis" in text                 # (i)
    assert "clinician's judgment" in text               # (ii)
    assert "do not change medications" in text          # (iii)


def test_disclaimer_explicitly_documented_as_allow_listed():
    """The disclaimer's text deliberately contains the words that the
    forbidden-verb linter forbids in normal user-facing strings:
    "diagnosis" and "treatment". These appear here because the
    boilerplate's whole purpose is to negate them ("is not a diagnosis",
    "do not start treatment"). This test documents the allow-list
    status explicitly so an auditor reviewing the linter's suppression
    can trace it.

    Mechanics: the linter does NOT scan AggregationOutput.disclaimer
    (Phase 1 narrowing decision). This test makes that decision visible
    by asserting the lemmas are present in the disclaimer AND the
    linter would have flagged them in an unprotected context."""
    out = _minimal_aggregation_output()
    standalone_findings = scan_text_for_forbidden_lemmas(out.disclaimer)
    # Sanity: the linter's scanner DOES find the lemmas when given the
    # disclaimer as raw text -- proving the boilerplate is genuinely
    # within scope of the linter's substantive logic.
    assert "diagnosis" in standalone_findings, (
        "Scanner did not find 'diagnosis' in the disclaimer; either the "
        "boilerplate has drifted or the scanner is broken."
    )
    assert "treatment" in standalone_findings, (
        "Scanner did not find 'treatment' in the disclaimer; either the "
        "boilerplate has drifted or the scanner is broken."
    )
    # The package-wide linter does NOT scan the disclaimer because the
    # AST walker filters to "string literals returned from public
    # functions" (Phase 1 narrowing). The disclaimer lives in a Field
    # default, not a return statement -- structurally outside scope.
    # commitments_log action item #17 is closed by THIS regression test
    # rather than by widening the linter (which would also flag the
    # FORBIDDEN_LEMMAS list itself, the §5.3 spec quotation in
    # docs/architecture_spec.md, and many other internal artifacts).


def test_disclaimer_does_not_drift_when_other_fields_change():
    """Constructing an AggregationOutput with non-default fields must
    not affect the disclaimer."""
    out = AggregationOutput(
        run_id="01J0000000000000000000000001",
        config_hash="a" * 64,
        locale="ar",
        population="uae_emirati",
        domains=[],
        score_results=[],
        red_flags=[],
        active_instruments={"cognitive": "moca", "osa": "stop_bang"},
        timestamp_utc="2026-05-04T12:34:56Z",
    )
    assert out.disclaimer == _EXPECTED_DISCLAIMER
