"""Running training data — VDOT tables, race distances, pace zones, plan templates.

Based on Jack Daniels' VDOT Running Formula (4th ed., 2022):
  - VDOT oxygen cost model for pace zone calculation
  - Riegel (1981) race time prediction formula (PMID: n/a, Runner's World)

Session RPE training load per Foster et al. (2001) "A new approach to monitoring
exercise training" (PMID: 11219501).

Training plan periodisation follows the Lydiard base → sharpening model
adapted with modern polarised intensity distribution (Seiler, 2010;
PMID: 20030776).
"""

# ── Standard Race Distances ───────────────────────────────────────────────

RACE_DISTANCES = {
    "5k":             {"km": 5.0,      "label": "5K",            "icon": "&#127939;"},
    "10k":            {"km": 10.0,     "label": "10K",           "icon": "&#127939;"},
    "half_marathon":  {"km": 21.0975,  "label": "Half Marathon", "icon": "&#127942;"},
    "marathon":       {"km": 42.195,   "label": "Marathon",      "icon": "&#127942;"},
}


# ── Pace Zone Definitions ─────────────────────────────────────────────────
# Jack Daniels' VDOT training paces expressed as % of VDOT pace.
# "vdot_pace_pct" means: zone pace = vdot_pace / pct_factor
# Higher pct_factor → slower pace (easy), lower → faster (reps).
#
# The VDOT pace itself corresponds to ~100% VO2max race effort (approx 10-12
# min race pace).  Zone paces are derived by scaling from that reference.

PACE_ZONE_DEFINITIONS = {
    "z1": {
        "name": "Easy / Recovery",
        "short": "Easy",
        "color": "#30D158",
        "vdot_pct_range": (0.65, 0.79),
        "description": (
            "Conversational pace. The foundation of aerobic development. "
            "Should feel comfortable enough to hold a full conversation. "
            "Most weekly mileage should be at this effort."
        ),
    },
    "z2": {
        "name": "Marathon Pace",
        "short": "MP",
        "color": "#0A84FF",
        "vdot_pct_range": (0.80, 0.82),
        "description": (
            "Goal marathon race pace. Teaches the body to burn fat efficiently "
            "at a meaningful effort. Used for marathon-specific long runs."
        ),
    },
    "z3": {
        "name": "Threshold / Tempo",
        "short": "Tempo",
        "color": "#FFD60A",
        "vdot_pct_range": (0.83, 0.88),
        "description": (
            "Comfortably hard — roughly one-hour race pace. Improves lactate "
            "clearance and raises the anaerobic threshold. Sustained 20-40 min "
            "efforts or cruise intervals."
        ),
    },
    "z4": {
        "name": "Interval / VO2max",
        "short": "Interval",
        "color": "#FF9F0A",
        "vdot_pct_range": (0.95, 1.00),
        "description": (
            "Hard 3-5 minute repeats at approximately 5K race pace. Maximises "
            "VO2max stimulus. Breathing is maximal; conversation impossible."
        ),
    },
    "z5": {
        "name": "Repetition",
        "short": "Reps",
        "color": "#FF453A",
        "vdot_pct_range": (1.05, 1.15),
        "description": (
            "Fast, short repeats (200-400 m) faster than 5K pace. Develops "
            "running economy and neuromuscular speed. Full recovery between reps."
        ),
    },
}


# ── VDOT Lookup Table ─────────────────────────────────────────────────────
# Approximate race paces (min/km) for common VDOT values.
# Derived from Daniels' Running Formula tables.
# Keys: VDOT integer; values: dict of pace per km for each zone + race paces.
#
# Race pace columns:
#   5k_pace, 10k_pace, half_pace, marathon_pace  — all in min/km
# Training pace columns:
#   easy_pace, tempo_pace, interval_pace, rep_pace — all in min/km

