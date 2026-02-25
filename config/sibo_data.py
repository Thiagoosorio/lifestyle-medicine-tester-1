"""SIBO & FODMAP Tracker config: symptoms, FODMAP foods, phases, diet types, evidence.

FODMAP serving-size thresholds aligned with Monash University Low FODMAP Diet guidance.
All evidence entries verified via PubMed API with confirmed PMIDs and DOIs.

Scientific basis:
- Monash University Low FODMAP Diet (https://www.monashfodmap.com/)
- ACG Clinical Guideline: SIBO (Pimentel 2020, PMID 32023228)
- Low FODMAP diet meta-analysis (Black 2021, PMID 34376515)
"""

# ==============================================================================
# DISCLAIMER — shown on every screen
# ==============================================================================

SIBO_DISCLAIMER = (
    "This tool tracks personal patterns only. It is not a diagnostic tool and does not "
    "replace medical advice. SIBO diagnosis requires breath testing or jejunal aspirate "
    "under clinical supervision (ACG 2020). Always consult a gastroenterologist or "
    "registered dietitian before making dietary changes."
)

# ==============================================================================
# GI SYMPTOMS — 7 symptoms tracked daily
# ==============================================================================

GI_SYMPTOMS = {
    "bloating": {"label": "Bloating", "max": 10, "description": "Abdominal distension or fullness"},
    "abdominal_pain": {"label": "Abdominal Pain", "max": 10, "description": "Cramping, aching, or sharp pain"},
    "gas": {"label": "Gas / Flatulence", "max": 10, "description": "Excessive gas or flatulence"},
    "diarrhea": {"label": "Diarrhea", "max": 3, "description": "0=none, 1=mild, 2=moderate, 3=severe"},
    "constipation": {"label": "Constipation", "max": 3, "description": "0=none, 1=mild, 2=moderate, 3=severe"},
    "nausea": {"label": "Nausea", "max": 10, "description": "Feeling of sickness or queasiness"},
    "fatigue": {"label": "Fatigue", "max": 10, "description": "Tiredness or low energy"},
}

# ==============================================================================
# FODMAP GROUPS — 6 categories
# ==============================================================================

FODMAP_GROUPS = {
    "fructans": {
        "label": "Fructans",
        "examples": "wheat, onion, garlic, rye, barley, artichoke",
        "color": "#FF9F0A",
        "description": "Oligosaccharides found in wheat, onion, garlic, and some fruits/vegetables",
    },
    "gos": {
        "label": "GOS",
        "examples": "legumes, cashews, pistachios",
        "color": "#FF6482",
        "description": "Galacto-oligosaccharides found in legumes and some nuts",
    },
    "lactose": {
        "label": "Lactose",
        "examples": "milk, yogurt, soft cheese, ice cream",
        "color": "#64D2FF",
        "description": "Disaccharide found in dairy products",
    },
    "fructose": {
        "label": "Excess Fructose",
        "examples": "apple, pear, mango, honey, HFCS",
        "color": "#30D158",
        "description": "Monosaccharide in excess of glucose in certain fruits and sweeteners",
    },
    "sorbitol": {
        "label": "Sorbitol",
        "examples": "apple, pear, stone fruits, sugar-free gum",
        "color": "#BF5AF2",
        "description": "Polyol found in stone fruits and artificial sweeteners",
    },
    "mannitol": {
        "label": "Mannitol",
        "examples": "mushrooms, cauliflower, watermelon, sugar-free gum",
        "color": "#5E5CE6",
        "description": "Polyol found in mushrooms, cauliflower, and some fruits",
    },
}

# ==============================================================================
# FODMAP FOODS — ~80 common foods with FODMAP ratings per Monash University
# Serving sizes based on Monash University Low FODMAP Diet app thresholds.
# Each: (name, category, serving_size, serving_unit, fodmap_rating,
#         fodmap_groups_json, low_fodmap_alternative)
# ==============================================================================

