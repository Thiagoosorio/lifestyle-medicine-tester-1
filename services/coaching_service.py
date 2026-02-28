"""AI coaching service: LLM integration, context assembly, conversation management."""

import os
from pathlib import Path
from dotenv import load_dotenv
from db.database import get_connection
from config.prompts import BASE_SYSTEM_PROMPT, CONTEXT_TEMPLATE, get_context_prompt, build_user_context
from services.wheel_service import get_current_wheel, get_stages
from services.goal_service import get_active_goals
from services.habit_service import get_overall_streak, get_week_completion_rate
from services.checkin_service import get_week_averages
from datetime import date, timedelta

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _get_llm_provider():
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    return provider


def _assemble_user_context(user_id: int) -> str:
    """Gather all relevant user data to include in the prompt."""
    wheel = get_current_wheel(user_id)
    wheel_scores = wheel["scores"] if wheel else None

    stages = get_stages(user_id)
    active_goals = get_active_goals(user_id)
    streak = get_overall_streak(user_id)

    week_start = date.today() - timedelta(days=date.today().weekday())
    week_avg = get_week_averages(user_id, week_start)
    habit_rate = get_week_completion_rate(user_id, week_start)

    recent_trends = {
        "avg_mood": week_avg.get("mood"),
        "avg_energy": week_avg.get("energy"),
        "habit_completion": habit_rate,
        "streak": streak,
    }

    # Phase 2 data — wrapped in try/except so missing tables don't break coaching
    sleep_data = None
    recovery_data = None
    biomarker_data = None
    nutrition_data = None
    fasting_data_ctx = None

    try:
        from services.sleep_service import get_latest_sleep_score, get_sleep_averages, get_chronotype
        latest_score = get_latest_sleep_score(user_id)
        avgs = get_sleep_averages(user_id, days=7)
        chrono = get_chronotype(user_id)
        sleep_data = {
            "latest_score": latest_score,
            "avg_duration": avgs.get("avg_duration") if avgs else None,
            "avg_efficiency": avgs.get("avg_efficiency") if avgs else None,
            "chronotype": chrono.get("data", {}).get("name") if chrono else None,
        }
    except Exception:
        pass

    try:
        from services.recovery_service import calculate_recovery_score
        rec = calculate_recovery_score(user_id)
        if rec:
            recovery_data = {"score": rec["score"], "zone": rec["zone"]["label"]}
    except Exception:
        pass

    try:
        from services.biomarker_service import calculate_biomarker_score, get_biomarker_summary
        bio_score = calculate_biomarker_score(user_id)
        bio_summary = get_biomarker_summary(user_id)
        if bio_score is not None or bio_summary:
            summary_str = ", ".join(f"{v} {k}" for k, v in bio_summary.items() if v > 0) if bio_summary else None
            biomarker_data = {"score": bio_score, "summary": summary_str}
    except Exception:
        pass

    try:
        from services.nutrition_service import get_nutrition_averages
        nut_avgs = get_nutrition_averages(user_id, days=30)
        if nut_avgs and nut_avgs.get("log_count"):
            nutrition_data = {
                "avg_plant_score": nut_avgs.get("avg_plant_score"),
                "avg_fiber": nut_avgs.get("avg_fiber"),
                "avg_plants": nut_avgs.get("avg_plants"),
            }
    except Exception:
        pass

    try:
        from services.fasting_service import get_fasting_stats
        fast_stats = get_fasting_stats(user_id, days=30)
        if fast_stats and fast_stats.get("total_fasts", 0) > 0:
            fasting_data_ctx = {
                "completion_rate": fast_stats.get("completion_rate"),
                "avg_hours": fast_stats.get("avg_hours"),
                "streak": fast_stats.get("streak"),
            }
    except Exception:
        pass

    organ_score_data = None
    try:
        from services.organ_score_service import get_organ_score_summary
        organ_summary = get_organ_score_summary(user_id)
        if organ_summary:
            organ_score_data = organ_summary
    except Exception:
        pass

    exercise_data = None
    try:
        from services.exercise_service import get_exercise_summary_for_coach
        exercise_data = get_exercise_summary_for_coach(user_id)
    except Exception:
        pass

    sibo_data = None
    try:
        from services.sibo_service import get_symptom_averages as sibo_sym_avg, get_current_phase as sibo_phase, get_tolerance_summary as sibo_tol
        sym_avg = sibo_sym_avg(user_id, days=7)
        phase = sibo_phase(user_id)
        tolerance = sibo_tol(user_id)
        if sym_avg:
            sibo_data = {
                "symptom_averages_7d": sym_avg,
                "current_phase": phase["phase"] if phase else None,
                "tolerance_results": tolerance if tolerance else None,
            }
    except Exception:
        pass

    meditation_data = None
    try:
        from services.growth_service import get_meditation_streak, get_meditation_stats
        streak = get_meditation_streak(user_id)
        med_stats = get_meditation_stats(user_id, days=30)
        if med_stats and med_stats.get("total_sessions", 0) > 0:
            meditation_data = {
                "streak": streak,
                "total_sessions_30d": med_stats["total_sessions"],
                "total_minutes_30d": med_stats["total_minutes"],
                "avg_duration": med_stats["avg_duration"],
            }
    except Exception:
        pass

    calorie_data = None
    diet_data = None

    try:
        from services.calorie_service import get_calorie_trends, get_calorie_targets
        cal_trends = get_calorie_trends(user_id, days=7)
        if cal_trends:
            avg_cal = sum(t["total_calories"] for t in cal_trends) / len(cal_trends)
            avg_pro = sum(t["total_protein_g"] for t in cal_trends) / len(cal_trends)
            targets = get_calorie_targets(user_id)
            calorie_data = {
                "avg_calories_7d": round(avg_cal),
                "avg_protein_7d": round(avg_pro),
                "calorie_target": targets.get("calorie_target", targets.get("calories", 2000)),
                "days_logged": len(cal_trends),
            }
    except Exception:
        pass

    try:
        from services.diet_service import get_latest_assessment
        assessment = get_latest_assessment(user_id)
        if assessment:
            diet_data = {
                "diet_type": assessment.get("data", {}).get("name", assessment.get("diet_type")),
                "hei_score": assessment.get("hei_score"),
                "assessment_date": assessment.get("assessment_date"),
            }
    except Exception:
        pass

    return build_user_context(
        wheel_scores=wheel_scores,
        stages=stages,
        active_goals=active_goals,
        recent_trends=recent_trends,
        sleep_data=sleep_data,
        recovery_data=recovery_data,
        biomarker_data=biomarker_data,
        nutrition_data=nutrition_data,
        fasting_data=fasting_data_ctx,
        calorie_data=calorie_data,
        diet_data=diet_data,
        meditation_data=meditation_data,
        sibo_data=sibo_data,
        organ_score_data=organ_score_data,
        exercise_data=exercise_data,
    )


