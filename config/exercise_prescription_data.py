"""Science-based exercise prescription data.

Volume landmarks based on Renaissance Periodization (RP) hypertrophy
guidelines (Israetel, Hoffmann & Smith, 2021) and systematic reviews on
resistance training volume (Schoenfeld et al., 2017 — PMID: 28032998).

Training split: Push / Pull / Legs (PPL) — validated by Schoenfeld et al.
(2015, PMID: 25932981) showing higher frequency (2×/week per muscle)
produces superior hypertrophy vs 1×/week bro-splits.
"""

# ── Volume Landmarks (sets per muscle group per WEEK) ─────────────────────
# MV  = Maintenance Volume (minimum to avoid muscle loss)
# MEV = Minimum Effective Volume (minimum for growth stimulus)
# MAV = Maximum Adaptive Volume (sweet spot for most lifters)
# MRV = Maximum Recoverable Volume (beyond this → overtraining)
# Source: RP Hypertrophy volume landmark articles & Schoenfeld meta-analyses

VOLUME_LANDMARKS = {
    "chest": {
        "label": "Chest",
        "mv": 6, "mev": 8, "mav_low": 12, "mav_high": 20, "mrv": 22,
        "note": "Includes all pressing + fly movements for pecs.",
    },
    "back": {
        "label": "Back (Lats & Upper Back)",
        "mv": 6, "mev": 8, "mav_low": 12, "mav_high": 20, "mrv": 25,
        "note": "Rows, pull-ups, pulldowns. Separate from rear delts.",
    },
    "shoulders_side": {
        "label": "Side & Rear Delts",
        "mv": 6, "mev": 8, "mav_low": 16, "mav_high": 22, "mrv": 26,
        "note": "Lateral raises, face pulls, reverse flys.",
    },
    "shoulders_front": {
        "label": "Front Delts",
        "mv": 0, "mev": 0, "mav_low": 6, "mav_high": 8, "mrv": 12,
        "note": "Usually covered by pressing. Direct work rarely needed.",
    },
    "biceps": {
        "label": "Biceps",
        "mv": 4, "mev": 8, "mav_low": 14, "mav_high": 20, "mrv": 26,
        "note": "Curls of any type. Rows contribute partial volume.",
    },
    "triceps": {
        "label": "Triceps",
        "mv": 4, "mev": 6, "mav_low": 10, "mav_high": 14, "mrv": 18,
        "note": "Pushdowns, extensions. Pressing contributes partial volume.",
    },
    "quads": {
        "label": "Quadriceps",
        "mv": 6, "mev": 8, "mav_low": 12, "mav_high": 18, "mrv": 20,
        "note": "Squats, leg press, lunges, leg extensions.",
    },
    "hamstrings": {
        "label": "Hamstrings",
        "mv": 4, "mev": 6, "mav_low": 10, "mav_high": 16, "mrv": 20,
        "note": "RDLs, leg curls, good mornings.",
    },
    "glutes": {
        "label": "Glutes",
        "mv": 0, "mev": 4, "mav_low": 8, "mav_high": 16, "mrv": 20,
        "note": "Hip thrusts, glute bridges. Squats/RDLs contribute.",
    },
    "calves": {
        "label": "Calves",
        "mv": 4, "mev": 6, "mav_low": 8, "mav_high": 16, "mrv": 20,
        "note": "Calf raises — seated and standing for both heads.",
    },
    "core": {
        "label": "Core / Abs",
        "mv": 0, "mev": 4, "mav_low": 8, "mav_high": 16, "mrv": 20,
        "note": "Crunches, planks, leg raises. Compounds contribute some.",
    },
}

# ── Mesocycle Progression ─────────────────────────────────────────────────
# Based on RP periodization model (Israetel et al.)
# Each mesocycle = 4-6 weeks. Volume ramps from MEV→MAV, then deload.

