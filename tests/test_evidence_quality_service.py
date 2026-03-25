from services.evidence_quality_service import (
    contradiction_watchlist_for_display,
    detect_evidence_contradictions,
    guideline_priority_score,
    protocol_evidence_confidence,
    sort_guideline_first,
)


def test_guideline_priority_score_prefers_guideline_language():
    guideline_entry = {
        "title": "AHA Clinical Practice Guideline for Blood Pressure",
        "summary": "Guideline recommendation from AHA and ACC.",
        "key_finding": "Strong recommendation for risk reduction.",
        "journal": "Circulation",
        "authors": "AHA Writing Committee",
        "tags": "hypertension,guideline",
        "study_type": "guideline",
        "evidence_grade": "A",
        "journal_tier": "elite",
        "year": 2025,
    }
    rct_entry = {
        "title": "Randomized Trial of Exercise",
        "summary": "Exercise improved blood pressure.",
        "key_finding": "Effective intervention.",
        "journal": "Sports Med",
        "authors": "Doe et al.",
        "tags": "hypertension,exercise",
        "study_type": "rct",
        "evidence_grade": "A",
        "journal_tier": "q1",
        "year": 2025,
    }
    assert guideline_priority_score(guideline_entry, reference_year=2026) > guideline_priority_score(
        rct_entry, reference_year=2026
    )


def test_sort_guideline_first_places_guideline_on_top():
    rows = [
        {"study_type": "rct", "evidence_grade": "A", "journal_tier": "q1", "year": 2025, "title": "RCT"},
        {
            "study_type": "guideline",
            "evidence_grade": "A",
            "journal_tier": "elite",
            "year": 2024,
            "title": "Guideline",
            "summary": "Clinical practice guideline",
        },
    ]
    ranked = sort_guideline_first(rows, reference_year=2026)
    assert ranked[0]["title"] == "Guideline"


def test_detect_evidence_contradictions_finds_direction_conflict():
    rows = [
        {
            "id": 1,
            "title": "Older review",
            "summary": "Intervention reduced symptoms significantly.",
            "key_finding": "Reduced risk and improved outcomes.",
            "tags": "sleep,insomnia",
            "pillar_id": 3,
            "evidence_grade": "A",
            "year": 2021,
        },
        {
            "id": 2,
            "title": "Newer trial",
            "summary": "No effect on symptom reduction was observed.",
            "key_finding": "Not associated with improvement.",
            "tags": "sleep,insomnia",
            "pillar_id": 3,
            "evidence_grade": "B",
            "year": 2025,
        },
    ]
    contradictions = detect_evidence_contradictions(rows, min_year_gap=1, max_results=10)
    assert len(contradictions) == 1
    assert contradictions[0]["newer"]["id"] == 2
    assert contradictions[0]["older"]["id"] == 1


def test_contradiction_watchlist_filters_by_confidence():
    rows = [
        {
            "id": 10,
            "title": "Older positive",
            "summary": "Reduced risk in cohort.",
            "key_finding": "Improved outcomes.",
            "tags": "nutrition,fiber",
            "pillar_id": 1,
            "evidence_grade": "A",
            "year": 2020,
        },
        {
            "id": 11,
            "title": "Newer negative",
            "summary": "No effect found for risk reduction.",
            "key_finding": "Did not improve outcomes.",
            "tags": "nutrition,fiber",
            "pillar_id": 1,
            "evidence_grade": "A",
            "year": 2025,
        },
    ]
    watchlist = contradiction_watchlist_for_display(rows, min_confidence=8, max_results=5)
    assert len(watchlist) == 1


def test_protocol_evidence_confidence_returns_insufficient_without_studies():
    result = protocol_evidence_confidence([])
    assert result["label"] == "Insufficient"
    assert result["score"] == 0


def test_protocol_evidence_confidence_penalizes_contradictions():
    coherent = [
        {
            "title": "Guideline",
            "summary": "Guideline recommends intervention and shows reduced risk.",
            "key_finding": "Reduced risk.",
            "tags": "bp,hypertension",
            "study_type": "guideline",
            "evidence_grade": "A",
            "journal_tier": "elite",
            "year": 2025,
        },
        {
            "title": "Meta-analysis",
            "summary": "Intervention reduced risk.",
            "key_finding": "Improved outcomes.",
            "tags": "bp,hypertension",
            "study_type": "meta_analysis",
            "evidence_grade": "A",
            "journal_tier": "q1",
            "year": 2024,
        },
    ]
    contradictory = coherent + [
        {
            "title": "New trial",
            "summary": "No effect on risk reduction.",
            "key_finding": "Did not improve outcomes.",
            "tags": "bp,hypertension",
            "study_type": "rct",
            "evidence_grade": "B",
            "journal_tier": "q1",
            "year": 2026,
        }
    ]

    score_coherent = protocol_evidence_confidence(coherent, reference_year=2026)["score"]
    score_contradictory = protocol_evidence_confidence(contradictory, reference_year=2026)["score"]
    assert score_contradictory < score_coherent
