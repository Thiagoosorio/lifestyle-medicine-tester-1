"""Exercise type definitions, intensity levels, weekly targets, and Strava mapping."""

# ── Exercise Types ──────────────────────────────────────────────────────────
# MET values from Ainsworth et al. 2011 Compendium of Physical Activities
# (PMID: 21681120)

EXERCISE_TYPES = {
    "run":        {"label": "Running",           "icon": "&#127939;", "category": "cardio",       "met_moderate": 8.0,  "met_vigorous": 11.5},
    "walk":       {"label": "Walking",           "icon": "&#128694;", "category": "cardio",       "met_moderate": 3.5,  "met_vigorous": 5.0},
    "cycle":      {"label": "Cycling",           "icon": "&#128692;", "category": "cardio",       "met_moderate": 6.8,  "met_vigorous": 10.0},
    "swim":       {"label": "Swimming",          "icon": "&#127946;", "category": "cardio",       "met_moderate": 6.0,  "met_vigorous": 9.8},
    "hike":       {"label": "Hiking",            "icon": "&#129406;", "category": "cardio",       "met_moderate": 5.3,  "met_vigorous": 7.8},
    "strength":   {"label": "Strength Training", "icon": "&#127947;", "category": "strength",     "met_moderate": 5.0,  "met_vigorous": 6.0},
    "yoga":       {"label": "Yoga",              "icon": "&#129496;", "category": "flexibility",  "met_moderate": 3.0,  "met_vigorous": 4.0},
    "pilates":    {"label": "Pilates",           "icon": "&#129336;", "category": "flexibility",  "met_moderate": 3.8,  "met_vigorous": 4.5},
    "hiit":       {"label": "HIIT",              "icon": "&#9889;",   "category": "mixed",        "met_moderate": 8.0,  "met_vigorous": 12.0},
    "dance":      {"label": "Dance",             "icon": "&#128131;", "category": "cardio",       "met_moderate": 5.5,  "met_vigorous": 7.8},
    "rowing":     {"label": "Rowing",            "icon": "&#128675;", "category": "cardio",       "met_moderate": 7.0,  "met_vigorous": 12.0},
    "elliptical": {"label": "Elliptical",        "icon": "&#128260;", "category": "cardio",       "met_moderate": 5.0,  "met_vigorous": 8.0},
    "sports":     {"label": "Sports",            "icon": "&#9917;",   "category": "mixed",        "met_moderate": 6.0,  "met_vigorous": 10.0},
    "stretching": {"label": "Stretching",        "icon": "&#128582;", "category": "flexibility",  "met_moderate": 2.5,  "met_vigorous": 3.0},
    "other":      {"label": "Other",             "icon": "&#127941;", "category": "mixed",        "met_moderate": 5.0,  "met_vigorous": 8.0},
}

# Sort order for display
EXERCISE_TYPE_ORDER = [
    "run", "walk", "cycle", "swim", "hike",
    "strength", "yoga", "pilates", "hiit",
    "dance", "rowing", "elliptical", "sports",
    "stretching", "other",
]

# ── Intensity Levels ────────────────────────────────────────────────────────

INTENSITY_LEVELS = {
    "light":    {"label": "Light",    "color": "#30D158", "hr_zone": "50-63% max HR", "multiplier": 0.5, "description": "Easy effort, can hold a conversation"},
    "moderate": {"label": "Moderate", "color": "#FFD60A", "hr_zone": "64-76% max HR", "multiplier": 1.0, "description": "Brisk effort, can talk in short sentences"},
    "vigorous": {"label": "Vigorous", "color": "#FF453A", "hr_zone": "77-93% max HR", "multiplier": 2.0, "description": "Hard effort, difficult to talk"},
}

# ── Weekly Targets (ACLM / WHO / AHA Guidelines) ───────────────────────────
# WHO 2020 guidelines (PMID: 33239350):
# - 150-300 min/week moderate OR 75-150 min vigorous aerobic
# - Muscle-strengthening at moderate+ intensity 2+ days/week
# Vigorous minutes count as 2x moderate (MET equivalence)

WEEKLY_TARGETS = {
    "aerobic_moderate_min": 150,  # minimum; vigorous counted as 2x
    "strength_days": 2,
    "flexibility_sessions": 2,    # recommended, not a hard guideline
}

# Category display metadata
EXERCISE_CATEGORIES = {
    "cardio":      {"label": "Cardio",      "icon": "&#10084;",   "color": "#FF453A"},
    "strength":    {"label": "Strength",    "icon": "&#127947;",  "color": "#0A84FF"},
    "flexibility": {"label": "Flexibility", "icon": "&#129496;",  "color": "#BF5AF2"},
    "mixed":       {"label": "Mixed",       "icon": "&#9889;",    "color": "#FF9F0A"},
}

# ── Strava Activity Type Mapping ────────────────────────────────────────────

STRAVA_TYPE_MAP = {
    "Run": "run",
    "Trail Run": "run",
    "Virtual Run": "run",
    "Walk": "walk",
    "Hike": "hike",
    "Ride": "cycle",
    "Virtual Ride": "cycle",
    "Mountain Bike Ride": "cycle",
    "E-Bike Ride": "cycle",
    "Gravel Ride": "cycle",
    "Swim": "swim",
    "Weight Training": "strength",
    "Workout": "strength",
    "Yoga": "yoga",
    "Pilates": "pilates",
    "HIIT": "hiit",
    "Crossfit": "hiit",
    "Dance": "dance",
    "Rowing": "rowing",
    "Virtual Rowing": "rowing",
    "Elliptical": "elliptical",
    "Soccer": "sports",
    "Tennis": "sports",
    "Pickleball": "sports",
    "Badminton": "sports",
    "Basketball": "sports",
    "Golf": "sports",
    "Rock Climbing": "strength",
    "Stair Stepper": "cardio",
}

# Default mapping for unknown Strava types
STRAVA_DEFAULT_TYPE = "other"
STRAVA_DEFAULT_CATEGORY = "mixed"
