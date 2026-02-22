"""
Fasting Data — Metabolic zone definitions, fasting type configurations,
and zone-specific guidance.

Scientific basis:
- Fed → Early Fasting → Fat Burning → Ketosis → Deep Ketosis & Autophagy
- Zone timings from consensus of metabolic physiology literature
- Autophagy evidence largely from animal models (PMID: 30172870)
- IF umbrella reviews: PMID 39618023, 34919135, 38335125
"""

# ── Metabolic Zones ──────────────────────────────────────────────────────
# Each zone describes the dominant metabolic state at that fasting duration.

FASTING_ZONES = [
    {
        "id": "fed",
        "name": "Fed State",
        "start_hours": 0,
        "end_hours": 4,
        "color": "#30D158",       # green — energy available
        "icon": "&#127860;",      # fork and knife
        "description": "Insulin elevated, nutrients being absorbed and stored.",
        "mechanism": (
            "After eating, blood glucose rises and the pancreas releases insulin. "
            "Glucose is taken up by cells for energy; excess is stored as glycogen "
            "in the liver and muscles, and as triglycerides in adipose tissue."
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
        "description": "Insulin drops, liver glycogen fuels blood glucose.",
        "mechanism": (
            "Insulin levels fall as the post-absorptive state begins. The liver "
            "breaks down glycogen (glycogenolysis) to maintain blood glucose. "
            "Free fatty acid release from adipose tissue begins to increase."
        ),
        "causation_note": None,
    },
    {
        "id": "fat_burning",
        "name": "Fat Burning",
        "start_hours": 12,
        "end_hours": 18,
        "color": "#FF9F0A",       # orange — active lipolysis
        "icon": "&#128293;",      # fire
        "description": "Glycogen depleted, lipolysis accelerates, growth hormone rises.",
        "mechanism": (
            "Hepatic glycogen stores are substantially depleted. The body shifts "
            "to fatty acid oxidation as the primary fuel source. Growth hormone "
            "secretion increases, promoting fat mobilization while preserving "
            "lean mass. Gluconeogenesis maintains blood glucose from amino acids "
            "and glycerol."
        ),
        "causation_note": None,
    },
    {
        "id": "ketosis",
        "name": "Ketosis",
        "start_hours": 18,
        "end_hours": 24,
        "color": "#BF5AF2",       # purple — metabolic shift
        "icon": "&#9889;",        # lightning bolt
        "description": "Liver produces ketone bodies; brain begins using BHB for fuel.",
        "mechanism": (
            "With sustained low insulin and depleted glycogen, the liver converts "
            "fatty acids into ketone bodies (beta-hydroxybutyrate, acetoacetate). "
            "The brain, which cannot directly use fatty acids, begins utilizing "
            "BHB for up to 60-70% of its energy needs. AMPK signaling increases."
        ),
        "causation_note": None,
    },
    {
        "id": "deep_ketosis",
        "name": "Deep Ketosis & Autophagy",
        "start_hours": 24,
        "end_hours": 72,
        "color": "#FF375F",       # red — advanced
        "icon": "&#9851;",        # recycling symbol
        "description": "Cellular recycling pathways activated; mTOR suppressed.",
        "mechanism": (
            "Prolonged fasting further activates AMPK and suppresses mTOR, "
            "triggering autophagy — the cell's recycling program that degrades "
            "damaged organelles and misfolded proteins. Ketone levels peak. "
            "Immune cell regeneration may occur with extended fasts (>48h)."
        ),
        "causation_note": (
            "Most autophagy timing evidence derives from animal models. "
            "Human autophagy biomarker studies are limited and exact onset "
            "timing varies individually (PMID: 30172870)."
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
        "color": "#8E8E93",
    },
}


# ── Fasting Safety Notes ─────────────────────────────────────────────────

FASTING_SAFETY = {
    "contraindications": [
        "Pregnancy or breastfeeding",
        "Type 1 diabetes or insulin-dependent Type 2 diabetes",
        "History of eating disorders",
        "Underweight (BMI < 18.5)",
        "Children and adolescents under 18",
        "Active infections or acute illness",
    ],
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
