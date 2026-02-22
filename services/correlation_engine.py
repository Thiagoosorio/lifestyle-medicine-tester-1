"""Smart Correlation / Insights Engine.

Auto-detects correlations between habits and mood/energy, and generates
personalized natural-language insights from check-in and habit data.
"""

from datetime import date, timedelta
from db.database import get_connection
from config.settings import PILLARS

# ── Mapping helpers ────────────────────────────────────────────────────────

PILLAR_FIELDS = {
    1: "nutrition_rating",
    2: "activity_rating",
    3: "sleep_rating",
    4: "stress_rating",
    5: "connection_rating",
    6: "substance_rating",
}

PILLAR_FIELD_TO_ID = {v: k for k, v in PILLAR_FIELDS.items()}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── 5. Pearson correlation (no external deps) ─────────────────────────────

def pearson_r(x: list, y: list) -> float:
    """Compute the Pearson correlation coefficient between two equal-length
    numeric lists.  Returns 0.0 when the inputs are too short or have zero
    variance.
    """
    n = len(x)
    if n != len(y) or n < 3:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = 0.0
    den_x = 0.0
    den_y = 0.0
    for xi, yi in zip(x, y):
        dx = xi - mean_x
        dy = yi - mean_y
        num += dx * dy
        den_x += dx * dx
        den_y += dy * dy

    denom = (den_x * den_y) ** 0.5
    if denom == 0:
        return 0.0
    return num / denom


# ── 1. Habit ↔ mood / energy correlations ─────────────────────────────────

