"""Evidence grading system, study type hierarchy, journal tiers, research domains, and display constants.

v2.0 — Precision & Lifestyle Medicine Research Framework
"""

# ── Research Domains (§ C — v2.0) ─────────────────────────────────────────────
RESEARCH_DOMAINS = {
    "longevity": {
        "label": "Longevity & Aging Biology",
        "journals": ["Nature Aging", "Aging Cell", "GeroScience", "Journals of Gerontology A & B", "Ageing Research Reviews"],
    },
    "gerontology": {
        "label": "Gerontology & Clinical Aging",
        "journals": ["JAGS", "Age and Ageing", "The Gerontologist"],
    },
    "lifestyle_medicine": {
        "label": "Lifestyle Medicine",
        "journals": ["American Journal of Lifestyle Medicine", "BJSM", "The Lancet Public Health"],
    },
    "exercise_science": {
        "label": "Exercise Science",
        "journals": ["Medicine & Science in Sports & Exercise", "Journal of Applied Physiology", "Sports Medicine"],
    },
    "nutrition": {
        "label": "Nutrition",
        "journals": ["American Journal of Clinical Nutrition", "Journal of Nutrition", "Advances in Nutrition", "Nutrients"],
    },
    "sleep_science": {
        "label": "Sleep Science",
        "journals": ["Sleep", "Journal of Clinical Sleep Medicine", "Sleep Medicine Reviews", "Sleep Health"],
    },
    "stress_pni": {
        "label": "Stress & Psychoneuroimmunology",
        "journals": ["Psychoneuroendocrinology", "Brain Behavior and Immunity", "Psychosomatic Medicine", "Stress"],
    },
    "toxicology": {
        "label": "Toxicology & Environmental Health",
        "journals": ["Environmental Health Perspectives", "Toxicological Sciences", "Environment International"],
    },
    "precision_medicine": {
        "label": "Precision / Genomic Medicine",
        "journals": ["Nature Medicine", "NEJM", "Genome Medicine", "Genetics in Medicine"],
    },
    "cardio_metabolic": {
        "label": "Cardiovascular & Metabolic Health",
        "journals": ["Circulation", "JACC", "European Heart Journal", "Diabetes Care", "The Lancet Diabetes & Endocrinology"],
    },
}

# ── Journal Quality Tiers (§ D — v2.0) ───────────────────────────────────────
JOURNAL_TIERS = {
    "elite": {
        "label": "Elite",
        "description": "Top 10% by impact factor / CiteScore in the relevant field",
        "color": "#FFD700",  # Gold
        "flag": None,
    },
    "q1": {
        "label": "Q1",
        "description": "Top 25% (JCR / Scimago quartile)",
        "color": "#34C759",  # Green
        "flag": None,
    },
    "q2": {
        "label": "Q2",
        "description": "25-50th percentile",
        "color": "#0A84FF",  # Blue
        "flag": None,
    },
    "q3": {
        "label": "Q3",
        "description": "50-75th percentile — interpret with caution",
        "color": "#FF9F0A",  # Orange
        "flag": "Lower-tier journal, interpret with caution",
    },
    "q4": {
        "label": "Q4",
        "description": "Bottom 25% — high caution warranted",
        "color": "#FF453A",  # Red
        "flag": "Low-tier journal, high caution warranted",
    },
}

# ── Evidence Quality Tiers (§ E Rule 9 — v2.0) ──────────────────────────────
EVIDENCE_QUALITY_TIERS = {
    "tier_a": {
        "label": "Tier A — Guidelines / Consensus",
        "examples": "WHO, CDC, NIH, AHA/ACC, ADA, USPSTF, NICE, AASM, ACMT",
        "priority": 1,
    },
    "tier_b": {
        "label": "Tier B — Systematic Reviews / Meta-analyses / Large RCTs",
        "examples": "Cochrane, GRADE-rated SRs, landmark RCTs",
        "priority": 2,
    },
    "tier_c": {
        "label": "Tier C — Observational / Mechanistic",
        "examples": "Prospective cohorts, Mendelian randomisation, cell/animal mechanistic work",
        "priority": 3,
    },
}

