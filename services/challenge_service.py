"""Weekly Challenges system: auto-generated challenges based on the user's weakest pillars."""

from db.database import get_connection
from datetime import date, timedelta, datetime
from config.settings import PILLARS
import random

# ── Challenge Library ─────────────────────────────────────────────────────────
# Each pillar has at least 5 challenges.
# Keys: title, description, target_count, difficulty (easy/medium/hard), coin_reward (5/10/15)

CHALLENGE_LIBRARY = {
    1: [  # Nutrition
        {
            "title": "5-a-Day Champion",
            "description": "Eat at least 5 servings of vegetables for 5 days this week.",
            "target_count": 5,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Hydration Hero",
            "description": "Drink 8 glasses of water for 5 days this week.",
            "target_count": 5,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Cook From Scratch",
            "description": "Prepare 4 homemade meals from whole ingredients this week.",
            "target_count": 4,
            "difficulty": "hard",
            "coin_reward": 15,
        },
        {
            "title": "Sugar-Free Sprint",
            "description": "Go 3 days this week without any added sugar.",
            "target_count": 3,
            "difficulty": "hard",
            "coin_reward": 15,
        },
        {
            "title": "Rainbow Plate",
            "description": "Eat 5 different colored fruits or veggies in a single day, 3 times this week.",
            "target_count": 3,
            "difficulty": "easy",
            "coin_reward": 5,
        },
    ],
    2: [  # Physical Activity
        {
            "title": "Step It Up",
            "description": "Hit 8,000+ steps for 5 days this week.",
            "target_count": 5,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Morning Mover",
            "description": "Complete an exercise session before 9 AM, 4 times this week.",
            "target_count": 4,
            "difficulty": "hard",
            "coin_reward": 15,
        },
        {
            "title": "Strength Session",
            "description": "Complete 2 dedicated strength training workouts this week.",
            "target_count": 2,
            "difficulty": "easy",
            "coin_reward": 5,
        },
        {
            "title": "Active Commute",
            "description": "Walk or bike instead of driving for 3 trips this week.",
            "target_count": 3,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Movement Snacks",
            "description": "Take 5-minute movement breaks throughout the day, 4 days this week.",
            "target_count": 4,
            "difficulty": "easy",
            "coin_reward": 5,
        },
    ],
    3: [  # Sleep
        {
            "title": "Early Bird",
            "description": "Be in bed by 10:30 PM for 5 nights this week.",
            "target_count": 5,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Screen Sunset",
            "description": "No screens for 30 minutes before bed, 5 nights this week.",
            "target_count": 5,
            "difficulty": "hard",
            "coin_reward": 15,
        },
        {
            "title": "Sleep Sanctuary",
            "description": "Practice a sleep hygiene ritual (dim lights, cool room, calm) for 5 nights.",
            "target_count": 5,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Consistent Clock",
            "description": "Wake up at the same time (within 30 min) for 5 days this week.",
            "target_count": 5,
            "difficulty": "easy",
            "coin_reward": 5,
        },
        {
            "title": "Power Down",
            "description": "Complete a relaxation routine before bed for 4 nights this week.",
            "target_count": 4,
            "difficulty": "easy",
            "coin_reward": 5,
        },
    ],
    4: [  # Stress Management
        {
            "title": "Breathe Easy",
            "description": "Do a breathing exercise for 5 days this week.",
            "target_count": 5,
            "difficulty": "easy",
            "coin_reward": 5,
        },
        {
            "title": "Mindful Minutes",
            "description": "Meditate for 10+ minutes, 4 days this week.",
            "target_count": 4,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Nature Dose",
            "description": "Spend meaningful time outdoors for 3 days this week.",
            "target_count": 3,
            "difficulty": "easy",
            "coin_reward": 5,
        },
        {
            "title": "Gratitude Streak",
            "description": "Write down 3 things you're grateful for, 5 days this week.",
            "target_count": 5,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Digital Detox",
            "description": "Take 1 hour of screen-free relaxation, 4 days this week.",
            "target_count": 4,
            "difficulty": "hard",
            "coin_reward": 15,
        },
    ],
    5: [  # Social Connection
        {
            "title": "Connection Call",
            "description": "Have a meaningful conversation with someone, 4 days this week.",
            "target_count": 4,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Acts of Kindness",
            "description": "Perform 3 deliberate kind gestures this week.",
            "target_count": 3,
            "difficulty": "easy",
            "coin_reward": 5,
        },
        {
            "title": "Quality Time",
            "description": "Spend phone-free time with loved ones, 3 times this week.",
            "target_count": 3,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Reach Out",
            "description": "Contact someone you haven't spoken to in a while, 2 times this week.",
            "target_count": 2,
            "difficulty": "easy",
            "coin_reward": 5,
        },
        {
            "title": "Lunch Together",
            "description": "Share a meal with someone, 3 times this week.",
            "target_count": 3,
            "difficulty": "hard",
            "coin_reward": 15,
        },
    ],
    6: [  # Substance Avoidance
        {
            "title": "Clean Days",
            "description": "Stay substance-free for 5 days this week.",
            "target_count": 5,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Swap It Out",
            "description": "Replace a substance with a healthy alternative, 4 times this week.",
            "target_count": 4,
            "difficulty": "hard",
            "coin_reward": 15,
        },
        {
            "title": "Mindful Check",
            "description": "Pause and reflect before consuming any substance, 5 days this week.",
            "target_count": 5,
            "difficulty": "medium",
            "coin_reward": 10,
        },
        {
            "title": "Morning Clarity",
            "description": "Start each day substance-free for all 7 days this week.",
            "target_count": 7,
            "difficulty": "hard",
            "coin_reward": 15,
        },
        {
            "title": "Trigger Tracker",
            "description": "Identify and journal your substance triggers, 3 times this week.",
            "target_count": 3,
            "difficulty": "easy",
            "coin_reward": 5,
        },
    ],
}

