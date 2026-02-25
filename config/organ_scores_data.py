"""Organ health score definitions with validated formulas and citations.

Each score definition includes:
- formula_key: maps to the pure computation function in organ_score_service.py
- required_biomarkers: biomarker codes from biomarkers_data.py
- required_clinical: fields from user_clinical_profile table
- interpretation: severity ranges with labels
- citation: PMID and text from peer-reviewed literature

Citation quality: top-10% / Q1 journals prioritized, newest publications preferred.
Tier: 'validated' = published peer-reviewed formula; 'derived' = experimental/emerging.
"""

import json

ORGAN_SCORE_DEFINITIONS = [
    # ═══════════════════════════════════════════════════════════════════════════
    # LIVER — Tier 1
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "code": "fib4",
        "name": "FIB-4 Index",
        "organ_system": "liver",
        "tier": "validated",
        "formula_key": "calc_fib4",
        "required_biomarkers": ["ast", "alt", "platelets"],
        "required_clinical": ["age"],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 1.3, "label": "Low risk of advanced fibrosis", "severity": "optimal"},
                {"min": 1.3, "max": 2.67, "label": "Indeterminate — further evaluation recommended", "severity": "elevated"},
                {"min": 2.67, "label": "High risk of advanced fibrosis", "severity": "high"},
            ]
        }),
        "citation_pmid": "38851997",
        "citation_text": "EASL-EASD-EASO 2024 Guidelines. J Hepatol 81(3):492-542. [Q1, top 10%]. Original: Sterling RK et al. Hepatology 2006. PMID: 16729309",
        "description": "Non-invasive liver fibrosis assessment using age, AST, ALT, and platelet count. Recommended as first-line screening by EASL 2024 and AASLD 2023 guidelines.",
        "sort_order": 1,
    },
    {
        "code": "apri",
        "name": "APRI",
        "organ_system": "liver",
        "tier": "validated",
        "formula_key": "calc_apri",
        "required_biomarkers": ["ast", "platelets"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 0.5, "label": "Significant fibrosis unlikely", "severity": "optimal"},
                {"min": 0.5, "max": 1.0, "label": "Indeterminate", "severity": "elevated"},
                {"min": 1.0, "max": 2.0, "label": "Significant fibrosis likely", "severity": "high"},
                {"min": 2.0, "label": "Cirrhosis likely", "severity": "critical"},
            ]
        }),
        "citation_pmid": "39983746",
        "citation_text": "Liguori A et al. Lancet Gastro Hepatol 2025;10(4):332-349. WHO 2024 meta-analysis (264 studies). [Q1, top 10%]. Original: Wai CT et al. Hepatology 2003. PMID: 12883497",
        "description": "AST-to-Platelet Ratio Index. Simple fibrosis screening endorsed by WHO 2024 guidelines. Uses AST upper limit of normal (40 U/L).",
        "sort_order": 2,
    },
    {
        "code": "nafld_fibrosis",
        "name": "NAFLD Fibrosis Score",
        "organ_system": "liver",
        "tier": "validated",
        "formula_key": "calc_nafld_fibrosis",
        "required_biomarkers": ["ast", "alt", "platelets", "albumin"],
        "required_clinical": ["age", "bmi", "diabetes_status"],
        "interpretation": json.dumps({
            "ranges": [
                {"max": -1.455, "label": "Advanced fibrosis unlikely (F0-F2)", "severity": "optimal"},
                {"min": -1.455, "max": 0.675, "label": "Indeterminate — consider further testing", "severity": "elevated"},
                {"min": 0.675, "label": "Advanced fibrosis likely (F3-F4)", "severity": "high"},
            ]
        }),
        "citation_pmid": "17393509",
        "citation_text": "Angulo P et al. Hepatology 2007;45(4):846-54. [Q1, top 10%]. Endorsed by AASLD 2023 (PMID: 36727674) and EASL 2024 (PMID: 38851997)",
        "description": "Composite score for NAFLD/MASLD fibrosis staging. Requires BMI and diabetes status in addition to blood labs.",
        "sort_order": 3,
    },
    # ═══════════════════════════════════════════════════════════════════════════
    # KIDNEY — Tier 1
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "code": "ckd_epi_egfr",
        "name": "CKD-EPI eGFR (2021)",
        "organ_system": "kidney",
        "tier": "validated",
        "formula_key": "calc_ckd_epi_2021",
        "required_biomarkers": ["creatinine"],
        "required_clinical": ["age", "sex"],
        "interpretation": json.dumps({
            "ranges": [
                {"min": 90, "label": "G1: Normal or high kidney function", "severity": "optimal"},
                {"min": 60, "max": 89, "label": "G2: Mildly decreased", "severity": "normal"},
                {"min": 45, "max": 59, "label": "G3a: Mildly to moderately decreased", "severity": "elevated"},
                {"min": 30, "max": 44, "label": "G3b: Moderately to severely decreased", "severity": "high"},
                {"min": 15, "max": 29, "label": "G4: Severely decreased", "severity": "critical"},
                {"max": 14, "label": "G5: Kidney failure", "severity": "critical"},
            ]
        }),
        "citation_pmid": "34554658",
        "citation_text": "Inker LA et al. N Engl J Med 2021;385(19):1737-49. Race-free equation. [Q1, top 10%]",
        "description": "Estimated glomerular filtration rate using the 2021 CKD-EPI race-free creatinine equation. Gold standard for kidney function assessment.",
        "sort_order": 10,
    },
    {
        "code": "kdigo_risk",
        "name": "KDIGO CKD Risk Category",
        "organ_system": "kidney",
        "tier": "validated",
        "formula_key": "calc_kdigo_risk",
        "required_biomarkers": ["creatinine", "uacr"],
        "required_clinical": ["age", "sex"],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 1, "label": "Low risk (green) — routine monitoring", "severity": "optimal"},
                {"min": 1, "max": 2, "label": "Moderately increased risk (yellow)", "severity": "elevated"},
                {"min": 2, "max": 3, "label": "High risk (orange)", "severity": "high"},
                {"min": 3, "label": "Very high risk (red)", "severity": "critical"},
            ]
        }),
        "citation_pmid": "38490803",
        "citation_text": "KDIGO 2024 CKD Guideline. Kidney Int 2024;105(4S):S117-S314. [Q1]",
        "description": "Combined eGFR + albuminuria risk matrix from KDIGO 2024. Provides CKD progression risk stratification.",
        "sort_order": 11,
    },
    # ═══════════════════════════════════════════════════════════════════════════
    # CARDIOVASCULAR — Tier 1
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "code": "ascvd_pce",
        "name": "ASCVD 10-Year Risk (PCE)",
        "organ_system": "cardiovascular",
        "tier": "validated",
        "formula_key": "calc_ascvd_pce",
        "required_biomarkers": ["total_cholesterol", "hdl_cholesterol"],
        "required_clinical": ["age", "sex", "systolic_bp", "on_bp_medication", "smoking_status", "diabetes_status"],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 5.0, "label": "Low risk (<5%)", "severity": "optimal"},
                {"min": 5.0, "max": 7.5, "label": "Borderline risk (5-7.5%)", "severity": "normal"},
                {"min": 7.5, "max": 20.0, "label": "Intermediate risk (7.5-20%)", "severity": "elevated"},
                {"min": 20.0, "label": "High risk (>=20%)", "severity": "high"},
            ]
        }),
        "citation_pmid": "24222018",
        "citation_text": "Goff DC Jr et al. Circulation 2014;129(S2):S49-73. [Q1, top 10%]. Note: Being superseded by PREVENT equations (Khan 2024, PMID: 37947085)",
        "description": "Pooled Cohort Equations for 10-year atherosclerotic cardiovascular disease risk. Requires blood pressure, smoking, and diabetes status.",
        "sort_order": 20,
    },
    {
        "code": "prevent_10yr",
        "name": "AHA PREVENT 10-Year Risk",
        "organ_system": "cardiovascular",
        "tier": "validated",
        "formula_key": "calc_prevent_10yr",
        "required_biomarkers": ["total_cholesterol", "hdl_cholesterol", "creatinine"],
        "required_clinical": ["age", "sex", "systolic_bp", "on_bp_medication", "smoking_status", "diabetes_status", "bmi"],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 5.0, "label": "Low risk (<5%)", "severity": "optimal"},
                {"min": 5.0, "max": 7.5, "label": "Borderline risk (5-7.5%)", "severity": "normal"},
                {"min": 7.5, "max": 20.0, "label": "Intermediate risk (7.5-20%)", "severity": "elevated"},
                {"min": 20.0, "label": "High risk (>=20%)", "severity": "high"},
            ]
        }),
        "citation_pmid": "37947085",
        "citation_text": "Khan SS et al. Circulation 2024;149(6):430-449. AHA PREVENT Equations. Race-free, adds eGFR + BMI. [Q1, top 10%]",
        "description": "AHA's newest cardiovascular risk equations (2024). Race-free, includes eGFR and BMI, predicts heart failure in addition to ASCVD. Ages 30-79.",
        "sort_order": 21,
    },
    # ═══════════════════════════════════════════════════════════════════════════
    # METABOLIC — Tier 1
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "code": "homa_ir",
        "name": "HOMA-IR",
        "organ_system": "metabolic",
        "tier": "validated",
        "formula_key": "calc_homa_ir",
        "required_biomarkers": ["fasting_insulin", "fasting_glucose"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 1.0, "label": "Normal insulin sensitivity", "severity": "optimal"},
                {"min": 1.0, "max": 1.9, "label": "Early insulin resistance", "severity": "normal"},
                {"min": 1.9, "max": 2.9, "label": "Moderate insulin resistance", "severity": "elevated"},
                {"min": 2.9, "label": "Significant insulin resistance", "severity": "high"},
            ]
        }),
        "citation_pmid": "3899825",
        "citation_text": "Matthews DR et al. Diabetologia 1985;28(7):412-9. [Q1]. Meta-analysis: Gonzalez-Gonzalez et al. 2022, PMID: 36181637",
        "description": "Homeostatic Model Assessment of Insulin Resistance. Uses fasting insulin and glucose. NHANES population 80th percentile ~2.5.",
        "sort_order": 30,
    },
    {
        "code": "homa_b",
        "name": "HOMA-B",
        "organ_system": "metabolic",
        "tier": "validated",
        "formula_key": "calc_homa_b",
        "required_biomarkers": ["fasting_insulin", "fasting_glucose"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"min": 80, "label": "Normal beta-cell function", "severity": "optimal"},
                {"min": 50, "max": 79, "label": "Mildly reduced beta-cell function", "severity": "elevated"},
                {"max": 49, "label": "Significantly reduced beta-cell function", "severity": "high"},
            ]
        }),
        "citation_pmid": "3899825",
        "citation_text": "Matthews DR et al. Diabetologia 1985;28(7):412-9. [Q1]",
        "description": "Homeostatic Model Assessment of Beta-Cell Function. Estimates pancreatic beta-cell secretory capacity from fasting values. 100% = normal reference.",
        "sort_order": 31,
    },
    {
        "code": "tyg_index",
        "name": "TyG Index",
        "organ_system": "metabolic",
        "tier": "validated",
        "formula_key": "calc_tyg_index",
        "required_biomarkers": ["triglycerides", "fasting_glucose"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 8.0, "label": "Normal insulin sensitivity", "severity": "optimal"},
                {"min": 8.0, "max": 8.5, "label": "Borderline insulin resistance", "severity": "normal"},
                {"min": 8.5, "max": 9.0, "label": "Insulin resistance likely", "severity": "elevated"},
                {"min": 9.0, "label": "High insulin resistance / MetS risk", "severity": "high"},
            ]
        }),
        "citation_pmid": "36521498",
        "citation_text": "Lopez-Jaramillo P et al. Lancet Healthy Longev 2023;4(1):e23-e33. PURE study (141,243 participants, 22 countries). [Q1, top 10%]",
        "description": "Triglyceride-Glucose Index. Does not require insulin measurement — uses standard lipid panel and glucose. Strong predictor of CVD and T2DM in the PURE study.",
        "sort_order": 32,
    },
    {
        "code": "mcauley_index",
        "name": "McAuley Index",
        "organ_system": "metabolic",
        "tier": "validated",
        "formula_key": "calc_mcauley_index",
        "required_biomarkers": ["fasting_insulin", "triglycerides"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"min": 7.0, "label": "Good insulin sensitivity", "severity": "optimal"},
                {"min": 5.8, "max": 6.99, "label": "Borderline insulin resistance", "severity": "elevated"},
                {"max": 5.79, "label": "Insulin resistant", "severity": "high"},
            ]
        }),
        "citation_pmid": "11289468",
        "citation_text": "McAuley KA et al. Diabetes Care 2001;24(3):460-4. [Q1]. Validated: Hammel et al. 2023, Lancet Reg Health Eur. PMID: 37465325 [Q1, top 10%]",
        "description": "Insulin sensitivity index using fasting insulin and triglycerides. AUC ~0.85-0.86 for metabolic syndrome detection. Validated across lifespan (ages 5-80).",
        "sort_order": 33,
    },
    # ═══════════════════════════════════════════════════════════════════════════
    # INFLAMMATORY — Tier 1
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "code": "glasgow_prognostic",
        "name": "Glasgow Prognostic Score",
        "organ_system": "inflammatory",
        "tier": "validated",
        "formula_key": "calc_glasgow_prognostic",
        "required_biomarkers": ["hs_crp", "albumin"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 0, "label": "GPS 0 — Low systemic inflammation", "severity": "optimal"},
                {"min": 1, "max": 1, "label": "GPS 1 — Moderate inflammation", "severity": "elevated"},
                {"min": 2, "label": "GPS 2 — Significant inflammation", "severity": "high"},
            ]
        }),
        "citation_pmid": "22995477",
        "citation_text": "McMillan DC. Cancer Treat Rev 2013;39(5):534-40. [Q1]. HS-mGPS meta-analysis: Wu et al. 2023, PMID: 36674837 [Q1]",
        "description": "Simple systemic inflammation assessment using CRP and albumin. Originally validated in oncology, broadly applicable. GPS 2 = CRP >10 AND albumin <3.5.",
        "sort_order": 40,
    },
    {
        "code": "sii",
        "name": "SII (Systemic Immune-Inflammation Index)",
        "organ_system": "inflammatory",
        "tier": "validated",
        "formula_key": "calc_sii",
        "required_biomarkers": ["platelets", "neutrophils_abs", "lymphocytes_abs"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 500, "label": "Normal — low systemic inflammation", "severity": "optimal"},
                {"min": 500, "max": 800, "label": "Mildly elevated inflammation", "severity": "normal"},
                {"min": 800, "max": 1200, "label": "Elevated inflammation", "severity": "elevated"},
                {"min": 1200, "label": "Significantly elevated inflammation", "severity": "high"},
            ]
        }),
        "citation_pmid": "39400697",
        "citation_text": "Li W et al. Inflammation Research 2024;73(12):2199-2216. Meta-analysis (33 studies, 427,819 participants). [Q1]",
        "description": "Combines platelets, neutrophils, and lymphocytes to assess systemic inflammation. Every 100-unit increase raises all-cause mortality risk by 5%.",
        "sort_order": 41,
    },
    {
        "code": "nlr",
        "name": "NLR (Neutrophil-to-Lymphocyte Ratio)",
        "organ_system": "inflammatory",
        "tier": "validated",
        "formula_key": "calc_nlr",
        "required_biomarkers": ["neutrophils_abs", "lymphocytes_abs"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"max": 2.0, "label": "Normal", "severity": "optimal"},
                {"min": 2.0, "max": 3.0, "label": "Mildly elevated", "severity": "normal"},
                {"min": 3.0, "max": 6.0, "label": "Elevated — pathological inflammation", "severity": "elevated"},
                {"min": 6.0, "label": "Significantly elevated — severe inflammation", "severity": "high"},
            ]
        }),
        "citation_pmid": "35408994",
        "citation_text": "Buonacera A et al. Int J Mol Sci 2022;23(7):3636. Comprehensive review. [Q1]",
        "description": "Simple ratio of neutrophils to lymphocytes from standard CBC with differential. Validated across oncology, cardiology, and infectious disease.",
        "sort_order": 42,
    },
    # ═══════════════════════════════════════════════════════════════════════════
    # THYROID — Tier 2 (Derived/Experimental)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "code": "jostel_tsh_index",
        "name": "Jostel's TSH Index",
        "organ_system": "thyroid",
        "tier": "derived",
        "formula_key": "calc_jostel_tsh_index",
        "required_biomarkers": ["tsh", "free_t4"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"min": 1.3, "max": 4.1, "label": "Normal pituitary-thyroid feedback", "severity": "optimal"},
                {"max": 1.29, "label": "Low — may suggest central hypothyroidism", "severity": "elevated"},
                {"min": 4.11, "label": "Elevated — pituitary over-stimulation", "severity": "elevated"},
            ]
        }),
        "citation_pmid": "19226261",
        "citation_text": "Jostel A et al. Clin Endocrinol 2009;71(4):529-34. Calibrated in >9,500 subjects. ETA 2018 acknowledged. [Q2]",
        "description": "FT4-adjusted TSH index. Assesses pituitary thyrotroph function. Useful for detecting central hypothyroidism. Limited population norms.",
        "sort_order": 50,
    },
    {
        "code": "spina_gt",
        "name": "SPINA-GT (Thyroid Secretory Capacity)",
        "organ_system": "thyroid",
        "tier": "derived",
        "formula_key": "calc_spina_gt",
        "required_biomarkers": ["tsh", "free_t4"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"min": 1.41, "max": 8.67, "label": "Normal thyroid secretory capacity", "severity": "optimal"},
                {"max": 1.40, "label": "Reduced secretory capacity", "severity": "elevated"},
                {"min": 8.68, "label": "Elevated secretory capacity", "severity": "elevated"},
            ]
        }),
        "citation_pmid": "27375554",
        "citation_text": "Dietrich JW et al. Front Endocrinol 2016;7:57. SPINA Thyr framework. [Q1]",
        "description": "Estimates maximum thyroid hormone secretion rate. Research tool — not yet adopted in clinical guidelines. Units: pmol/s.",
        "sort_order": 51,
    },
    {
        "code": "spina_gd",
        "name": "SPINA-GD (Peripheral Deiodinase Activity)",
        "organ_system": "thyroid",
        "tier": "derived",
        "formula_key": "calc_spina_gd",
        "required_biomarkers": ["free_t3", "free_t4"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"min": 20, "max": 40, "label": "Normal T4-to-T3 conversion", "severity": "optimal"},
                {"max": 19, "label": "Reduced peripheral conversion", "severity": "elevated"},
                {"min": 41, "label": "Elevated peripheral conversion", "severity": "elevated"},
            ]
        }),
        "citation_pmid": "27375554",
        "citation_text": "Dietrich JW et al. Front Endocrinol 2016;7:57. SPINA Thyr framework. [Q1]",
        "description": "Estimates sum activity of peripheral deiodinases (T4 to T3 conversion). Research tool — limited clinical validation. Units: nmol/s.",
        "sort_order": 52,
    },
    # ═══════════════════════════════════════════════════════════════════════════
    # HEMATOLOGIC — Tier 2 (Derived/Experimental)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "code": "iron_status_composite",
        "name": "Iron Status Composite",
        "organ_system": "hematologic",
        "tier": "derived",
        "formula_key": "calc_iron_status_composite",
        "required_biomarkers": ["ferritin", "iron", "tibc", "transferrin_sat"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"min": 60, "label": "Good iron status", "severity": "optimal"},
                {"min": 40, "max": 59, "label": "Borderline iron status", "severity": "normal"},
                {"min": 20, "max": 39, "label": "Suboptimal iron status", "severity": "elevated"},
                {"max": 19, "label": "Poor iron status — possible deficiency", "severity": "high"},
            ]
        }),
        "citation_pmid": "39011129",
        "citation_text": "Iolascon A et al. HemaSphere 2024;8(7):e108. EHA recommendations for iron deficiency. [Q1]. NHANES 2017-2020 population reference distributions.",
        "description": "Composite percentile score based on ferritin, serum iron, TIBC, and TSAT ranked against NHANES 2017-2020 reference data. No validated single composite exists — this is a derived experimental index.",
        "sort_order": 60,
    },
    {
        "code": "cbc_composite",
        "name": "CBC Health Composite",
        "organ_system": "hematologic",
        "tier": "derived",
        "formula_key": "calc_cbc_composite",
        "required_biomarkers": ["hemoglobin", "mcv", "rdw", "wbc", "platelets"],
        "required_clinical": [],
        "interpretation": json.dumps({
            "ranges": [
                {"min": 60, "label": "Healthy blood cell profile", "severity": "optimal"},
                {"min": 40, "max": 59, "label": "Borderline blood cell profile", "severity": "normal"},
                {"min": 20, "max": 39, "label": "Suboptimal blood cell profile", "severity": "elevated"},
                {"max": 19, "label": "Abnormal blood cell profile — review needed", "severity": "high"},
            ]
        }),
        "citation_pmid": None,
        "citation_text": "Derived composite using NHANES 2017-2020 reference distributions for age/sex-stratified CBC parameters. No validated single hematologic health index exists.",
        "description": "Experimental composite score combining hemoglobin, MCV, RDW, WBC, and platelets against population reference ranges. Each marker ranked by percentile, then averaged.",
        "sort_order": 61,
    },
]

# Organ system display metadata
ORGAN_SYSTEMS = {
    "liver": {"name": "Liver Health", "icon": "&#129516;", "color": "#8B4513", "sort_order": 1},
    "kidney": {"name": "Kidney Health", "icon": "&#128167;", "color": "#4682B4", "sort_order": 2},
    "cardiovascular": {"name": "Cardiovascular Risk", "icon": "&#128147;", "color": "#DC143C", "sort_order": 3},
    "metabolic": {"name": "Metabolic Health", "icon": "&#9889;", "color": "#FF8C00", "sort_order": 4},
    "inflammatory": {"name": "Inflammatory Status", "icon": "&#128293;", "color": "#FF4500", "sort_order": 5},
    "thyroid": {"name": "Thyroid Function", "icon": "&#129507;", "color": "#9370DB", "sort_order": 6},
    "hematologic": {"name": "Hematologic & Iron", "icon": "&#129656;", "color": "#B22222", "sort_order": 7},
}
