from models.assessment import (
    create_assessment,
    get_latest_assessment,
    get_assessment_history,
    get_latest_stages,
)
from config.settings import PILLARS, get_score_label


def submit_assessment(user_id: int, scores: dict, notes: dict = None, stages: dict = None) -> str:
    return create_assessment(user_id, scores, notes, stages)


def get_current_wheel(user_id: int) -> dict | None:
    return get_latest_assessment(user_id)


def get_history(user_id: int, limit: int = 20) -> list:
    return get_assessment_history(user_id, limit)


def get_stages(user_id: int) -> dict:
    return get_latest_stages(user_id)


def compute_changes(user_id: int) -> dict | None:
    """Compare latest two assessments and return deltas per pillar."""
    history = get_assessment_history(user_id, limit=2)
    if len(history) < 2:
        return None

    current = history[0]["scores"]
    previous = history[1]["scores"]

    changes = {}
    for pid in PILLARS:
        cur = current.get(pid, 0)
        prev = previous.get(pid, 0)
        delta = cur - prev
        changes[pid] = {
            "current": cur,
            "previous": prev,
            "delta": delta,
            "direction": "up" if delta > 0 else ("down" if delta < 0 else "same"),
            "label": get_score_label(cur),
        }
    return changes


def get_total_score(scores: dict) -> int:
    return sum(scores.values())


def get_score_summary(scores: dict) -> str:
    total = get_total_score(scores)
    if total <= 18:
        return "Below Average — Focus on building foundational habits"
    elif total <= 30:
        return "Average — Good start, room for growth"
    elif total <= 42:
        return "Very Good — Strong lifestyle medicine practice"
    return "Excellent — You're thriving across all pillars!"
