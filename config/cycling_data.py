"""Cycling training data — TrainerRoad-style power-based prescription.

Based on Coggan 7-zone power model (Allen & Coggan, "Training and Racing with
a Power Meter", 3rd ed.) and Renaissance Periodization periodization principles.

TSS/IF/CTL/ATL/TSB methodology from Dr. Andrew Coggan's Performance Manager.
"""

# ── Coggan 7 Power Zones ───────────────────────────────────────────────────
# Each zone expressed as % of FTP. Colors match common cycling app conventions.

POWER_ZONES = {
    "z1": {
        "name": "Active Recovery",
        "min_pct": 0,
        "max_pct": 55,
        "color": "#9E9E9E",
        "description": "Very easy spinning. Used for warm-up, cool-down, and recovery between hard efforts. Feels effortless.",
    },
    "z2": {
        "name": "Endurance",
        "min_pct": 56,
        "max_pct": 75,
        "color": "#2196F3",
        "description": "All-day conversational pace. Primary aerobic development zone. Maximises fat oxidation and builds your aerobic base.",
    },
    "z3": {
        "name": "Tempo",
        "min_pct": 76,
        "max_pct": 87,
        "color": "#4CAF50",
        "description": "Comfortably hard. Improves lactate clearance and aerobic capacity. Harder to hold a conversation.",
    },
    "z4": {
        "name": "Lactate Threshold",
        "min_pct": 88,
        "max_pct": 94,
        "color": "#F9AB00",
        "description": "Sweet spot and threshold. High training stimulus per hour. Breathing is laboured; speech limited to short sentences.",
    },
    "z5": {
        "name": "VO2max",
        "min_pct": 95,
        "max_pct": 105,
        "color": "#E8710A",
        "description": "Very hard. Raises VO2max ceiling. Short intervals of 3–8 minutes. Breathing is maximal; conversation impossible.",
    },
    "z6": {
        "name": "Anaerobic Capacity",
        "min_pct": 106,
        "max_pct": 120,
        "color": "#D93025",
        "description": "Maximal short efforts. Raises anaerobic capacity. 30 s–3 min intervals. Severe pain, maximal effort.",
    },
    "z7": {
        "name": "Neuromuscular Power",
        "min_pct": 121,
        "max_pct": 300,
        "color": "#7B1FA2",
        "description": "Sprint power. Pure neuromuscular recruitment. Under 15 seconds. Full sprint, no pacing.",
    },
}

# ── Workout Types ──────────────────────────────────────────────────────────

WORKOUT_TYPES = {
    "recovery":   {"label": "Recovery",    "color": "#9E9E9E", "icon": "&#128564;", "primary_zone": "z1"},
    "endurance":  {"label": "Endurance",   "color": "#2196F3", "icon": "&#128690;", "primary_zone": "z2"},
    "tempo":      {"label": "Tempo",       "color": "#4CAF50", "icon": "&#127939;", "primary_zone": "z3"},
    "sweet_spot": {"label": "Sweet Spot",  "color": "#F9AB00", "icon": "&#127922;", "primary_zone": "z4"},
    "threshold":  {"label": "Threshold",   "color": "#E8710A", "icon": "&#128293;", "primary_zone": "z4"},
    "vo2max":     {"label": "VO2max",      "color": "#D93025", "icon": "&#128170;", "primary_zone": "z5"},
    "anaerobic":  {"label": "Anaerobic",   "color": "#7B1FA2", "icon": "&#9889;",   "primary_zone": "z6"},
}

# ── Structured Workout Library ─────────────────────────────────────────────
# Each interval: duration_sec, power_pct (fraction of FTP), label, zone