FODMAP_FOODS = [
    # ── FRUITS ────────────────────────────────────────────────────────────
    # Low FODMAP fruits
    ("Banana, firm (unripe)", "fruits", 1, "medium", "low", "[]", None),
    ("Blueberries", "fruits", 40, "g", "low", "[]", None),
    ("Grapes", "fruits", 28, "g", "low", "[]", None),
    ("Kiwi", "fruits", 2, "small", "low", "[]", None),
    ("Orange", "fruits", 1, "medium", "low", "[]", None),
    ("Strawberries", "fruits", 65, "g", "low", "[]", None),
    ("Pineapple", "fruits", 120, "g", "low", "[]", None),
    ("Cantaloupe", "fruits", 120, "g", "low", "[]", None),
    ("Raspberries", "fruits", 60, "g", "low", "[]", None),
    ("Dragon fruit", "fruits", 120, "g", "low", "[]", None),
    # High FODMAP fruits
    ("Apple", "fruits", 1, "medium", "high", '["fructose","sorbitol"]', "Kiwi or orange"),
    ("Pear", "fruits", 1, "medium", "high", '["fructose","sorbitol"]', "Banana (firm)"),
    ("Mango", "fruits", 120, "g", "high", '["fructose"]', "Pineapple"),
    ("Watermelon", "fruits", 150, "g", "high", '["fructose","mannitol"]', "Cantaloupe"),
    ("Cherries", "fruits", 100, "g", "high", '["fructose","sorbitol"]', "Strawberries"),
    ("Peach", "fruits", 1, "medium", "moderate", '["sorbitol"]', "Kiwi"),
    ("Plum", "fruits", 2, "small", "moderate", '["sorbitol"]', "Grapes"),
    ("Banana, ripe", "fruits", 1, "medium", "moderate", '["fructans"]', "Banana (firm)"),

    # ── VEGETABLES ────────────────────────────────────────────────────────
    # Low FODMAP vegetables
    ("Carrot", "vegetables", 75, "g", "low", "[]", None),
    ("Potato", "vegetables", 1, "medium", "low", "[]", None),
    ("Tomato", "vegetables", 1, "medium", "low", "[]", None),
    ("Zucchini", "vegetables", 65, "g", "low", "[]", None),
    ("Bell pepper", "vegetables", 52, "g", "low", "[]", None),
    ("Lettuce", "vegetables", 75, "g", "low", "[]", None),
    ("Cucumber", "vegetables", 75, "g", "low", "[]", None),
    ("Spinach", "vegetables", 75, "g", "low", "[]", None),
    ("Green beans", "vegetables", 75, "g", "low", "[]", None),
    ("Eggplant", "vegetables", 75, "g", "low", "[]", None),
    ("Bok choy", "vegetables", 75, "g", "low", "[]", None),
    ("Ginger", "vegetables", 5, "g", "low", "[]", None),
    # High FODMAP vegetables
    ("Garlic", "vegetables", 1, "clove", "high", '["fructans"]', "Garlic-infused oil"),
    ("Onion", "vegetables", 30, "g", "high", '["fructans"]', "Green part of spring onion"),
    ("Cauliflower", "vegetables", 75, "g", "high", '["mannitol"]', "Broccoli (heads only)"),
    ("Mushrooms", "vegetables", 75, "g", "high", '["mannitol"]', "Zucchini"),
    ("Asparagus", "vegetables", 75, "g", "high", '["fructans"]', "Green beans"),
    ("Artichoke", "vegetables", 1, "medium", "high", '["fructans"]', "Eggplant"),
    ("Leek (white part)", "vegetables", 30, "g", "high", '["fructans"]', "Leek (green part only)"),
    ("Celery", "vegetables", 75, "g", "moderate", '["mannitol"]', "Cucumber"),
    ("Sweet potato", "vegetables", 75, "g", "moderate", '["mannitol"]', "Potato"),
    ("Broccoli", "vegetables", 75, "g", "low", "[]", None),
    ("Cabbage, common", "vegetables", 75, "g", "low", "[]", None),
    ("Spring onion (green part)", "vegetables", 12, "g", "low", "[]", None),

    # ── GRAINS & CEREALS ──────────────────────────────────────────────────
    # Low FODMAP grains
    ("Rice, white", "grains", 190, "g cooked", "low", "[]", None),
    ("Rice, brown", "grains", 190, "g cooked", "low", "[]", None),
    ("Oats", "grains", 52, "g dry", "low", "[]", None),
    ("Quinoa", "grains", 155, "g cooked", "low", "[]", None),
    ("Corn / polenta", "grains", 75, "g", "low", "[]", None),
    ("Gluten-free bread", "grains", 1, "slice", "low", "[]", None),
    ("Sourdough spelt bread", "grains", 1, "slice", "low", "[]", None),
    # High FODMAP grains
    ("Wheat bread", "grains", 1, "slice", "high", '["fructans"]', "Sourdough spelt or GF bread"),
    ("Wheat pasta", "grains", 145, "g cooked", "high", '["fructans"]', "Rice or GF pasta"),
    ("Rye bread", "grains", 1, "slice", "high", '["fructans"]', "Sourdough spelt bread"),
    ("Couscous", "grains", 100, "g cooked", "high", '["fructans"]', "Quinoa"),
    ("Barley", "grains", 100, "g cooked", "high", '["fructans"]', "Rice"),

    # ── DAIRY ─────────────────────────────────────────────────────────────
    # Low FODMAP dairy
    ("Cheddar cheese", "dairy", 40, "g", "low", "[]", None),
    ("Brie", "dairy", 40, "g", "low", "[]", None),
    ("Parmesan", "dairy", 40, "g", "low", "[]", None),
    ("Butter", "dairy", 20, "g", "low", "[]", None),
    ("Lactose-free milk", "dairy", 250, "mL", "low", "[]", None),
    ("Lactose-free yogurt", "dairy", 200, "g", "low", "[]", None),
    ("Almond milk", "dairy", 250, "mL", "low", "[]", None),
    # High FODMAP dairy
    ("Cow's milk", "dairy", 250, "mL", "high", '["lactose"]', "Lactose-free milk"),
    ("Yogurt (regular)", "dairy", 200, "g", "high", '["lactose"]', "Lactose-free yogurt"),
    ("Ice cream", "dairy", 100, "g", "high", '["lactose"]', "Sorbet or lactose-free ice cream"),
    ("Soft cheese (ricotta)", "dairy", 40, "g", "high", '["lactose"]', "Hard cheese (cheddar, parmesan)"),
    ("Cream cheese", "dairy", 30, "g", "moderate", '["lactose"]', "Brie or cheddar"),

    # ── PROTEIN ───────────────────────────────────────────────────────────
    ("Chicken breast", "protein", 120, "g", "low", "[]", None),
    ("Salmon", "protein", 120, "g", "low", "[]", None),
    ("Eggs", "protein", 2, "large", "low", "[]", None),
    ("Beef", "protein", 120, "g", "low", "[]", None),
    ("Tofu (firm)", "protein", 170, "g", "low", "[]", None),
    ("Tempeh", "protein", 100, "g", "low", "[]", None),
    ("Tuna", "protein", 120, "g", "low", "[]", None),

    # ── LEGUMES ───────────────────────────────────────────────────────────
    ("Lentils, canned", "legumes", 46, "g", "low", "[]", None),
    ("Chickpeas, canned", "legumes", 42, "g", "low", "[]", None),
    ("Lentils, boiled (large serve)", "legumes", 150, "g", "high", '["gos","fructans"]', "Canned lentils (small serve)"),
    ("Kidney beans", "legumes", 150, "g", "high", '["gos"]', "Canned lentils (small serve)"),
    ("Baked beans", "legumes", 150, "g", "high", '["gos","fructans"]', "Canned lentils (small serve)"),
    ("Black beans", "legumes", 150, "g", "high", '["gos"]', "Tofu or tempeh"),

    # ── CONDIMENTS & SWEETENERS ───────────────────────────────────────────
    ("Honey", "condiments", 7, "g", "high", '["fructose"]', "Maple syrup"),
    ("Maple syrup", "condiments", 15, "mL", "low", "[]", None),
    ("Soy sauce", "condiments", 15, "mL", "low", "[]", None),
    ("Garlic-infused oil", "condiments", 15, "mL", "low", "[]", None),
    ("Tomato sauce (no onion/garlic)", "condiments", 30, "mL", "low", "[]", None),
    ("High fructose corn syrup", "condiments", 15, "mL", "high", '["fructose"]', "Maple syrup or table sugar"),

    # ── BEVERAGES ─────────────────────────────────────────────────────────
    ("Water", "beverages", 250, "mL", "low", "[]", None),
    ("Coffee (black)", "beverages", 250, "mL", "low", "[]", None),
    ("Tea (black/green)", "beverages", 250, "mL", "low", "[]", None),
    ("Chamomile tea", "beverages", 250, "mL", "moderate", '["fructans"]', "Peppermint tea"),
    ("Peppermint tea", "beverages", 250, "mL", "low", "[]", None),
    ("Apple juice", "beverages", 250, "mL", "high", '["fructose","sorbitol"]', "Cranberry juice"),
    ("Orange juice (fresh)", "beverages", 125, "mL", "low", "[]", None),
]

