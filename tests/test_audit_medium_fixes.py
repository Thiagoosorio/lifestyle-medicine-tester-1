"""Regression tests for MEDIUM-severity fixes from the app-wide QA audit.

Covers the pure-function behaviour changes so they cannot silently regress:
  - Glasgow Prognostic Score is the *modified* GPS (albumin point only with
    inflammation).
  - HEI-2020 moderation components take the conservative (min) mapping.
  - Garmin epoch-millisecond timestamps parse to a local HH:MM.
  - The evidence-contradiction detector does not corrupt its outer loop
    variable via an inner-loop swap.
"""

from services.organ_score_service import calc_glasgow_prognostic
from services.diet_service import _estimate_hei_from_answers
from services.garmin_service import _garmin_hhmm
from services.evidence_quality_service import detect_evidence_contradictions


# ── Modified Glasgow Prognostic Score (#15) ──────────────────────────────

def test_mgps_isolated_hypoalbuminaemia_scores_zero():
    # CRP normal, albumin low: original GPS would award 1, mGPS awards 0.
    assert calc_glasgow_prognostic(crp=3.0, albumin=3.0) == 0


def test_mgps_inflammation_only_scores_one():
    assert calc_glasgow_prognostic(crp=25.0, albumin=4.0) == 1


def test_mgps_inflammation_and_hypoalbuminaemia_scores_two():
    assert calc_glasgow_prognostic(crp=25.0, albumin=3.0) == 2


def test_mgps_none_inputs_return_none():
    assert calc_glasgow_prognostic(crp=None, albumin=4.0) is None


# ── HEI-2020 moderation components (#17) ─────────────────────────────────

def test_hei_moderation_uses_min_adequacy_uses_max(monkeypatch):
    """Pin the actual reduction: a moderation component with a good (8) and a
    bad (2) mapped answer must resolve to 2 (min), while an adequacy component
    resolves to its best (max). This fails if the code reverts to max() for
    moderation."""
    import config.diet_data as dd
    monkeypatch.setattr(dd, "HEI_COMPONENTS", {
        "sodium": {"max_score": 10, "type": "moderation", "label": "Sodium"},
        "total_fruits": {"max_score": 5, "type": "adequacy", "label": "Fruits"},
    })
    monkeypatch.setattr(dd, "DIET_QUIZ_QUESTIONS", [
        {"hei_map": {0: {"sodium": 8}}},                 # q0: good sodium
        {"hei_map": {0: {"sodium": 2}}},                 # q1: bad sodium
        {"hei_map": {0: {"total_fruits": 1}, 1: {"total_fruits": 5}}},  # q2
    ])
    total, comps = _estimate_hei_from_answers([0, 0, 1])
    assert comps["sodium"] == 2          # min([8, 2]) — bad answer pulls it down
    assert comps["total_fruits"] == 5    # max([5]) — best adequacy evidence
    assert total == 7


# ── Garmin epoch-ms timestamps (#19) ─────────────────────────────────────

def test_garmin_hhmm_parses_epoch_ms_int():
    # 2021-06-01 22:30:00 UTC in ms.
    ts = 1622586600000
    assert _garmin_hhmm(ts) == "22:30"


def test_garmin_hhmm_parses_iso_string():
    assert _garmin_hhmm("2021-06-01T22:30:00.0") == "22:30"


def test_garmin_hhmm_handles_missing():
    assert _garmin_hhmm(None) is None
    assert _garmin_hhmm("") is None


# ── Evidence-contradiction loop-variable safety (#16) ────────────────────

def test_contradiction_detector_does_not_corrupt_outer_loop():
    """A newer 'positive' claim vs an older 'negative' claim on the same
    pillar/tag is a contradiction. With three items where the first is the
    newest, the inner swap must not corrupt later comparisons."""
    rows = [
        {"id": 1, "year": 2024, "pillar_id": 1, "tags": "sleep",
         "summary": "improved sleep and reduces insomnia", "evidence_grade": "A"},
        {"id": 2, "year": 2010, "pillar_id": 1, "tags": "sleep",
         "summary": "no effect and did not improve sleep", "evidence_grade": "B"},
        {"id": 3, "year": 2005, "pillar_id": 1, "tags": "sleep",
         "summary": "ineffective, higher risk of poor sleep", "evidence_grade": "C"},
    ]
    results = detect_evidence_contradictions(rows, min_year_gap=1)
    # Each contradiction must pair a genuinely newer item with an older one.
    assert results
    for c in results:
        assert c["newer"]["year"] > c["older"]["year"]


# ── Sex-agnostic biomarker classification (#42) ──────────────────────────

def test_sex_dependent_biomarker_not_scored_on_male_band_when_sex_unknown():
    from config.biomarkers_data import BIOMARKERS_BY_CODE
    from services.biomarker_service import classify_result

    testo = BIOMARKERS_BY_CODE["testosterone_total"]
    # A normal-for-female value must NOT be flagged critical/low just because
    # sex is unknown (previously it hit the male-defaulted floor).
    assert classify_result(40, testo) == "in_range"
    assert classify_result(40, testo, sex="female") == "in_range"
    # A normal-for-MALE value must NOT be flagged critical_high just because
    # the female band has an upper critical of 150 — the union must treat the
    # male band's unbounded (None) upper limit as unbounded, not absent.
    assert classify_result(600, testo) == "in_range"
    assert classify_result(600, testo, sex="male") == "in_range"
    # Genuinely extreme values are still flagged sex-agnostically.
    assert classify_result(5, testo) == "critical_low"


def test_hemoglobin_stays_usable_and_critical_still_fires_without_sex():
    from config.biomarkers_data import BIOMARKERS_BY_CODE
    from services.biomarker_service import classify_result

    hb = BIOMARKERS_BY_CODE["hemoglobin"]
    assert classify_result(14, hb) == "in_range"
    assert classify_result(5, hb) == "critical_low"


# ── Evidence entry pillar assignment (#41) ───────────────────────────────

def test_hs_crp_evidence_entry_has_a_pillar():
    import config.evidence_data as ed
    entries = next(
        v for v in vars(ed).values()
        if isinstance(v, list) and v and isinstance(v[0], dict) and "pmid" in v[0]
    )
    entry = next(e for e in entries if e["pmid"] == "14621448")
    assert entry["pillar_id"] is not None