WORKOUT_LIBRARY = [

    # ── RECOVERY ──────────────────────────────────────────────────────────
    {
        "id": "recovery_30",
        "name": "Easy Spin",
        "type": "recovery",
        "duration_min": 30,
        "tss_estimate": 22,
        "difficulty_level": 1.0,
        "description": "30-minute active recovery at Z1. Keep power under 55% FTP. Flushes legs between hard sessions. Do not go harder — this is rest, not training.",
        "intervals": [
            {"duration_sec": 300,  "power_pct": 0.50, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 1500, "power_pct": 0.50, "label": "Z1 Spin",    "zone": "z1"},
            {"duration_sec": 300,  "power_pct": 0.45, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "recovery_45",
        "name": "Pettit",
        "type": "recovery",
        "duration_min": 45,
        "tss_estimate": 34,
        "difficulty_level": 1.5,
        "description": "45-minute aerobic spin with brief neuromuscular openers mid-ride. Good between hard days or as a pre-race shakeout ride.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.05, "label": "Opener 1",   "zone": "z5"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Easy",       "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.05, "label": "Opener 2",   "zone": "z5"},
            {"duration_sec": 1200, "power_pct": 0.50, "label": "Z1 Spin",    "zone": "z1"},
            {"duration_sec": 600,  "power_pct": 0.45, "label": "Cool-down",  "zone": "z1"},
        ],
    },

    # ── ENDURANCE ─────────────────────────────────────────────────────────
    {
        "id": "endurance_60",
        "name": "Carson -4",
        "type": "endurance",
        "duration_min": 60,
        "tss_estimate": 46,
        "difficulty_level": 2.0,
        "description": "60 minutes of steady Z2 riding. Pure aerobic base building. Hold 65% FTP throughout. The foundation of all cycling fitness.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 2400, "power_pct": 0.65, "label": "Z2 Base",    "zone": "z2"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "endurance_90",
        "name": "Koip -2",
        "type": "endurance",
        "duration_min": 90,
        "tss_estimate": 68,
        "difficulty_level": 3.0,
        "description": "90-minute Z2 endurance ride with a brief tempo pick-up mid-ride. Develops the aerobic engine while introducing slightly higher loads.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 2400, "power_pct": 0.65, "label": "Z2 Base",    "zone": "z2"},
            {"duration_sec": 600,  "power_pct": 0.82, "label": "Tempo Block", "zone": "z3"},
            {"duration_sec": 1200, "power_pct": 0.65, "label": "Z2 Return",  "zone": "z2"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "endurance_120",
        "name": "Fletcher",
        "type": "endurance",
        "duration_min": 120,
        "tss_estimate": 91,
        "difficulty_level": 4.0,
        "description": "2-hour aerobic endurance ride. Strong Z2 base stimulus. The bread-and-butter of any serious training plan.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 6000, "power_pct": 0.68, "label": "Z2 Endurance","zone": "z2"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },

    # ── TEMPO ─────────────────────────────────────────────────────────────
    {
        "id": "tempo_60_3x10",
        "name": "Geiger",
        "type": "tempo",
        "duration_min": 60,
        "tss_estimate": 55,
        "difficulty_level": 3.5,
        "description": "3×10-minute tempo intervals at 83% FTP with 5-minute easy recovery. Improves lactate clearance and raises the tempo ceiling.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 600,  "power_pct": 0.83, "label": "Tempo 1",    "zone": "z3"},
            {"duration_sec": 300,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 600,  "power_pct": 0.83, "label": "Tempo 2",    "zone": "z3"},
            {"duration_sec": 300,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 600,  "power_pct": 0.83, "label": "Tempo 3",    "zone": "z3"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "tempo_75_2x20",
        "name": "Mount Field",
        "type": "tempo",
        "duration_min": 75,
        "tss_estimate": 72,
        "difficulty_level": 5.0,
        "description": "2×20-minute tempo at 85% FTP with 5-minute recovery. Extended aerobic tempo stimulus. Tough but sustainable.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 1200, "power_pct": 0.85, "label": "Tempo 1",    "zone": "z3"},
            {"duration_sec": 300,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 1200, "power_pct": 0.85, "label": "Tempo 2",    "zone": "z3"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },

    # ── SWEET SPOT ────────────────────────────────────────────────────────
    {
        "id": "ss_60_2x15",
        "name": "Antelope",
        "type": "sweet_spot",
        "duration_min": 60,
        "tss_estimate": 64,
        "difficulty_level": 4.5,
        "description": "2×15-minute sweet spot intervals at 90% FTP. The most time-efficient training zone — high aerobic benefit with manageable fatigue.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 900,  "power_pct": 0.90, "label": "SS 1",       "zone": "z4"},
            {"duration_sec": 300,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 900,  "power_pct": 0.90, "label": "SS 2",       "zone": "z4"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "ss_75_3x12",
        "name": "Eclipse",
        "type": "sweet_spot",
        "duration_min": 75,
        "tss_estimate": 80,
        "difficulty_level": 5.5,
        "description": "3×12-minute sweet spot at 90-94% FTP with 4-minute recoveries. More total sweet spot volume for greater aerobic adaptation.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 720,  "power_pct": 0.92, "label": "SS 1",       "zone": "z4"},
            {"duration_sec": 240,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 720,  "power_pct": 0.92, "label": "SS 2",       "zone": "z4"},
            {"duration_sec": 240,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 720,  "power_pct": 0.92, "label": "SS 3",       "zone": "z4"},
            {"duration_sec": 660,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "ss_90_3x15",
        "name": "Carillon",
        "type": "sweet_spot",
        "duration_min": 90,
        "tss_estimate": 100,
        "difficulty_level": 6.5,
        "description": "3×15-minute sweet spot blocks at 88-94% FTP. High aerobic stimulus. A benchmark sweet spot workout that builds real fitness.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 900,  "power_pct": 0.91, "label": "SS 1",       "zone": "z4"},
            {"duration_sec": 300,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 900,  "power_pct": 0.91, "label": "SS 2",       "zone": "z4"},
            {"duration_sec": 300,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 900,  "power_pct": 0.91, "label": "SS 3",       "zone": "z4"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },

    # ── THRESHOLD ─────────────────────────────────────────────────────────
    {
        "id": "threshold_60_2x10",
        "name": "Kaiser",
        "type": "threshold",
        "duration_min": 60,
        "tss_estimate": 68,
        "difficulty_level": 5.0,
        "description": "2×10-minute threshold intervals at exactly 100% FTP. Classic workout to raise lactate threshold. Hard but achievable.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 600,  "power_pct": 1.00, "label": "FTP 1",      "zone": "z4"},
            {"duration_sec": 300,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 600,  "power_pct": 1.00, "label": "FTP 2",      "zone": "z4"},
            {"duration_sec": 300,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 600,  "power_pct": 1.00, "label": "FTP 3",      "zone": "z4"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "threshold_75_20min",
        "name": "Lamarck",
        "type": "threshold",
        "duration_min": 75,
        "tss_estimate": 82,
        "difficulty_level": 6.5,
        "description": "One sustained 20-minute FTP interval. Tests and builds threshold power. Often used as a fitness assessment.",
        "intervals": [
            {"duration_sec": 900,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 1200, "power_pct": 1.00, "label": "FTP Block",  "zone": "z4"},
            {"duration_sec": 900,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "threshold_90_3x12",
        "name": "Mount Baldy",
        "type": "threshold",
        "duration_min": 90,
        "tss_estimate": 105,
        "difficulty_level": 7.5,
        "description": "3×12-minute threshold efforts with 6-minute recoveries. High training load. Only attempt this when well-rested.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 720,  "power_pct": 1.00, "label": "FTP 1",      "zone": "z4"},
            {"duration_sec": 360,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 720,  "power_pct": 1.00, "label": "FTP 2",      "zone": "z4"},
            {"duration_sec": 360,  "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 720,  "power_pct": 1.00, "label": "FTP 3",      "zone": "z4"},
            {"duration_sec": 720,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },

    # ── VO2MAX ────────────────────────────────────────────────────────────
    {
        "id": "vo2_45_5x3",
        "name": "Baird +2",
        "type": "vo2max",
        "duration_min": 45,
        "tss_estimate": 60,
        "difficulty_level": 6.0,
        "description": "5×3-minute VO2max intervals at 108% FTP with equal rest. Raises your aerobic ceiling. Expect maximal breathing and burning legs.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.08, "label": "VO2 1",      "zone": "z5"},
            {"duration_sec": 180,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.08, "label": "VO2 2",      "zone": "z5"},
            {"duration_sec": 180,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.08, "label": "VO2 3",      "zone": "z5"},
            {"duration_sec": 180,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.08, "label": "VO2 4",      "zone": "z5"},
            {"duration_sec": 180,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.08, "label": "VO2 5",      "zone": "z5"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "vo2_60_4x5",
        "name": "Ericsson",
        "type": "vo2max",
        "duration_min": 60,
        "tss_estimate": 78,
        "difficulty_level": 7.0,
        "description": "4×5-minute VO2max efforts at 102% FTP. Sustained oxygen uptake at maximal aerobic power. A classic VO2max builder.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 300,  "power_pct": 1.02, "label": "VO2 1",      "zone": "z5"},
            {"duration_sec": 300,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 300,  "power_pct": 1.02, "label": "VO2 2",      "zone": "z5"},
            {"duration_sec": 300,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 300,  "power_pct": 1.02, "label": "VO2 3",      "zone": "z5"},
            {"duration_sec": 300,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 300,  "power_pct": 1.02, "label": "VO2 4",      "zone": "z5"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "vo2_60_6x3",
        "name": "Dade +1",
        "type": "vo2max",
        "duration_min": 60,
        "tss_estimate": 80,
        "difficulty_level": 7.5,
        "description": "6×3-minute VO2max at 110% FTP. Higher intensity than Baird — brutal but highly effective for raising VO2max.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.10, "label": "VO2 1",      "zone": "z5"},
            {"duration_sec": 180,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.10, "label": "VO2 2",      "zone": "z5"},
            {"duration_sec": 180,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.10, "label": "VO2 3",      "zone": "z5"},
            {"duration_sec": 180,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.10, "label": "VO2 4",      "zone": "z5"},
            {"duration_sec": 180,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.10, "label": "VO2 5",      "zone": "z5"},
            {"duration_sec": 180,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 180,  "power_pct": 1.10, "label": "VO2 6",      "zone": "z5"},
            {"duration_sec": 660,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },

    # ── ANAEROBIC ─────────────────────────────────────────────────────────
    {
        "id": "anaerobic_45_8x1",
        "name": "Bluebell",
        "type": "anaerobic",
        "duration_min": 45,
        "tss_estimate": 68,
        "difficulty_level": 7.0,
        "description": "8×1-minute anaerobic intervals at 120% FTP with 2-minute recovery. Builds top-end power and anaerobic capacity.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.20, "label": "An 1",       "zone": "z6"},
            {"duration_sec": 120,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.20, "label": "An 2",       "zone": "z6"},
            {"duration_sec": 120,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.20, "label": "An 3",       "zone": "z6"},
            {"duration_sec": 120,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.20, "label": "An 4",       "zone": "z6"},
            {"duration_sec": 120,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.20, "label": "An 5",       "zone": "z6"},
            {"duration_sec": 120,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.20, "label": "An 6",       "zone": "z6"},
            {"duration_sec": 120,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.20, "label": "An 7",       "zone": "z6"},
            {"duration_sec": 120,  "power_pct": 0.55, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 60,   "power_pct": 1.20, "label": "An 8",       "zone": "z6"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "anaerobic_50_10x30",
        "name": "Spanish Needle",
        "type": "anaerobic",
        "duration_min": 50,
        "tss_estimate": 72,
        "difficulty_level": 8.5,
        "description": "10×30-second all-out repeats at 150% FTP with 2-minute recovery. Extremely high power output. Develops sprint and anaerobic repeatability.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 1",   "zone": "z7"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 2",   "zone": "z7"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 3",   "zone": "z7"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 4",   "zone": "z7"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 5",   "zone": "z7"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 6",   "zone": "z7"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 7",   "zone": "z7"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 8",   "zone": "z7"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 9",   "zone": "z7"},
            {"duration_sec": 120,  "power_pct": 0.50, "label": "Rest",       "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.50, "label": "Sprint 10",  "zone": "z7"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
    {
        "id": "anaerobic_45_crit",
        "name": "Criterium Simulation",
        "type": "anaerobic",
        "duration_min": 45,
        "tss_estimate": 65,
        "difficulty_level": 7.5,
        "description": "Criterium-style 30/15s micro-intervals alternating 130% and 60% FTP. Mimics the attack/recover demands of crit racing.",
        "intervals": [
            {"duration_sec": 600,  "power_pct": 0.55, "label": "Warm-up",    "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 15,   "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 15,   "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 15,   "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 15,   "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 15,   "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 15,   "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 15,   "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 300,  "power_pct": 0.60, "label": "Rest Block", "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 15,   "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 15,   "power_pct": 0.60, "label": "Recovery",   "zone": "z1"},
            {"duration_sec": 30,   "power_pct": 1.30, "label": "Attack",     "zone": "z6"},
            {"duration_sec": 600,  "power_pct": 0.50, "label": "Cool-down",  "zone": "z1"},
        ],
    },
]

# ── O(1) lookup dict ───────────────────────────────────────────────────────
WORKOUT_LIBRARY_BY_ID: dict = {w["id"]: w for w in WORKOUT_LIBRARY}

# ── Training Phases ────────────────────────────────────────────────────────

TRAINING_PHASES = {
    "base": {
        "label": "Base Phase",
        "weeks": 8,
        "color": "#2196F3",
        "description": (
            "Build your aerobic engine with Z2 endurance and sweet spot work. "
            "Volume rises progressively over 8 weeks with a deload every 4th week. "
            "Based on Seiler (2010) polarised training model — 80% low intensity, 20% high."
        ),
        "tss_range": (300, 450),
        "primary_types": ["endurance", "sweet_spot", "tempo"],
        "weekly_structure": {
            3: ["endurance_60", "ss_60_2x15", "endurance_90"],
            4: ["recovery_30", "endurance_60", "ss_60_2x15", "endurance_90"],
            5: ["recovery_30", "endurance_60", "ss_60_2x15", "tempo_60_3x10", "endurance_90"],
            6: ["recovery_30", "endurance_60", "ss_60_2x15", "tempo_60_3x10", "endurance_90", "ss_75_3x12"],
        },
        "deload_structure": {
            3: ["recovery_30", "endurance_60", "recovery_45"],
            4: ["recovery_30", "recovery_45", "endurance_60", "recovery_30"],
            5: ["recovery_30", "recovery_45", "endurance_60", "recovery_30", "recovery_45"],
            6: ["recovery_30", "recovery_45", "endurance_60", "recovery_30", "recovery_45", "endurance_60"],
        },
    },
    "build": {
        "label": "Build Phase",
        "weeks": 8,
        "color": "#E8710A",
        "description": (
            "Raise your threshold and VO2max with harder structured work. "
            "Assumes a solid aerobic base. Higher fatigue — prioritise sleep and nutrition. "
            "Deload every 4th week. Based on Laursen & Jenkins (2002) HIIT research."
        ),
        "tss_range": (400, 550),
        "primary_types": ["threshold", "vo2max", "sweet_spot"],
        "weekly_structure": {
            3: ["endurance_60", "threshold_60_2x10", "vo2_45_5x3"],
            4: ["recovery_30", "endurance_60", "threshold_60_2x10", "vo2_45_5x3"],
            5: ["recovery_30", "endurance_60", "ss_60_2x15", "threshold_60_2x10", "vo2_45_5x3"],
            6: ["recovery_30", "endurance_60", "ss_75_3x12", "threshold_75_20min", "vo2_60_4x5", "endurance_90"],
        },
        "deload_structure": {
            3: ["recovery_30", "endurance_60", "recovery_45"],
            4: ["recovery_30", "recovery_45", "endurance_60", "recovery_30"],
            5: ["recovery_30", "recovery_45", "endurance_60", "recovery_30", "recovery_45"],
            6: ["recovery_30", "recovery_45", "endurance_60", "recovery_30", "recovery_45", "endurance_60"],
        },
    },
    "specialty": {
        "label": "Specialty / Peak Phase",
        "weeks": 4,
        "color": "#7B1FA2",
        "description": (
            "Sharpen for your goal event. Week 1-3 maintain high intensity; "
            "Week 4 is a taper (reduced volume, maintained intensity). "
            "Anaerobic and sprint work raise top-end power while the aerobic base carries you."
        ),
        "tss_range": (350, 500),
        "primary_types": ["anaerobic", "vo2max", "threshold"],
        "weekly_structure": {
            3: ["endurance_60", "vo2_45_5x3", "anaerobic_45_8x1"],
            4: ["recovery_30", "endurance_60", "vo2_60_4x5", "anaerobic_45_8x1"],
            5: ["recovery_30", "endurance_60", "ss_60_2x15", "vo2_60_4x5", "anaerobic_45_8x1"],
            6: ["recovery_30", "endurance_60", "threshold_60_2x10", "vo2_60_4x5", "anaerobic_45_8x1", "endurance_90"],
        },
        "deload_structure": {  # Week 4 taper
            3: ["recovery_30", "endurance_60", "recovery_45"],
            4: ["recovery_30", "recovery_30", "endurance_60", "recovery_30"],
            5: ["recovery_30", "recovery_30", "endurance_60", "recovery_30", "recovery_45"],
            6: ["recovery_30", "recovery_30", "endurance_60", "recovery_30", "recovery_45", "endurance_60"],
        },
    },
}

# ── Difficulty Survey (post-ride) ──────────────────────────────────────────

DIFFICULTY_SURVEY_OPTIONS = {
    1: {"label": "Very Easy",  "emoji": "&#128526;", "description": "Could have done much more", "progression_delta": 0.5},
    2: {"label": "Easy",       "emoji": "&#128522;", "description": "Felt controlled throughout", "progression_delta": 0.3},
    3: {"label": "Moderate",   "emoji": "&#128528;", "description": "Right on target",            "progression_delta": 0.2},
    4: {"label": "Hard",       "emoji": "&#128530;", "description": "Tough but completed",        "progression_delta": 0.1},
    5: {"label": "All Out",    "emoji": "&#128565;", "description": "Max effort, barely finished", "progression_delta": 0.0},
}

# ── Athlete Profile Options ────────────────────────────────────────────────

ATHLETE_TYPES = [
    "All-Around",
    "Climber",
    "Time Trialist",
    "Criterium Racer",
    "Endurance / Gran Fondo",
    "Triathlete",
    "Casual Fitness",
]

# ── Progression Defaults ───────────────────────────────────────────────────

PROGRESSION_DEFAULTS = {
    "endurance":  1.0,
    "tempo":      1.0,
    "sweet_spot": 1.0,
    "threshold":  1.0,
    "vo2max":     1.0,
    "anaerobic":  1.0,
}

# ── W/kg Racer Category Benchmarks ────────────────────────────────────────

WATT_KG_CATEGORIES = [
    {"label": "Cat 5 / Recreational", "min_wkg": 0.0,  "max_wkg": 2.5,  "color": "#9E9E9E"},
    {"label": "Cat 4",                "min_wkg": 2.5,  "max_wkg": 3.2,  "color": "#2196F3"},
    {"label": "Cat 3",                "min_wkg": 3.2,  "max_wkg": 4.0,  "color": "#4CAF50"},
    {"label": "Cat 2",                "min_wkg": 4.0,  "max_wkg": 4.6,  "color": "#F9AB00"},
    {"label": "Cat 1",                "min_wkg": 4.6,  "max_wkg": 5.2,  "color": "#E8710A"},
    {"label": "Pro / Elite",          "min_wkg": 5.2,  "max_wkg": 99.0, "color": "#7B1FA2"},
]
