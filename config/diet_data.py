"""
Diet Pattern Assessment — Inspired by Diet ID (Dr. David Katz, Yale).

Scientific basis:
- Healthy Eating Index 2020 (HEI-2020): USDA/CNPP scoring system
- Diet Quality Photo Navigation (DQPN): Katz DL et al (PMID: 25015212)
- Mediterranean diet: Estruch R et al (PMID: 29897866)
- DASH diet: Sacks FM et al (PMID: 11136953)
- Plant-based diets: Satija A et al (PMID: 29659968)
- Dietary patterns & T2D: Jannasch F et al (PMID: 28424256)
"""

# ══════════════════════════════════════════════════════════════════════════════
# DIET PATTERN DEFINITIONS (8 patterns)
# ══════════════════════════════════════════════════════════════════════════════

DIET_PATTERNS = {
    "mediterranean": {
        "name": "Mediterranean",
        "icon": "&#127813;",
        "color": "#30D158",
        "subtitle": "Heart-Healthy Traditional",
        "description": (
            "Rich in fruits, vegetables, whole grains, legumes, nuts, olive oil, "
            "and fish. Moderate dairy and wine with meals. Limited red meat and sweets. "
            "Inspired by traditional eating patterns of Greece, Southern Italy, and Spain."
        ),
        "strengths": [
            "Excellent cardiovascular protection (PREDIMED trial, PMID: 29897866)",
            "Rich in healthy monounsaturated fats from olive oil and nuts",
            "High in antioxidants and anti-inflammatory compounds",
            "Associated with longevity in Blue Zone populations",
        ],
        "improvements": [
            "Ensure adequate fiber from whole grains and legumes (target 30g/day)",
            "Moderate alcohol consumption carefully or eliminate entirely",
        ],
        "evidence": "PREDIMED trial: 30% CVD risk reduction (PMID: 29897866)",
        "hei_typical": [70, 90],
    },
    "dash": {
        "name": "DASH",
        "icon": "&#128154;",
        "color": "#0A84FF",
        "subtitle": "Blood Pressure Optimized",
        "description": (
            "Dietary Approaches to Stop Hypertension. Emphasizes fruits, vegetables, "
            "whole grains, lean proteins, and low-fat dairy. Specifically designed to "
            "reduce sodium and increase potassium, calcium, and magnesium intake."
        ),
        "strengths": [
            "Clinically proven to lower blood pressure (PMID: 11136953)",
            "Strong evidence for cardiovascular disease prevention",
            "Well-balanced macronutrient distribution",
            "19% reduction in type 2 diabetes risk (PMID: 28424256)",
        ],
        "improvements": [
            "Consider adding more plant-based proteins and healthy fats",
            "Increase omega-3 fatty acid intake from fish or plant sources",
        ],
        "evidence": "DASH trial: SBP reduced 5.5 mmHg vs control (PMID: 11136953)",
        "hei_typical": [65, 85],
    },
    "plant_based": {
        "name": "Plant-Based",
        "icon": "&#127793;",
        "color": "#34C759",
        "subtitle": "Whole Food Plant Forward",
        "description": (
            "Centered on fruits, vegetables, whole grains, legumes, nuts, and seeds "
            "with minimal or no animal products. Includes vegan and whole-food "
            "plant-based variations. Emphasizes nutrient density and fiber."
        ),
        "strengths": [
            "Highest fiber intake of any dietary pattern",
            "Strong evidence for weight management (PMID: 35672940)",
            "Rich in phytonutrients and antioxidants",
            "Lower environmental impact than animal-heavy diets",
        ],
        "improvements": [
            "Monitor vitamin B12, vitamin D, iron, and omega-3 status",
            "Ensure adequate protein through legume and grain combinations",
            "Consider supplementing B12 if fully plant-based",
        ],
        "evidence": "Vegan diets: -4.1kg weight, -0.18% HbA1c (PMID: 35672940)",
        "hei_typical": [60, 90],
    },
    "flexitarian": {
        "name": "Flexitarian",
        "icon": "&#127807;",
        "color": "#64D2FF",
        "subtitle": "Flexible Plant-Forward",
        "description": (
            "Primarily plant-based with occasional inclusion of meat, fish, and dairy. "
            "Focuses on increasing plant foods rather than strict elimination. A practical "
            "and sustainable approach for most people."
        ),
        "strengths": [
            "Balanced and nutritionally complete without supplements",
            "Sustainable and socially flexible approach",
            "Good variety ensures micronutrient adequacy",
            "Gradual shift toward more plants is achievable long-term",
        ],
        "improvements": [
            "Continue increasing plant-to-animal food ratio over time",
            "Choose high-quality animal products when consumed",
            "Aim for at least 30 different plant foods per week",
        ],
        "evidence": "Plant-based diets linked to 23% lower T2D risk (PMID: 29659968)",
        "hei_typical": [55, 75],
    },
    "standard_american": {
        "name": "Standard American",
        "icon": "&#127828;",
        "color": "#FF453A",
        "subtitle": "Typical Western Pattern",
        "description": (
            "Characterized by high intake of ultra-processed foods, refined grains, "
            "added sugars, sodium, and saturated fats. Low in fruits, vegetables, "
            "whole grains, and fiber. The most common dietary pattern in the US."
        ),
        "strengths": [
            "Familiar and widely available food options",
            "No special preparation required",
        ],
        "improvements": [
            "Gradually replace ultra-processed foods with whole foods",
            "Add 1 serving of vegetables to each meal as a starting point",
            "Switch from refined to whole grains (brown rice, whole wheat)",
            "Reduce added sugar intake (target <25g/day for women, <36g/day for men)",
            "Increase fiber to 25-30g/day through fruits, vegetables, and legumes",
        ],
        "evidence": "Ultra-processed food: per 50g/day -> RR 1.02 all-cause mortality (PMID: 38363072)",
        "hei_typical": [25, 45],
    },
    "low_carb": {
        "name": "Low-Carb / Keto",
        "icon": "&#129370;",
        "color": "#FFD60A",
        "subtitle": "Carbohydrate Restricted",
        "description": (
            "Restricts carbohydrate intake to promote fat burning and ketosis. "
            "Typically high in meats, fish, eggs, nuts, and non-starchy vegetables. "
            "May include very low-carb (keto: <50g/day) or moderate low-carb (<130g/day)."
        ),
        "strengths": [
            "Can be effective for short-term weight loss",
            "May improve blood sugar control in type 2 diabetes",
            "Reduces cravings and hunger through ketosis",
        ],
        "improvements": [
            "Ensure adequate fiber intake from non-starchy vegetables",
            "Monitor cholesterol levels, especially LDL",
            "Include plant-based fats (nuts, avocado, olive oil) over saturated fats",
            "Consider long-term sustainability and social implications",
            "Watch for micronutrient deficiencies (potassium, magnesium, folate)",
        ],
        "evidence": "Low-carb diets show mixed long-term evidence; short-term weight loss is well-supported",
        "hei_typical": [30, 55],
    },
    "paleo": {
        "name": "Paleo",
        "icon": "&#129384;",
        "color": "#FF9F0A",
        "subtitle": "Ancestral Approach",
        "description": (
            "Based on foods presumed to have been available to Paleolithic humans: "
            "meats, fish, vegetables, fruits, nuts, and seeds. Excludes grains, "
            "legumes, dairy, refined sugars, and processed foods."
        ),
        "strengths": [
            "Eliminates ultra-processed foods and refined sugars",
            "High in protein and vegetables",
            "Can improve satiety and reduce calorie intake",
        ],
        "improvements": [
            "Whole grains and legumes have strong evidence for health benefits",
            "Consider reintroducing legumes (rich in fiber, protein, minerals)",
            "Ensure calcium intake without dairy (leafy greens, fortified alternatives)",
            "May be expensive and socially restrictive",
        ],
        "evidence": "Limited long-term RCT evidence for Paleo specifically",
        "hei_typical": [35, 60],
    },
    "traditional": {
        "name": "Traditional / Cultural",
        "icon": "&#127758;",
        "color": "#BF5AF2",
        "subtitle": "Heritage-Based Eating",
        "description": (
            "Rooted in cultural food traditions from various world cuisines "
            "(Asian, Latin American, African, Middle Eastern, etc.). Typically "
            "features whole foods, traditional cooking methods, and community meals."
        ),
        "strengths": [
            "Deep cultural connection and social significance",
            "Often based on generations of practical nutritional wisdom",
            "Traditional diets tend to be whole-food based",
            "Community and family meal traditions support wellbeing",
        ],
        "improvements": [
            "Adapt traditional recipes to reduce sodium and added fats if needed",
            "Maintain the whole-food foundation while increasing plant diversity",
            "Preserve fermented food traditions (gut microbiome benefits)",
        ],
        "evidence": "Traditional diets globally associated with lower chronic disease rates",
        "hei_typical": [40, 70],
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# DIET QUIZ QUESTIONS (12 questions)
# Each answer assigns scores to diet patterns. Highest total = best match.
# ══════════════════════════════════════════════════════════════════════════════

DIET_QUIZ_QUESTIONS = [
    {
        "id": 1,
        "question": "How many servings of fruits and vegetables do you eat per day?",
        "options": [
            {"label": "0-1 servings", "scores": {"standard_american": 4, "low_carb": 1}},
            {"label": "2-3 servings", "scores": {"flexitarian": 2, "traditional": 2, "paleo": 2}},
            {"label": "4-5 servings", "scores": {"dash": 3, "mediterranean": 3, "flexitarian": 2}},
            {"label": "6+ servings", "scores": {"plant_based": 4, "mediterranean": 3, "dash": 3}},
        ],
        "hei_map": {
            0: {"total_fruits": 1, "whole_fruits": 1, "total_vegetables": 1, "greens_beans": 0},
            1: {"total_fruits": 2, "whole_fruits": 2, "total_vegetables": 2, "greens_beans": 1},
            2: {"total_fruits": 4, "whole_fruits": 4, "total_vegetables": 4, "greens_beans": 3},
            3: {"total_fruits": 5, "whole_fruits": 5, "total_vegetables": 5, "greens_beans": 5},
        },
    },
    {
        "id": 2,
        "question": "How often do you eat whole grains (brown rice, oats, whole wheat)?",
        "options": [
            {"label": "Rarely or never", "scores": {"low_carb": 3, "paleo": 3, "standard_american": 2}},
            {"label": "A few times per week", "scores": {"flexitarian": 2, "traditional": 2}},
            {"label": "Daily", "scores": {"mediterranean": 3, "dash": 3, "flexitarian": 2}},
            {"label": "Multiple times daily", "scores": {"plant_based": 3, "dash": 3, "traditional": 2}},
        ],
        "hei_map": {
            0: {"whole_grains": 1},
            1: {"whole_grains": 4},
            2: {"whole_grains": 7},
            3: {"whole_grains": 10},
        },
    },
    {
        "id": 3,
        "question": "How often do you eat red meat (beef, pork, lamb)?",
        "options": [
            {"label": "Never", "scores": {"plant_based": 4, "flexitarian": 1}},
            {"label": "1-2 times per week", "scores": {"mediterranean": 3, "dash": 2, "flexitarian": 3}},
            {"label": "3-5 times per week", "scores": {"paleo": 3, "low_carb": 2, "traditional": 2}},
            {"label": "Daily or more", "scores": {"standard_american": 4, "low_carb": 2}},
        ],
        "hei_map": {
            0: {"saturated_fats": 10},
            1: {"saturated_fats": 7},
            2: {"saturated_fats": 4},
            3: {"saturated_fats": 1},
        },
    },
    {
        "id": 4,
        "question": "How often do you eat fish or seafood?",
        "options": [
            {"label": "Rarely or never", "scores": {"standard_american": 2, "plant_based": 1}},
            {"label": "1-2 times per week", "scores": {"dash": 3, "flexitarian": 2, "traditional": 2}},
            {"label": "3+ times per week", "scores": {"mediterranean": 4, "paleo": 2}},
            {"label": "Daily", "scores": {"mediterranean": 3}},
        ],
        "hei_map": {
            0: {"seafood_plant_protein": 1},
            1: {"seafood_plant_protein": 3},
            2: {"seafood_plant_protein": 5},
            3: {"seafood_plant_protein": 5},
        },
    },
    {
        "id": 5,
        "question": "How often do you eat legumes (beans, lentils, chickpeas)?",
        "options": [
            {"label": "Rarely or never", "scores": {"paleo": 3, "low_carb": 2, "standard_american": 2}},
            {"label": "1-2 times per week", "scores": {"flexitarian": 2, "traditional": 2}},
            {"label": "3-5 times per week", "scores": {"mediterranean": 3, "dash": 3}},
            {"label": "Daily", "scores": {"plant_based": 4, "mediterranean": 2, "dash": 2}},
        ],
        "hei_map": {
            0: {"greens_beans": 0, "total_protein": 2},
            1: {"greens_beans": 2, "total_protein": 3},
            2: {"greens_beans": 4, "total_protein": 4},
            3: {"greens_beans": 5, "total_protein": 5},
        },
    },
    {
        "id": 6,
        "question": "What is your dairy consumption like?",
        "options": [
            {"label": "No dairy at all", "scores": {"plant_based": 3, "paleo": 2}},
            {"label": "Occasional (cheese, yogurt)", "scores": {"mediterranean": 2, "flexitarian": 2}},
            {"label": "Regular (daily milk, cheese, yogurt)", "scores": {"dash": 3, "traditional": 2}},
            {"label": "Heavy (multiple servings daily)", "scores": {"standard_american": 2}},
        ],
        "hei_map": {
            0: {"dairy": 2},
            1: {"dairy": 5},
            2: {"dairy": 8},
            3: {"dairy": 10},
        },
    },
    {
        "id": 7,
        "question": "How often do you consume sweets, desserts, or sugary drinks?",
        "options": [
            {"label": "Rarely (a few times per month)", "scores": {"plant_based": 3, "mediterranean": 3, "dash": 3, "paleo": 2}},
            {"label": "1-2 times per week", "scores": {"flexitarian": 2, "traditional": 2}},
            {"label": "3-5 times per week", "scores": {"standard_american": 2}},
            {"label": "Daily", "scores": {"standard_american": 4}},
        ],
        "hei_map": {
            0: {"added_sugars": 10},
            1: {"added_sugars": 7},
            2: {"added_sugars": 4},
            3: {"added_sugars": 1},
        },
    },
    {
        "id": 8,
        "question": "What cooking fat do you use most often?",
        "options": [
            {"label": "Olive oil or avocado oil", "scores": {"mediterranean": 4, "dash": 2, "flexitarian": 2}},
            {"label": "Butter or ghee", "scores": {"low_carb": 2, "paleo": 2, "traditional": 2}},
            {"label": "Vegetable/canola oil", "scores": {"standard_american": 2, "dash": 1}},
            {"label": "Coconut oil or other", "scores": {"paleo": 2, "plant_based": 1}},
        ],
        "hei_map": {
            0: {"fatty_acids": 10},
            1: {"fatty_acids": 3},
            2: {"fatty_acids": 6},
            3: {"fatty_acids": 5},
        },
    },
    {
        "id": 9,
        "question": "How often do you eat fast food or restaurant meals?",
        "options": [
            {"label": "Rarely (a few times per month)", "scores": {"plant_based": 2, "mediterranean": 2, "dash": 2}},
            {"label": "1-2 times per week", "scores": {"flexitarian": 2, "traditional": 2}},
            {"label": "3-5 times per week", "scores": {"standard_american": 3}},
            {"label": "Daily or almost daily", "scores": {"standard_american": 4}},
        ],
        "hei_map": {
            0: {"sodium": 9, "refined_grains": 8},
            1: {"sodium": 6, "refined_grains": 6},
            2: {"sodium": 3, "refined_grains": 3},
            3: {"sodium": 1, "refined_grains": 1},
        },
    },
    {
        "id": 10,
        "question": "What do you typically snack on?",
        "options": [
            {"label": "Fruits, nuts, or vegetables", "scores": {"plant_based": 3, "mediterranean": 3, "dash": 2}},
            {"label": "Cheese, yogurt, or eggs", "scores": {"low_carb": 3, "dash": 1, "flexitarian": 1}},
            {"label": "Chips, cookies, or candy", "scores": {"standard_american": 4}},
            {"label": "I don't snack often", "scores": {"traditional": 2, "paleo": 1}},
        ],
        "hei_map": {
            0: {"total_fruits": 5, "refined_grains": 8},
            1: {"dairy": 9, "refined_grains": 6},
            2: {"added_sugars": 2, "refined_grains": 2},
            3: {"refined_grains": 7},
        },
    },
    {
        "id": 11,
        "question": "How aware are you of sodium (salt) in your food?",
        "options": [
            {"label": "Very aware - I actively limit salt", "scores": {"dash": 4, "plant_based": 2}},
            {"label": "Somewhat aware - I try to moderate", "scores": {"mediterranean": 2, "flexitarian": 2}},
            {"label": "Not very aware", "scores": {"standard_american": 2, "traditional": 2}},
            {"label": "I don't pay attention to salt", "scores": {"standard_american": 3}},
        ],
        "hei_map": {
            0: {"sodium": 10},
            1: {"sodium": 7},
            2: {"sodium": 4},
            3: {"sodium": 2},
        },
    },
    {
        "id": 12,
        "question": "Which best describes your overall eating philosophy?",
        "options": [
            {"label": "Eat mostly plants, minimize processed foods", "scores": {"plant_based": 4, "mediterranean": 2}},
            {"label": "Balanced meals from all food groups", "scores": {"dash": 3, "flexitarian": 3, "mediterranean": 2}},
            {"label": "High protein, low carbs", "scores": {"low_carb": 4, "paleo": 3}},
            {"label": "I eat whatever is convenient or available", "scores": {"standard_american": 4}},
        ],
        "hei_map": {
            0: {"total_protein": 5, "seafood_plant_protein": 4},
            1: {"total_protein": 4, "fatty_acids": 7},
            2: {"total_protein": 5, "refined_grains": 5},
            3: {"total_protein": 3, "added_sugars": 3},
        },
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# HEI-2020 COMPONENT DEFINITIONS (13 components, 100 total points)
# Source: USDA Center for Nutrition Policy and Promotion
# ══════════════════════════════════════════════════════════════════════════════

HEI_COMPONENTS = {
    "total_fruits": {"max_score": 5, "type": "adequacy", "label": "Total Fruits", "color": "#FF9F0A"},
    "whole_fruits": {"max_score": 5, "type": "adequacy", "label": "Whole Fruits", "color": "#FF375F"},
    "total_vegetables": {"max_score": 5, "type": "adequacy", "label": "Total Vegetables", "color": "#34C759"},
    "greens_beans": {"max_score": 5, "type": "adequacy", "label": "Greens & Beans", "color": "#30D158"},
    "whole_grains": {"max_score": 10, "type": "adequacy", "label": "Whole Grains", "color": "#FFD60A"},
    "dairy": {"max_score": 10, "type": "adequacy", "label": "Dairy", "color": "#FFFFFF"},
    "total_protein": {"max_score": 5, "type": "adequacy", "label": "Total Protein", "color": "#0A84FF"},
    "seafood_plant_protein": {"max_score": 5, "type": "adequacy", "label": "Seafood & Plant Proteins", "color": "#64D2FF"},
    "fatty_acids": {"max_score": 10, "type": "adequacy", "label": "Fatty Acids Ratio", "color": "#BF5AF2"},
    "refined_grains": {"max_score": 10, "type": "moderation", "label": "Refined Grains", "color": "#8E6A3A"},
    "sodium": {"max_score": 10, "type": "moderation", "label": "Sodium", "color": "#FF453A"},
    "added_sugars": {"max_score": 10, "type": "moderation", "label": "Added Sugars", "color": "#FF375F"},
    "saturated_fats": {"max_score": 10, "type": "moderation", "label": "Saturated Fats", "color": "#FF9F0A"},
}

# ══════════════════════════════════════════════════════════════════════════════
# HEI SCORE ZONES
# ══════════════════════════════════════════════════════════════════════════════

HEI_SCORE_ZONES = {
    "excellent": {
        "min": 80, "max": 100, "label": "Excellent", "color": "#30D158",
        "message": "Your diet aligns very well with the Dietary Guidelines for Americans.",
    },
    "good": {
        "min": 60, "max": 79, "label": "Good", "color": "#64D2FF",
        "message": "Solid dietary pattern with room for targeted improvements.",
    },
    "fair": {
        "min": 40, "max": 59, "label": "Needs Improvement", "color": "#FFD60A",
        "message": "Several areas of your diet could benefit from changes.",
    },
    "poor": {
        "min": 0, "max": 39, "label": "Poor", "color": "#FF453A",
        "message": "Significant dietary improvements recommended for long-term health.",
    },
}
