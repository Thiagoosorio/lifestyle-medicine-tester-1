"""Dashboard experience helpers inspired by top health and habit apps."""

from config.settings import MILESTONE_COLORS, MILESTONE_THRESHOLDS, PILLARS


_ZONE_DEFS = (
    {"min_score": 80, "label": "Primed", "summary": "Strong signals today. Push your highest-value habits.", "color": "#34C759"},
    {"min_score": 65, "label": "Ready", "summary": "Good baseline. Stay consistent with your core routines.", "color": "#64D2FF"},
    {"min_score": 45, "label": "Steady", "summary": "Mixed signals. Keep the day simple and protect momentum.", "color": "#FF9F0A"},
    {"min_score": 0, "label": "Recharge", "summary": "Lower readiness. Prioritize sleep, recovery, and basics.", "color": "#FF453A"},
)

_FOCUS_TEMPLATES = {
    1: {
        "title": "Nutrition Reset",
        "actions": [
            "Build one plate around vegetables first.",
            "Log at least two meals today.",
            "Add one high-fiber food (beans, oats, or leafy greens).",
        ],
        "cta_page": "pages/nutrition_logger.py",
        "cta_label": "Open Nutrition Logger",
    },
    2: {
        "title": "Movement Anchor",
        "actions": [
            "Complete one 20-minute walk or workout block.",
            "Log one exercise session.",
            "Take one extra movement break this afternoon.",
        ],
        "cta_page": "pages/exercise_tracker.py",
        "cta_label": "Open Exercise Tracker",
    },
    3: {
        "title": "Sleep Protect",
        "actions": [
            "Set your bedtime target before 9 PM.",
            "Keep screens off for 30 minutes before bed.",
            "Log your sleep details tomorrow morning.",
        ],
        "cta_page": "pages/sleep_tracker.py",
        "cta_label": "Open Sleep Tracker",
    },
    4: {
        "title": "Stress Downshift",
        "actions": [
            "Do one 5-minute breathing or mindfulness session.",
            "Take one short reset break between tasks.",
            "Write one line about what helped you feel calmer.",
        ],
        "cta_page": "pages/daily_growth.py",
        "cta_label": "Open Daily Growth",
    },
    5: {
        "title": "Connection Dose",
        "actions": [
            "Send one meaningful message to someone you care about.",
            "Schedule one short social touchpoint this week.",
            "Log one gratitude note tied to a relationship.",
        ],
        "cta_page": "pages/daily_growth.py",
        "cta_label": "Open Daily Growth",
    },
    6: {
        "title": "Clean Choice",
        "actions": [
            "Plan one substitute for a trigger behavior today.",
            "Track one moment of urge and response.",
            "Choose one alcohol-free or smoke-free window.",
        ],
        "cta_page": "pages/protocols.py",
        "cta_label": "Open Daily Protocols",
    },
}

_STAGE_NOTES = {
    "precontemplation": "Stage cue: keep it tiny today. Awareness beats pressure.",
    "contemplation": "Stage cue: choose one action that feels realistic right now.",
    "preparation": "Stage cue: lock in time and place for your first action.",
    "action": "Stage cue: protect consistency and remove friction.",
    "maintenance": "Stage cue: reinforce identity and prevent backsliding.",
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _to_score(value) -> float | None:
    if value is None:
        return None
    try:
        return _clamp(float(value))
    except (TypeError, ValueError):
        return None


def compute_readiness(
    sleep_score,
    recovery_score,
    habits_done: int,
    habits_total: int,
    checkins_last7: int,
) -> dict:
    """Compute a 0-100 readiness score from available daily signals."""
    components = []

    sleep = _to_score(sleep_score)
    if sleep is not None:
        components.append({"name": "Sleep", "score": sleep, "weight": 0.35})

    recovery = _to_score(recovery_score)
    if recovery is not None:
        components.append({"name": "Recovery", "score": recovery, "weight": 0.35})

    if habits_total > 0:
        habits_pct = _clamp(max(0, habits_done) / habits_total * 100.0)
        components.append({"name": "Habits", "score": habits_pct, "weight": 0.20})

    checkins = _clamp(max(0, min(7, checkins_last7)) / 7 * 100.0)
    components.append({"name": "Check-ins", "score": checkins, "weight": 0.10})

    total_weight = sum(c["weight"] for c in components)
    weighted_sum = sum(c["score"] * c["weight"] for c in components)
    score = int(round(weighted_sum / total_weight)) if total_weight > 0 else 50

    zone = next(z for z in _ZONE_DEFS if score >= z["min_score"])
    return {
        "score": score,
        "zone": zone["label"],
        "summary": zone["summary"],
        "color": zone["color"],
        "components": [
            {"name": c["name"], "score": int(round(c["score"]))}
            for c in components
        ],
    }


def get_focus_pillar_id(scores: dict[int, int]) -> int:
    """Pick the pillar that needs most attention (lowest score, stable tie-break)."""
    if not scores:
        return 1
    return sorted(scores.items(), key=lambda item: (item[1], item[0]))[0][0]


def build_focus_mission(scores: dict[int, int], stages: dict | None = None) -> dict:
    """Build a daily mission card based on the user's lowest-scoring pillar."""
    pillar_id = get_focus_pillar_id(scores)
    template = _FOCUS_TEMPLATES[pillar_id]
    pillar = PILLARS[pillar_id]

    stage = (stages or {}).get(pillar_id)
    stage_note = _STAGE_NOTES.get(stage)

    return {
        "pillar_id": pillar_id,
        "pillar_name": pillar["display_name"],
        "pillar_color": pillar["color"],
        "pillar_score": scores.get(pillar_id, 0),
        "title": template["title"],
        "actions": template["actions"],
        "cta_page": template["cta_page"],
        "cta_label": template["cta_label"],
        "stage": stage,
        "stage_note": stage_note,
    }


def get_streak_badge(streak_days: int) -> dict:
    """Return the highest milestone badge earned for a given streak length."""
    earned = None
    for milestone in MILESTONE_THRESHOLDS:
        if streak_days >= milestone["days"]:
            earned = milestone

    if not earned:
        return {"label": "Starter", "days": 0, "tier": "starter", "emoji": "-", "color": "#AEAEB2"}

    return {
        "label": earned["label"],
        "days": earned["days"],
        "tier": earned["tier"],
        "emoji": earned["emoji"],
        "color": MILESTONE_COLORS.get(earned["tier"], "#AEAEB2"),
    }
