import services.organ_score_service as oss


def test_overall_composite_returns_none_without_scores(monkeypatch):
    monkeypatch.setattr(oss, "get_all_score_definitions", lambda: [{"code": "x", "organ_system": "liver"}])
    monkeypatch.setattr(oss, "get_latest_scores", lambda _uid: [])

    assert oss.compute_overall_organ_score(1) is None


def test_overall_composite_is_organ_balanced_not_formula_count_biased(monkeypatch):
    definitions = [
        {"code": "h1", "organ_system": "cardiovascular"},
        {"code": "h2", "organ_system": "cardiovascular"},
        {"code": "h3", "organ_system": "cardiovascular"},
        {"code": "h4", "organ_system": "cardiovascular"},
        {"code": "l1", "organ_system": "liver"},
    ]
    latest_scores = [
        {"code": "h1", "name": "H1", "organ_system": "cardiovascular", "tier": "validated", "severity": "optimal"},
        {"code": "h2", "name": "H2", "organ_system": "cardiovascular", "tier": "validated", "severity": "optimal"},
        {"code": "h3", "name": "H3", "organ_system": "cardiovascular", "tier": "validated", "severity": "optimal"},
        {"code": "h4", "name": "H4", "organ_system": "cardiovascular", "tier": "validated", "severity": "optimal"},
        {"code": "l1", "name": "L1", "organ_system": "liver", "tier": "validated", "severity": "critical"},
    ]
    monkeypatch.setattr(oss, "get_all_score_definitions", lambda: definitions)
    monkeypatch.setattr(oss, "get_latest_scores", lambda _uid: latest_scores)

    overall = oss.compute_overall_organ_score(42)
    assert overall is not None
    assert overall["overall_score_100"] == 56.0
    assert overall["overall_score_10"] == 5.6
    assert overall["overall_label"] == "Watchlist"

    organ_scores = {row["organ_system"]: row["score_100"] for row in overall["organ_breakdown"]}
    assert organ_scores["cardiovascular"] == 100.0
    assert organ_scores["liver"] == 12.0


def test_overall_composite_coverage_and_confidence(monkeypatch):
    definitions = [
        {"code": "c1", "organ_system": "cardiovascular"},
        {"code": "c2", "organ_system": "cardiovascular"},
        {"code": "l1", "organ_system": "liver"},
        {"code": "k1", "organ_system": "kidney"},
    ]
    latest_scores = [
        {"code": "c1", "name": "C1", "organ_system": "cardiovascular", "tier": "validated", "severity": "normal"},
        {"code": "c2", "name": "C2", "organ_system": "cardiovascular", "tier": "derived", "severity": "elevated"},
    ]
    monkeypatch.setattr(oss, "get_all_score_definitions", lambda: definitions)
    monkeypatch.setattr(oss, "get_latest_scores", lambda _uid: latest_scores)

    overall = oss.compute_overall_organ_score(99)
    assert overall is not None
    assert overall["organs_covered"] == 1
    assert overall["total_organs"] == 3
    assert overall["organ_coverage_pct"] == 33
    assert overall["score_coverage_pct"] == 50
    assert overall["validated_share_pct"] == 50
    assert overall["overall_confidence_label"] in {"Low", "Very Low"}
    assert set(overall["missing_organs"]) == {"liver", "kidney"}


def test_evidence_weight_is_primary_driver():
    # Evidence must dominate: validated-elevated still outweighs derived-optimal.
    validated_elevated = oss._composite_score_weight("validated", "elevated")
    derived_optimal = oss._composite_score_weight("derived", "optimal")
    assert validated_elevated > derived_optimal


def test_prevention_weight_boosts_early_warning_within_same_tier():
    validated_normal = oss._composite_score_weight("validated", "normal")
    validated_elevated = oss._composite_score_weight("validated", "elevated")
    assert validated_elevated > validated_normal


def test_optional_advanced_scores_do_not_reduce_core_coverage(monkeypatch):
    definitions = [
        {"code": "hsi", "organ_system": "liver"},
        {"code": "fli", "organ_system": "liver"},  # optional advanced
        {"code": "apob_risk", "organ_system": "cardiovascular"},  # optional advanced
    ]
    latest_scores = [
        {"code": "hsi", "name": "HSI", "organ_system": "liver", "tier": "validated", "severity": "normal"},
    ]
    monkeypatch.setattr(oss, "get_all_score_definitions", lambda: definitions)
    monkeypatch.setattr(oss, "get_latest_scores", lambda _uid: latest_scores)

    overall = oss.compute_overall_organ_score(77)
    assert overall is not None
    assert overall["computed_scores"] == 1
    assert overall["total_definitions"] == 1
    assert overall["score_coverage_pct"] == 100
    assert overall["optional_scores_used"] == 0
