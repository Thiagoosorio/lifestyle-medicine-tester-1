"""
Fasting Data — Approximate fasting phase definitions, protocol configurations,
and safety guidance.

Scientific basis:
- Time bands are approximate population-level physiology, not measured states
- Individual substrate use and ketone production vary substantially
- Human autophagy onset cannot be inferred from a fasting timer
- IF umbrella reviews: PMID 39618023, 34919135, 38335125
"""

# ── Metabolic Zones ──────────────────────────────────────────────────────
# Each phase is an approximate educational time band, not a measured metabolic state.

FASTING_ZONES = [
    {
        "id": "fed",
        "name": "Fed State",
        "start_hours": 0,
        "end_hours": 4,
        "color": "#30D158",       # green — energy available
        "icon": "&#127860;",      # fork and knife
        "description": "A recent meal may still be undergoing absorption and storage.",
        "mechanism": (
            "After eating, glucose and insulin typically rise while nutrients are absorbed. "
            "The timing and magnitude vary with meal composition, activity, medications, "
            "and individual physiology; this timer does not measure them."
        ),
        "causation_note": None,
    },
    {
        "id": "early_fasting",
        "name": "Early Fasting",
        "start_hours": 4,
        "end_hours": 12,
        "color": "#FFD60A",       # yellow — transitioning
        "icon": "&#9203;",        # timer
        "description": "Post-meal insulin may decline while liver glycogen supports glucose.",
        "mechanism": (
            "As absorption winds down, insulin generally declines and liver glycogen may "
            "contribute more to blood glucose. Fatty-acid release may increase gradually. "
            "A clock alone cannot determine these changes for an individual."
        ),
        "causation_note": None,
    },
    {
        "id": "fat_burning",
        "name": "Greater Fat Use May Begin",
        "start_hours": 12,
        "end_hours": 18,
        "color": "#FF9F0A",       # orange — active lipolysis
        "icon": "&#128293;",      # fire
        "description": "Fat oxidation may contribute more; glycogen is not assumed depleted.",
        "mechanism": (
            "Population studies suggest fat oxidation often contributes more as fasting "
            "continues, while glycogen use and gluconeogenesis vary. This is not a claim "
            "that glycogen is depleted or that fat is the primary fuel at this time."
        ),
        "causation_note": None,
    },
    {
        "id": "ketosis",
        "name": "Ketone Production May Rise",
        "start_hours": 18,
        "end_hours": 24,
        "color": "#BF5AF2",       # purple — metabolic shift
        "icon": "&#9889;",        # lightning bolt
        "description": "Ketones may rise, but ketosis is not established without measurement.",
        "mechanism": (
            "The liver may increase ketone production as insulin and carbohydrate "
            "availability decline. The onset and degree vary widely, and this timer does "
            "not measure beta-hydroxybutyrate, glucose, insulin, or cellular signaling."
        ),
        "causation_note": None,
    },
    {
        "id": "deep_ketosis",
        "name": "Extended Fasting",
        "start_hours": 24,
        "end_hours": 72,
        "color": "#FF375F",       # red — advanced
        "icon": "&#9851;",        # recycling symbol
        "description": "Metabolic and cellular responses remain variable and unmeasured.",
        "mechanism": (
            "Longer fasting can increase ketone production and alter nutrient-sensing "
            "pathways, but a duration threshold does not establish deep ketosis, autophagy, "
            "or immune-cell regeneration in an individual. Extended fasting also carries "
            "greater medication, glucose, hydration, and electrolyte risks."
        ),
        "causation_note": (
            "Human autophagy evidence is limited and tissue-specific; onset cannot be "
            "determined from elapsed time (PMID: 30172870). More than 24 hours requires "
            "review of the specific plan with a qualified clinician."
        ),
    },
]


# ── Fasting Types ────────────────────────────────────────────────────────
# Protocols available for users to select when starting a fast.