def _get_conversation_history(user_id: int, limit: int = 20) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT role, content FROM coaching_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        messages = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        return messages
    finally:
        conn.close()


def _save_message(user_id: int, role: str, content: str, context_type: str = None):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO coaching_messages (user_id, role, content, context_type) VALUES (?, ?, ?, ?)",
            (user_id, role, content, context_type),
        )
        conn.commit()
    finally:
        conn.close()


def get_coaching_response(user_id: int, message: str, context_type: str = "general") -> str:
    """Get an AI coaching response."""
    # Save the user's message
    _save_message(user_id, "user", message, context_type)

    # Assemble context
    user_context = _assemble_user_context(user_id)
    context_prompt = get_context_prompt(context_type)
    system_prompt = BASE_SYSTEM_PROMPT + "\n\n" + context_prompt + "\n\n" + CONTEXT_TEMPLATE.format(user_context=user_context)

    # Get conversation history
    history = _get_conversation_history(user_id, limit=20)

    # Call LLM
    provider = _get_llm_provider()
    try:
        if provider == "anthropic":
            response = _call_anthropic(system_prompt, history)
        elif provider == "openai":
            response = _call_openai(system_prompt, history)
        else:
            response = _fallback_response(context_type, user_context)
    except Exception as e:
        response = f"I'm having trouble connecting to the AI service right now. Error: {str(e)}\n\nIn the meantime, here's a quick tip: {_get_quick_tip(context_type)}"

    # Save the response
    _save_message(user_id, "assistant", response, context_type)
    return response


def _call_anthropic(system_prompt: str, messages: list) -> str:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text


