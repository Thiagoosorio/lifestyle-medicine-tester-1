"""
Sleep Data — Chronotype definitions, sleep scoring weights, and body clock windows.

Scientific basis:
- Chronotype assessment: Horne-Ostberg Morningness-Eveningness Questionnaire (PMID: 1027738)
- Animal model mapping: Breus 4-animal framework for user-friendly communication
- Sleep quality scoring: Pittsburgh Sleep Quality Index components (PMID: 2748771)
- Duration guidelines: NSF/AASM 7-9h for adults (PMID: 20469800, 28889101)
- Sleep regularity: Social Jet Lag Index (PMID: 33054339)
"""

# ── Chronotype Definitions ───────────────────────────────────────────────
# MEQ (Morningness-Eveningness Questionnaire) score → chronotype mapping.
# MEQ range: 16-86.  Higher = more morning-oriented.

CHRONOTYPES = {
    "lion": {
        "name": "Lion",
        "subtitle": "Early Riser",
        "meq_min": 59,
        "meq_max": 86,
        "icon": "&#129409;",           # lion face
        "color": "#FFD60A",            # warm yellow
        "description": (
            "You're a natural early riser. Your energy peaks in the morning "
            "and tapers off in the early evening. You thrive with an early "
            "bedtime and wake time."
        ),
        "ideal_bedtime": "21:30-22:00",
        "ideal_waketime": "05:30-06:00",
        "peak_focus": "08:00-12:00",
        "peak_exercise": "06:00-10:00",
        "wind_down": "20:30-21:00",
        "traits": [
            "High energy in morning hours",
            "Most productive before noon",
            "Naturally drowsy by 21:00-22:00",
            "May struggle with late social events",
        ],
    },
    "bear": {
        "name": "Bear",
        "subtitle": "Solar Cycle",
        "meq_min": 42,
        "meq_max": 58,
        "icon": "&#128059;",           # bear face
        "color": "#30D158",            # green — most common
        "description": (
            "You follow the solar cycle — most people are Bears. Your energy "
            "rises mid-morning and peaks around midday. A consistent 7-8h "
            "sleep schedule works best."
        ),
        "ideal_bedtime": "22:30-23:00",
        "ideal_waketime": "06:30-07:00",
        "peak_focus": "10:00-14:00",
        "peak_exercise": "07:30-12:00",
        "wind_down": "21:30-22:00",
        "traits": [
            "Follows natural daylight patterns",
            "Mid-morning energy peak",
            "Steady productivity throughout the day",
            "About 55% of the population",
        ],
    },
    "wolf": {
        "name": "Wolf",
        "subtitle": "Night Owl",
        "meq_min": 16,
        "meq_max": 41,
        "icon": "&#128058;",           # wolf face
        "color": "#BF5AF2",            # purple — evening
        "description": (
            "You come alive in the evening. Creative energy surges after "
            "dark. You need a later schedule and may struggle with early "
            "morning obligations."
        ),
        "ideal_bedtime": "00:00-00:30",
        "ideal_waketime": "07:30-08:00",
        "peak_focus": "17:00-21:00",
        "peak_exercise": "17:00-20:00",
        "wind_down": "23:00-23:30",
        "traits": [
            "Creative bursts in the evening",
            "Slow to wake, hits stride after noon",
            "Peak performance late afternoon/evening",
            "May experience social jet lag with 9-5 schedules",
        ],
    },
    "dolphin": {
        "name": "Dolphin",
        "subtitle": "Light Sleeper",
        "meq_min": None,
        "meq_max": None,
        "icon": "&#128044;",           # dolphin
        "color": "#64D2FF",            # light blue
        "description": (
            "You're a light, irregular sleeper. You may have trouble falling "
            "or staying asleep. Routine and sleep hygiene are especially "
            "important for you."
        ),
        "ideal_bedtime": "23:00-23:30",
        "ideal_waketime": "06:30-07:00",
        "peak_focus": "10:00-12:00",
        "peak_exercise": "07:00-09:00",
        "wind_down": "22:00-22:30",
        "traits": [
            "Light, easily disrupted sleep",
            "High intelligence, often anxious sleepers",
            "Variable energy throughout the day",
            "Benefit most from strict sleep hygiene",
        ],
        "detection_criteria": {
            "min_days": 7,
            "avg_latency_min": 30,
            "avg_efficiency_below": 85,
            "avg_awakenings_above": 2,
        },
    },
}


