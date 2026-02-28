"""Post-check-in AI insight engine: generates personalized data-driven insights."""

from datetime import date, timedelta
from db.database import get_connection
from models.checkin import get_checkins_for_range


def get_or_generate_insight(user_id: int, today_str: str = None) -> str | None:
    """Get cached insight for today, or generate a new one."""
    if today_str is None:
        today_str = date.today().isoformat()

    conn = get_connection()
    try:
        # Check cache
        row = conn.execute(
            "SELECT insight_text FROM daily_insights WHERE user_id = ? AND insight_date = ?",
            (user_id, today_str),
        ).fetchone()
        if row:
            return row["insight_text"]
    finally:
        conn.close()

    # Generate new insight
    insight = _generate_insight(user_id, today_str)
    if insight:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO daily_insights (user_id, insight_date, insight_text) VALUES (?, ?, ?)",
                (user_id, today_str, insight),
            )
            conn.commit()
        finally:
            conn.close()
    return insight


def _generate_insight(user_id: int, today_str: str) -> str | None:
    """Generate an insight based on check-in data and trends."""
    # Get today's check-in
    conn = get_connection()
    try:
        today_data = conn.execute(
            "SELECT * FROM daily_checkins WHERE user_id = ? AND checkin_date = ?",
            (user_id, today_str),
        ).fetchone()
        if not today_data:
            return None
        today_data = dict(today_data)
    finally:
        conn.close()

    # Get recent 14 days of check-ins
    start_date = (date.fromisoformat(today_str) - timedelta(days=14)).isoformat()
    recent = get_checkins_for_range(user_id, start_date, today_str)

    if len(recent) < 3:
        return _simple_insight(today_data)

    # Try LLM-powered insight first
    try:
        return _llm_insight(user_id, today_data, recent)
    except Exception:
        pass

    # Fallback: deterministic pattern-based insight
    return _pattern_insight(today_data, recent)


def _llm_insight(user_id: int, today_data: dict, recent: list) -> str:
    """Generate an AI-powered insight using the LLM."""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-anthropic-api-key-here":
        raise ValueError("No API key configured")

    # Build compact data summary
    fields = ["mood", "energy", "nutrition_rating", "activity_rating",
              "sleep_rating", "stress_rating", "connection_rating", "substance_rating"]

    recent_summary = []
    for c in recent[-7:]:
        vals = {f: c.get(f) for f in fields if c.get(f) is not None}
        recent_summary.append(f"{c['checkin_date']}: {vals}")

    today_vals = {f: today_data.get(f) for f in fields if today_data.get(f) is not None}

    prompt = f"""You are a lifestyle medicine coach. Given this user's check-in data, provide ONE specific, data-backed insight in 2-3 sentences. Be warm, specific, and actionable.

Today's check-in: {today_vals}
Recent 7 days: {recent_summary}

Focus on patterns, correlations (e.g., sleep vs energy, activity vs mood), or notable changes. Don't be generic — reference specific numbers."""

    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _pattern_insight(today_data: dict, recent: list) -> str:
    """Deterministic pattern-based insight when no LLM is available."""
    insights = []

    # Sleep-energy correlation
    sleep_vals = [c["sleep_rating"] for c in recent if c.get("sleep_rating")]
    energy_vals = [c["energy"] for c in recent if c.get("energy")]
    if sleep_vals and energy_vals and today_data.get("sleep_rating") and today_data.get("energy"):
        avg_sleep = sum(sleep_vals) / len(sleep_vals)
        avg_energy = sum(energy_vals) / len(energy_vals)
        if today_data["sleep_rating"] >= avg_sleep + 1 and today_data["energy"] >= avg_energy + 1:
            insights.append(f"Great sleep pays off! Your sleep rating ({today_data['sleep_rating']}) is above your recent average ({avg_sleep:.1f}), and your energy is up too.")
        elif today_data["sleep_rating"] <= avg_sleep - 1:
            insights.append(f"Your sleep rating ({today_data['sleep_rating']}) is below your recent average ({avg_sleep:.1f}). Consider your wind-down routine tonight.")

    # Mood trend
    mood_vals = [c["mood"] for c in recent if c.get("mood")]
    if mood_vals and today_data.get("mood"):
        avg_mood = sum(mood_vals) / len(mood_vals)
        if today_data["mood"] >= avg_mood + 1.5:
            insights.append(f"Your mood ({today_data['mood']}) is notably higher than your {len(mood_vals)}-day average ({avg_mood:.1f}). What's working well for you?")
        elif today_data["mood"] <= avg_mood - 1.5:
            insights.append(f"Your mood ({today_data['mood']}) dipped below your average ({avg_mood:.1f}). Remember: tough days are part of the journey, and they don't erase your progress.")

    # Activity boost
    if today_data.get("activity_rating") and today_data.get("mood"):
        activity_mood_pairs = [(c.get("activity_rating"), c.get("mood")) for c in recent
                               if c.get("activity_rating") and c.get("mood")]
        if len(activity_mood_pairs) >= 5:
            high_activity = [m for a, m in activity_mood_pairs if a >= 7]
            low_activity = [m for a, m in activity_mood_pairs if a <= 4]
            if high_activity and low_activity:
                diff = sum(high_activity)/len(high_activity) - sum(low_activity)/len(low_activity)
                if diff > 1:
                    insights.append(f"Pattern spotted: on active days your mood averages {sum(high_activity)/len(high_activity):.1f} vs {sum(low_activity)/len(low_activity):.1f} on less active days. Movement is your mood booster!")

    # Consistency check
    if len(recent) >= 7:
        insights.append(f"You've checked in {len(recent)} of the last 14 days. {'Great consistency!' if len(recent) >= 10 else 'Try to check in daily — consistency reveals the patterns that drive real change.'}")

    return insights[0] if insights else None


def _simple_insight(today_data: dict) -> str:
    """Basic insight for users with little data history."""
    mood = today_data.get("mood", 5)
    if mood >= 7:
        return "You're feeling good today! Take note of what's contributing to this positive state — it's valuable data for building lasting habits."
    elif mood <= 3:
        return "Tough days happen and they're part of the journey. Even showing up to check in is a win. Be gentle with yourself today."
    return "Thanks for checking in! The more data you log, the more patterns we can find to help you thrive."