VDOT_TABLE = {
    30: {
        "5k_pace": 7.04, "10k_pace": 7.35, "half_pace": 8.08, "marathon_pace": 8.42,
        "easy_pace": 9.34, "tempo_pace": 7.58, "interval_pace": 7.04, "rep_pace": 6.30,
    },
    32: {
        "5k_pace": 6.40, "10k_pace": 7.07, "half_pace": 7.39, "marathon_pace": 8.12,
        "easy_pace": 9.02, "tempo_pace": 7.30, "interval_pace": 6.40, "rep_pace": 6.08,
    },
    34: {
        "5k_pace": 6.19, "10k_pace": 6.42, "half_pace": 7.13, "marathon_pace": 7.44,
        "easy_pace": 8.32, "tempo_pace": 7.04, "interval_pace": 6.19, "rep_pace": 5.48,
    },
    36: {
        "5k_pace": 6.00, "10k_pace": 6.20, "half_pace": 6.49, "marathon_pace": 7.20,
        "easy_pace": 8.06, "tempo_pace": 6.42, "interval_pace": 6.00, "rep_pace": 5.30,
    },
    38: {
        "5k_pace": 5.43, "10k_pace": 6.00, "half_pace": 6.28, "marathon_pace": 6.57,
        "easy_pace": 7.42, "tempo_pace": 6.22, "interval_pace": 5.43, "rep_pace": 5.14,
    },
    40: {
        "5k_pace": 5.28, "10k_pace": 5.43, "half_pace": 6.09, "marathon_pace": 6.37,
        "easy_pace": 7.21, "tempo_pace": 6.03, "interval_pace": 5.28, "rep_pace": 4.59,
    },
    42: {
        "5k_pace": 5.14, "10k_pace": 5.27, "half_pace": 5.51, "marathon_pace": 6.18,
        "easy_pace": 7.02, "tempo_pace": 5.46, "interval_pace": 5.14, "rep_pace": 4.46,
    },
    44: {
        "5k_pace": 5.01, "10k_pace": 5.13, "half_pace": 5.35, "marathon_pace": 6.01,
        "easy_pace": 6.44, "tempo_pace": 5.31, "interval_pace": 5.01, "rep_pace": 4.33,
    },
    46: {
        "5k_pace": 4.50, "10k_pace": 5.00, "half_pace": 5.21, "marathon_pace": 5.46,
        "easy_pace": 6.28, "tempo_pace": 5.17, "interval_pace": 4.50, "rep_pace": 4.22,
    },
    48: {
        "5k_pace": 4.39, "10k_pace": 4.49, "half_pace": 5.08, "marathon_pace": 5.32,
        "easy_pace": 6.14, "tempo_pace": 5.05, "interval_pace": 4.39, "rep_pace": 4.12,
    },
    50: {
        "5k_pace": 4.30, "10k_pace": 4.38, "half_pace": 4.56, "marathon_pace": 5.19,
        "easy_pace": 6.00, "tempo_pace": 4.53, "interval_pace": 4.30, "rep_pace": 4.02,
    },
    52: {
        "5k_pace": 4.21, "10k_pace": 4.29, "half_pace": 4.46, "marathon_pace": 5.08,
        "easy_pace": 5.48, "tempo_pace": 4.42, "interval_pace": 4.21, "rep_pace": 3.53,
    },
    54: {
        "5k_pace": 4.13, "10k_pace": 4.20, "half_pace": 4.36, "marathon_pace": 4.57,
        "easy_pace": 5.36, "tempo_pace": 4.32, "interval_pace": 4.13, "rep_pace": 3.45,
    },
    56: {
        "5k_pace": 4.05, "10k_pace": 4.12, "half_pace": 4.27, "marathon_pace": 4.47,
        "easy_pace": 5.26, "tempo_pace": 4.23, "interval_pace": 4.05, "rep_pace": 3.38,
    },
    58: {
        "5k_pace": 3.58, "10k_pace": 4.04, "half_pace": 4.18, "marathon_pace": 4.38,
        "easy_pace": 5.16, "tempo_pace": 4.14, "interval_pace": 3.58, "rep_pace": 3.31,
    },
    60: {
        "5k_pace": 3.52, "10k_pace": 3.57, "half_pace": 4.11, "marathon_pace": 4.30,
        "easy_pace": 5.07, "tempo_pace": 4.07, "interval_pace": 3.52, "rep_pace": 3.24,
    },
    62: {
        "5k_pace": 3.46, "10k_pace": 3.51, "half_pace": 4.04, "marathon_pace": 4.22,
        "easy_pace": 4.59, "tempo_pace": 4.00, "interval_pace": 3.46, "rep_pace": 3.18,
    },
    64: {
        "5k_pace": 3.40, "10k_pace": 3.45, "half_pace": 3.57, "marathon_pace": 4.15,
        "easy_pace": 4.51, "tempo_pace": 3.53, "interval_pace": 3.40, "rep_pace": 3.13,
    },
    66: {
        "5k_pace": 3.35, "10k_pace": 3.39, "half_pace": 3.51, "marathon_pace": 4.09,
        "easy_pace": 4.44, "tempo_pace": 3.47, "interval_pace": 3.35, "rep_pace": 3.08,
    },
    68: {
        "5k_pace": 3.30, "10k_pace": 3.34, "half_pace": 3.45, "marathon_pace": 4.03,
        "easy_pace": 4.38, "tempo_pace": 3.42, "interval_pace": 3.30, "rep_pace": 3.03,
    },
    70: {
        "5k_pace": 3.26, "10k_pace": 3.29, "half_pace": 3.40, "marathon_pace": 3.57,
        "easy_pace": 4.32, "tempo_pace": 3.37, "interval_pace": 3.26, "rep_pace": 2.59,
    },
}


# ── Training Plan Templates ───────────────────────────────────────────────
# Structured week templates for each goal distance.
# Session types: easy, long, tempo, interval, recovery, rest
# Percentages refer to target weekly volume.
#
# Plans follow a polarised model: ~80% easy, ~10% moderate/tempo, ~10% hard.
# Long run capped at 30-35% of weekly volume (Pfitzinger & Douglas, 2009).