# ── Pillar rating field mapping ───────────────────────────────────────────────
_PILLAR_RATING_FIELDS = {
    1: "nutrition_rating",
    2: "activity_rating",
    3: "sleep_rating",
    4: "stress_rating",
    5: "connection_rating",
    6: "substance_rating",
}


def _ensure_table():
    """Create the weekly_challenges table if it does not exist."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weekly_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                week_start TEXT NOT NULL,
                pillar_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                target_count INTEGER NOT NULL DEFAULT 5,
                current_count INTEGER NOT NULL DEFAULT 0,
                difficulty TEXT NOT NULL DEFAULT 'medium',
                coin_reward INTEGER NOT NULL DEFAULT 10,
                status TEXT NOT NULL DEFAULT 'active',
                completed_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_id, week_start, title)
            )
        """)
        conn.commit()
    finally:
        conn.close()


# Run on module import so the table is always ready.
_ensure_table()


def _get_week_start(ref_date: date | None = None) -> str:
    """Return the ISO date string for the Monday of the current week."""
    if ref_date is None:
        ref_date = date.today()
    monday = ref_date - timedelta(days=ref_date.weekday())
    return monday.isoformat()


def _get_weakest_pillars(user_id: int, count: int = 3) -> list[int]:
    """Return the *count* pillar IDs with the lowest average ratings over the
    last 14 days of check-ins. Falls back to random pillars when data is sparse."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT nutrition_rating, activity_rating, sleep_rating,
                      stress_rating, connection_rating, substance_rating
               FROM daily_checkins
               WHERE user_id = ? AND checkin_date >= date('now', '-14 days')
               ORDER BY checkin_date DESC""",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        # No check-in data at all -- pick randomly
        return random.sample(list(PILLARS.keys()), min(count, len(PILLARS)))

    # Compute averages per pillar
    averages: dict[int, float] = {}
    for pid, field in _PILLAR_RATING_FIELDS.items():
        values = [dict(r)[field] for r in rows if dict(r).get(field) is not None]
        averages[pid] = sum(values) / len(values) if values else 5.0  # default mid-score

    # Sort ascending (weakest first) and return top *count*
    sorted_pillars = sorted(averages, key=lambda pid: averages[pid])
    return sorted_pillars[:count]


def _generate_challenges(user_id: int) -> list[dict]:
    """Pick 3 challenges from the library based on the user's weakest pillars.
    Each challenge comes from a different pillar when possible."""
    week_start = _get_week_start()
    weakest = _get_weakest_pillars(user_id, count=3)

    challenges = []
    for pillar_id in weakest:
        pool = CHALLENGE_LIBRARY.get(pillar_id, [])
        if not pool:
            continue
        chosen = random.choice(pool)
        challenges.append({
            "user_id": user_id,
            "week_start": week_start,
            "pillar_id": pillar_id,
            "title": chosen["title"],
            "description": chosen["description"],
            "target_count": chosen["target_count"],
            "difficulty": chosen["difficulty"],
            "coin_reward": chosen["coin_reward"],
        })

    return challenges


