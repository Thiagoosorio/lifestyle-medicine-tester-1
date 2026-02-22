"""Service for Diet Pattern Assessment — pattern identification and HEI scoring."""

from db.database import get_connection
import json
from datetime import date


def assess_diet_pattern(user_id, answers):
    """
    Assess diet pattern from quiz answers.

    answers: list of selected option indices (0-3) for each of the 12 questions.

    Returns: {
        "diet_type": "mediterranean",
        "data": DIET_PATTERNS["mediterranean"],
        "hei_score": 72,
        "component_scores": {...},
        "all_pattern_scores": {"mediterranean": 28, "dash": 22, ...},
    }
    """
    from config.diet_data import DIET_PATTERNS, DIET_QUIZ_QUESTIONS

    diet_type, all_scores = _calculate_diet_type(answers)
    hei_score, component_scores = _estimate_hei_from_answers(answers)

    save_diet_assessment(user_id, diet_type, hei_score, component_scores, answers)

    return {
        "diet_type": diet_type,
        "data": DIET_PATTERNS[diet_type],
        "hei_score": hei_score,
        "component_scores": component_scores,
        "all_pattern_scores": all_scores,
    }


def _calculate_diet_type(answers):
    """Calculate which diet pattern best matches the answers."""
    from config.diet_data import DIET_QUIZ_QUESTIONS, DIET_PATTERNS

    pattern_scores = {k: 0 for k in DIET_PATTERNS}

    for i, option_idx in enumerate(answers):
        if i >= len(DIET_QUIZ_QUESTIONS):
            break
        q = DIET_QUIZ_QUESTIONS[i]
        if option_idx < len(q["options"]):
            scores = q["options"][option_idx].get("scores", {})
            for pattern, pts in scores.items():
                if pattern in pattern_scores:
                    pattern_scores[pattern] += pts

    best = max(pattern_scores, key=pattern_scores.get)
    return best, pattern_scores


def _estimate_hei_from_answers(answers):
    """Estimate HEI-2020 score from quiz answers."""
    from config.diet_data import DIET_QUIZ_QUESTIONS, HEI_COMPONENTS

    component_scores = {k: 0 for k in HEI_COMPONENTS}

    for i, option_idx in enumerate(answers):
        if i >= len(DIET_QUIZ_QUESTIONS):
            break
        q = DIET_QUIZ_QUESTIONS[i]
        hei_map = q.get("hei_map", {})
        if option_idx in hei_map:
            for comp, val in hei_map[option_idx].items():
                if comp in component_scores:
                    component_scores[comp] = max(component_scores[comp], val)

    # Clamp to max scores
    for comp, info in HEI_COMPONENTS.items():
        component_scores[comp] = min(component_scores[comp], info["max_score"])

    total = sum(component_scores.values())
    total = min(100, max(0, total))

    return total, component_scores


def save_diet_assessment(user_id, diet_type, hei_score, component_scores, answers):
    """Save assessment result to database."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO diet_assessments
               (user_id, assessment_date, diet_type, hei_score,
                component_scores, answers)
               VALUES (?,?,?,?,?,?)""",
            (user_id, date.today().isoformat(), diet_type, hei_score,
             json.dumps(component_scores), json.dumps(answers)),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_assessment(user_id):
    """Get the most recent diet assessment for a user."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT * FROM diet_assessments
               WHERE user_id = ? ORDER BY assessment_date DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["component_scores"] = json.loads(result["component_scores"]) if result["component_scores"] else {}
        result["answers"] = json.loads(result["answers"]) if result["answers"] else []
        from config.diet_data import DIET_PATTERNS
        result["data"] = DIET_PATTERNS.get(result["diet_type"], {})
        return result
    finally:
        conn.close()


def get_assessment_history(user_id):
    """Get all diet assessments for trend display."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM diet_assessments
               WHERE user_id = ? ORDER BY assessment_date""",
            (user_id,),
        ).fetchall()
        results = []
        from config.diet_data import DIET_PATTERNS
        for r in rows:
            d = dict(r)
            d["component_scores"] = json.loads(d["component_scores"]) if d["component_scores"] else {}
            d["data"] = DIET_PATTERNS.get(d["diet_type"], {})
            results.append(d)
        return results
    finally:
        conn.close()


def get_hei_score_zone(score):
    """Return the zone info for a given HEI score."""
    from config.diet_data import HEI_SCORE_ZONES
    for zone in HEI_SCORE_ZONES.values():
        if zone["min"] <= score <= zone["max"]:
            return zone
    return HEI_SCORE_ZONES["poor"]
