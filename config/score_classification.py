"""Lifecycle + domain classification for every organ-score definition.

Kept as a side-table (not merged into organ_scores_data.py) so the clinical
judgments here are easy to review and revise without touching formula code.

Schema per entry:
    lifecycle        "active" | "superseded" | "research"
    lifecycle_note   short rationale the reviewer can challenge
    superseded_by    for lifecycle == "superseded", the preferred score code
    primary_domain   one of: heart_metabolism, brain_health,
                     muscle_bones, gut_digestion, system_wide
    secondary_domains  list of other domains the score informs

Domain rationale
    heart_metabolism   CVD risk + lipids + insulin resistance + adiposity
    brain_health       dementia / neurovascular / cognitive substrates
    muscle_bones       bone density, sarcopenia, physical function, fractures
    gut_digestion      hepato-gastroenterology (liver scores live here per
                       classical GI axis) -- thin today; microbiome/
                       permeability markers not yet in the panel
    system_wide        genuinely integrative by construction (biological
                       age, inflammatory composites, organ-system markers
                       that predict multi-system outcomes)

Lifecycle rationale
    active         current guideline or clinical-practice standard
    superseded     a better-validated score for the same clinical question
                   now exists; keep for teaching / completeness but
                   deprioritize in UX
    research       emerging evidence; not yet guideline-endorsed
"""

from __future__ import annotations


DOMAIN_CODES: tuple[str, ...] = (
    "heart_metabolism",
    "brain_health",
    "muscle_bones",
    "gut_digestion",
    "system_wide",
)

DOMAIN_LABELS = {
    "heart_metabolism": "Heart & Metabolism",
    "brain_health": "Brain Health",
    "muscle_bones": "Muscle & Bones",
    "gut_digestion": "Gut & Digestion",
    "system_wide": "System-Wide",
}

LIFECYCLE_CODES: tuple[str, ...] = ("active", "superseded", "research")