def get_or_create_weekly_challenges(user_id: int) -> list[dict]:
    """Return this week's challenges. If none exist yet, auto-generate 3."""
    week_start = _get_week_start()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM weekly_challenges WHERE user_id = ? AND week_start = ? ORDER BY id",
            (user_id, week_start),
        ).fetchall()

        if rows:
            return [dict(r) for r in rows]

        # Generate new challenges for this week
        new_challenges = _generate_challenges(user_id)
        for ch in new_challenges:
            conn.execute(
                """INSERT OR IGNORE INTO weekly_challenges
                   (user_id, week_start, pillar_id, title, description,
                    target_count, difficulty, coin_reward)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ch["user_id"], ch["week_start"], ch["pillar_id"],
                    ch["title"], ch["description"], ch["target_count"],
                    ch["difficulty"], ch["coin_reward"],
                ),
            )
        conn.commit()

        # Re-fetch to get auto-generated IDs and defaults
        rows = conn.execute(
            "SELECT * FROM weekly_challenges WHERE user_id = ? AND week_start = ? ORDER BY id",
            (user_id, week_start),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def increment_challenge(user_id: int, challenge_id: int) -> dict:
    """Increment current_count by 1. If the target is reached, mark as completed
    and award coins. Returns the updated challenge dict."""
    from services.coin_service import award_coins

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM weekly_challenges WHERE id = ? AND user_id = ?",
            (challenge_id, user_id),
        ).fetchone()

        if not row:
            return {}

        challenge = dict(row)

        # Already completed -- no further increments
        if challenge["status"] == "completed":
            return challenge

        new_count = min(challenge["current_count"] + 1, challenge["target_count"])
        now_str = datetime.now().isoformat(timespec="seconds")

        if new_count >= challenge["target_count"]:
            conn.execute(
                """UPDATE weekly_challenges
                   SET current_count = ?, status = 'completed', completed_at = ?
                   WHERE id = ?""",
                (new_count, now_str, challenge_id),
            )
            conn.commit()

            # Award coins via the coin service
            reason = f"challenge_{challenge_id}"
            award_coins(user_id, challenge["coin_reward"], reason, date.today().isoformat())

            challenge["current_count"] = new_count
            challenge["status"] = "completed"
            challenge["completed_at"] = now_str
        else:
            conn.execute(
                "UPDATE weekly_challenges SET current_count = ? WHERE id = ?",
                (new_count, challenge_id),
            )
            conn.commit()
            challenge["current_count"] = new_count

        return challenge
    finally:
        conn.close()


def get_challenge_history(user_id: int, weeks_back: int = 4) -> list[dict]:
    """Return past challenges grouped by week_start, most recent first.
    Each entry: {week_start, challenges: [...], completed, total, coins_earned}."""
    cutoff = (date.today() - timedelta(weeks=weeks_back)).isoformat()
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM weekly_challenges
               WHERE user_id = ? AND week_start >= ?
               ORDER BY week_start DESC, id""",
            (user_id, cutoff),
        ).fetchall()
    finally:
        conn.close()

    # Group by week_start
    weeks: dict[str, list[dict]] = {}
    for r in rows:
        ch = dict(r)
        ws = ch["week_start"]
        weeks.setdefault(ws, []).append(ch)

    result = []
    for ws in sorted(weeks.keys(), reverse=True):
        challenges = weeks[ws]
        completed = sum(1 for c in challenges if c["status"] == "completed")
        total = len(challenges)
        coins = sum(c["coin_reward"] for c in challenges if c["status"] == "completed")
        result.append({
            "week_start": ws,
            "challenges": challenges,
            "completed": completed,
            "total": total,
            "coins_earned": coins,
        })

    return result


def get_all_time_stats(user_id: int) -> dict:
    """Return lifetime challenge statistics for the leaderboard section."""
    conn = get_connection()
    try:
        # Total completed
        total_completed = conn.execute(
            "SELECT COUNT(*) as cnt FROM weekly_challenges WHERE user_id = ? AND status = 'completed'",
            (user_id,),
        ).fetchone()["cnt"]

        # Total attempted
        total_attempted = conn.execute(
            "SELECT COUNT(*) as cnt FROM weekly_challenges WHERE user_id = ?",
            (user_id,),
        ).fetchone()["cnt"]

        # Completion rate
        completion_rate = (total_completed / total_attempted) if total_attempted > 0 else 0.0

        # Total coins earned from challenges
        total_coins = conn.execute(
            "SELECT COALESCE(SUM(coin_reward), 0) as coins FROM weekly_challenges WHERE user_id = ? AND status = 'completed'",
            (user_id,),
        ).fetchone()["coins"]

        # Best week ever (most completions in a single week)
        best_week_row = conn.execute(
            """SELECT week_start, COUNT(*) as cnt
               FROM weekly_challenges
               WHERE user_id = ? AND status = 'completed'
               GROUP BY week_start
               ORDER BY cnt DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        best_week = dict(best_week_row) if best_week_row else None

        # Streak: consecutive weeks where ALL challenges were completed
        weeks_rows = conn.execute(
            """SELECT week_start,
                      COUNT(*) as total,
                      SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
               FROM weekly_challenges
               WHERE user_id = ?
               GROUP BY week_start
               ORDER BY week_start DESC""",
            (user_id,),
        ).fetchall()

        perfect_streak = 0
        for wr in weeks_rows:
            w = dict(wr)
            if w["completed"] == w["total"] and w["total"] > 0:
                perfect_streak += 1
            else:
                break

        return {
            "total_completed": total_completed,
            "total_attempted": total_attempted,
            "completion_rate": completion_rate,
            "total_coins": total_coins,
            "best_week": best_week,
            "perfect_week_streak": perfect_streak,
        }
    finally:
        conn.close()