# ==============================================================================
# FODMAP FOOD CATEGORIES — for display grouping
# ==============================================================================

FODMAP_FOOD_CATEGORIES = {
    "fruits": {"label": "Fruits", "icon": "&#127815;"},
    "vegetables": {"label": "Vegetables", "icon": "&#129382;"},
    "grains": {"label": "Grains & Cereals", "icon": "&#127838;"},
    "dairy": {"label": "Dairy & Alternatives", "icon": "&#129371;"},
    "protein": {"label": "Protein", "icon": "&#129385;"},
    "legumes": {"label": "Legumes", "icon": "&#129372;"},
    "condiments": {"label": "Condiments & Sweeteners", "icon": "&#129474;"},
    "beverages": {"label": "Beverages", "icon": "&#129380;"},
}

# ==============================================================================
# FODMAP PHASES — 3-phase Low-FODMAP protocol
# ==============================================================================

FODMAP_PHASES = {
    "elimination": {
        "label": "Elimination",
        "duration_weeks": "2-6",
        "description": "Remove all high-FODMAP foods to establish a symptom baseline.",
        "color": "#FF453A",
        "guidance": (
            "During elimination, eat only low-FODMAP foods. This phase typically lasts "
            "2-6 weeks. If symptoms improve significantly, proceed to reintroduction."
        ),
    },
    "reintroduction": {
        "label": "Reintroduction",
        "duration_weeks": "6-8",
        "description": "Test one FODMAP group at a time (3-day challenge + 3-day washout).",
        "color": "#FF9F0A",
        "guidance": (
            "Test one FODMAP group at a time over 3 days, increasing the dose each day. "
            "Then observe a 3-day washout period (return to low-FODMAP) before testing "
            "the next group. Record your symptoms each day."
        ),
    },
    "personalization": {
        "label": "Personalization",
        "duration_weeks": "Ongoing",
        "description": "Reintroduce tolerated foods; avoid only identified triggers.",
        "color": "#30D158",
        "guidance": (
            "Based on your reintroduction results, build a personalized diet that includes "
            "tolerated FODMAP foods while avoiding your specific triggers. The goal is the "
            "least restrictive diet that manages your symptoms."
        ),
    },
}

