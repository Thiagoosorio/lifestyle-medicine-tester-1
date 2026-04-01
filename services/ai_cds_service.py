"""AI clinical decision support benchmarking and rollout planning."""

from __future__ import annotations

from config.ai_cds_catalog import (
    AI_CDS_USE_CASES,
    GITHUB_LIFESTYLE_PATTERNS,
    INSTITUTION_EMR_BENCHMARKS,
    LIFESTYLE_EVIDENCE_BASE,
)


def get_institution_emr_benchmarks() -> list[dict]:
    return list(INSTITUTION_EMR_BENCHMARKS)


def get_ai_cds_use_cases() -> list[dict]:
    return list(AI_CDS_USE_CASES)


def get_lifestyle_evidence_base() -> list[dict]:
    return list(LIFESTYLE_EVIDENCE_BASE)


def get_github_lifestyle_patterns() -> list[dict]:
    return list(GITHUB_LIFESTYLE_PATTERNS)


def _profile_completeness(snapshot: dict) -> int:
    patient = snapshot.get("patient", {}) or {}
    points = 0

    if patient.get("age") is not None:
        points += 10
    if patient.get("sex"):
        points += 10
    if patient.get("bmi") is not None:
        points += 10
    if patient.get("systolic_bp") is not None and patient.get("diastolic_bp") is not None:
        points += 10

    if snapshot.get("labs_attention", {}).get("all"):
        points += 20
    if snapshot.get("organ_overall"):
        points += 15
    if snapshot.get("wearable"):
        points += 10
    if snapshot.get("test_results"):
        points += 10
    if snapshot.get("interventions_active") or snapshot.get("diagnoses_active"):
        points += 5

    return min(points, 100)


def _cardio_metabolic_risk_signal(snapshot: dict) -> bool:
    domains = snapshot.get("organ_domain_categories", []) or []
    for row in domains:
        if row.get("domain_code") == "heart_metabolism":
            score_10 = row.get("score_10")
            elevated = int(row.get("elevated_or_worse") or 0)
            if score_10 is None:
                return False
            return score_10 <= 6.5 or elevated >= 1
    return bool(snapshot.get("organ_high_risk_scores"))


def _domain_row(snapshot: dict, domain_code: str) -> dict | None:
    for row in snapshot.get("organ_domain_categories", []) or []:
        if row.get("domain_code") == domain_code:
            return row
    return None


def _is_domain_needing_support(snapshot: dict, domain_code: str, threshold: float = 6.8) -> bool:
    row = _domain_row(snapshot, domain_code)
    if not row:
        return False
    score = row.get("score_10")
    elevated = int(row.get("elevated_or_worse") or 0)
    if score is None:
        return False
    return score <= threshold or elevated >= 1


def build_lifestyle_intervention_support(snapshot: dict) -> list[dict]:
    """Build domain-based lifestyle intervention support cards."""
    interventions: list[dict] = []
    counts = snapshot.get("counts", {}) or {}
    wearable = snapshot.get("wearable") or {}

    if _is_domain_needing_support(snapshot, "heart_metabolism", threshold=6.8):
        interventions.append(
            {
                "domain": "Heart & Metabolism",
                "priority": "P1",
                "trigger": "Domain score low/elevated risk signals present.",
                "recommendation": (
                    "Mediterranean-style nutrition + 150-300 min/week moderate aerobic + "
                    "2+ resistance sessions/week + BP-aware sodium strategy."
                ),
                "success_metric": "Track BP trend, LDL/non-HDL, TG/HDL, and weekly exercise adherence.",
                "evidence_topics": [
                    "Mediterranean diet for primary CVD prevention",
                    "Physical activity dose-response and prevention",
                    "Blood pressure management with non-pharmacologic interventions",
                ],
            }
        )

    if _is_domain_needing_support(snapshot, "gut_digestion", threshold=7.0):
        interventions.append(
            {
                "domain": "Gut & Digestion",
                "priority": "P1",
                "trigger": "Liver-digestive domain risk elevated or score below target.",
                "recommendation": (
                    "Weight-focused liver protocol: reduce ultra-processed foods and refined sugars, "
                    "increase fiber-rich whole foods, and prescribe progressive activity."
                ),
                "success_metric": "Follow AST/ALT/GGT trend and liver-risk score movement over 8-12 weeks.",
                "evidence_topics": [
                    "NAFLD/MASLD lifestyle-first management",
                    "Physical activity dose-response and prevention",
                ],
            }
        )

    if _is_domain_needing_support(snapshot, "brain_health", threshold=7.0) or (
        wearable and float(wearable.get("overall_readiness_10") or 0) < 6.5
    ):
        interventions.append(
            {
                "domain": "Brain Health",
                "priority": "P2",
                "trigger": "Brain/sleep resilience signal below target.",
                "recommendation": (
                    "Sleep-anchoring protocol: fixed wake time, consistent bedtime window, "
                    "morning light exposure, and late-evening stimulant cutoff."
                ),
                "success_metric": "Track sleep efficiency, sleep consistency, and daytime recovery score.",
                "evidence_topics": [
                    "Physical activity dose-response and prevention",
                    "Primary prevention lifestyle and risk-factor control",
                ],
            }
        )

    if _is_domain_needing_support(snapshot, "muscle_bones", threshold=7.0):
        interventions.append(
            {
                "domain": "Muscle & Bones",
                "priority": "P2",
                "trigger": "Muscle-bone support domain has low confidence or low score.",
                "recommendation": (
                    "Strength-first plan (2-3 sessions/week) + adequate protein distribution "
                    "+ balance/mobility block."
                ),
                "success_metric": "Track lean mass trend, strength progressions, and functional test cadence.",
                "evidence_topics": [
                    "Physical activity dose-response and prevention",
                    "Primary prevention lifestyle and risk-factor control",
                ],
            }
        )

    if _is_domain_needing_support(snapshot, "system_wide", threshold=7.0):
        interventions.append(
            {
                "domain": "System Wide (incl. Hormone Health)",
                "priority": "P2",
                "trigger": "System-wide markers indicate broad prevention opportunity.",
                "recommendation": (
                    "Integrated protocol: sleep regularity, physical activity progression, "
                    "nutrition quality upgrade, and stress-management micro-habits."
                ),
                "success_metric": "Monitor flagged lab count and overall organ composite trend monthly.",
                "evidence_topics": [
                    "Prediabetes/T2D prevention with lifestyle change",
                    "Primary prevention lifestyle and risk-factor control",
                ],
            }
        )

    if not interventions:
        interventions.append(
            {
                "domain": "Prevention Baseline",
                "priority": "P3",
                "trigger": "No major elevated domain signal today.",
                "recommendation": (
                    "Maintain current plan; reinforce adherence and set one incremental behavior goal for this week."
                ),
                "success_metric": (
                    f"Keep flagged labs <= {counts.get('labs_flagged', 0)} and preserve readiness trend over 4 weeks."
                ),
                "evidence_topics": [
                    "Physical activity dose-response and prevention",
                    "Primary prevention lifestyle and risk-factor control",
                ],
            }
        )

    return interventions


