"""Service for Daily Growth: meditation logging, quotes, nudges."""

import random
from datetime import date, timedelta
from db.database import get_connection
from config.growth_data import WISDOM_QUOTES, MINDFULNESS_NUDGES, REFLECTION_PROMPTS


# ══════════════════════════════════════════════════════════════════════════════
# MEDITATION
# ══════════════════════════════════════════════════════════════════════════════

def log_meditation(user_id, session_date, duration_minutes, meditation_type,
                   mood_before=None, mood_after=None, notes=None):
    """Save a meditation session and update the streak."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO meditation_sessions
               (user_id, session_date, duration_minutes, meditation_type,
                mood_before, mood_after, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, session_date, duration_minutes, meditation_type,
             mood_before, mood_after, notes),
        )
        conn.commit()
    finally:
        conn.close()
    # Recalculate streak
    _update_streak(user_id)


def get_meditation_streak(user_id):
    """Count consecutive days with at least one meditation session."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT DISTINCT session_date FROM meditation_sessions
               WHERE user_id = ? ORDER BY session_date DESC""",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return 0

    dates = [row["session_date"] for row in rows]
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    # Streak must include today or yesterday to be active
    if dates[0] != today and dates[0] != yesterday:
        return 0

    streak = 1
    for i in range(1, len(dates)):
        prev = date.fromisoformat(dates[i - 1])
        curr = date.fromisoformat(dates[i])
        if (prev - curr).days == 1:
            streak += 1
        else:
            break
    return streak


def _update_streak(user_id):
    """Update the cached streak in daily_growth_state."""
    streak = get_meditation_streak(user_id)
    today_str = date.today().isoformat()
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM daily_growth_state WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE daily_growth_state
                   SET meditation_streak = ?, updated_at = datetime('now')
                   WHERE user_id = ?""",
                (streak, user_id),
            )
        else:
            conn.execute(
                """INSERT INTO daily_growth_state
                   (user_id, meditation_streak, state_date)
                   VALUES (?, ?, ?)""",
                (user_id, streak, today_str),
            )
        conn.commit()
    finally:
        conn.close()