MESOCYCLE_TEMPLATES = {
    "beginner": {
        "label": "Beginner (0-1 years)",
        "weeks": 4,
        "progression": [
            {"week": 1, "volume_pct": 0.0,   "rir": 4, "label": "MEV — Learn movements"},
            {"week": 2, "volume_pct": 0.33,  "rir": 3, "label": "Low MAV — Build base"},
            {"week": 3, "volume_pct": 0.50,  "rir": 2, "label": "Mid MAV — Progressive overload"},
            {"week": 4, "volume_pct": -1,    "rir": 5, "label": "Deload — Recovery"},
        ],
        "note": "Focus on form mastery and progressive overload. 3 days/week PPL.",
    },
    "intermediate": {
        "label": "Intermediate (1-3 years)",
        "weeks": 5,
        "progression": [
            {"week": 1, "volume_pct": 0.0,   "rir": 3, "label": "MEV — Resensitize"},
            {"week": 2, "volume_pct": 0.25,  "rir": 3, "label": "Low MAV — Build volume"},
            {"week": 3, "volume_pct": 0.50,  "rir": 2, "label": "Mid MAV — Push limits"},
            {"week": 4, "volume_pct": 0.75,  "rir": 1, "label": "High MAV — Overreach"},
            {"week": 5, "volume_pct": -1,    "rir": 5, "label": "Deload — Recovery"},
        ],
        "note": "Push/Pull/Legs 2× per week (6 days). Track RIR and load progression.",
    },
    "advanced": {
        "label": "Advanced (3+ years)",
        "weeks": 6,
        "progression": [
            {"week": 1, "volume_pct": 0.0,   "rir": 3, "label": "MEV — Resensitize"},
            {"week": 2, "volume_pct": 0.20,  "rir": 3, "label": "Low MAV — Build base"},
            {"week": 3, "volume_pct": 0.40,  "rir": 2, "label": "Mid MAV — Challenge"},
            {"week": 4, "volume_pct": 0.60,  "rir": 2, "label": "High MAV — Push hard"},
            {"week": 5, "volume_pct": 0.80,  "rir": 1, "label": "Near MRV — Overreach"},
            {"week": 6, "volume_pct": -1,    "rir": 5, "label": "Deload — Recovery"},
        ],
        "note": "PPL 2× per week (6 days). Periodize intensity and exercise selection.",
    },
}

# ── PPL Split — Exercise Slots ────────────────────────────────────────────
# Maps each day to muscle groups targeted and exercise slots.
# Exercises are pulled from the existing EXERCISE_LIBRARY.

PPL_SPLIT = {
    "push": {
        "label": "Push Day",
        "icon": "&#128170;",
        "color": "#D93025",
        "subtitle": "Chest, Shoulders, Triceps",
        "muscle_groups": ["chest", "shoulders", "triceps"],
        "slots": [
            {"muscle": "chest",    "type": "compound",  "label": "Chest Compound",     "sets": 4, "reps": "6-10",  "rir": 2},
            {"muscle": "chest",    "type": "compound",  "label": "Chest Compound 2",   "sets": 3, "reps": "8-12",  "rir": 2},
            {"muscle": "chest",    "type": "isolation",  "label": "Chest Isolation",    "sets": 3, "reps": "12-15", "rir": 1},
            {"muscle": "shoulders","type": "compound",  "label": "Shoulder Press",      "sets": 3, "reps": "8-12",  "rir": 2},
            {"muscle": "shoulders","type": "isolation",  "label": "Lateral Raise",      "sets": 3, "reps": "12-20", "rir": 1},
            {"muscle": "triceps",  "type": "isolation",  "label": "Triceps Isolation",  "sets": 3, "reps": "10-15", "rir": 1},
        ],
    },
    "pull": {
        "label": "Pull Day",
        "icon": "&#129470;",
        "color": "#1A73E8",
        "subtitle": "Back, Biceps, Rear Delts",
        "muscle_groups": ["back", "biceps", "shoulders"],
        "slots": [
            {"muscle": "back",    "type": "compound",  "label": "Back Compound",       "sets": 4, "reps": "6-10",  "rir": 2},
            {"muscle": "back",    "type": "compound",  "label": "Back Compound 2",     "sets": 3, "reps": "8-12",  "rir": 2},
            {"muscle": "back",    "type": "isolation",  "label": "Back Isolation",      "sets": 3, "reps": "12-15", "rir": 1},
            {"muscle": "shoulders","type": "isolation",  "label": "Rear Delt Isolation", "sets": 3, "reps": "15-20", "rir": 1, "prefer_id": "rear_delt_fly"},
            {"muscle": "biceps",  "type": "isolation",  "label": "Biceps Curl 1",      "sets": 3, "reps": "10-12", "rir": 1},
            {"muscle": "biceps",  "type": "isolation",  "label": "Biceps Curl 2",      "sets": 3, "reps": "12-15", "rir": 1},
        ],
    },
    "legs": {
        "label": "Legs Day",
        "icon": "&#129461;",
        "color": "#1E8E3E",
        "subtitle": "Quads, Hamstrings, Glutes, Calves",
        "muscle_groups": ["legs", "glutes"],
        "slots": [
            {"muscle": "legs",   "type": "compound",  "label": "Quad Compound",       "sets": 4, "reps": "6-10",  "rir": 2},
            {"muscle": "legs",   "type": "compound",  "label": "Quad Compound 2",     "sets": 3, "reps": "8-12",  "rir": 2},
            {"muscle": "legs",   "type": "isolation",  "label": "Quad Isolation",      "sets": 3, "reps": "12-15", "rir": 1},
            {"muscle": "glutes", "type": "compound",  "label": "Hip Hinge",           "sets": 3, "reps": "8-12",  "rir": 2, "prefer_id": "hip_thrust"},
            {"muscle": "glutes", "type": "isolation",  "label": "Glute Isolation",     "sets": 3, "reps": "12-15", "rir": 1},
            {"muscle": "legs",   "type": "isolation",  "label": "Calf Raise",          "sets": 4, "reps": "12-20", "rir": 1, "prefer_id": "calf_raise"},
        ],
    },
}