# Per-score classification. Every score_code in ORGAN_SCORE_DEFINITIONS must
# appear here (enforced by tests/test_score_classification.py).
SCORE_CLASSIFICATION: dict[str, dict] = {
    # ─── Cardiovascular primary ──────────────────────────────────────────────
    "prevent_10yr": {
        "lifecycle": "active",
        "lifecycle_note": "AHA 2024 primary CVD-risk calculator.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "prevent_10yr_ascvd": {
        "lifecycle": "active",
        "lifecycle_note": "AHA 2024 ASCVD sub-score (MI + stroke).",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "prevent_10yr_hf": {
        "lifecycle": "active",
        "lifecycle_note": "AHA 2024 heart-failure sub-score; new endpoint not in PCE.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "ascvd_pce": {
        "lifecycle": "active",
        "lifecycle_note": "Still in wide clinical use alongside PREVENT 2024; kept for continuity.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "qrisk3": {
        "lifecycle": "active",
        "lifecycle_note": "NICE-mandated UK CVD risk tool.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "framingham_cvd": {
        "lifecycle": "superseded",
        "superseded_by": "prevent_10yr",
        "lifecycle_note": "Framingham 2008 superseded by ACC/AHA PCE (2013), now PREVENT (2024).",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "who_na_me_cvd_lab": {
        "lifecycle": "active",
        "lifecycle_note": "WHO 2019 regional chart; primary reference for UAE CVD risk.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "who_na_me_cvd_nonlab": {
        "lifecycle": "active",
        "lifecycle_note": "WHO 2019 non-lab companion to the lab chart.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "cha2ds2_vasc": {
        "lifecycle": "active",
        "lifecycle_note": "ESC / AHA standard for stroke risk in atrial fibrillation.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },

    # ─── Lipid particles / ratios ────────────────────────────────────────────
    "non_hdl_c": {
        "lifecycle": "active",
        "lifecycle_note": "ESC/AHA lipid-guideline primary residual-risk target.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "apob_risk": {
        "lifecycle": "active",
        "lifecycle_note": "ApoB is the causal-particle metric; preferred over LDL-C in 2023+ guidelines.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "remnant_cholesterol": {
        "lifecycle": "active",
        "lifecycle_note": "TG-rich lipoprotein marker; rising in clinical use.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "lpa_risk": {
        "lifecycle": "active",
        "lifecycle_note": "Lp(a) is guideline-endorsed once-per-lifetime measurement.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "aip": {
        "lifecycle": "active",
        "lifecycle_note": "Atherogenic Index of Plasma; widely cited in metabolic-syndrome literature.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "tg_hdl_ratio": {
        "lifecycle": "active",
        "lifecycle_note": "Widely used bedside insulin-resistance / atherogenic-dyslipidemia flag.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "castelli_ratio": {
        "lifecycle": "superseded",
        "superseded_by": "apob_risk",
        "lifecycle_note": "Castelli I (TC/HDL, 1983) superseded by ApoB and non-HDL; kept for teaching.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },

    # ─── Insulin resistance / metabolic ──────────────────────────────────────
    "homa_ir": {
        "lifecycle": "active",
        "lifecycle_note": "Gold-standard insulin-resistance surrogate when insulin is available.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health", "muscle_bones"],
    },
    "homa_b": {
        "lifecycle": "superseded",
        "superseded_by": "homa_ir",
        "lifecycle_note": "Beta-cell function research index; rarely a bedside decision tool.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "quicki": {
        "lifecycle": "superseded",
        "superseded_by": "tyg_index",
        "lifecycle_note": "QUICKI (2000) largely superseded by simpler TyG / METS-IR indices that skip insulin.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "mcauley_index": {
        "lifecycle": "superseded",
        "superseded_by": "mets_ir",
        "lifecycle_note": "McAuley (2001) superseded by TyG and METS-IR for insulin-resistance surrogacy.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "tyg_index": {
        "lifecycle": "active",
        "lifecycle_note": "Widely used insulin-resistance surrogate without fasting insulin.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "tyg_bmi": {
        "lifecycle": "active",
        "lifecycle_note": "TyG variant incorporating adiposity.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "mets_ir": {
        "lifecycle": "active",
        "lifecycle_note": "Metabolic score for insulin resistance; solid recent validation.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health"],
    },
    "lap_index": {
        "lifecycle": "active",
        "lifecycle_note": "Lipid accumulation product -- visceral-adiposity surrogate.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "vai": {
        "lifecycle": "active",
        "lifecycle_note": "Visceral adiposity index; validated across several cohorts.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": [],
    },
    "findrisc": {
        "lifecycle": "active",
        "lifecycle_note": "FINDRISC is the European primary-care T2DM risk standard.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["system_wide"],
    },

    # ─── Biological age ──────────────────────────────────────────────────────
    "phenoage": {
        "lifecycle": "active",
        "lifecycle_note": "Levine PhenoAge; validated all-cause mortality predictor.",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism"],
    },
    "framingham_vascular_age_gap": {
        "lifecycle": "research",
        "lifecycle_note": "Exploratory biological-age derivative; reasonable intuition, limited validation.",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism", "brain_health"],
    },

    # ─── Liver / hepato-gastroenterology ─────────────────────────────────────
    "fib4": {
        "lifecycle": "active",
        "lifecycle_note": "AASLD / EASL primary-care triage for advanced liver fibrosis.",
        "primary_domain": "gut_digestion",
        "secondary_domains": ["heart_metabolism", "brain_health"],
    },
    "apri": {
        "lifecycle": "active",
        "lifecycle_note": "WHO-endorsed resource-limited alternative to FIB-4.",
        "primary_domain": "gut_digestion",
        "secondary_domains": [],
    },
    "nafld_fibrosis": {
        "lifecycle": "active",
        "lifecycle_note": "NAFLD Fibrosis Score -- historical reference; FIB-4 preferred in primary care.",
        "primary_domain": "gut_digestion",
        "secondary_domains": ["heart_metabolism", "brain_health"],
    },
    "hsi": {
        "lifecycle": "active",
        "lifecycle_note": "EASL-endorsed steatosis screen (MASLD screening).",
        "primary_domain": "gut_digestion",
        "secondary_domains": ["heart_metabolism"],
    },
    "fli": {
        "lifecycle": "active",
        "lifecycle_note": "Fatty Liver Index; widely used steatosis screen.",
        "primary_domain": "gut_digestion",
        "secondary_domains": ["heart_metabolism"],
    },
    "bard_score": {
        "lifecycle": "superseded",
        "superseded_by": "fib4",
        "lifecycle_note": "BARD (2008) largely superseded by FIB-4 for primary-care NAFLD triage.",
        "primary_domain": "gut_digestion",
        "secondary_domains": ["heart_metabolism"],
    },
    "albi_score": {
        "lifecycle": "active",
        "lifecycle_note": "Hepatic reserve quantifier; primary use in hepatocellular-cancer staging.",
        "primary_domain": "gut_digestion",
        "secondary_domains": [],
    },
    "amap_hcc": {
        "lifecycle": "active",
        "lifecycle_note": "HCC-risk score in chronic liver disease; specialist-care tool.",
        "primary_domain": "gut_digestion",
        "secondary_domains": [],
    },

    # ─── Kidney (no primary domain in the 5; integrative by construction) ────
    "ckd_epi_egfr": {
        "lifecycle": "active",
        "lifecycle_note": "KDIGO-endorsed race-free eGFR (2021).",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism", "muscle_bones"],
    },
    "kdigo_risk": {
        "lifecycle": "active",
        "lifecycle_note": "KDIGO CKD heatmap stratification.",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism", "muscle_bones"],
    },
    "kfre_2yr": {
        "lifecycle": "active",
        "lifecycle_note": "Kidney Failure Risk Equation, 2-year; widely adopted in nephrology.",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism"],
    },
    "kfre_5yr": {
        "lifecycle": "active",
        "lifecycle_note": "Kidney Failure Risk Equation, 5-year.",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism"],
    },

    # ─── Musculoskeletal primary ─────────────────────────────────────────────
    "dxa_osteoporosis_who": {
        "lifecycle": "active",
        "lifecycle_note": "WHO / ISCD T-score classification; diagnostic standard.",
        "primary_domain": "muscle_bones",
        "secondary_domains": [],
    },
    "ewgsop2_sarcopenia": {
        "lifecycle": "active",
        "lifecycle_note": "EWGSOP2 2019 sarcopenia consensus staging.",
        "primary_domain": "muscle_bones",
        "secondary_domains": ["system_wide"],
    },
    "fnih_low_lean_mass": {
        "lifecycle": "active",
        "lifecycle_note": "FNIH Sarcopenia Project cutpoints; ALM/BMI ratio.",
        "primary_domain": "muscle_bones",
        "secondary_domains": [],
    },
    "qfracture_major": {
        "lifecycle": "active",
        "lifecycle_note": "QFracture 10-year major fracture (UK primary care).",
        "primary_domain": "muscle_bones",
        "secondary_domains": [],
    },
    "qfracture_hip": {
        "lifecycle": "active",
        "lifecycle_note": "QFracture 10-year hip fracture.",
        "primary_domain": "muscle_bones",
        "secondary_domains": [],
    },

    # ─── Brain / cognition ───────────────────────────────────────────────────
    "caide_dementia": {
        "lifecycle": "active",
        "lifecycle_note": "Kivipelto CAIDE; widely cited midlife dementia-risk model.",
        "primary_domain": "brain_health",
        "secondary_domains": ["heart_metabolism"],
    },
    "homocysteine_neurovascular": {
        "lifecycle": "active",
        "lifecycle_note": "Homocysteine is an AHA-recognized CVD modifier and midlife dementia-risk signal; neurovascular label reflects the score's primary framing in this app.",
        "primary_domain": "brain_health",
        "secondary_domains": ["heart_metabolism", "gut_digestion", "system_wide"],
    },

    # ─── Hematology / anemia / iron ──────────────────────────────────────────
    "cbc_mortality_risk": {
        "lifecycle": "active",
        "lifecycle_note": "Patel 2010 RDW + WHO anemia; validated all-cause mortality signal.",
        "primary_domain": "system_wide",
        "secondary_domains": ["muscle_bones", "gut_digestion"],
    },
    "iron_status_composite": {
        "lifecycle": "research",
        "lifecycle_note": "Composite derived from NHANES percentiles; not a formal published composite.",
        "primary_domain": "system_wide",
        "secondary_domains": ["muscle_bones", "gut_digestion"],
    },

    # ─── Thyroid ─────────────────────────────────────────────────────────────
    "thyroid_guideline_pattern": {
        "lifecycle": "active",
        "lifecycle_note": "ETA-style TSH+FT4 pattern mapping.",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism", "brain_health", "muscle_bones"],
    },
    "jostel_tsh_index": {
        "lifecycle": "research",
        "lifecycle_note": "Theoretical central-thyroid model; not guideline-endorsed.",
        "primary_domain": "system_wide",
        "secondary_domains": [],
    },
    "spina_gt": {
        "lifecycle": "research",
        "lifecycle_note": "SPINA thyroid secretory capacity; academic / research use.",
        "primary_domain": "system_wide",
        "secondary_domains": [],
    },
    "spina_gd": {
        "lifecycle": "research",
        "lifecycle_note": "SPINA peripheral deiodinase activity; academic / research use.",
        "primary_domain": "system_wide",
        "secondary_domains": [],
    },
    "tfqi": {
        "lifecycle": "research",
        "lifecycle_note": "Thyroid Feedback Quantile Index; emerging research construct.",
        "primary_domain": "system_wide",
        "secondary_domains": [],
    },

    # ─── Systemic inflammation ───────────────────────────────────────────────
    "sii": {
        "lifecycle": "active",
        "lifecycle_note": "Systemic Immune-Inflammation Index; broad prognostic validation.",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism"],
    },
    "nlr": {
        "lifecycle": "active",
        "lifecycle_note": "Neutrophil/Lymphocyte ratio; broad outcome literature.",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism"],
    },
    "plr": {
        "lifecycle": "research",
        "lifecycle_note": "Platelet/Lymphocyte ratio; emerging prognostic marker.",
        "primary_domain": "system_wide",
        "secondary_domains": [],
    },
    "glasgow_prognostic": {
        "lifecycle": "research",
        "lifecycle_note": "Oncology prognostic score; lifestyle-medicine use is off-label.",
        "primary_domain": "system_wide",
        "secondary_domains": ["heart_metabolism", "gut_digestion"],
    },
    "pni": {
        "lifecycle": "research",
        "lifecycle_note": "Onodera Prognostic Nutritional Index; nutritional-status composite.",
        "primary_domain": "system_wide",
        "secondary_domains": ["muscle_bones", "gut_digestion"],
    },

    # ─── Sleep / respiratory ─────────────────────────────────────────────────
    "nosas": {
        "lifecycle": "active",
        "lifecycle_note": "NoSAS sleep-apnea screen; widely validated.",
        "primary_domain": "heart_metabolism",
        "secondary_domains": ["brain_health", "system_wide"],
    },
}


def get_classification(score_code: str) -> dict:
    """Return the classification entry for a score, or a permissive default."""
    return SCORE_CLASSIFICATION.get(score_code, {
        "lifecycle": "active",
        "lifecycle_note": "",
        "primary_domain": "system_wide",
        "secondary_domains": [],
    })


def scores_for_domain(domain: str, primary_only: bool = False) -> list[str]:
    """Return every score_code that lists ``domain`` as primary or secondary."""
    out: list[str] = []
    for code, info in SCORE_CLASSIFICATION.items():
        if info.get("primary_domain") == domain:
            out.append(code)
            continue
        if not primary_only and domain in (info.get("secondary_domains") or ()):
            out.append(code)
    return out


def active_scores() -> list[str]:
    return [c for c, info in SCORE_CLASSIFICATION.items() if info.get("lifecycle") == "active"]


def superseded_scores() -> list[str]:
    return [c for c, info in SCORE_CLASSIFICATION.items() if info.get("lifecycle") == "superseded"]


def research_scores() -> list[str]:
    return [c for c, info in SCORE_CLASSIFICATION.items() if info.get("lifecycle") == "research"]