# ── MEQ Simplified Questions ────────────────────────────────────────────
# Shortened 5-question version of the MEQ for in-app chronotype assessment.
# Full MEQ is 19 questions; this validated short form preserves discrimination.

MEQ_QUESTIONS = [
    {
        "id": 1,
        "question": "If you were entirely free to plan your evening, at what time would you choose to go to bed?",
        "options": [
            {"label": "Before 21:00", "score": 5},
            {"label": "21:00 - 22:00", "score": 4},
            {"label": "22:00 - 00:00", "score": 3},
            {"label": "00:00 - 01:30", "score": 2},
            {"label": "After 01:30", "score": 1},
        ],
    },
    {
        "id": 2,
        "question": "If you were entirely free to plan your morning, at what time would you choose to get up?",
        "options": [
            {"label": "Before 06:00", "score": 5},
            {"label": "06:00 - 07:00", "score": 4},
            {"label": "07:00 - 09:00", "score": 3},
            {"label": "09:00 - 11:00", "score": 2},
            {"label": "After 11:00", "score": 1},
        ],
    },
    {
        "id": 3,
        "question": "How alert do you feel during the first 30 minutes after waking?",
        "options": [
            {"label": "Very alert", "score": 5},
            {"label": "Fairly alert", "score": 4},
            {"label": "Somewhat groggy", "score": 3},
            {"label": "Very groggy", "score": 2},
            {"label": "Cannot function", "score": 1},
        ],
    },
    {
        "id": 4,
        "question": "At what time of day do you feel your best (peak energy)?",
        "options": [
            {"label": "Early morning (06:00-09:00)", "score": 5},
            {"label": "Late morning (09:00-12:00)", "score": 4},
            {"label": "Afternoon (12:00-17:00)", "score": 3},
            {"label": "Evening (17:00-21:00)", "score": 2},
            {"label": "Night (after 21:00)", "score": 1},
        ],
    },
    {
        "id": 5,
        "question": "If you had to take a demanding 2-hour test, when would you choose to take it?",
        "options": [
            {"label": "08:00 - 10:00", "score": 5},
            {"label": "10:00 - 12:00", "score": 4},
            {"label": "12:00 - 14:00", "score": 3},
            {"label": "14:00 - 18:00", "score": 2},
            {"label": "After 18:00", "score": 1},
        ],
    },
]

# Score interpretation for 5-question version:
# Total range: 5-25, scaled to MEQ range 16-86
# Scale factor: meq_score = 16 + (raw_score - 5) * (70 / 20)
MEQ_SCALE_MIN = 5
MEQ_SCALE_MAX = 25
MEQ_MAPPED_MIN = 16
MEQ_MAPPED_MAX = 86


# ── Sleep Scoring Weights ────────────────────────────────────────────────
# Component weights for the composite sleep score (0-100).
# Based on PSQI domains (PMID: 2748771) with added consistency component.

SLEEP_SCORE_WEIGHTS = {
    "duration": {
        "weight": 0.30,
        "label": "Duration",
        "icon": "&#128164;",           # zzz
        "description": "7-9 hours is optimal for adults (AASM/NSF guidelines).",
        "optimal_min_hours": 7.0,
        "optimal_max_hours": 9.0,
        "acceptable_min_hours": 6.0,
        "acceptable_max_hours": 10.0,
    },
    "latency": {
        "weight": 0.15,
        "label": "Sleep Latency",
        "icon": "&#9202;",             # timer clock
        "description": "Time to fall asleep. Under 15 minutes is ideal.",
        "optimal_max_min": 15,
        "acceptable_max_min": 30,
        "poor_min": 60,
    },
    "efficiency": {
        "weight": 0.20,
        "label": "Sleep Efficiency",
        "icon": "&#128171;",           # battery
        "description": "Time asleep / time in bed. Above 85% is healthy.",
        "optimal_pct": 90,
        "acceptable_pct": 85,
        "poor_pct": 75,
    },
    "disturbance": {
        "weight": 0.15,
        "label": "Disturbances",
        "icon": "&#128276;",           # bell
        "description": "Night awakenings. Zero to one is ideal.",
        "optimal_max": 1,
        "acceptable_max": 3,
        "poor_min": 5,
    },
    "quality": {
        "weight": 0.10,
        "label": "Subjective Quality",
        "icon": "&#11088;",            # star
        "description": "Your self-rated sleep quality (1-5 scale).",
        "scale_min": 1,
        "scale_max": 5,
    },
    "consistency": {
        "weight": 0.10,
        "label": "Schedule Consistency",
        "icon": "&#128338;",           # clock
        "description": "Regular bed/wake times reduce social jet lag (PMID: 33054339).",
        "optimal_variance_min": 30,
        "acceptable_variance_min": 60,
        "poor_variance_min": 90,
    },
}


