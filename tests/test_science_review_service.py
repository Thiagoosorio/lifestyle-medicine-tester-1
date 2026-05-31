from services.science_review_service import (
    build_evidence_library_audit,
    build_hpr_science_audit,
    build_science_review,
    build_score_science_audit,
    evidence_freshness,
)


def test_science_review_builds_all_sections():
    review = build_science_review(reference_year=2026)
    assert review["scores"]["total_scores"] > 20
    assert review["evidence"]["total_entries"] > 50
    assert review["hpr"]["total_protocol_rows"] == 97
    assert review["actions"]


def test_score_science_audit_tracks_lifecycle_and_tiers():
    audit = build_score_science_audit()
    assert audit["tier_counts"]["validated"] > 0
    assert "active" in audit["lifecycle_counts"]
    assert audit["score_rows"]


def test_evidence_library_audit_tracks_missing_metadata_and_freshness():
    audit = build_evidence_library_audit(reference_year=2026)
    assert audit["grade_counts"]
    assert audit["freshness_counts"]
    assert isinstance(audit["missing_metadata"], list)
    assert isinstance(audit["refresh_candidates"], list)


def test_hpr_science_audit_preserves_unvalidated_status():
    audit = build_hpr_science_audit()
    assert audit["evidence_status"] == "extracted_not_validated"
    assert audit["reference_issue_count"] >= 1


def test_evidence_freshness_boundaries():
    assert evidence_freshness(2026, reference_year=2026)["status"] == "fresh"
    assert evidence_freshness(2022, reference_year=2026)["status"] == "monitor"
    assert evidence_freshness(2020, reference_year=2026)["status"] == "stale"
    assert evidence_freshness(2018, reference_year=2026)["status"] == "legacy"
    assert evidence_freshness(None, reference_year=2026)["status"] == "undated"