TRAINING_PLAN_TEMPLATES = {
    "5k": {
        "label": "5K Race Plan",
        "description": (
            "Sharpen your speed for a 5K. Emphasises VO2max intervals and "
            "tempo work alongside an easy-run base."
        ),
        "min_weeks": 6,
        "max_weeks": 12,
        "peak_weekly_km_factor": 1.4,  # peak km = current_weekly * factor
        "sessions_per_week": 5,
        "weekly_structure": [
            {"day": "Mon", "type": "easy",     "km_pct": 0.15, "description": "Easy run"},
            {"day": "Tue", "type": "interval", "km_pct": 0.15, "description": "5x1000m at Interval pace, 400m jog recovery"},
            {"day": "Wed", "type": "rest",     "km_pct": 0.0,  "description": "Rest or cross-train"},
            {"day": "Thu", "type": "tempo",    "km_pct": 0.20, "description": "20-30 min sustained at Tempo pace"},
            {"day": "Fri", "type": "easy",     "km_pct": 0.15, "description": "Easy recovery run"},
            {"day": "Sat", "type": "long",     "km_pct": 0.30, "description": "Long run at Easy pace"},
            {"day": "Sun", "type": "rest",     "km_pct": 0.0,  "description": "Full rest"},
        ],
        "taper_weeks": 1,
        "progression_pct_per_week": 0.08,  # weekly volume increase cap
    },
    "10k": {
        "label": "10K Race Plan",
        "description": (
            "Build endurance and tempo strength for a strong 10K. Balances "
            "threshold work with aerobic volume."
        ),
        "min_weeks": 8,
        "max_weeks": 14,
        "peak_weekly_km_factor": 1.5,
        "sessions_per_week": 5,
        "weekly_structure": [
            {"day": "Mon", "type": "easy",     "km_pct": 0.15, "description": "Easy run"},
            {"day": "Tue", "type": "interval", "km_pct": 0.15, "description": "6x1000m at Interval pace, 400m jog recovery"},
            {"day": "Wed", "type": "easy",     "km_pct": 0.10, "description": "Easy recovery run"},
            {"day": "Thu", "type": "tempo",    "km_pct": 0.20, "description": "25-35 min at Tempo pace"},
            {"day": "Fri", "type": "rest",     "km_pct": 0.0,  "description": "Rest or cross-train"},
            {"day": "Sat", "type": "long",     "km_pct": 0.30, "description": "Long run at Easy pace"},
            {"day": "Sun", "type": "easy",     "km_pct": 0.10, "description": "Easy recovery run or rest"},
        ],
        "taper_weeks": 1,
        "progression_pct_per_week": 0.07,
    },
    "half_marathon": {
        "label": "Half Marathon Plan",
        "description": (
            "Build the aerobic engine for 21.1 km. Marathon pace and tempo "
            "sessions develop stamina; long runs build endurance."
        ),
        "min_weeks": 10,
        "max_weeks": 16,
        "peak_weekly_km_factor": 1.6,
        "sessions_per_week": 5,
        "weekly_structure": [
            {"day": "Mon", "type": "easy",     "km_pct": 0.15, "description": "Easy run"},
            {"day": "Tue", "type": "tempo",    "km_pct": 0.18, "description": "30-40 min at Tempo pace"},
            {"day": "Wed", "type": "easy",     "km_pct": 0.12, "description": "Easy recovery run"},
            {"day": "Thu", "type": "interval", "km_pct": 0.13, "description": "5x1200m at Interval pace, 600m jog recovery"},
            {"day": "Fri", "type": "rest",     "km_pct": 0.0,  "description": "Rest or cross-train"},
            {"day": "Sat", "type": "long",     "km_pct": 0.32, "description": "Long run at Easy pace with last 3 km at MP"},
            {"day": "Sun", "type": "easy",     "km_pct": 0.10, "description": "Easy recovery run or rest"},
        ],
        "taper_weeks": 2,
        "progression_pct_per_week": 0.06,
    },
    "marathon": {
        "label": "Marathon Plan",
        "description": (
            "Full marathon preparation. High aerobic volume with marathon-pace "
            "specificity. Long runs progressively build to 32-35 km."
        ),
        "min_weeks": 14,
        "max_weeks": 20,
        "peak_weekly_km_factor": 1.8,
        "sessions_per_week": 6,
        "weekly_structure": [
            {"day": "Mon", "type": "easy",     "km_pct": 0.12, "description": "Easy recovery run"},
            {"day": "Tue", "type": "tempo",    "km_pct": 0.15, "description": "35-45 min at Tempo pace"},
            {"day": "Wed", "type": "easy",     "km_pct": 0.12, "description": "Easy run"},
            {"day": "Thu", "type": "interval", "km_pct": 0.12, "description": "5x1000m at Interval pace, 400m jog recovery"},
            {"day": "Fri", "type": "easy",     "km_pct": 0.10, "description": "Easy run or rest"},
            {"day": "Sat", "type": "long",     "km_pct": 0.33, "description": "Long run at Easy pace, last 5 km at MP"},
            {"day": "Sun", "type": "rest",     "km_pct": 0.0,  "description": "Full rest"},
        ],
        "taper_weeks": 3,
        "progression_pct_per_week": 0.05,
    },
}
