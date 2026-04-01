"""AI clinical decision support benchmarking and rollout planning."""

from __future__ import annotations

from config.ai_cds_catalog import AI_CDS_USE_CASES, INSTITUTION_EMR_BENCHMARKS


def get_institution_emr_benchmarks() -> list[dict]:
    return list(INSTITUTION_EMR_BENCHMARKS)


def get_ai_cds_use_cases() -> list[dict]:
    return list(AI_CDS_USE_CASES)


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


def build_ai_cds_rollout_plan(snapshot: dict) -> dict:
    """Build an evidence-backed, human-in-the-loop AI CDS rollout plan."""
    counts = snapshot.get("counts", {}) or {}
    readiness = _profile_completeness(snapshot)

    labs_critical = int(counts.get("labs_critical", 0) or 0)
    labs_flagged = int(counts.get("labs_flagged", 0) or 0)
    high_risk_scores = int(counts.get("organ_scores_high_risk", 0) or 0)
    has_cardio_signal = _cardio_metabolic_risk_signal(snapshot)

    modules = []

    modules.append(
        {
            "module": "Critical Event Triage Copilot",
            "priority": "P1" if labs_critical > 0 else "P2",
            "status": "Activate now" if labs_critical > 0 else "Design + dry-run",
            "why_now": (
                f"{labs_critical} critical lab alerts currently detected."
                if labs_critical > 0
                else "Build before first critical event to ensure response reliability."
            ),
            "safety_model": "Human clinician confirms all recommendations; closed-loop escalation log required.",
            "evidence_anchor": "TREWS sepsis implementation (Nature Medicine 2022, PMID 35864252).",
        }
    )

    modules.append(
        {
            "module": "Guideline Gap Finder (Risk -> Action)",
            "priority": "P1" if labs_flagged > 0 or high_risk_scores > 0 else "P2",
            "status": "Activate now" if labs_flagged > 0 or high_risk_scores > 0 else "Pilot",
            "why_now": (
                f"{labs_flagged} flagged labs and {high_risk_scores} high-risk organ scores need prioritized follow-up."
                if labs_flagged > 0 or high_risk_scores > 0
                else "Keeps prevention actions aligned with current risk trends."
            ),
            "safety_model": "Show rationale + cited source for each suggested action; never auto-place orders.",
            "evidence_anchor": "FDA CDS guidance + NICE ESF governance expectations.",
        }
    )

    modules.append(
        {
            "module": "Cardiometabolic Confirmatory-Test Trigger",
            "priority": "P1" if has_cardio_signal else "P3",
            "status": "Pilot now" if has_cardio_signal else "Backlog",
            "why_now": (
                "Cardiometabolic domain shows elevated risk signal; support early confirmation workflows."
                if has_cardio_signal
                else "Await stronger cardiometabolic risk signals before activating."
            ),
            "safety_model": "AI suggests tests only; clinician approves all follow-up imaging/labs.",
            "evidence_anchor": "Mayo AI-ECG pragmatic cluster trial (Health Serv Res 2021).",
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
        "Phase 1 (0-2 weeks): turn on triage + guideline gap finder with mandatory clinician confirmation.",
        "Phase 2 (2-6 weeks): pilot cardiometabolic confirmatory-test trigger in high-risk users only.",
        "Phase 3 (ongoing): expand documentation copilot with audit metrics (acceptance, override, safety events).",
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

