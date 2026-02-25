"""Biomarker definitions with standard AND optimal ranges.

Standard ranges = typical lab reference ranges.
Optimal ranges = evidence-based targets for health optimization.
Sources: AHA/ACC, ADA, AACE, Endocrine Society, clinical literature.

Categories: lipids, metabolic, inflammation, vitamins, thyroid, liver, kidney, blood_count, minerals
"""

BIOMARKER_DEFINITIONS = [
    # ═══════════════════════════════════════════════════════════════════════
    # LIPIDS
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "total_cholesterol", "name": "Total Cholesterol", "category": "lipids",
        "unit": "mg/dL", "standard_low": 125, "standard_high": 200,
        "optimal_low": 150, "optimal_high": 180,
        "critical_low": None, "critical_high": 300,
        "description": "Sum of all cholesterol in blood.",
        "clinical_note": "AHA: desirable <200 mg/dL. Optimal for CVD prevention 150-180.",
        "pillar_id": 1, "sort_order": 1,
    },
    {
        "code": "ldl_cholesterol", "name": "LDL Cholesterol", "category": "lipids",
        "unit": "mg/dL", "standard_low": None, "standard_high": 130,
        "optimal_low": None, "optimal_high": 100,
        "critical_low": None, "critical_high": 190,
        "description": "Low-density lipoprotein ('bad' cholesterol).",
        "clinical_note": "AHA/ACC 2018: <100 primary prevention, <70 very high risk. Lifestyle medicine target <100.",
        "pillar_id": 1, "sort_order": 2,
    },
    {
        "code": "hdl_cholesterol", "name": "HDL Cholesterol", "category": "lipids",
        "unit": "mg/dL", "standard_low": 40, "standard_high": None,
        "optimal_low": 60, "optimal_high": None,
        "critical_low": 20, "critical_high": None,
        "description": "High-density lipoprotein ('good' cholesterol). Higher is better.",
        "clinical_note": "AHA: >40 men, >50 women minimum. Optimal >60 for cardiovascular protection.",
        "pillar_id": 2, "sort_order": 3,
    },
    {
        "code": "triglycerides", "name": "Triglycerides", "category": "lipids",
        "unit": "mg/dL", "standard_low": None, "standard_high": 150,
        "optimal_low": None, "optimal_high": 100,
        "critical_low": None, "critical_high": 500,
        "description": "Blood fat level. Responds strongly to diet and exercise.",
        "clinical_note": "AHA: normal <150. Optimal <100. Very high >500 (pancreatitis risk).",
        "pillar_id": 1, "sort_order": 4,
    },
    {
        "code": "ldl_particle_number", "name": "LDL Particle Number", "category": "lipids",
        "unit": "nmol/L", "standard_low": None, "standard_high": 1300,
        "optimal_low": None, "optimal_high": 1000,
        "critical_low": None, "critical_high": 1600,
        "description": "Measures actual number of LDL particles. May be more predictive than LDL-C alone.",
        "clinical_note": "Advanced lipid marker. Low risk <1000, moderate 1000-1299, high ≥1300.",
        "pillar_id": 1, "sort_order": 5,
    },
    {
        "code": "apob", "name": "ApoB", "category": "lipids",
        "unit": "mg/dL", "standard_low": None, "standard_high": 130,
        "optimal_low": None, "optimal_high": 90,
        "critical_low": None, "critical_high": 160,
        "description": "Apolipoprotein B — one per atherogenic lipoprotein particle.",
        "clinical_note": "Emerging as best single measure of atherogenic burden. European guidelines: <65 very high risk.",
        "pillar_id": 1, "sort_order": 6,
    },
    {
        "code": "lpa", "name": "Lp(a)", "category": "lipids",
        "unit": "nmol/L", "standard_low": None, "standard_high": 75,
        "optimal_low": None, "optimal_high": 30,
        "critical_low": None, "critical_high": 125,
        "description": "Lipoprotein(a) — genetically determined cardiovascular risk factor.",
        "clinical_note": "Largely genetic; >75 nmol/L is elevated risk. Measure once in lifetime. Limited lifestyle modification.",
        "pillar_id": None, "sort_order": 7,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # METABOLIC
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "fasting_glucose", "name": "Fasting Glucose", "category": "metabolic",
        "unit": "mg/dL", "standard_low": 70, "standard_high": 100,
        "optimal_low": 75, "optimal_high": 86,
        "critical_low": 50, "critical_high": 126,
        "description": "Fasting blood sugar level.",
        "clinical_note": "ADA: normal <100, pre-diabetes 100-125, diabetes ≥126. Optimal 75-86 for lowest progression risk.",
        "pillar_id": 1, "sort_order": 10,
    },
    {
        "code": "hba1c", "name": "HbA1c", "category": "metabolic",
        "unit": "%", "standard_low": 4.0, "standard_high": 5.7,
        "optimal_low": 4.5, "optimal_high": 5.2,
        "critical_low": None, "critical_high": 6.5,
        "description": "3-month average blood sugar (glycated hemoglobin).",
        "clinical_note": "ADA/IEC (PMID: 19502545): normal <5.7%, pre-diabetes 5.7-6.4%, diabetes ≥6.5%. Optimal 4.5-5.2%.",
        "pillar_id": 1, "sort_order": 11,
    },
    {
        "code": "fasting_insulin", "name": "Fasting Insulin", "category": "metabolic",
        "unit": "uIU/mL", "standard_low": 2.6, "standard_high": 24.9,
        "optimal_low": 2.6, "optimal_high": 8.0,
        "critical_low": None, "critical_high": 30,
        "description": "Early marker of insulin resistance, often elevated before glucose rises.",
        "clinical_note": "Standard range very wide; optimal <8 suggests good insulin sensitivity.",
        "pillar_id": 1, "sort_order": 12,
    },
    {
        "code": "homa_ir", "name": "HOMA-IR", "category": "metabolic",
        "unit": "index", "standard_low": None, "standard_high": 2.5,
        "optimal_low": None, "optimal_high": 1.0,
        "critical_low": None, "critical_high": 5.0,
        "description": "Homeostatic Model Assessment of Insulin Resistance. Calculated from fasting glucose and insulin.",
        "clinical_note": "HOMA-IR = (fasting glucose mg/dL x fasting insulin uIU/mL) / 405. Optimal <1.0.",
        "pillar_id": 1, "sort_order": 13,
    },
    {
        "code": "uric_acid", "name": "Uric Acid", "category": "metabolic",
        "unit": "mg/dL", "standard_low": 2.4, "standard_high": 7.0,
        "optimal_low": 3.0, "optimal_high": 5.5,
        "critical_low": None, "critical_high": 9.0,
        "description": "Elevated levels associated with gout and metabolic syndrome.",
        "clinical_note": "Keep below 6.0 for gout prevention. Associated with fructose metabolism.",
        "pillar_id": 1, "sort_order": 14,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # INFLAMMATION
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "hs_crp", "name": "hs-CRP", "category": "inflammation",
        "unit": "mg/L", "standard_low": None, "standard_high": 3.0,
        "optimal_low": None, "optimal_high": 1.0,
        "critical_low": None, "critical_high": 10.0,
        "description": "High-sensitivity C-reactive protein — systemic inflammation marker.",
        "clinical_note": "AHA (PMID: 14621448): <1.0 low CVD risk, 1-3 moderate, >3 high. >10 suggests acute infection.",
        "pillar_id": None, "sort_order": 20,
    },
    {
        "code": "homocysteine", "name": "Homocysteine", "category": "inflammation",
        "unit": "umol/L", "standard_low": 5, "standard_high": 15,
        "optimal_low": 5, "optimal_high": 10,
        "critical_low": None, "critical_high": 20,
        "description": "Amino acid linked to cardiovascular risk. Modifiable with B vitamins.",
        "clinical_note": "Elevated by B12/folate deficiency, common in plant-based diets without supplementation.",
        "pillar_id": 1, "sort_order": 21,
    },
    {
        "code": "esr", "name": "ESR (Sed Rate)", "category": "inflammation",
        "unit": "mm/hr", "standard_low": 0, "standard_high": 20,
        "optimal_low": 0, "optimal_high": 10,
        "critical_low": None, "critical_high": 100,
        "description": "Erythrocyte sedimentation rate — nonspecific inflammation marker.",
        "clinical_note": "Nonspecific; elevated in infection, autoimmune disease, malignancy. Age-adjusted upper limit.",
        "pillar_id": None, "sort_order": 22,
    },
    {
        "code": "ferritin", "name": "Ferritin", "category": "inflammation",
        "unit": "ng/mL", "standard_low": 12, "standard_high": 300,
        "optimal_low": 40, "optimal_high": 150,
        "critical_low": 10, "critical_high": 1000,
        "description": "Iron storage protein; also an acute phase reactant (rises with inflammation).",
        "clinical_note": "Low = iron deficiency. Very high = hemochromatosis or inflammation. Optimal 40-150.",
        "pillar_id": 1, "sort_order": 23,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # VITAMINS
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "vitamin_d", "name": "Vitamin D (25-OH)", "category": "vitamins",
        "unit": "ng/mL", "standard_low": 20, "standard_high": 100,
        "optimal_low": 40, "optimal_high": 60,
        "critical_low": 10, "critical_high": 150,
        "description": "Most adults deficient. Critical for bone health, immune function, mood.",
        "clinical_note": "Endocrine Society: optimal 40-60 ng/mL. PMID 24922127: <30 ng/mL linked to higher mortality.",
        "pillar_id": 1, "sort_order": 30,
    },
    {
        "code": "vitamin_b12", "name": "Vitamin B12", "category": "vitamins",
        "unit": "pg/mL", "standard_low": 200, "standard_high": 900,
        "optimal_low": 500, "optimal_high": 800,
        "critical_low": 150, "critical_high": None,
        "description": "Essential for nerve function and red blood cell formation.",
        "clinical_note": "Common deficiency in plant-based diets and older adults. Supplementation recommended for vegans.",
        "pillar_id": 1, "sort_order": 31,
    },
    {
        "code": "folate", "name": "Folate (Vitamin B9)", "category": "vitamins",
        "unit": "ng/mL", "standard_low": 3.0, "standard_high": 20,
        "optimal_low": 10, "optimal_high": 20,
        "critical_low": 2.0, "critical_high": None,
        "description": "Essential for DNA synthesis and methylation. Usually adequate in plant-rich diets.",
        "clinical_note": "Low folate + low B12 = elevated homocysteine. Most plant-rich diets provide adequate folate.",
        "pillar_id": 1, "sort_order": 32,
    },
    {
        "code": "iron", "name": "Serum Iron", "category": "vitamins",
        "unit": "ug/dL", "standard_low": 60, "standard_high": 170,
        "optimal_low": 60, "optimal_high": 150,
        "critical_low": 30, "critical_high": 200,
        "description": "Serum iron level. Best interpreted alongside ferritin and TIBC.",
        "clinical_note": "Serum iron fluctuates; ferritin is a better marker of iron stores.",
        "pillar_id": 1, "sort_order": 33,
    },
    {
        "code": "omega3_index", "name": "Omega-3 Index", "category": "vitamins",
        "unit": "%", "standard_low": 4, "standard_high": None,
        "optimal_low": 8, "optimal_high": 12,
        "critical_low": 2, "critical_high": None,
        "description": "EPA+DHA as percentage of total red blood cell fatty acids.",
        "clinical_note": "Optimal 8-12% for cardiovascular protection. Most Western diets yield 4-5%.",
        "pillar_id": 1, "sort_order": 34,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # THYROID
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "tsh", "name": "TSH", "category": "thyroid",
        "unit": "mIU/L", "standard_low": 0.4, "standard_high": 4.0,
        "optimal_low": 1.0, "optimal_high": 2.5,
        "critical_low": 0.1, "critical_high": 10.0,
        "description": "Thyroid-stimulating hormone. Primary thyroid screening test.",
        "clinical_note": "AACE: optimal 1.0-2.5. Standard range may miss subclinical thyroid dysfunction.",
        "pillar_id": None, "sort_order": 40,
    },
    {
        "code": "free_t4", "name": "Free T4", "category": "thyroid",
        "unit": "ng/dL", "standard_low": 0.8, "standard_high": 1.8,
        "optimal_low": 1.0, "optimal_high": 1.5,
        "critical_low": 0.5, "critical_high": 3.0,
        "description": "Free thyroxine — active thyroid hormone.",
        "clinical_note": "Interpret alongside TSH. Low free T4 + high TSH = hypothyroidism.",
        "pillar_id": None, "sort_order": 41,
    },
    {
        "code": "free_t3", "name": "Free T3", "category": "thyroid",
        "unit": "pg/mL", "standard_low": 2.3, "standard_high": 4.2,
        "optimal_low": 3.0, "optimal_high": 3.8,
        "critical_low": 1.5, "critical_high": 6.0,
        "description": "Free triiodothyronine — most metabolically active thyroid hormone.",
        "clinical_note": "Some functional medicine practitioners prioritize this marker.",
        "pillar_id": None, "sort_order": 42,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # HORMONES
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "cortisol_am", "name": "Cortisol (AM)", "category": "hormones",
        "unit": "ug/dL", "standard_low": 6.2, "standard_high": 19.4,
        "optimal_low": 10, "optimal_high": 18,
        "critical_low": 3, "critical_high": 25,
        "description": "Morning cortisol — stress hormone. Should peak in early morning.",
        "clinical_note": "Must be drawn 7-9 AM fasting. Reflects HPA axis function. Chronically elevated = stress.",
        "pillar_id": 4, "sort_order": 50,
    },
    {
        "code": "dhea_s", "name": "DHEA-S", "category": "hormones",
        "unit": "ug/dL", "standard_low": 35, "standard_high": 430,
        "optimal_low": 200, "optimal_high": 400,
        "critical_low": 15, "critical_high": 600,
        "description": "Dehydroepiandrosterone sulfate — adrenal hormone, declines with age.",
        "clinical_note": "Age-dependent reference ranges. Low levels associated with aging and chronic stress.",
        "pillar_id": 4, "sort_order": 51,
    },
    {
        "code": "testosterone_total", "name": "Total Testosterone", "category": "hormones",
        "unit": "ng/dL", "standard_low": 300, "standard_high": 1000,
        "optimal_low": 500, "optimal_high": 800,
        "critical_low": 200, "critical_high": None,
        "description": "Primary male sex hormone (also important in women at lower levels).",
        "clinical_note": "Ranges shown for adult males. Exercise, sleep quality, and stress management all influence levels.",
        "pillar_id": 2, "sort_order": 52,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # LIVER
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "alt", "name": "ALT (SGPT)", "category": "liver",
        "unit": "U/L", "standard_low": 7, "standard_high": 56,
        "optimal_low": 7, "optimal_high": 25,
        "critical_low": None, "critical_high": 200,
        "description": "Alanine aminotransferase — liver enzyme. Most specific for liver damage.",
        "clinical_note": "Elevated by alcohol, NAFLD, hepatitis, medications. Optimal <25 U/L.",
        "pillar_id": 6, "sort_order": 60,
    },
    {
        "code": "ast", "name": "AST (SGOT)", "category": "liver",
        "unit": "U/L", "standard_low": 10, "standard_high": 40,
        "optimal_low": 10, "optimal_high": 25,
        "critical_low": None, "critical_high": 200,
        "description": "Aspartate aminotransferase — liver/muscle enzyme.",
        "clinical_note": "Less specific than ALT for liver. Also elevated by muscle damage/exercise.",
        "pillar_id": 6, "sort_order": 61,
    },
    {
        "code": "ggt", "name": "GGT", "category": "liver",
        "unit": "U/L", "standard_low": 0, "standard_high": 65,
        "optimal_low": 0, "optimal_high": 30,
        "critical_low": None, "critical_high": 200,
        "description": "Gamma-glutamyl transferase — sensitive to alcohol use and liver stress.",
        "clinical_note": "Most sensitive marker for alcohol-related liver damage. Also a CVD risk marker.",
        "pillar_id": 6, "sort_order": 62,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # KIDNEY
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "egfr", "name": "eGFR", "category": "kidney",
        "unit": "mL/min/1.73m2", "standard_low": 60, "standard_high": None,
        "optimal_low": 90, "optimal_high": None,
        "critical_low": 15, "critical_high": None,
        "description": "Estimated glomerular filtration rate — kidney function indicator.",
        "clinical_note": ">90 normal, 60-89 mild decrease, 30-59 moderate, 15-29 severe, <15 kidney failure.",
        "pillar_id": None, "sort_order": 70,
    },
    {
        "code": "creatinine", "name": "Creatinine", "category": "kidney",
        "unit": "mg/dL", "standard_low": 0.7, "standard_high": 1.3,
        "optimal_low": 0.7, "optimal_high": 1.0,
        "critical_low": None, "critical_high": 4.0,
        "description": "Waste product from muscle metabolism filtered by kidneys.",
        "clinical_note": "Varies by muscle mass. Interpret with eGFR for kidney function assessment.",
        "pillar_id": None, "sort_order": 71,
    },
    {
        "code": "bun", "name": "BUN", "category": "kidney",
        "unit": "mg/dL", "standard_low": 6, "standard_high": 20,
        "optimal_low": 8, "optimal_high": 16,
        "critical_low": None, "critical_high": 50,
        "description": "Blood urea nitrogen — kidney function and hydration marker.",
        "clinical_note": "Elevated by dehydration, high protein intake, or kidney dysfunction.",
        "pillar_id": None, "sort_order": 72,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # BLOOD COUNT
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "wbc", "name": "WBC", "category": "blood_count",
        "unit": "K/uL", "standard_low": 4.5, "standard_high": 11.0,
        "optimal_low": 4.5, "optimal_high": 7.5,
        "critical_low": 2.0, "critical_high": 30.0,
        "description": "White blood cell count — immune system marker.",
        "clinical_note": "Low WBC in optimal range (4.5-7.5) suggests lower systemic inflammation.",
        "pillar_id": None, "sort_order": 80,
    },
    {
        "code": "hemoglobin", "name": "Hemoglobin", "category": "blood_count",
        "unit": "g/dL", "standard_low": 12.0, "standard_high": 17.5,
        "optimal_low": 13.5, "optimal_high": 16.0,
        "critical_low": 7.0, "critical_high": 20.0,
        "description": "Oxygen-carrying protein in red blood cells.",
        "clinical_note": "Ranges differ by sex. Low = anemia. Common deficiency in plant-based diets without iron attention.",
        "pillar_id": 1, "sort_order": 81,
    },
    {
        "code": "hematocrit", "name": "Hematocrit", "category": "blood_count",
        "unit": "%", "standard_low": 36, "standard_high": 51,
        "optimal_low": 40, "optimal_high": 48,
        "critical_low": 25, "critical_high": 60,
        "description": "Percentage of blood volume occupied by red blood cells.",
        "clinical_note": "Interpret alongside hemoglobin. Dehydration falsely elevates hematocrit.",
        "pillar_id": None, "sort_order": 82,
    },
    {
        "code": "platelets", "name": "Platelets", "category": "blood_count",
        "unit": "K/uL", "standard_low": 150, "standard_high": 400,
        "optimal_low": 175, "optimal_high": 300,
        "critical_low": 50, "critical_high": 600,
        "description": "Blood clotting cells. Very high or very low can be concerning.",
        "clinical_note": "Low = bleeding risk. High = clotting risk or reactive thrombocytosis.",
        "pillar_id": None, "sort_order": 83,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # MINERALS
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "magnesium", "name": "Magnesium", "category": "minerals",
        "unit": "mg/dL", "standard_low": 1.7, "standard_high": 2.2,
        "optimal_low": 2.0, "optimal_high": 2.2,
        "critical_low": 1.0, "critical_high": 3.0,
        "description": "Essential mineral involved in 300+ enzymatic reactions. Most adults deficient.",
        "clinical_note": "Serum Mg is a poor indicator of total body stores (only 1% of Mg is in serum).",
        "pillar_id": 1, "sort_order": 90,
    },
    {
        "code": "zinc", "name": "Zinc", "category": "minerals",
        "unit": "ug/dL", "standard_low": 60, "standard_high": 120,
        "optimal_low": 80, "optimal_high": 110,
        "critical_low": 40, "critical_high": None,
        "description": "Essential for immune function, wound healing, and taste/smell.",
        "clinical_note": "Deficiency common in elderly, vegetarians, and those with GI disease. Excess competes with copper.",
        "pillar_id": 1, "sort_order": 91,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # ADDITIONAL BIOMARKERS FOR ORGAN HEALTH SCORES
    # ═══════════════════════════════════════════════════════════════════════
    {
        "code": "albumin", "name": "Albumin", "category": "liver",
        "unit": "g/dL", "standard_low": 3.5, "standard_high": 5.5,
        "optimal_low": 4.0, "optimal_high": 5.0,
        "critical_low": 2.5, "critical_high": None,
        "description": "Major plasma protein synthesized by the liver. Marker of liver synthetic function and nutritional status.",
        "clinical_note": "Low albumin indicates chronic liver disease, malnutrition, or nephrotic syndrome. Used in NAFLD-FS and Glasgow Prognostic Score.",
        "pillar_id": 1, "sort_order": 63,
    },
    {
        "code": "uacr", "name": "Urine Albumin-to-Creatinine Ratio", "category": "kidney",
        "unit": "mg/g", "standard_low": None, "standard_high": 30,
        "optimal_low": None, "optimal_high": 10,
        "critical_low": None, "critical_high": 300,
        "description": "Measures albumin leakage into urine. Sensitive early marker of kidney damage.",
        "clinical_note": "KDIGO 2024: A1 (<30), A2 (30-300), A3 (>300). Used in KDIGO CKD Risk Category.",
        "pillar_id": None, "sort_order": 73,
    },
    {
        "code": "neutrophils_abs", "name": "Neutrophils (Absolute)", "category": "blood_count",
        "unit": "K/uL", "standard_low": 1.5, "standard_high": 8.0,
        "optimal_low": 2.0, "optimal_high": 6.0,
        "critical_low": 0.5, "critical_high": 20.0,
        "description": "Absolute neutrophil count from CBC with differential.",
        "clinical_note": "Used in NLR and SII inflammatory indices. Low = neutropenia risk. High = acute infection/inflammation.",
        "pillar_id": None, "sort_order": 84,
    },
    {
        "code": "lymphocytes_abs", "name": "Lymphocytes (Absolute)", "category": "blood_count",
        "unit": "K/uL", "standard_low": 1.0, "standard_high": 4.8,
        "optimal_low": 1.5, "optimal_high": 3.5,
        "critical_low": 0.5, "critical_high": 10.0,
        "description": "Absolute lymphocyte count from CBC with differential.",
        "clinical_note": "Used in NLR and SII inflammatory indices. Low lymphocytes associated with immune compromise.",
        "pillar_id": None, "sort_order": 85,
    },
    {
        "code": "mcv", "name": "MCV (Mean Corpuscular Volume)", "category": "blood_count",
        "unit": "fL", "standard_low": 80, "standard_high": 100,
        "optimal_low": 82, "optimal_high": 95,
        "critical_low": 60, "critical_high": 120,
        "description": "Average red blood cell volume. Low = microcytic (iron deficiency), high = macrocytic (B12/folate deficiency).",
        "clinical_note": "Key for anemia classification. Low MCV → iron studies. High MCV → B12/folate levels.",
        "pillar_id": None, "sort_order": 86,
    },
    {
        "code": "rdw", "name": "RDW (Red Cell Distribution Width)", "category": "blood_count",
        "unit": "%", "standard_low": 11.5, "standard_high": 14.5,
        "optimal_low": 11.5, "optimal_high": 13.5,
        "critical_low": None, "critical_high": 20.0,
        "description": "Measures variation in red blood cell size. Elevated in mixed anemias and inflammatory states.",
        "clinical_note": "Elevated RDW is an independent predictor of all-cause mortality (PMID: 20442389).",
        "pillar_id": None, "sort_order": 87,
    },
    {
        "code": "tibc", "name": "TIBC (Total Iron-Binding Capacity)", "category": "minerals",
        "unit": "ug/dL", "standard_low": 250, "standard_high": 370,
        "optimal_low": 260, "optimal_high": 350,
        "critical_low": None, "critical_high": 500,
        "description": "Indirect measure of transferrin. High TIBC suggests iron deficiency.",
        "clinical_note": "Interpret alongside ferritin and serum iron. High TIBC + low ferritin = iron deficiency anemia.",
        "pillar_id": 1, "sort_order": 92,
    },
    {
        "code": "transferrin_sat", "name": "Transferrin Saturation", "category": "minerals",
        "unit": "%", "standard_low": 20, "standard_high": 50,
        "optimal_low": 25, "optimal_high": 45,
        "critical_low": 10, "critical_high": 60,
        "description": "Percentage of transferrin saturated with iron. Key marker for iron status assessment.",
        "clinical_note": "Low (<20%) suggests iron deficiency. High (>45%) may indicate iron overload/hemochromatosis.",
        "pillar_id": 1, "sort_order": 93,
    },
]