# ==============================================================================
# SIBO DIET TYPES — with evidence confidence grades
# ==============================================================================

SIBO_DIET_TYPES = {
    "low_fodmap": {
        "label": "Low-FODMAP",
        "confidence": "A",
        "note": "First-line dietary approach for SIBO/IBS symptom management",
        "description": (
            "Systematic elimination and reintroduction of fermentable short-chain "
            "carbohydrates. Supported by meta-analysis (Black 2021) showing superiority "
            "over other dietary interventions for IBS symptoms."
        ),
    },
    "elemental": {
        "label": "Elemental Diet",
        "confidence": "B",
        "note": "80-85% lactulose breath test normalization in 14 days (Pimentel 2004)",
        "description": (
            "Pre-digested liquid formula (amino acids, simple sugars, medium-chain "
            "triglycerides) that is absorbed in the proximal small intestine, starving "
            "distal bacterial overgrowth. Requires medical supervision."
        ),
    },
    "biphasic": {
        "label": "Biphasic Diet",
        "confidence": "C",
        "note": "Limited evidence; based on expert opinion and clinical experience only",
        "description": (
            "Two-phase approach combining aspects of low-FODMAP and specific carbohydrate "
            "diets. Phase 1 is highly restrictive; Phase 2 gradually reintroduces foods. "
            "Not yet validated in controlled trials."
        ),
    },
    "specific_carb": {
        "label": "SCD (Specific Carbohydrate Diet)",
        "confidence": "C",
        "note": "Anecdotal reports; no controlled trials specifically for SIBO",
        "description": (
            "Eliminates most complex carbohydrates (disaccharides and polysaccharides), "
            "allowing only monosaccharides. Some overlap with low-FODMAP principles but "
            "lacks SIBO-specific clinical evidence."
        ),
    },
}

# ==============================================================================
# EVIDENCE — 6 PubMed-verified citations (Tier A & B only)
# Same structure as config/evidence_data.py EVIDENCE_LIBRARY entries
# ==============================================================================