def get_meditation_history(user_id, days=30):
    """Get recent meditation sessions."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM meditation_sessions
               WHERE user_id = ? AND session_date >= ?
               ORDER BY session_date DESC, created_at DESC""",
            (user_id, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_meditation_stats(user_id, days=30):
    """Get meditation statistics for a period."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COUNT(*) as total_sessions,
                      COALESCE(SUM(duration_minutes), 0) as total_minutes,
                      COALESCE(AVG(duration_minutes), 0) as avg_duration,
                      COALESCE(AVG(mood_after), 0) as avg_mood_after
               FROM meditation_sessions
               WHERE user_id = ? AND session_date >= ?""",
            (user_id, cutoff),
        ).fetchone()

        # Type breakdown
        types = conn.execute(
            """SELECT meditation_type, COUNT(*) as cnt
               FROM meditation_sessions
               WHERE user_id = ? AND session_date >= ?
               GROUP BY meditation_type ORDER BY cnt DESC""",
            (user_id, cutoff),
        ).fetchall()

        return {
            "total_sessions": row["total_sessions"],
            "total_minutes": row["total_minutes"],
            "avg_duration": round(row["avg_duration"], 1),
            "avg_mood_after": round(row["avg_mood_after"], 1) if row["avg_mood_after"] else None,
            "type_breakdown": {r["meditation_type"]: r["cnt"] for r in types},
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# DAILY QUOTE
# ══════════════════════════════════════════════════════════════════════════════

def get_daily_quote(user_id):
    """Return today's quote. Assigns one if not yet assigned for today.
    Avoids repeats within the last 30 days."""
    today_str = date.today().isoformat()
    conn = get_connection()
    try:
        # Check if we already have a quote for today
        state = conn.execute(
            "SELECT current_quote_index, state_date FROM daily_growth_state WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if state and state["state_date"] == today_str and state["current_quote_index"] is not None:
            idx = state["current_quote_index"]
        else:
            idx = _pick_fresh_index(conn, user_id, "quote", len(WISDOM_QUOTES))
            _set_daily_state(conn, user_id, today_str, quote_index=idx)
            # Record interaction
            conn.execute(
                """INSERT OR IGNORE INTO quote_interactions
                   (user_id, quote_index, shown_date)
                   VALUES (?, ?, ?)""",
                (user_id, idx, today_str),
            )
            conn.commit()
    finally:
        conn.close()

    quote = WISDOM_QUOTES[idx]
    theme = quote["theme"]
    prompts = REFLECTION_PROMPTS.get(theme, REFLECTION_PROMPTS["awareness"])
    # Pick a stable reflection prompt based on quote index
    reflection = prompts[idx % len(prompts)]

    return {
        "index": idx,
        "text": quote["text"],
        "author": quote["author"],
        "source": quote["source"],
        "theme": theme,
        "reflection_prompt": reflection,
    }


def get_extra_quotes(user_id, count=4):
    """Return a few additional random quotes (for the 'More quotes' section)."""
    today_str = date.today().isoformat()
    conn = get_connection()
    try:
        state = conn.execute(
            "SELECT current_quote_index FROM daily_growth_state WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        current_idx = state["current_quote_index"] if state else -1
    finally:
        conn.close()

    available = [i for i in range(len(WISDOM_QUOTES)) if i != current_idx]
    selected = random.sample(available, min(count, len(available)))
    return [{"index": i, **WISDOM_QUOTES[i]} for i in selected]


def save_quote_reflection(user_id, quote_index, shown_date, text):
    """Save a user's reflection on a quote."""
    conn = get_connection()
    try:
        # Ensure interaction row exists
        conn.execute(
            """INSERT OR IGNORE INTO quote_interactions
               (user_id, quote_index, shown_date)
               VALUES (?, ?, ?)""",
            (user_id, quote_index, shown_date),
        )
        conn.execute(
            """UPDATE quote_interactions
               SET reflection_text = ?
               WHERE user_id = ? AND quote_index = ? AND shown_date = ?""",
            (text, user_id, quote_index, shown_date),
        )
        conn.commit()
    finally:
        conn.close()


def toggle_favorite_quote(user_id, quote_index, shown_date):
    """Toggle the favorite status of a quote. Returns new is_favorite value."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO quote_interactions
               (user_id, quote_index, shown_date)
               VALUES (?, ?, ?)""",
            (user_id, quote_index, shown_date),
        )
        row = conn.execute(
            """SELECT is_favorite FROM quote_interactions
               WHERE user_id = ? AND quote_index = ? AND shown_date = ?""",
            (user_id, quote_index, shown_date),
        ).fetchone()
        new_val = 0 if row and row["is_favorite"] else 1
        conn.execute(
            """UPDATE quote_interactions SET is_favorite = ?
               WHERE user_id = ? AND quote_index = ? AND shown_date = ?""",
            (new_val, user_id, quote_index, shown_date),
        )
        conn.commit()
        return new_val
    finally:
        conn.close()


def get_favorite_quotes(user_id):
    """Get all favorited quotes for a user."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT quote_index, shown_date, reflection_text
               FROM quote_interactions
               WHERE user_id = ? AND is_favorite = 1
               ORDER BY shown_date DESC""",
            (user_id,),
        ).fetchall()
        result = []
        for r in rows:
            idx = r["quote_index"]
            if 0 <= idx < len(WISDOM_QUOTES):
                q = WISDOM_QUOTES[idx]
                result.append({
                    "index": idx,
                    "text": q["text"],
                    "author": q["author"],
                    "source": q["source"],
                    "shown_date": r["shown_date"],
                    "reflection": r["reflection_text"],
                })
        return result
    finally:
        conn.close()


def get_quote_favorite_status(user_id, quote_index, shown_date):
    """Check if a specific quote is favorited."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT is_favorite FROM quote_interactions
               WHERE user_id = ? AND quote_index = ? AND shown_date = ?""",
            (user_id, quote_index, shown_date),
        ).fetchone()
        return row["is_favorite"] if row else 0
    finally:
        conn.close()


def get_existing_reflection(user_id, quote_index, shown_date):
    """Get existing reflection text for a quote."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT reflection_text FROM quote_interactions
               WHERE user_id = ? AND quote_index = ? AND shown_date = ?""",
            (user_id, quote_index, shown_date),
        ).fetchone()
        return row["reflection_text"] if row else None
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# DAILY NUDGE
# ══════════════════════════════════════════════════════════════════════════════