def _call_openai(system_prompt: str, messages: list) -> str:
    from openai import OpenAI
    client = OpenAI()
    oai_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=oai_messages,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _fallback_response(context_type: str, user_context: str) -> str:
    """Simple rule-based response when no LLM is available."""
    responses = {
        "general": "I'd love to help you with your lifestyle medicine journey! To get AI-powered coaching, please set up your API key in the .env file. In the meantime, check out your Wheel of Life assessment to identify areas for growth.",
        "wheel_review": "Looking at your wheel assessment, focus on your two lowest-scoring pillars this week. Pick one small, achievable action for each. Remember: progress, not perfection!",
        "goal_help": "Great goals follow the SMART-EST framework. Make sure your goal is Specific, Measurable, Achievable, Relevant, and Time-bound. Consider what Evidence supports your approach and how you can Tailor it to your life.",
        "weekly_reflection": "Take a moment to appreciate what went well this week. What's one thing you're proud of? What's one small thing you'd like to do differently next week?",
        "barrier_analysis": "When you're stuck, ask yourself: Is it a knowledge/skill issue (Capability)? An environment/support issue (Opportunity)? Or a motivation/habit issue (Motivation)? Identifying the barrier type helps find the right solution.",
        "thought_check": "Share a thought you're having about your health journey. Common distortions include: All-or-Nothing Thinking ('I missed one day, it's all ruined'), Catastrophizing ('This will never work'), and Overgeneralization ('I always fail'). Recognizing the pattern is the first step to reframing it!",
    }
    return responses.get(context_type, responses["general"])


def _get_quick_tip(context_type: str) -> str:
    import random
    from config.settings import MOTIVATIONAL_QUOTES
    return random.choice(MOTIVATIONAL_QUOTES)


def clear_conversation(user_id: int):
    """Clear all coaching messages for a user."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM coaching_messages WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


# ── BloodGPT AI Blood Analysis ──────────────────────────────────────────────

_BLOOD_ANALYSIS_SYSTEM_PROMPT = """\
You are a medical-grade blood biomarker analysis AI with expertise in clinical laboratory \
medicine, preventive cardiology, endocrinology, and evidence-based lifestyle medicine. \
You analyse blood panels with the rigour of a board-certified internist while applying \
lifestyle medicine principles to identify root causes and actionable interventions.

Analyse the blood panel below in exactly 4 sections using the markdown headers shown. \
Be specific, quantitative, and evidence-based. Total response: 800-1000 words.

## 1. Holistic Interpretation
Analyse ALL markers together - never in isolation. Identify:
- Clinical patterns and syndrome clusters (metabolic syndrome: TG>150 + HDL<40/50 + glucose>100; insulin resistance: HOMA-IR pattern; thyroid dysfunction; vitamin/mineral deficiency clusters; anaemia subtypes; inflammation cascade; cardiovascular risk constellations)
- How markers interact and what combinations reveal beyond individual values
- Severity: use "pattern consistent with" / "suggests" / "warrants evaluation" - NEVER diagnose
- Distinguish standard-range (clinically acceptable) from optimal-range (lifestyle medicine target)
- Cite evidence grade (Grade A/B/C) for key clinical claims

## 2. Delta & Trend Analysis
For each marker that changed >5% since the previous panel:
- Direction: Improving / Worsening / Stable
- Velocity: absolute change per month
- Zone transitions (e.g., borderline HIGH -> HIGH): flag as PRIORITY
- Overall trajectory summary
If no previous data is available, write: "No previous lab data available for comparison."

## 3. Personalised Lifestyle Interventions
Provide 6-8 specific, ranked interventions for out-of-range markers. Format each as:
**[Intervention name]** - [specific, quantified action] | Expected impact: [magnitude from RCTs] | Evidence: Grade [A/B/C] | Mechanism: [one sentence]

Rank by: (1) evidence strength, (2) expected magnitude, (3) feasibility.
Examples of specificity required: "omega-3 2-4g/day EPA+DHA reduces TG by 20-30% (Grade A, meta-analysis of 21 RCTs)", "30 min/day aerobic exercise reduces fasting glucose 3-5 mg/dL (Grade A)".
Cover all abnormal categories present in the panel.

## 4. Next Steps
- 3-5 additional tests to consider, each with a one-line rationale
- Retest timeline per category (e.g., "lipids: recheck in 3 months after dietary intervention")
- Which values warrant prompt clinical attention vs monitoring at home
- 2-3 specific talking points for the next healthcare provider visit

