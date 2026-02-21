"""AI coaching service: LLM integration, context assembly, conversation management."""

import os
from dotenv import load_dotenv
from db.database import get_connection
from config.prompts import BASE_SYSTEM_PROMPT, CONTEXT_TEMPLATE, get_context_prompt, build_user_context
from services.wheel_service import get_current_wheel, get_stages
from services.goal_service import get_active_goals
from services.habit_service import get_overall_streak, get_week_completion_rate
from services.checkin_service import get_week_averages
from datetime import date, timedelta

load_dotenv()


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

    return build_user_context(
        wheel_scores=wheel_scores,
        stages=stages,
        active_goals=active_goals,
        recent_trends=recent_trends,
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
        model="claude-sonnet-4-20250514",
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