def get_daily_nudge(user_id):
    """Return today's mindfulness nudge. Avoids repeats within 30 days."""
    today_str = date.today().isoformat()
    conn = get_connection()
    try:
        state = conn.execute(
            "SELECT current_nudge_index, state_date FROM daily_growth_state WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if state and state["state_date"] == today_str and state["current_nudge_index"] is not None:
            idx = state["current_nudge_index"]
        else:
            idx = _pick_fresh_index(conn, user_id, "nudge", len(MINDFULNESS_NUDGES))
            _set_daily_state(conn, user_id, today_str, nudge_index=idx)
            conn.execute(
                """INSERT OR IGNORE INTO nudge_shown
                   (user_id, nudge_index, shown_date)
                   VALUES (?, ?, ?)""",
                (user_id, idx, today_str),
            )
            conn.commit()
    finally:
        conn.close()

    return {"index": idx, "text": MINDFULNESS_NUDGES[idx]}


def acknowledge_nudge(user_id, nudge_index, shown_date):
    """Mark a nudge as acknowledged."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO nudge_shown
               (user_id, nudge_index, shown_date)
               VALUES (?, ?, ?)""",
            (user_id, nudge_index, shown_date),
        )
        conn.execute(
            """UPDATE nudge_shown SET acknowledged = 1
               WHERE user_id = ? AND nudge_index = ? AND shown_date = ?""",
            (user_id, nudge_index, shown_date),
        )
        conn.commit()
    finally:
        conn.close()


def is_nudge_acknowledged(user_id, nudge_index, shown_date):
    """Check if today's nudge was already acknowledged."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT acknowledged FROM nudge_shown
               WHERE user_id = ? AND nudge_index = ? AND shown_date = ?""",
            (user_id, nudge_index, shown_date),
        ).fetchone()
        return bool(row and row["acknowledged"])
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _pick_fresh_index(conn, user_id, item_type, pool_size):
    """Pick a random index avoiding those shown in the last 30 days."""
    cutoff = (date.today() - timedelta(days=30)).isoformat()

    if item_type == "quote":
        rows = conn.execute(
            """SELECT DISTINCT quote_index FROM quote_interactions
               WHERE user_id = ? AND shown_date >= ?""",
            (user_id, cutoff),
        ).fetchall()
        recent = {r["quote_index"] for r in rows}
    else:
        rows = conn.execute(
            """SELECT DISTINCT nudge_index FROM nudge_shown
               WHERE user_id = ? AND shown_date >= ?""",
            (user_id, cutoff),
        ).fetchall()
        recent = {r["nudge_index"] for r in rows}

    available = [i for i in range(pool_size) if i not in recent]
    if not available:
        # Pool exhausted — allow repeats
        available = list(range(pool_size))

    return random.choice(available)


def _set_daily_state(conn, user_id, today_str, quote_index=None, nudge_index=None):
    """Create or update the daily growth state row."""
    existing = conn.execute(
        "SELECT id, state_date FROM daily_growth_state WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if existing:
        if existing["state_date"] != today_str:
            # New day — reset both slots
            conn.execute(
                """UPDATE daily_growth_state
                   SET current_quote_index = ?, current_nudge_index = ?,
                       state_date = ?, updated_at = datetime('now')
                   WHERE user_id = ?""",
                (quote_index, nudge_index, today_str, user_id),
            )
        else:
            # Same day — only update the slot being set
            if quote_index is not None:
                conn.execute(
                    """UPDATE daily_growth_state
                       SET current_quote_index = ?, updated_at = datetime('now')
                       WHERE user_id = ?""",
                    (quote_index, user_id),
                )
            if nudge_index is not None:
                conn.execute(
                    """UPDATE daily_growth_state
                       SET current_nudge_index = ?, updated_at = datetime('now')
                       WHERE user_id = ?""",
                    (nudge_index, user_id),
                )
    else:
        conn.execute(
            """INSERT INTO daily_growth_state
               (user_id, current_quote_index, current_nudge_index, state_date)
               VALUES (?, ?, ?, ?)""",
            (user_id, quote_index, nudge_index, today_str),
        )
    conn.commit()
