from datetime import date
from models.goal import create_goal, get_goals, get_goal, update_goal_progress, update_goal_status


def create_smart_goal(user_id: int, data: dict) -> int:
    return create_goal(user_id, data)


def get_active_goals(user_id: int) -> list:
    return get_goals(user_id, status="active")


def get_all_goals(user_id: int, status: str = None, pillar_id: int = None) -> list:
    return get_goals(user_id, status=status, pillar_id=pillar_id)


def update_progress(goal_id: int, user_id: int, progress_pct: int, current_value: float = None, notes: str = ""):
    update_goal_progress(goal_id, user_id, progress_pct, current_value, notes)


def mark_completed(goal_id: int, user_id: int):
    update_goal_status(goal_id, user_id, "completed")


def mark_abandoned(goal_id: int, user_id: int, reason: str = ""):
    update_goal_status(goal_id, user_id, "abandoned", reason)


def pause_goal(goal_id: int, user_id: int):
    update_goal_status(goal_id, user_id, "paused")


def resume_goal(goal_id: int, user_id: int):
    update_goal_status(goal_id, user_id, "active")


def get_days_remaining(goal: dict) -> int:
    target = date.fromisoformat(goal["target_date"][:10])
    return (target - date.today()).days


def get_goal_stats(user_id: int) -> dict:
    all_goals = get_goals(user_id)
    active = [g for g in all_goals if g["status"] == "active"]
    completed = [g for g in all_goals if g["status"] == "completed"]
    abandoned = [g for g in all_goals if g["status"] == "abandoned"]
    return {
        "total": len(all_goals),
        "active": len(active),
        "completed": len(completed),
        "abandoned": len(abandoned),
        "completion_rate": len(completed) / max(len(completed) + len(abandoned), 1),
    }
