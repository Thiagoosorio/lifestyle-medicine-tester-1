"""App constants, pillar definitions, stage definitions, and color schemes."""

APP_NAME = "Lifestyle Medicine Coach"
APP_ICON = ":material/favorite:"

# ── Pillar definitions ──────────────────────────────────────────────────────
PILLARS = {
    1: {
        "name": "nutrition",
        "display_name": "Nutrition",
        "icon": ":material/restaurant:",
        "color": "#4CAF50",
        "description": "Whole-food, plant-predominant eating. Emphasis on vegetables, fruits, whole grains, legumes, nuts, and seeds.",
        "quick_tip": "Try adding one extra serving of vegetables to your meals today.",
    },
    2: {
        "name": "physical_activity",
        "display_name": "Physical Activity",
        "icon": ":material/directions_run:",
        "color": "#2196F3",
        "description": "Regular movement: 150+ min/week moderate or 75+ min/week vigorous aerobic activity, plus strength training 2+ days/week.",
        "quick_tip": "A 10-minute walk counts. Start small and build up.",
    },
    3: {
        "name": "sleep",
        "display_name": "Sleep",
        "icon": ":material/bedtime:",
        "color": "#9C27B0",
        "description": "Restorative sleep: consistently achieving 7-9 hours of quality sleep with good sleep hygiene.",
        "quick_tip": "Set a consistent bedtime and avoid screens 30 minutes before sleep.",
    },
    4: {
        "name": "stress_management",
        "display_name": "Stress Management",
        "icon": ":material/self_improvement:",
        "color": "#FF9800",
        "description": "Practices to manage chronic stress: mindfulness, meditation, breathing exercises, yoga, time in nature.",
        "quick_tip": "Try 3 deep breaths right now. Inhale for 4 counts, hold for 4, exhale for 6.",
    },
    5: {
        "name": "social_connection",
        "display_name": "Social Connection",
        "icon": ":material/group:",
        "color": "#E91E63",
        "description": "Meaningful relationships, community involvement, and a sense of belonging and connectedness.",
        "quick_tip": "Reach out to someone you care about today, even just a quick message.",
    },
    6: {
        "name": "substance_avoidance",
        "display_name": "Substance Avoidance",
        "icon": ":material/block:",
        "color": "#607D8B",
        "description": "Eliminating tobacco, limiting or eliminating alcohol, and avoiding other harmful substances.",
        "quick_tip": "If you drink alcohol, try replacing one drink this week with sparkling water.",
    },
}

PILLAR_NAMES = {pid: p["display_name"] for pid, p in PILLARS.items()}
PILLAR_COLORS = {pid: p["color"] for pid, p in PILLARS.items()}

# ── Stages of Change (TTM) ─────────────────────────────────────────────────
STAGES_OF_CHANGE = {
    "precontemplation": {
        "label": "Pre-contemplation",
        "description": "Not currently thinking about changing this area.",
        "coaching_approach": "Raise awareness gently. Provide information without pressure.",
    },
    "contemplation": {
        "label": "Contemplation",
        "description": "Thinking about making a change but haven't started yet.",
        "coaching_approach": "Explore ambivalence. Highlight the benefits of change.",
    },
    "preparation": {
        "label": "Preparation",
        "description": "Planning to take action soon and taking small steps.",
        "coaching_approach": "Help create specific plans. Set SMART goals. Build confidence.",
    },
    "action": {
        "label": "Action",
        "description": "Actively working on changing this behavior.",
        "coaching_approach": "Support and reinforce. Track progress. Troubleshoot barriers.",
    },
    "maintenance": {
        "label": "Maintenance",
        "description": "Have sustained this change for 6+ months.",
        "coaching_approach": "Prevent relapse. Celebrate consistency. Strengthen identity.",
    },
}

# ── COM-B Components ────────────────────────────────────────────────────────
COMB_COMPONENTS = {
    "capability_physical": "Physical Capability — Do you have the physical ability?",
    "capability_psychological": "Psychological Capability — Do you have the knowledge and skills?",
    "opportunity_physical": "Physical Opportunity — Does your environment support this?",
    "opportunity_social": "Social Opportunity — Do people around you support this?",
    "motivation_reflective": "Reflective Motivation — Do you have clear goals and plans?",
    "motivation_automatic": "Automatic Motivation — Is this becoming a habit?",
}

# ── Score interpretation ────────────────────────────────────────────────────
def get_score_label(score: int) -> str:
    if score <= 3:
        return "Needs Attention"
    elif score <= 5:
        return "Developing"
    elif score <= 7:
        return "Good"
    elif score <= 9:
        return "Very Good"
    return "Excellent"


def get_score_color(score: int) -> str:
    if score <= 3:
        return "#F44336"
    elif score <= 5:
        return "#FF9800"
    elif score <= 7:
        return "#FFC107"
    elif score <= 9:
        return "#8BC34A"
    return "#4CAF50"


# ── Motivational quotes ────────────────────────────────────────────────────
MOTIVATIONAL_QUOTES = [
    "The greatest wealth is health. — Virgil",
    "Take care of your body. It's the only place you have to live. — Jim Rohn",
    "Small daily improvements over time lead to stunning results. — Robin Sharma",
    "Health is not about the weight you lose, but about the life you gain.",
    "The journey of a thousand miles begins with a single step. — Lao Tzu",
    "You don't have to be extreme, just consistent.",
    "Wellness is the complete integration of body, mind, and spirit. — Greg Anderson",
    "Every day is a new opportunity to invest in your health.",
    "Progress, not perfection.",
    "Your body hears everything your mind says. Stay positive.",
    "The doctor of the future will give no medicine, but will interest his patients in the care of the human frame. — Thomas Edison",
    "Lifestyle is medicine. Every choice is a prescription.",
    "It is health that is the real wealth, not pieces of gold and silver. — Mahatma Gandhi",
    "What you do every day matters more than what you do once in a while.",
    "The best time to plant a tree was 20 years ago. The second best time is now.",
]

# ── Default habits per pillar ───────────────────────────────────────────────
DEFAULT_HABITS = {
    1: [  # Nutrition
        "Eat 5+ servings of fruits/vegetables",
        "Drink 8 glasses of water",
        "Eat a whole-food meal",
    ],
    2: [  # Physical Activity
        "30 minutes of movement",
        "Take 8,000+ steps",
        "Stretching or flexibility exercise",
    ],
    3: [  # Sleep
        "In bed by target bedtime",
        "No screens 30 min before bed",
        "7+ hours of sleep",
    ],
    4: [  # Stress Management
        "5 minutes of meditation/breathing",
        "Spend time in nature",
        "Practice gratitude",
    ],
    5: [  # Social Connection
        "Connect with a friend or family member",
        "Act of kindness",
        "Quality time with loved ones",
    ],
    6: [  # Substance Avoidance
        "Alcohol-free day",
        "Tobacco-free day",
        "Mindful about substance choices",
    ],
}