SIBO_EVIDENCE = [
    {
        "pmid": "32023228", "doi": "10.14309/ajg.0000000000000501",
        "title": "ACG Clinical Guideline: Small Intestinal Bacterial Overgrowth",
        "authors": "Pimentel M, Saad RJ, Long MD, Rao SSC",
        "journal": "Am J Gastroenterol", "year": 2020,
        "study_type": "guideline", "evidence_grade": "A", "pillar_id": 1,
        "summary": (
            "Comprehensive clinical guideline defining SIBO diagnostic criteria, "
            "optimal testing methods (glucose and lactulose breath tests), and treatment "
            "options including antibiotics and dietary modifications."
        ),
        "key_finding": (
            "Glucose breath test has higher specificity; lactulose breath test has higher "
            "sensitivity but lower specificity. Rifaximin is the preferred antibiotic."
        ),
        "effect_size": None,
        "sample_size": None,
        "population": "Adults with suspected SIBO",
        "dose_response": None,
        "causation_note": "Clinical practice guideline based on GRADE systematic review.",
        "tags": "SIBO,guideline,diagnosis,breath_test,treatment,ACG",
        "url": "https://pubmed.ncbi.nlm.nih.gov/32023228/",
        "journal_tier": "q1", "domain": "gastroenterology",
    },
    {
        "pmid": "34376515", "doi": "10.1136/gutjnl-2021-325214",
        "title": "Efficacy of a low FODMAP diet in irritable bowel syndrome: systematic review and network meta-analysis",
        "authors": "Black CJ, Staudacher HM, Ford AC",
        "journal": "Gut", "year": 2021,
        "study_type": "meta_analysis", "evidence_grade": "A", "pillar_id": 1,
        "summary": (
            "Network meta-analysis of 13 RCTs (944 patients) showing low FODMAP diet "
            "ranked first for global IBS symptom improvement, abdominal pain, bloating, "
            "and bowel habit compared to all other dietary interventions."
        ),
        "key_finding": (
            "Low FODMAP diet vs habitual diet: RR of symptoms not improving = 0.67 "
            "(95% CI 0.48-0.91, P-score 0.99). Ranked first for all endpoints."
        ),
        "effect_size": "RR 0.67 (95% CI 0.48-0.91) for global symptoms vs habitual diet",
        "sample_size": 944,
        "population": "Adults with IBS (13 RCTs)",
        "dose_response": None,
        "causation_note": (
            "RCT-based meta-analysis supports causal inference for symptom improvement. "
            "Most trials were in secondary/tertiary care; reintroduction phase not studied."
        ),
        "tags": "FODMAP,IBS,meta_analysis,diet,symptoms,network_meta_analysis",
        "url": "https://pubmed.ncbi.nlm.nih.gov/34376515/",
        "journal_tier": "elite", "domain": "gastroenterology",
    },
    {
        "pmid": "37375587", "doi": "10.3390/nu15122683",
        "title": "Gut Symptoms during FODMAP Restriction and Symptom Response to Food Challenges during FODMAP Reintroduction: A Real-World Evaluation in 21,462 Participants Using a Mobile Application",
        "authors": "Dimidi E, Belogianni K, Whelan K, Lomer MCE",
        "journal": "Nutrients", "year": 2023,
        "study_type": "cohort", "evidence_grade": "B", "pillar_id": 1,
        "summary": (
            "Largest real-world study of a low FODMAP diet app (21,462 users). During "
            "FODMAP restriction, overall symptoms improved significantly (57% to 44%). "
            "During reintroduction, wheat bread (41%), onion (39%), milk (40%), garlic "
            "(35%), and wheat pasta (41%) were the most common dietary triggers."
        ),
        "key_finding": (
            "Mobile app-based FODMAP management reduces gut symptoms and identifies "
            "dietary triggers during reintroduction. Top triggers: wheat, onion, milk, garlic."
        ),
        "effect_size": "Overall symptoms: 57% to 44% (p<0.001)",
        "sample_size": 21462,
        "population": "Low FODMAP diet app users",
        "dose_response": None,
        "causation_note": (
            "Observational cohort without control group. Self-reported outcomes. "
            "Supports feasibility of app-based FODMAP management."
        ),
        "tags": "FODMAP,mobile_app,IBS,reintroduction,dietary_triggers,real_world",
        "url": "https://pubmed.ncbi.nlm.nih.gov/37375587/",
        "journal_tier": "q2", "domain": "gastroenterology",
    },
    {
        "pmid": "39001958", "doi": "10.1007/s10620-024-08543-1",
        "title": "Elemental Diet as a Therapeutic Modality: A Comprehensive Review",
        "authors": "Nasser J, Mehravar S, Pimentel M, Lim J, Mathur R, Boustany A, Rezaie A",
        "journal": "Dig Dis Sci", "year": 2024,
        "study_type": "systematic_review", "evidence_grade": "B", "pillar_id": 1,
        "summary": (
            "Comprehensive review of elemental diets for GI diseases including SIBO. "
            "Elemental diets appear to exhibit clinical benefit in SIBO, EoE, IBD, and "
            "other conditions. High passive absorption rate and anti-inflammatory "
            "properties are key mechanisms."
        ),
        "key_finding": (
            "Elemental diets show benefit across multiple GI conditions. "
            "Intolerance rates up to 40% when taken orally due to poor palatability."
        ),
        "effect_size": None,
        "sample_size": None,
        "population": "Patients with GI diseases (review of multiple studies)",
        "dose_response": None,
        "causation_note": (
            "Narrative review; large prospective trials lacking. "
            "Summarizes existing evidence across heterogeneous study designs."
        ),
        "tags": "elemental_diet,SIBO,review,enteral_nutrition,GI_diseases",
        "url": "https://pubmed.ncbi.nlm.nih.gov/39001958/",
        "journal_tier": "q2", "domain": "gastroenterology",
    },
    {
        "pmid": "14992438", "doi": "10.1023/b:ddas.0000011605.43979.e1",
        "title": "A 14-day elemental diet is highly effective in normalizing the lactulose breath test",
        "authors": "Pimentel M, Constantino T, Kong Y, Bajwa M, Rezaei A, Park S",
        "journal": "Dig Dis Sci", "year": 2004,
        "study_type": "cohort", "evidence_grade": "B", "pillar_id": 1,
        "summary": (
            "Landmark study showing a 14-day exclusive elemental diet normalized the "
            "lactulose breath test in 80% of IBS subjects with suspected SIBO by day 15, "
            "and 85% by day 21. Normalized subjects showed 66% symptom improvement."
        ),
        "key_finding": (
            "80% LBT normalization at day 15; 85% by day 21. "
            "Symptom improvement 66.4% in responders vs 11.9% in non-responders (p<0.001)."
        ),
        "effect_size": "80% LBT normalization (day 15); 66.4% symptom improvement in responders",
        "sample_size": 93,
        "population": "IBS subjects with abnormal lactulose breath test",
        "dose_response": "14 days: 80%; extended to 21 days: 85% normalization",
        "causation_note": (
            "Retrospective chart review without control group. "
            "Strong effect size but requires confirmation in controlled trials."
        ),
        "tags": "elemental_diet,SIBO,lactulose_breath_test,IBS,Pimentel",
        "url": "https://pubmed.ncbi.nlm.nih.gov/14992438/",
        "journal_tier": "q2", "domain": "gastroenterology",
    },
    {
        "pmid": "40362719", "doi": "10.3390/nu17091410",
        "title": "Nutritional Approach to Small Intestinal Bacterial Overgrowth: A Narrative Review",
        "authors": "Velasco-Aburto S, Llama-Palacios A, Sanchez MC, Ciudad MJ, Collado L",
        "journal": "Nutrients", "year": 2025,
        "study_type": "systematic_review", "evidence_grade": "B", "pillar_id": 1,
        "summary": (
            "Narrative review summarizing dietary management for SIBO. Covers specific "
            "diets (low-FODMAP, elemental, SCD, biphasic), dietary supplements, and the "
            "role of the dietitian. Emphasizes nutrition as pivotal in SIBO management."
        ),
        "key_finding": (
            "Low-FODMAP and elemental diets have the strongest evidence for SIBO symptom "
            "management. Biphasic and SCD diets lack controlled trial evidence."
        ),
        "effect_size": None,
        "sample_size": None,
        "population": "Patients with SIBO (narrative review)",
        "dose_response": None,
        "causation_note": "Narrative review; quality of individual studies varies.",
        "tags": "SIBO,nutrition,FODMAP,elemental_diet,dietary_management,review",
        "url": "https://pubmed.ncbi.nlm.nih.gov/40362719/",
        "journal_tier": "q2", "domain": "gastroenterology",
    },
]

# ==============================================================================
# CORRELATION INTERPRETATION
# ==============================================================================

CORRELATION_STRENGTH = {
    "negligible": {"min": 0.0, "max": 0.1, "label": "Negligible", "color": "#AEAEB2"},
    "weak": {"min": 0.1, "max": 0.3, "label": "Weak", "color": "#FFD60A"},
    "moderate": {"min": 0.3, "max": 0.5, "label": "Moderate", "color": "#FF9F0A"},
    "strong": {"min": 0.5, "max": 0.7, "label": "Strong", "color": "#FF453A"},
    "very_strong": {"min": 0.7, "max": 1.0, "label": "Very Strong", "color": "#FF2D55"},
}