# ── Sleep Score Zones ────────────────────────────────────────────────────

SLEEP_SCORE_ZONES = {
    "excellent": {
        "min": 85,
        "max": 100,
        "label": "Excellent",
        "color": "#30D158",
        "icon": "&#127775;",           # glowing star
        "message": "Outstanding sleep! Your body is getting the rest it needs.",
    },
    "good": {
        "min": 70,
        "max": 84,
        "label": "Good",
        "color": "#64D2FF",
        "icon": "&#128077;",           # thumbs up
        "message": "Solid sleep. Minor improvements could optimize recovery.",
    },
    "fair": {
        "min": 50,
        "max": 69,
        "label": "Fair",
        "color": "#FFD60A",
        "icon": "&#9888;",             # warning
        "message": "Room for improvement. Focus on sleep hygiene habits.",
    },
    "poor": {
        "min": 0,
        "max": 49,
        "label": "Poor",
        "color": "#FF375F",
        "icon": "&#10071;",            # exclamation
        "message": "Sleep needs attention. Review your habits and environment.",
    },
}


# ── Body Clock Windows ──────────────────────────────────────────────────
# 24-hour optimal activity windows per chronotype.
# Used to render a daily body clock visualization.

BODY_CLOCK_ACTIVITIES = [
    {"id": "deep_sleep", "label": "Deep Sleep", "color": "#3C3C6E", "icon": "&#127769;"},
    {"id": "wake_up", "label": "Wake Up", "color": "#FFD60A", "icon": "&#127749;"},
    {"id": "peak_focus", "label": "Peak Focus", "color": "#FF9F0A", "icon": "&#129504;"},
    {"id": "exercise", "label": "Best Exercise", "color": "#30D158", "icon": "&#127939;"},
    {"id": "light_tasks", "label": "Light Tasks", "color": "#64D2FF", "icon": "&#128221;"},
    {"id": "wind_down", "label": "Wind Down", "color": "#BF5AF2", "icon": "&#128148;"},
    {"id": "sleep_prep", "label": "Sleep Prep", "color": "#AEAEB2", "icon": "&#128716;"},
]


# ── Sleep Hygiene Tips ───────────────────────────────────────────────────
# Evidence-backed recommendations shown contextually based on user data.

SLEEP_HYGIENE_TIPS = {
    "caffeine": {
        "tip": "Stop caffeine 8-10 hours before bedtime.",
        "trigger": "caffeine_cutoff_late",
        "evidence": "Caffeine has a half-life of ~5h; residual levels disrupt sleep architecture.",
    },
    "screens": {
        "tip": "Reduce screen exposure 60-90 minutes before bed.",
        "trigger": "screen_cutoff_late",
        "evidence": "Blue light suppresses melatonin secretion and delays sleep onset.",
    },
    "alcohol": {
        "tip": "Avoid alcohol within 3 hours of bedtime.",
        "trigger": "alcohol_before_bed",
        "evidence": "Alcohol fragments REM sleep and increases awakenings in the second half of the night.",
    },
    "consistency": {
        "tip": "Keep bed and wake times within 30 minutes, even on weekends.",
        "trigger": "inconsistent_schedule",
        "evidence": "Irregular sleep timing disrupts circadian rhythm (social jet lag, PMID: 33054339).",
    },
    "latency": {
        "tip": "If you can't sleep after 20 minutes, get up and do something calming.",
        "trigger": "high_latency",
        "evidence": "Stimulus control therapy — bed should be associated with sleep, not wakefulness.",
    },
    "environment": {
        "tip": "Keep bedroom cool (18-20°C / 65-68°F), dark, and quiet.",
        "trigger": "general",
        "evidence": "Core body temperature drop facilitates sleep onset; light/noise disrupt sleep stages.",
    },
    "exercise_timing": {
        "tip": "Finish vigorous exercise at least 3 hours before bedtime.",
        "trigger": "late_exercise",
        "evidence": "Exercise raises core temperature and sympathetic tone; allow time for wind-down.",
    },
}
