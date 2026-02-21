"""Deterministic behavior change framework logic (Stages of Change, COM-B)."""

from config.settings import PILLARS, STAGES_OF_CHANGE, COMB_COMPONENTS
from db.database import get_connection


# ── Stage of Change Assessment Questions ────────────────────────────────────

STAGE_QUESTIONS = {}
for pid, pillar in PILLARS.items():
    name = pillar["display_name"]
    STAGE_QUESTIONS[pid] = [
        {"text": f"I am not currently thinking about changing my {name.lower()} habits.", "stage": "precontemplation"},
        {"text": f"I am thinking about improving my {name.lower()} but haven't started yet.", "stage": "contemplation"},
        {"text": f"I am planning to improve my {name.lower()} in the next month and taking small steps.", "stage": "preparation"},
        {"text": f"I have been actively working on improving my {name.lower()} for less than 6 months.", "stage": "action"},
        {"text": f"I have maintained good {name.lower()} habits for 6 months or more.", "stage": "maintenance"},
    ]


def get_stage_questions(pillar_id: int) -> list:
    return STAGE_QUESTIONS.get(pillar_id, [])


def assess_stage(selected_statement_index: int, pillar_id: int) -> str:
    questions = get_stage_questions(pillar_id)
    if 0 <= selected_statement_index < len(questions):
        return questions[selected_statement_index]["stage"]
    return "precontemplation"


# ── COM-B Barrier Assessment Questions ──────────────────────────────────────

COMB_QUESTIONS = {
    "capability_physical": "I have the physical ability to {action}.",
    "capability_psychological": "I know what I need to do and have the skills to {action}.",
    "opportunity_physical": "My environment and schedule make it easy to {action}.",
    "opportunity_social": "The people around me support me in {action}.",
    "motivation_reflective": "I have clear goals and reasons for {action}.",
    "motivation_automatic": "It feels natural/habitual for me to {action}.",
}

PILLAR_ACTIONS = {
    1: "eat a healthy, whole-food diet",
    2: "be physically active regularly",
    3: "get quality sleep consistently",
    4: "manage stress effectively",
    5: "maintain meaningful social connections",
    6: "avoid harmful substances",
}


def get_comb_questions(pillar_id: int) -> dict:
    action = PILLAR_ACTIONS.get(pillar_id, "make this change")
    return {
        key: template.format(action=action)
        for key, template in COMB_QUESTIONS.items()
    }


def identify_primary_barrier(scores: dict) -> str:
    """Given COM-B scores (1-5 per component), identify the primary barrier.
    Returns one of: 'capability', 'opportunity', 'motivation'.
    """
    capability = (scores.get("capability_physical", 3) + scores.get("capability_psychological", 3)) / 2
    opportunity = (scores.get("opportunity_physical", 3) + scores.get("opportunity_social", 3)) / 2
    motivation = (scores.get("motivation_reflective", 3) + scores.get("motivation_automatic", 3)) / 2

    barriers = {"capability": capability, "opportunity": opportunity, "motivation": motivation}
    return min(barriers, key=barriers.get)


def get_barrier_interventions(barrier_type: str) -> list:
    """Get recommended interventions based on the primary barrier type."""
    interventions = {
        "capability": [
            "Learn more about this area through reliable sources (ACLM, evidence-based guides)",
            "Practice the specific skills needed (e.g., cooking, exercise technique)",
            "Consider working with a professional (nutritionist, trainer, therapist)",
            "Start with simpler versions of the behavior and build up gradually",
        ],
        "opportunity": [
            "Modify your environment to make the healthy choice the easy choice",
            "Schedule the behavior at a consistent time each day",
            "Find a buddy or group for accountability and support",
            "Remove barriers and triggers in your physical environment",
            "Talk to the people around you about your goals and how they can help",
        ],
        "motivation": [
            "Reconnect with your deeper values and reasons for wanting this change",
            "Use habit stacking: link the new behavior to an existing habit",
            "Set up small rewards for consistent practice",
            "Track your progress visually to see how far you've come",
            "Start so small it feels almost too easy (the 'tiny habits' approach)",
        ],
    }
    return interventions.get(barrier_type, [])


def save_comb_assessment(user_id: int, pillar_id: int, scores: dict):
    """Save a COM-B assessment to the database."""
    primary = identify_primary_barrier(scores)
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO comb_assessments
               (user_id, pillar_id, capability_physical, capability_psychological,
                opportunity_physical, opportunity_social,
                motivation_reflective, motivation_automatic, primary_barrier)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, pillar_id,
             scores.get("capability_physical"),
             scores.get("capability_psychological"),
             scores.get("opportunity_physical"),
             scores.get("opportunity_social"),
             scores.get("motivation_reflective"),
             scores.get("motivation_automatic"),
             primary),
        )
        conn.commit()
    finally:
        conn.close()