# ── Weekly Schedule Templates ─────────────────────────────────────────────

SCHEDULE_TEMPLATES = {
    "ppl_3": {
        "label": "PPL 3-Day (1× per muscle/week)",
        "days_per_week": 3,
        "schedule": ["push", "pull", "legs"],
        "rest_days": [3, 4],  # 0-indexed rest after day indices
        "recommended_for": "beginner",
        "note": "Each muscle group trained once per week. Good for beginners or recovery phases.",
    },
    "ppl_4": {
        "label": "PPL 4-Day (Upper/Lower hybrid)",
        "days_per_week": 4,
        "schedule": ["push", "pull", "legs", "push"],
        "rest_days": [2],
        "recommended_for": "beginner",
        "note": "Push trained 2×, pull and legs 1×. Alternate the extra day each week.",
    },
    "ppl_6": {
        "label": "PPL 6-Day (2× per muscle/week)",
        "days_per_week": 6,
        "schedule": ["push", "pull", "legs", "push", "pull", "legs"],
        "rest_days": [],
        "recommended_for": "intermediate",
        "note": "Optimal frequency: every muscle hit twice per week. Schoenfeld et al. (2016, PMID: 27102172).",
    },
}

# ── RIR (Reps In Reserve) Guidance ────────────────────────────────────────

RIR_GUIDE = {
    5: {"label": "Very Easy", "color": "#1E8E3E", "desc": "Warm-up / deload intensity. Could do 5+ more reps."},
    4: {"label": "Easy", "color": "#1E8E3E", "desc": "Comfortable effort. Good for first week of mesocycle."},
    3: {"label": "Moderate", "color": "#F9AB00", "desc": "Challenging but controlled. Standard training effort."},
    2: {"label": "Hard", "color": "#E8710A", "desc": "2 reps left in the tank. Strong stimulus."},
    1: {"label": "Very Hard", "color": "#D93025", "desc": "1 rep from failure. High stimulus, high fatigue."},
    0: {"label": "Failure", "color": "#D93025", "desc": "Cannot complete another rep. Use sparingly for isolation exercises."},
}

# ── Mapping: exercise_library muscle_group → prescription muscle slots ────
# The exercise library uses: chest, back, shoulders, biceps, triceps, legs, glutes, core
# PPL slots use the same keys, so mapping is direct.

LIBRARY_MUSCLE_MAP = {
    "chest": "chest",
    "back": "back",
    "shoulders": "shoulders",
    "biceps": "biceps",
    "triceps": "triceps",
    "legs": "legs",
    "glutes": "glutes",
    "core": "core",
}

# ── Deload Protocol ──────────────────────────────────────────────────────

DELOAD_PROTOCOL = {
    "volume_reduction": 0.50,   # Drop to 50% of previous week's sets
    "intensity_reduction": 0.0, # Keep weight the same (or slight reduction)
    "rir_target": 5,            # Stay far from failure
    "note": "Maintain weight on the bar but cut volume in half. "
            "Focus on technique and recovery. (Ogasawara et al., 2013 — PMID: 23604232)",
}