FASTING_TYPES = {
    "12:12": {
        "label": "12:12",
        "target_hours": 12,
        "eating_window": 12,
        "difficulty": 1,
        "description": "Beginner-friendly — 12h fast, 12h eating window.",
        "color": "#30D158",
    },
    "14:10": {
        "label": "14:10",
        "target_hours": 14,
        "eating_window": 10,
        "difficulty": 1,
        "description": "Gentle step up — 14h fast, 10h eating window.",
        "color": "#30D158",
    },
    "16:8": {
        "label": "16:8",
        "target_hours": 16,
        "eating_window": 8,
        "difficulty": 2,
        "description": "Most popular protocol — 16h fast, 8h eating window.",
        "color": "#FFD60A",
    },
    "18:6": {
        "label": "18:6",
        "target_hours": 18,
        "eating_window": 6,
        "difficulty": 2,
        "description": "Intermediate — 18h fast, 6h eating window.",
        "color": "#FFD60A",
    },
    "20:4": {
        "label": "20:4 (Warrior)",
        "target_hours": 20,
        "eating_window": 4,
        "difficulty": 3,
        "description": "Advanced — 20h fast, 4h eating window.",
        "color": "#FF9F0A",
    },
    "OMAD": {
        "label": "OMAD",
        "target_hours": 23,
        "eating_window": 1,
        "difficulty": 3,
        "description": "One Meal A Day — ~23h fast, 1h eating window.",
        "color": "#FF9F0A",
    },
    "24h": {
        "label": "24-Hour Fast",
        "target_hours": 24,
        "eating_window": 0,
        "difficulty": 3,
        "description": "Full day fast — eat dinner, skip next day, eat following dinner.",
        "color": "#FF375F",
    },
    "36h": {
        "label": "36-Hour Fast",
        "target_hours": 36,
        "eating_window": 0,
        "difficulty": 3,
        "description": "Extended fast — skip an entire day of eating.",
        "color": "#FF375F",
    },
    "custom": {
        "label": "Custom",
        "target_hours": None,
        "eating_window": None,
        "difficulty": 0,
        "description": "Set your own fasting duration.",
        "color": "#AEAEB2",
    },
}


# ── Fasting Safety Notes ─────────────────────────────────────────────────

# ── Chronotype-Based Fasting Windows ────────────────────────────────────
# Optimal eating/fasting windows based on chronotype circadian rhythm.
# Reference: Chronotype influence on meal timing — PMID: 31375734

CHRONOTYPE_FASTING_WINDOWS = {
    "lion": {
        "label": "Early Bird (Lion)",
        "eating_12": ("06:00", "18:00"),
        "eating_16_8": ("07:00", "15:00"),
        "tip": "Your energy peaks in the morning. Front-load meals early and finish eating by mid-afternoon for best metabolic alignment.",
    },
    "bear": {
        "label": "Balanced (Bear)",
        "eating_12": ("08:00", "20:00"),
        "eating_16_8": ("10:00", "18:00"),
        "tip": "You follow a solar schedule. A classic 10-6 eating window works well. Aim for your largest meal at lunch.",
    },
    "wolf": {
        "label": "Night Owl (Wolf)",
        "eating_12": ("10:00", "22:00"),
        "eating_16_8": ("12:00", "20:00"),
        "tip": "Your metabolism runs later. A noon-to-8pm eating window lets you skip breakfast naturally. Avoid eating after 10pm.",
    },
    "dolphin": {
        "label": "Light Sleeper (Dolphin)",
        "eating_12": ("08:00", "19:00"),
        "eating_16_8": ("09:00", "17:00"),
        "tip": "Your circadian rhythm is sensitive. Keep a gentle fasting schedule and avoid extended fasts (>18h) which may worsen sleep.",
    },
}


FASTING_SAFETY = {
    "contraindications": [
        "Pregnancy or breastfeeding",
        "Type 1 diabetes or insulin-dependent Type 2 diabetes",
        "History of eating disorders",
        "Underweight (BMI < 18.5)",
        "Children and adolescents under 18",
        "Active infections or acute illness",
    ],
    "glucose_medication_question": (
        "I take insulin or another glucose-lowering medication."
    ),
    "screen_acknowledgement": (
        "I reviewed the conditions above, answered accurately, and understand that "
        "this tracker cannot determine whether fasting is medically safe for me."
    ),
    "clinician_review_acknowledgement": (
        "A qualified clinician who knows my medications and health history has reviewed "
        "this specific fasting duration with me."
    ),
    "phase_notice": (
        "The phase shown is only an approximate time-based estimate. It does not measure "
        "glycogen, fuel use, ketosis, insulin, autophagy, or any other metabolic state."
    ),
    "general_guidance": (
        "Stay hydrated with water, black coffee, or plain tea during fasts. "
        "Break extended fasts gently with small, easily digestible meals. "
        "Consult a healthcare provider before starting fasts longer than 24 hours."
    ),
    "disclaimer": (
        "Fasting protocols are for general wellness information only and do not "
        "constitute medical advice. Always consult your healthcare provider "
        "before making significant changes to your eating patterns."
    ),
}