# ── Evidence Grades (based on OCEBM Levels of Evidence) ─────────────────────
EVIDENCE_GRADES = {
    "A": {
        "label": "Grade A",
        "name": "Strong",
        "description": "Systematic reviews of RCTs or high-quality meta-analyses.",
        "color": "#34C759",  # Apple green
        "icon": "&#9733;&#9733;&#9733;&#9733;",
    },
    "B": {
        "label": "Grade B",
        "name": "Moderate",
        "description": "Individual RCTs or well-designed controlled trials.",
        "color": "#0A84FF",  # Apple blue
        "icon": "&#9733;&#9733;&#9733;",
    },
    "C": {
        "label": "Grade C",
        "name": "Limited",
        "description": "Observational studies (cohort, case-control, cross-sectional).",
        "color": "#FF9F0A",  # Apple orange
        "icon": "&#9733;&#9733;",
    },
    "D": {
        "label": "Grade D",
        "name": "Expert",
        "description": "Expert opinion, case reports, or clinical guidelines without direct evidence grading.",
        "color": "rgba(235,235,245,0.3)",  # Apple label tertiary
        "icon": "&#9733;",
    },
}

# ── Study Type Hierarchy (ordered best → weakest) ───────────────────────────
STUDY_TYPES = {
    "meta_analysis": {
        "label": "Meta-Analysis",
        "short": "MA",
        "default_grade": "A",
        "description": "Statistical synthesis of results from multiple studies.",
    },
    "systematic_review": {
        "label": "Systematic Review",
        "short": "SR",
        "default_grade": "A",
        "description": "Comprehensive review using systematic search methodology.",
    },
    "rct": {
        "label": "Randomized Controlled Trial",
        "short": "RCT",
        "default_grade": "B",
        "description": "Participants randomly assigned to treatment or control groups.",
    },
    "cohort": {
        "label": "Cohort Study",
        "short": "Cohort",
        "default_grade": "C",
        "description": "Follows groups over time to compare outcomes.",
    },
    "case_control": {
        "label": "Case-Control Study",
        "short": "CC",
        "default_grade": "C",
        "description": "Compares people with a condition to those without.",
    },
    "cross_sectional": {
        "label": "Cross-Sectional Study",
        "short": "XS",
        "default_grade": "C",
        "description": "Snapshot of a population at one point in time.",
    },
    "case_report": {
        "label": "Case Report",
        "short": "CR",
        "default_grade": "D",
        "description": "Detailed report of a single patient or small group.",
    },
    "expert_opinion": {
        "label": "Expert Opinion",
        "short": "EO",
        "default_grade": "D",
        "description": "Opinion from recognized authorities.",
    },
    "guideline": {
        "label": "Clinical Guideline",
        "short": "GL",
        "default_grade": "D",
        "description": "Recommendations from medical organizations based on evidence review.",
    },
}

# Ordered list for display (strongest first)
STUDY_TYPE_ORDER = [
    "meta_analysis", "systematic_review", "rct", "cohort",
    "case_control", "cross_sectional", "case_report",
    "expert_opinion", "guideline",
]

# ── Evidence Pyramid Levels ─────────────────────────────────────────────────
EVIDENCE_PYRAMID = [
    {"level": 1, "label": "Systematic Reviews & Meta-Analyses", "grade": "A",
     "width": 40, "description": "Highest quality: combines multiple studies"},
    {"level": 2, "label": "Randomized Controlled Trials", "grade": "B",
     "width": 55, "description": "Gold standard for individual studies"},
    {"level": 3, "label": "Cohort & Case-Control Studies", "grade": "C",
     "width": 70, "description": "Observational: correlation, not always causation"},
    {"level": 4, "label": "Case Reports & Expert Opinion", "grade": "D",
     "width": 85, "description": "Starting point: useful but weakest evidence"},
]