STRICT RULES:
- Never diagnose. Use "pattern consistent with", "suggests", "warrants evaluation"
- Quantify all interventions with effect sizes from RCTs or meta-analyses where available
- Always recommend provider discussion for critical, rapidly worsening, or severely abnormal values
- Distinguish statistical abnormality from clinical significance
- Do not speculate beyond what the data shows

"""


def get_blood_ai_analysis(user_id: int, lab_date: str) -> str:
    """Generate a BloodGPT-style AI analysis for a specific lab date.

    Assembles structured biomarker context, calls Claude with a specialist
    medical analysis prompt, and returns the formatted markdown report.
    Returns an error/info string if data is insufficient or the API is unavailable.
    """
    from services.biomarker_service import get_blood_analysis_context

    context = get_blood_analysis_context(user_id, lab_date)
    if not context:
        return (
            "**Insufficient data for analysis.** "
            "Please log at least 3 biomarkers for this lab date and try again."
        )

    full_prompt = _BLOOD_ANALYSIS_SYSTEM_PROMPT + context

    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=2000,
            system=full_prompt,
            messages=[{"role": "user", "content": "Please analyse my blood panel."}],
        )
        return response.content[0].text
    except Exception as exc:
        return (
            f"**Unable to reach AI analysis service:** {exc}\n\n"
            "Check that your `ANTHROPIC_API_KEY` is set in the `.env` file."
        )


# ── Cycling-specific AI Coach ───────────────────────────────────────────────

_CYCLING_SYSTEM_PROMPT = """\
You are an expert cycling coach specialising in power-based training. \
You have access to the athlete's complete cycling training data below.

COACHING PRINCIPLES — follow every one strictly:
1. Quantitative only — cite specific watts, percentages, minutes, and TSS values in every recommendation. Never give vague advice like "train harder".
2. Reference workout names from the library when suggesting sessions (e.g. "do Antelope — 2×15 Sweet Spot at ~90% FTP").
3. Interpret CTL/ATL/TSB using the Banister impulse-response model: CTL = 42-day rolling average (fitness), ATL = 7-day rolling average (fatigue), TSB = CTL − ATL (form).
4. TSB zones: >+10 = fresh/risk of detraining; 0 to +10 = neutral; −20 to 0 = productive fatigue (normal training); −20 to −30 = high fatigue; below −30 = overreaching.
5. Progressive overload: NEVER recommend increasing intensity or volume if TSB < −20 or if ATL > CTL × 1.4.
6. FTP retest: ONLY recommend re-testing if BOTH: (a) CTL has been flat (< 2 TSS change) for 14+ consecutive days AND (b) it has been 42+ days since the last FTP test.
7. Progression levels (1.0–10.0): if a level is < 3.0 for an energy system, recommend starter workouts for that system; if > 7.0, suggest advanced intervals.
8. Always ground your answer in the athlete's actual numbers from the training data. Do not fabricate values.

{cycling_context}
"""

_CYCLING_COACH_HISTORY_LIMIT = 10  # last N messages with context_type='cycling'


def get_cycling_coaching_response(user_id: int, user_message: str) -> str:
    """Get a cycling-specific AI coaching response with full PMC and training context.

    Uses a specialist cycling system prompt with CTL/ATL/TSB data, progression levels,
    and recent ride history. Stores messages with context_type='cycling' to keep
    cycling history separate from general health coaching.
    """
    from services.cycling_service import get_cycling_coach_context

    cycling_context = get_cycling_coach_context(user_id)
    system_prompt = _CYCLING_SYSTEM_PROMPT.format(cycling_context=cycling_context)

    # Fetch last N cycling-specific messages for continuity
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT role, content FROM coaching_messages
               WHERE user_id = ? AND context_type = 'cycling'
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, _CYCLING_COACH_HISTORY_LIMIT),
        ).fetchall()
        history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    finally:
        conn.close()

    messages = history + [{"role": "user", "content": user_message}]

    # Call Anthropic with higher token limit for detailed interval plans
    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=1500,
            system=system_prompt,
            messages=messages,
        )
        ai_response = response.content[0].text
    except Exception as exc:
        ai_response = (
            f"Unable to reach the coaching service: {exc}\n\n"
            "Check that your ANTHROPIC_API_KEY is set in the .env file."
        )

    _save_message(user_id, "user", user_message, "cycling")
    _save_message(user_id, "assistant", ai_response, "cycling")
    return ai_response