# Category display order and labels
BIOMARKER_CATEGORIES = {
    "lipids": {"label": "Lipid Panel", "sort_order": 1, "icon": "&#128147;"},
    "metabolic": {"label": "Metabolic Health", "sort_order": 2, "icon": "&#9889;"},
    "inflammation": {"label": "Inflammation", "sort_order": 3, "icon": "&#128293;"},
    "vitamins": {"label": "Vitamins & Nutrients", "sort_order": 4, "icon": "&#127774;"},
    "thyroid": {"label": "Thyroid", "sort_order": 5, "icon": "&#129507;"},
    "hormones": {"label": "Hormones", "sort_order": 6, "icon": "&#128170;"},
    "liver": {"label": "Liver Function", "sort_order": 7, "icon": "&#129516;"},
    "kidney": {"label": "Kidney Function", "sort_order": 8, "icon": "&#128167;"},
    "blood_count": {"label": "Blood Count", "sort_order": 9, "icon": "&#129656;"},
    "minerals": {"label": "Minerals", "sort_order": 10, "icon": "&#128142;"},
}

# Category weights for composite biomarker score calculation
CATEGORY_WEIGHTS = {
    "metabolic": 1.5,
    "lipids": 1.3,
    "inflammation": 1.2,
    "vitamins": 1.0,
    "thyroid": 1.0,
    "hormones": 1.0,
    "liver": 1.0,
    "kidney": 1.0,
    "blood_count": 1.0,
    "minerals": 1.0,
}
