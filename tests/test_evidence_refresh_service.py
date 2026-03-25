from services.evidence_refresh_service import (
    _extract_year,
    _infer_journal_tier,
    _map_pub_types_to_study_type,
    score_evidence_priority,
)


def test_map_pub_types_to_study_type_prefers_meta_analysis():
    study_type = _map_pub_types_to_study_type(["Randomized Controlled Trial", "Meta-Analysis"])
    assert study_type == "meta_analysis"


def test_map_pub_types_to_study_type_maps_rct():
    study_type = _map_pub_types_to_study_type(["Randomized Controlled Trial"])
    assert study_type == "rct"


def test_extract_year_handles_mixed_pubdate_formats():
    assert _extract_year("2025 Jan 14") == 2025
    assert _extract_year("2024-11-01") == 2024


def test_infer_journal_tier_detects_elite_journals():
    assert _infer_journal_tier("N Engl J Med") == "elite"
    assert _infer_journal_tier("The Lancet") == "elite"


def test_score_evidence_priority_rewards_quality_and_recency():
    high_quality = {
        "evidence_grade": "A",
        "study_type": "meta_analysis",
        "journal_tier": "elite",
        "year": 2025,
    }
    lower_quality = {
        "evidence_grade": "C",
        "study_type": "cross_sectional",
        "journal_tier": "q3",
        "year": 2018,
    }
    assert score_evidence_priority(high_quality, reference_year=2026) > score_evidence_priority(
        lower_quality, reference_year=2026
    )