def get_habit_mood_correlations(user_id: int, days_back: int = 90) -> list[dict]:
    """For each active habit, compare avg mood/energy on days the habit was
    completed vs days it was not.  Returns a sorted list of dicts.
    """
    start_date = (date.today() - timedelta(days=days_back)).isoformat()
    end_date = date.today().isoformat()

    conn = get_connection()
    try:
        # Active habits
        habits = conn.execute(
            "SELECT id, name, pillar_id FROM habits "
            "WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchall()
        habits = [dict(h) for h in habits]

        if not habits:
            return []

        # All check-in dates with mood & energy in the window
        checkins = conn.execute(
            "SELECT checkin_date, mood, energy FROM daily_checkins "
            "WHERE user_id = ? AND checkin_date BETWEEN ? AND ? "
            "AND mood IS NOT NULL AND energy IS NOT NULL",
            (user_id, start_date, end_date),
        ).fetchall()
        checkins = [dict(c) for c in checkins]

        if not checkins:
            return []

        checkin_map = {c["checkin_date"]: c for c in checkins}
        checkin_dates = set(checkin_map.keys())
        total_days = len(checkin_dates)

        # All habit completions in the window
        logs = conn.execute(
            "SELECT habit_id, log_date, completed_count FROM habit_log "
            "WHERE user_id = ? AND log_date BETWEEN ? AND ? AND completed_count > 0",
            (user_id, start_date, end_date),
        ).fetchall()

        # Build set of (habit_id, date) for completed entries
        done_set: set[tuple[int, str]] = set()
        for row in logs:
            done_set.add((row["habit_id"], row["log_date"]))

    finally:
        conn.close()

    results = []
    for habit in habits:
        hid = habit["id"]
        mood_with, energy_with = [], []
        mood_without, energy_without = [], []

        for d in checkin_dates:
            c = checkin_map[d]
            if (hid, d) in done_set:
                mood_with.append(c["mood"])
                energy_with.append(c["energy"])
            else:
                mood_without.append(c["mood"])
                energy_without.append(c["energy"])

        times_done = len(mood_with)
        if times_done == 0 or len(mood_without) == 0:
            continue  # Can't compare if one bucket is empty

        avg_mood_with = sum(mood_with) / len(mood_with)
        avg_mood_without = sum(mood_without) / len(mood_without)
        avg_energy_with = sum(energy_with) / len(energy_with)
        avg_energy_without = sum(energy_without) / len(energy_without)

        mood_diff = avg_mood_with - avg_mood_without
        energy_diff = avg_energy_with - avg_energy_without

        # Strength classification based on the larger absolute difference
        max_diff = max(abs(mood_diff), abs(energy_diff))
        if max_diff > 1.5:
            strength = "strong"
        elif max_diff > 0.8:
            strength = "moderate"
        else:
            strength = "weak"

        results.append({
            "habit_name": habit["name"],
            "pillar_id": habit["pillar_id"],
            "mood_with": round(avg_mood_with, 2),
            "mood_without": round(avg_mood_without, 2),
            "mood_diff": round(mood_diff, 2),
            "energy_with": round(avg_energy_with, 2),
            "energy_without": round(avg_energy_without, 2),
            "energy_diff": round(energy_diff, 2),
            "times_done": times_done,
            "total_days": total_days,
            "correlation_strength": strength,
        })

    # Sort by largest positive mood_diff descending
    results.sort(key=lambda r: r["mood_diff"], reverse=True)
    return results


# ── 2. Pillar-pair correlations ────────────────────────────────────────────

def get_pillar_correlations(user_id: int, days_back: int = 90) -> dict:
    """Compute pairwise Pearson correlations between pillar ratings.
    Returns a dict of {(pillar_a_id, pillar_b_id): correlation_coefficient}
    including only pairs with |r| > 0.3.
    """
    start_date = (date.today() - timedelta(days=days_back)).isoformat()
    end_date = date.today().isoformat()

    fields = list(PILLAR_FIELDS.values())
    cols = ", ".join(fields)

    conn = get_connection()
    try:
        rows = conn.execute(
            f"SELECT {cols} FROM daily_checkins "
            "WHERE user_id = ? AND checkin_date BETWEEN ? AND ?",
            (user_id, start_date, end_date),
        ).fetchall()
        rows = [dict(r) for r in rows]
    finally:
        conn.close()

    if len(rows) < 5:
        return {}

    # Build per-pillar value lists (skip None entries per pair)
    pillar_ids = list(PILLAR_FIELDS.keys())
    correlations = {}

    for i in range(len(pillar_ids)):
        for j in range(i + 1, len(pillar_ids)):
            pid_a = pillar_ids[i]
            pid_b = pillar_ids[j]
            field_a = PILLAR_FIELDS[pid_a]
            field_b = PILLAR_FIELDS[pid_b]

            xs, ys = [], []
            for row in rows:
                va = row.get(field_a)
                vb = row.get(field_b)
                if va is not None and vb is not None:
                    xs.append(va)
                    ys.append(vb)

            if len(xs) < 5:
                continue

            r = pearson_r(xs, ys)
            if abs(r) > 0.3:
                correlations[(pid_a, pid_b)] = round(r, 2)

    return correlations


# ── 3. Pattern insights ───────────────────────────────────────────────────

def get_pattern_insights(user_id: int, days_back: int = 60) -> list[str]:
    """Generate natural-language insight strings from data patterns.
    Returns max 8 insights sorted by significance.
    """
    insights: list[tuple[float, str]] = []  # (importance_score, text)

    start_date = (date.today() - timedelta(days=days_back)).isoformat()
    end_date = date.today().isoformat()

    conn = get_connection()
    try:
        checkins = conn.execute(
            "SELECT * FROM daily_checkins "
            "WHERE user_id = ? AND checkin_date BETWEEN ? AND ? "
            "ORDER BY checkin_date",
            (user_id, start_date, end_date),
        ).fetchall()
        checkins = [dict(c) for c in checkins]

        habits = conn.execute(
            "SELECT id, name, pillar_id FROM habits "
            "WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchall()
        habits = [dict(h) for h in habits]

        logs = conn.execute(
            "SELECT habit_id, log_date, completed_count FROM habit_log "
            "WHERE user_id = ? AND log_date BETWEEN ? AND ? AND completed_count > 0",
            (user_id, start_date, end_date),
        ).fetchall()
        logs = [dict(l) for l in logs]
    finally:
        conn.close()

    if not checkins:
        return []

    checkin_map = {c["checkin_date"]: c for c in checkins}
    checkin_dates = set(checkin_map.keys())
    done_set: set[tuple[int, str]] = {(l["habit_id"], l["log_date"]) for l in logs}

    # ── Insight: Top 3 mood boosters (habits) ──────────────────────────────
    correlations = get_habit_mood_correlations(user_id, days_back)
    positive_habits = [h for h in correlations if h["mood_diff"] > 0.3]
    if len(positive_habits) >= 3:
        top3 = positive_habits[:3]
        names = ", ".join(h["habit_name"] for h in top3)
        insights.append((9.0, f"Your top 3 mood boosters: {names}"))
    elif len(positive_habits) >= 1:
        names = ", ".join(h["habit_name"] for h in positive_habits)
        insights.append((8.0, f"Your biggest mood booster{'s' if len(positive_habits) > 1 else ''}: {names}"))

    # ── Insight: Per-habit mood lift ───────────────────────────────────────
    for h in correlations[:5]:
        if h["mood_diff"] > 0.5:
            insights.append(
                (h["mood_diff"] * 4,
                 f"Your mood is {h['mood_diff']:.1f} points higher on days "
                 f"you complete \"{h['habit_name']}\"")
            )

    # ── Insight: Pillar-pair correlations ──────────────────────────────────
    pillar_corrs = get_pillar_correlations(user_id, days_back)
    for (pa, pb), r in sorted(pillar_corrs.items(), key=lambda kv: abs(kv[1]), reverse=True):
        name_a = PILLARS[pa]["display_name"]
        name_b = PILLARS[pb]["display_name"]
        strength = "strongly" if abs(r) > 0.7 else "moderately"

        if r > 0.3:
            verb = f"better {name_a.lower()} = more {name_b.lower()}"
            insights.append(
                (abs(r) * 6,
                 f"{name_a} and {name_b} are {strength} correlated "
                 f"(r={r:.2f}) \u2014 {verb}")
            )
        elif r < -0.3:
            insights.append(
                (abs(r) * 6,
                 f"{name_a} and {name_b} show an inverse correlation "
                 f"(r={r:.2f})")
            )
        if len(insights) > 12:
            break  # Enough candidates

    # ── Insight: Best day of the week ──────────────────────────────────────
    day_moods: dict[int, list[float]] = {}
    for c in checkins:
        if c.get("mood") is not None:
            dow = date.fromisoformat(c["checkin_date"]).weekday()
            day_moods.setdefault(dow, []).append(c["mood"])

    if day_moods:
        best_dow = max(day_moods, key=lambda d: sum(day_moods[d]) / len(day_moods[d]))
        avg = sum(day_moods[best_dow]) / len(day_moods[best_dow])
        if len(day_moods[best_dow]) >= 2:
            insights.append(
                (5.0,
                 f"Your strongest day is {DAY_NAMES[best_dow]} "
                 f"(avg mood: {avg:.1f})")
            )

    # ── Insight: Weekend vs weekday comparison per pillar ──────────────────
    for pid, field in PILLAR_FIELDS.items():
        weekday_vals, weekend_vals = [], []
        for c in checkins:
            val = c.get(field)
            if val is None:
                continue
            dow = date.fromisoformat(c["checkin_date"]).weekday()
            if dow < 5:
                weekday_vals.append(val)
            else:
                weekend_vals.append(val)

        if len(weekday_vals) >= 3 and len(weekend_vals) >= 2:
            wd_avg = sum(weekday_vals) / len(weekday_vals)
            we_avg = sum(weekend_vals) / len(weekend_vals)
            diff = we_avg - wd_avg
            pillar_name = PILLARS[pid]["display_name"]

            if diff < -1.0:
                insights.append(
                    (abs(diff) * 3,
                     f"Weekends show lower {pillar_name} ratings "
                     f"({we_avg:.1f} vs {wd_avg:.1f} on weekdays) \u2014 "
                     f"consider a weekend {pillar_name.lower()} routine")
                )
            elif diff > 1.0:
                insights.append(
                    (abs(diff) * 3,
                     f"Your {pillar_name} ratings are higher on weekends "
                     f"({we_avg:.1f} vs {wd_avg:.1f} on weekdays) \u2014 "
                     f"try bringing that weekend energy into your work week")
                )

    # ── Insight: Month-over-month trend per pillar ─────────────────────────
    if len(checkins) >= 14:
        mid = len(checkins) // 2
        first_half = checkins[:mid]
        second_half = checkins[mid:]

        for pid, field in PILLAR_FIELDS.items():
            first_vals = [c[field] for c in first_half if c.get(field) is not None]
            second_vals = [c[field] for c in second_half if c.get(field) is not None]

            if len(first_vals) >= 3 and len(second_vals) >= 3:
                first_avg = sum(first_vals) / len(first_vals)
                second_avg = sum(second_vals) / len(second_vals)
                trend = second_avg - first_avg
                pillar_name = PILLARS[pid]["display_name"]

                if trend >= 1.0:
                    insights.append(
                        (trend * 3,
                         f"You've been trending upward in {pillar_name} \u2014 "
                         f"up {trend:.1f} points over the last month")
                    )
                elif trend <= -1.0:
                    insights.append(
                        (abs(trend) * 3,
                         f"{pillar_name} has been trending downward \u2014 "
                         f"down {abs(trend):.1f} points recently. "
                         f"What changed?")
                    )

    # ── Insight: Streak impact analysis ────────────────────────────────────
    _add_streak_insights(habits, done_set, checkin_map, checkin_dates, insights)

    # De-duplicate, sort by importance, return top 8
    seen_texts: set[str] = set()
    unique: list[tuple[float, str]] = []
    for score, text in insights:
        if text not in seen_texts:
            seen_texts.add(text)
            unique.append((score, text))

    unique.sort(key=lambda t: t[0], reverse=True)
    return [text for _, text in unique[:8]]


def _add_streak_insights(
    habits: list[dict],
    done_set: set[tuple[int, str]],
    checkin_map: dict[str, dict],
    checkin_dates: set[str],
    insights: list[tuple[float, str]],
):
    """Analyze how consecutive-day streaks affect mood/energy."""
    for habit in habits:
        hid = habit["id"]

        # Build sorted list of dates the habit was completed
        completed_dates = sorted(d for (h, d) in done_set if h == hid)
        if len(completed_dates) < 5:
            continue

        # Find streaks of 3+ consecutive days
        streak_dates: set[str] = set()
        current_streak: list[str] = [completed_dates[0]]

        for i in range(1, len(completed_dates)):
            prev = date.fromisoformat(completed_dates[i - 1])
            curr = date.fromisoformat(completed_dates[i])
            if (curr - prev).days == 1:
                current_streak.append(completed_dates[i])
            else:
                if len(current_streak) >= 3:
                    streak_dates.update(current_streak)
                current_streak = [completed_dates[i]]
        if len(current_streak) >= 3:
            streak_dates.update(current_streak)

        if not streak_dates:
            continue

        non_streak_done = {d for (h, d) in done_set if h == hid} - streak_dates

        streak_moods = [
            checkin_map[d]["mood"]
            for d in streak_dates
            if d in checkin_map and checkin_map[d].get("mood") is not None
        ]
        non_streak_moods = [
            checkin_map[d]["mood"]
            for d in non_streak_done
            if d in checkin_map and checkin_map[d].get("mood") is not None
        ]

        if len(streak_moods) >= 3 and len(non_streak_moods) >= 2:
            streak_avg = sum(streak_moods) / len(streak_moods)
            non_avg = sum(non_streak_moods) / len(non_streak_moods)
            diff = streak_avg - non_avg

            if diff > 0.5:
                insights.append(
                    (diff * 3.5,
                     f"When you do \"{habit['name']}\" for 3+ days in a row, "
                     f"your mood averages {streak_avg:.1f} vs {non_avg:.1f} "
                     f"on one-off days \u2014 streaks matter!")
                )


# ── 4. Weekly digest ───────────────────────────────────────────────────────

def get_weekly_digest(user_id: int) -> dict:
    """Generate a weekly digest comparing this week to last week."""
    today = date.today()
    # This week: last 7 days
    this_start = (today - timedelta(days=6)).isoformat()
    this_end = today.isoformat()
    # Last week: 14-8 days ago
    last_start = (today - timedelta(days=13)).isoformat()
    last_end = (today - timedelta(days=7)).isoformat()

    conn = get_connection()
    try:
        this_week = conn.execute(
            "SELECT * FROM daily_checkins "
            "WHERE user_id = ? AND checkin_date BETWEEN ? AND ?",
            (user_id, this_start, this_end),
        ).fetchall()
        this_week = [dict(r) for r in this_week]

        last_week = conn.execute(
            "SELECT * FROM daily_checkins "
            "WHERE user_id = ? AND checkin_date BETWEEN ? AND ?",
            (user_id, last_start, last_end),
        ).fetchall()
        last_week = [dict(r) for r in last_week]

        # Habit completions this week
        habits = conn.execute(
            "SELECT id, name, pillar_id FROM habits "
            "WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchall()
        habits = [dict(h) for h in habits]

        logs = conn.execute(
            "SELECT habit_id, log_date FROM habit_log "
            "WHERE user_id = ? AND log_date BETWEEN ? AND ? AND completed_count > 0",
            (user_id, this_start, this_end),
        ).fetchall()
    finally:
        conn.close()

    # Default digest for sparse data
    digest = {
        "top_habit": None,
        "weakest_pillar": None,
        "strongest_pillar": None,
        "mood_trend": "stable",
        "energy_trend": "stable",
        "insight": "Keep logging daily to unlock personalized insights.",
        "recommendation": "Try to check in every day this week for the best analysis.",
    }

    if not this_week:
        return digest

    # ── Pillar averages this week ──────────────────────────────────────────
    pillar_avgs: dict[int, float] = {}
    for pid, field in PILLAR_FIELDS.items():
        vals = [c[field] for c in this_week if c.get(field) is not None]
        if vals:
            pillar_avgs[pid] = sum(vals) / len(vals)

    if pillar_avgs:
        strongest = max(pillar_avgs, key=pillar_avgs.get)
        weakest = min(pillar_avgs, key=pillar_avgs.get)
        digest["strongest_pillar"] = PILLARS[strongest]["display_name"]
        digest["weakest_pillar"] = PILLARS[weakest]["display_name"]

    # ── Top mood-boosting habit this week ──────────────────────────────────
    done_set = {(r["habit_id"], r["log_date"]) for r in logs}
    checkin_map = {c["checkin_date"]: c for c in this_week}
    checkin_dates = set(checkin_map.keys())

    best_habit_name = None
    best_mood_diff = -999.0

    for habit in habits:
        hid = habit["id"]
        mood_w, mood_wo = [], []
        for d in checkin_dates:
            m = checkin_map[d].get("mood")
            if m is None:
                continue
            if (hid, d) in done_set:
                mood_w.append(m)
            else:
                mood_wo.append(m)
        if mood_w and mood_wo:
            diff = (sum(mood_w) / len(mood_w)) - (sum(mood_wo) / len(mood_wo))
            if diff > best_mood_diff:
                best_mood_diff = diff
                best_habit_name = habit["name"]

    if best_habit_name and best_mood_diff > 0:
        digest["top_habit"] = best_habit_name

    # ── Mood / Energy trends ──────────────────────────────────────────────
    def _avg(items, key):
        vals = [c[key] for c in items if c.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    this_mood = _avg(this_week, "mood")
    last_mood = _avg(last_week, "mood")
    this_energy = _avg(this_week, "energy")
    last_energy = _avg(last_week, "energy")

    def _trend(current, previous, threshold=0.5):
        if current is None or previous is None:
            return "stable"
        diff = current - previous
        if diff >= threshold:
            return "improving"
        elif diff <= -threshold:
            return "declining"
        return "stable"

    digest["mood_trend"] = _trend(this_mood, last_mood)
    digest["energy_trend"] = _trend(this_energy, last_energy)

    # ── Key insight sentence ──────────────────────────────────────────────
    if digest["mood_trend"] == "improving":
        digest["insight"] = (
            f"Your mood is trending upward this week "
            f"({this_mood:.1f} avg vs {last_mood:.1f} last week). "
            f"Keep doing what's working!"
        )
    elif digest["mood_trend"] == "declining":
        digest["insight"] = (
            f"Your mood dipped this week ({this_mood:.1f} avg vs "
            f"{last_mood:.1f} last week). Small resets help \u2014 "
            f"consider a restorative activity today."
        )
    elif best_habit_name and best_mood_diff > 0.3:
        digest["insight"] = (
            f"\"{best_habit_name}\" was your top mood booster this week "
            f"(+{best_mood_diff:.1f} mood points on days completed)."
        )
    else:
        digest["insight"] = (
            f"You logged {len(this_week)} check-in{'s' if len(this_week) != 1 else ''} "
            f"this week. Consistency is your superpower!"
        )

    # ── Actionable recommendation ─────────────────────────────────────────
    if digest["weakest_pillar"]:
        weakest_name = digest["weakest_pillar"]
        weakest_avg = pillar_avgs.get(weakest, 0)
        # Find the matching pillar for a quick_tip
        weakest_pid = weakest if pillar_avgs else None
        tip = PILLARS.get(weakest_pid, {}).get("quick_tip", "")
        digest["recommendation"] = (
            f"Focus on {weakest_name} this week (avg {weakest_avg:.1f}/10). "
            f"{tip}"
        )
    elif digest["top_habit"]:
        digest["recommendation"] = (
            f"Double down on \"{digest['top_habit']}\" \u2014 "
            f"it's clearly lifting your mood."
        )
    else:
        digest["recommendation"] = (
            "Try completing at least 3 habits daily this week and see how "
            "it affects your mood."
        )

    return digest
