"""Cross-domain clinical patterns that link organ-score findings into a narrative.

Each pattern activates when its trigger groups are all satisfied by the current
organ-score snapshot. Patterns are evidence-backed clinical syndromes — not
diagnoses — that surface *why* multiple organ systems may be drifting together.

Schema:
    code             Stable identifier.
    name             Clinician-facing pattern title.
    narrative        Plain-language story linking the triggering signals.
    action           Suggested next steps (lifestyle, monitoring, referral).
    citation_pmid    Primary PMID (when a single consensus paper applies).
    citation_text    Source attribution shown to clinicians.
    severity_floor   Minimum shared severity required for a group to match
                     ("elevated" | "high" | "critical"). Default "elevated".
    trigger_groups   A list of groups. Every group must match. Each group:
        any_of        Score codes; at least one must be present at the
                      matching severity.
        min_severity  Overrides severity_floor for this group only.
"""

from __future__ import annotations

CROSS_DOMAIN_PATTERNS = [
    {
        "code": "masld_metabolic",
        "name": "Metabolic-Dysfunction-Associated Steatotic Liver Disease (MASLD)",
        "narrative": (
            "Hepatic steatosis / fibrosis markers coexist with insulin-resistance "
            "markers. Under the AASLD 2023 nomenclature, fatty liver driven by "
            "cardiometabolic risk factors is renamed MASLD (formerly NAFLD). The "
            "shared mechanism is insulin resistance: the liver stores excess "
            "glucose as fat and exports VLDL-rich triglycerides, which then feed "
            "atherogenic dyslipidemia. Cardiovascular events — not liver failure — "
            "are the leading cause of death in this phenotype."
        ),
        "action": (
            "Prioritize 7-10 percent weight reduction, Mediterranean or "
            "carbohydrate-restricted dietary patterns, structured aerobic + "
            "resistance exercise. Reassess hepatic and insulin-resistance panels "
            "in 12 weeks. Consider FibroScan if FIB-4 or NAFLD-FS remains indeterminate."
        ),
        "citation_pmid": "37363821",
        "citation_text": "Rinella ME et al. Hepatology 2023;78(6):1966-1986. AASLD multisociety Delphi consensus on steatotic liver disease nomenclature.",
        "trigger_groups": [
            {"any_of": ["hsi", "fli", "fib4", "nafld_fibrosis", "bard_score", "apri"]},
            {"any_of": ["homa_ir", "tyg_index", "mets_ir", "lap_index", "tyg_bmi", "vai", "mcauley_index"]},
        ],
    },
    {
        "code": "ckm_syndrome",
        "name": "Cardiovascular-Kidney-Metabolic (CKM) Syndrome",
        "narrative": (
            "Kidney dysfunction, metabolic dysregulation, and cardiovascular risk "
            "are co-activated. The AHA 2023 CKM staging framework recognizes these "
            "tissues as a single pathophysiological axis linked by insulin "
            "resistance, sympathetic overdrive, neurohormonal activation, and "
            "low-grade inflammation. Recognizing CKM unlocks shared therapies that "
            "benefit all three organ systems simultaneously (SGLT2 inhibitors, "
            "GLP-1 agonists, renin-angiotensin blockade)."
        ),
        "action": (
            "Check albuminuria (UACR) if not already done; optimize blood pressure, "
            "glycemic control, and LDL / ApoB. Consider SGLT2 inhibitor or GLP-1 "
            "agonist review given combined CVD, kidney, and metabolic indication. "
            "Include PREVENT 10-year risk in shared decision-making."
        ),
        "citation_pmid": "37767743",
        "citation_text": "Ndumele CE et al. Circulation 2023;148(20):1606-1635. AHA Presidential Advisory on CKM syndrome.",
        "trigger_groups": [
            {"any_of": ["prevent_10yr", "prevent_10yr_ascvd", "prevent_10yr_hf", "ascvd_pce", "qrisk3"]},
            {"any_of": ["ckd_epi_egfr", "kdigo_risk", "kfre_2yr", "kfre_5yr"]},
            {"any_of": ["homa_ir", "tyg_index", "mets_ir", "lap_index", "tyg_bmi", "vai"]},
        ],
    },
    {
        "code": "atherogenic_dyslipidemia",
        "name": "Atherogenic Dyslipidemia",
        "narrative": (
            "Multiple ApoB-particle-derived markers are elevated together. ApoB-"
            "containing particles (LDL, VLDL remnants, Lp(a)) are the causal agent "
            "of atherosclerosis; LDL-C alone underestimates risk when triglycerides "
            "or remnants are elevated. The pattern below strengthens the case for "
            "lipid-lowering therapy intensification beyond what any single LDL-C "
            "value would trigger."
        ),
        "action": (
            "Confirm ApoB and Lp(a) at least once in adulthood. Intensify lifestyle "
            "and lipid-lowering therapy targeting ApoB and non-HDL-C; consider "
            "high-intensity statin, ezetimibe, and PCSK9 inhibitor review guided by "
            "PREVENT 10-year ASCVD estimate."
        ),
        "citation_pmid": "35686204",
        "citation_text": "Mach F et al. Eur Heart J 2020;41(1):111-188 (ESC/EAS dyslipidaemia guideline); Sniderman AD et al. JAMA Cardiol 2019;4(12):1287-1295 (ApoB vs LDL-C).",
        "trigger_groups": [
            {"any_of": ["apob_risk", "non_hdl_c", "lpa_risk", "remnant_cholesterol",
                        "tg_hdl_ratio", "aip", "castelli_ratio"], "min_count": 2},
        ],
    },
    {
        "code": "chronic_inflammation",
        "name": "Chronic Low-Grade Inflammation (Inflammaging)",
        "narrative": (
            "Multiple blood-count-derived inflammatory indices are persistently "
            "elevated without evidence of acute illness. Chronic low-grade "
            "inflammation (inflammaging) independently accelerates cardiovascular, "
            "neurodegenerative, and cancer risk, and predicts mortality beyond "
            "any single disease. Common modifiable drivers are visceral adiposity, "
            "poor sleep, subclinical periodontitis, undertreated autoimmunity, "
            "and occult infection."
        ),
        "action": (
            "Review lifestyle drivers (adiposity, sleep, oral health); rule out "
            "active infection or autoimmune flare; consider CRP and ESR confirmation. "
            "Reassess in 8-12 weeks after targeted interventions."
        ),
        "citation_pmid": "24833586",
        "citation_text": "Franceschi C, Campisi J. J Gerontol A Biol Sci Med Sci 2014;69 Suppl 1:S4-9 (inflammaging); Fest J et al. Sci Rep 2018;8:10566 (NLR/PLR mortality).",
        "trigger_groups": [
            {"any_of": ["nlr", "sii", "plr", "glasgow_prognostic", "pni"], "min_count": 2},
        ],
    },
    {
        "code": "accelerated_biological_aging",
        "name": "Accelerated Biological Aging",
        "narrative": (
            "Biological-age markers indicate phenotypic age exceeds chronological "
            "age, and multiple organ systems are contributing. This pattern "
            "predicts all-cause mortality and frailty independent of any specific "
            "diagnosis. The common substrate is mitochondrial decline, senescent-"
            "cell burden, chronic inflammation, and blunted proteostasis."
        ),
        "action": (
            "Stack highest-yield longevity interventions: structured resistance + "
            "zone-2 aerobic training, protein-adequate diet, time-restricted "
            "eating trial, sleep optimization, and smoking / alcohol review. "
            "Re-measure PhenoAge or vascular-age gap in 6-12 months to track "
            "bio-age trajectory."
        ),
        "citation_pmid": "29676998",
        "citation_text": "Levine ME et al. Aging (Albany NY) 2018;10(4):573-591 (PhenoAge); Liu Z et al. PLoS Med 2018;15(12):e1002718 (validation).",
        "trigger_groups": [
            {"any_of": ["phenoage", "framingham_vascular_age_gap"]},
            {"any_of": ["prevent_10yr", "homa_ir", "nlr", "sii", "kdigo_risk",
                        "homocysteine_neurovascular", "cbc_mortality_risk"], "min_count": 2},
        ],
    },
]


CROSS_DOMAIN_PATTERNS_BY_CODE = {p["code"]: p for p in CROSS_DOMAIN_PATTERNS}