def build_ai_cds_rollout_plan(snapshot: dict) -> dict:
    """Build an evidence-backed, human-in-the-loop lifestyle AI rollout plan."""
    counts = snapshot.get("counts", {}) or {}
    readiness = _profile_completeness(snapshot)

    labs_flagged = int(counts.get("labs_flagged", 0) or 0)
    high_risk_scores = int(counts.get("organ_scores_high_risk", 0) or 0)
    has_cardio_signal = _cardio_metabolic_risk_signal(snapshot)
    has_wearable = bool(snapshot.get("wearable"))

    modules = []

    modules.append(
        {
            "module": "Lifestyle Intervention Opportunity Finder",
            "priority": "P1",
            "status": "Activate now",
            "why_now": (
                f"{labs_flagged} flagged labs and {high_risk_scores} high-risk scores can be translated into next-best lifestyle actions."
                if labs_flagged > 0 or high_risk_scores > 0
                else "Keeps prevention actions consistent even when risk is stable."
            ),
            "safety_model": "Human clinician confirms all recommendations before final plan sign-off.",
            "evidence_anchor": "WHO/ACC-AHA/AASLD lifestyle and prevention guidelines.",
        }
    )

    modules.append(
        {
            "module": "Domain-to-Protocol Recommendation Cards",
            "priority": "P1" if has_cardio_signal else "P2",
            "status": "Activate now",
            "why_now": (
                "Cardiometabolic risk stack is elevated and benefits from protocolized intervention support."
                if has_cardio_signal
                else "Improves consistency of prevention workflows across all 5 domains."
            ),
            "safety_model": "Show rationale + cited source for each suggested action; never auto-place orders.",
            "evidence_anchor": "Evidence-linked recommendation cards (CDS Hooks pattern + guideline citation).",
        }
    )

    modules.append(
        {
            "module": "Wearable Adherence & Recovery Drift Detector",
            "priority": "P1" if has_wearable else "P3",
            "status": "Pilot now" if has_wearable else "Backlog",
            "why_now": (
                "Wearable data is available and can surface early non-adherence to sleep/activity prescriptions."
                if has_wearable
                else "Await stable wearable stream before activating drift detection."
            ),
            "safety_model": "Detect and nudge only; clinician keeps final interpretation and clinical action.",
            "evidence_anchor": "Behavior-support with wearable context (e.g., Stanford GPTCoach prototype).",
        }
    )

    modules.append(
        {
            "module": "Visit Prep + Documentation Copilot",
            "priority": "P2",
            "status": "Activate now",
            "why_now": "Reduces charting burden and increases clinician time for decision-making.",
            "safety_model": "AI drafts only; clinician signs final note and plan.",
            "evidence_anchor": "JAMA Network Open 2024 virtual scribe outcomes (MGB cohort).",
        }
    )

    phases = [
        "Phase 1 (0-2 weeks): activate intervention opportunity finder + domain recommendation cards.",
        "Phase 2 (2-6 weeks): pilot wearable adherence/recovery drift detection.",
        "Phase 3 (ongoing): expand visit-prep copilot and monitor acceptance/override metrics.",
    ]

    return {
        "readiness_score_100": readiness,
        "readiness_label": (
            "High readiness" if readiness >= 75 else "Moderate readiness" if readiness >= 50 else "Early readiness"
        ),
        "modules": modules,
        "phases": phases,
        "governance_rules": [
            "Human-in-the-loop by default: no autonomous diagnosis or treatment decisions.",
            "Every recommendation must show rationale and source citation.",
            "Track acceptance/override and monitor for drift, bias, and alert fatigue.",
        ],
    }
