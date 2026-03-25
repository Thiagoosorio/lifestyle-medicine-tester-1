from services.dashboard_experience_service import (
    build_focus_mission,
    compute_readiness,
    get_focus_pillar_id,
    get_streak_badge,
)


def test_compute_readiness_uses_weighted_components():
    readiness = compute_readiness(
        sleep_score=80,
        recovery_score=60,
        habits_done=2,
        habits_total=4,
        checkins_last7=5,
    )
    assert readiness["score"] == 66
    assert readiness["zone"] == "Ready"


def test_compute_readiness_handles_missing_sleep_and_recovery():
    readiness = compute_readiness(
        sleep_score=None,
        recovery_score=None,
        habits_done=3,
        habits_total=3,
        checkins_last7=7,
    )
    assert readiness["score"] == 100
    assert readiness["zone"] == "Primed"


def test_get_focus_pillar_id_uses_stable_tie_break():
    scores = {1: 6, 2: 4, 3: 4, 4: 8, 5: 7, 6: 9}
    assert get_focus_pillar_id(scores) == 2


def test_build_focus_mission_includes_stage_note_when_available():
    scores = {1: 8, 2: 7, 3: 5, 4: 9, 5: 6, 6: 8}
    stages = {3: "preparation"}
    mission = build_focus_mission(scores, stages=stages)
    assert mission["pillar_id"] == 3
    assert "lock in time and place" in mission["stage_note"]


def test_get_streak_badge_returns_best_matching_milestone():
    badge = get_streak_badge(35)
    assert badge["label"] == "30 days"
    assert badge["days"] == 30
