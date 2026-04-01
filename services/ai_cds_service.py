"""AI clinical decision support benchmarking and rollout planning."""

from __future__ import annotations

from datetime import date

from config.ai_cds_catalog import (
    AI_CDS_USE_CASES,
    GITHUB_LIFESTYLE_PATTERNS,
    INSTITUTION_EMR_BENCHMARKS,
    LIFESTYLE_EVIDENCE_BASE,
)

_PLAN_GOALS = {
    "healthy_longevity": "Healthy Longevity",
    "cardiometabolic_reset": "Cardiometabolic Reset",
    "gut_liver_support": "Gut & Liver Support",
    "brain_performance": "Brain Performance",
}

_PLAN_TEMPLATES = {
    "balanced": "Balanced (all pillars)",
    "nutrition_first": "Nutrition-first",
    "movement_first": "Movement-first",
    "recovery_first": "Recovery-first",
}


def get_precision_plan_goals() -> list[dict]:
    return [{"code": code, "label": label} for code, label in _PLAN_GOALS.items()]


def get_precision_plan_templates() -> list[dict]:
    return [{"code": code, "label": label} for code, label in _PLAN_TEMPLATES.items()]


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


def _sorted_domain_scores(snapshot: dict) -> list[dict]:
    rows = []
    for row in snapshot.get("organ_domain_categories", []) or []:
        score = row.get("score_10")
        if score is None:
            continue
        rows.append(
            {
                "domain_code": row.get("domain_code"),
                "domain_name": row.get("domain_name"),
                "score_10": float(score),
            }
        )
    rows.sort(key=lambda x: x["score_10"])
    return rows


def _goal_specific_actions(goal_code: str) -> dict[str, list[str]]:
    if goal_code == "cardiometabolic_reset":
        return {
            "Nutrition": [
                "Use a Mediterranean meal pattern: at least 2 meals/day centered on vegetables, legumes, fish, olive oil, and nuts.",
                "Aim for >=30 g/day fiber and reduce ultra-processed snacks to <=1 serving/day.",
            ],
            "Movement": [
                "Target 150-300 min/week moderate aerobic work + 2 resistance sessions/week.",
                "Set a daily step floor and increase by 500-1000 steps every 1-2 weeks if tolerated.",
            ],
            "Recovery": [
                "Set fixed wake time and consistent sleep window for 7 nights/week.",
                "Use morning daylight exposure and reduce late-evening stimulants.",
            ],
            "Adherence": [
                "Define one if-then fallback: if a planned session is missed, complete a 10-15 minute walk the same day.",
                "Review weekly trend metrics each Sunday and adjust only one variable per week.",
            ],
        }

    if goal_code == "gut_liver_support":
        return {
            "Nutrition": [
                "Reduce added sugars and refined carbohydrates; prioritize minimally processed foods.",
                "Use protein + high-fiber meals to support glycemic and liver-fat control.",
            ],
            "Movement": [
                "Schedule brisk walking most days and 2 strength sessions/week.",
                "Add post-meal 10 minute walks after largest meals.",
            ],
            "Recovery": [
                "Maintain regular sleep timing to support metabolic rhythm alignment.",
                "Track digestion symptom trends with food pattern changes weekly.",
            ],
            "Adherence": [
                "Build a weekly meal template (repeatable breakfast/lunch options).",
                "Use a one-page log for food quality, activity, and key symptoms.",
            ],
        }

    if goal_code == "brain_performance":
        return {
            "Nutrition": [
                "Use a neuroprotective dietary pattern rich in colorful plants, omega-3 sources, and low refined sugar.",
                "Hydration and meal timing should support sustained daytime cognition.",
            ],
            "Movement": [
                "Combine aerobic movement with 2 sessions/week of resistance training.",
                "Include brief movement breaks every 60-90 minutes during sedentary work.",
            ],
            "Recovery": [
                "Prioritize sleep consistency and maintain pre-sleep wind-down routine.",
                "Use stress-regulation practice (breathwork or mindfulness) at least 5 days/week.",
            ],
            "Adherence": [
                "Set one daily cognitive-energy anchor habit (same wake + first light + short walk).",
                "Use weekly reflection to adjust workload, recovery, and exercise dose.",
            ],
        }

    return {
        "Nutrition": [
            "Use a whole-food, plant-forward pattern with sufficient protein and fiber.",
            "Keep food quality high on weekdays and use planned flexibility on weekends.",
        ],
        "Movement": [
            "Accumulate at least 150 min/week moderate activity plus 2 strength sessions.",
            "Increase volume progressively only when recovery metrics remain stable.",
        ],
        "Recovery": [
            "Protect sleep regularity and reduce late-evening stimulation.",
            "Use simple stress-management micro-practices daily.",
        ],
        "Adherence": [
            "Set one non-negotiable minimum action for each day.",
            "Review trend metrics weekly and tune one behavior at a time.",
        ],
    }


def _ordered_tracks_for_template(template_code: str, tracks: list[dict]) -> list[dict]:
    if template_code == "nutrition_first":
        order = ["Nutrition", "Movement", "Recovery", "Adherence"]
    elif template_code == "movement_first":
        order = ["Movement", "Recovery", "Nutrition", "Adherence"]
    elif template_code == "recovery_first":
        order = ["Recovery", "Movement", "Nutrition", "Adherence"]
    else:
        order = ["Nutrition", "Movement", "Recovery", "Adherence"]

    rank = {name: idx for idx, name in enumerate(order)}
    out = list(tracks)
    out.sort(key=lambda row: rank.get(row.get("title"), 99))
    return out


def build_precision_plan(snapshot: dict, goal_code: str, template_code: str) -> dict:
    """Build a NU-inspired precision plan from current user snapshot.

    Note: workflow inspired by NU's public product framing (goal-based plans + data integration),
    but content is generated from this app's own logic and evidence catalog.
    """
    goal_code = goal_code if goal_code in _PLAN_GOALS else "healthy_longevity"
    template_code = template_code if template_code in _PLAN_TEMPLATES else "balanced"

    domain_rows = _sorted_domain_scores(snapshot)
    priority_domains = [row["domain_name"] for row in domain_rows[:2]]
    if not priority_domains:
        priority_domains = ["Heart & Metabolism", "Brain Health"]

    actions = _goal_specific_actions(goal_code)
    tracks = []
    for title, action_rows in actions.items():
        tracks.append(
            {
                "title": title,
                "actions": action_rows,
            }
        )
    tracks = _ordered_tracks_for_template(template_code, tracks)

    checkpoints = [
        "Daily: complete minimum action for the highest-priority track.",
        "Weekly: review wearable readiness/resilience and training consistency.",
        "Bi-weekly: review symptoms, recovery quality, and adherence barriers.",
        "Monthly: review flagged labs and organ-domain trend movement.",
    ]

    retest_windows = [
        "Weeks 4-6: reassess behavior adherence and wearable trend shift.",
        "Weeks 8-12: repeat key labs aligned with active risk domains.",
        "Quarterly: recompute organ and wearable composites and refresh plan.",
    ]

    evidence_topics = [
        "Physical activity dose-response and prevention",
        "Primary prevention lifestyle and risk-factor control",
    ]
    if goal_code == "cardiometabolic_reset":
        evidence_topics.extend(
            [
                "Mediterranean diet for primary CVD prevention",
                "Blood pressure management with non-pharmacologic interventions",
                "Prediabetes/T2D prevention with lifestyle change",
            ]
        )
    elif goal_code == "gut_liver_support":
        evidence_topics.append("NAFLD/MASLD lifestyle-first management")
    elif goal_code == "brain_performance":
        evidence_topics.append("Primary prevention lifestyle and risk-factor control")

    # Preserve order while deduplicating.
    seen: set[str] = set()
    ordered_topics: list[str] = []
    for topic in evidence_topics:
        if topic in seen:
            continue
        seen.add(topic)
        ordered_topics.append(topic)

    return {
        "generated_on": date.today().isoformat(),
        "goal_code": goal_code,
        "goal_label": _PLAN_GOALS[goal_code],
        "template_code": template_code,
        "template_label": _PLAN_TEMPLATES[template_code],
        "horizon_weeks": 8,
        "priority_domains": priority_domains,
        "tracks": tracks,
        "checkpoints": checkpoints,
        "retest_windows": retest_windows,
        "evidence_topics": ordered_topics,
        "disclaimer": (
            "Lifestyle support plan for coaching and prevention. "
            "It does not replace clinician diagnosis or treatment decisions."
        ),
    }


def build_precision_plan_markdown(plan: dict, evidence_by_topic: dict[str, dict]) -> str:
    """Render precision plan as markdown for export/download."""
    lines: list[str] = []
    lines.append(f"# Precision Plan - {plan.get('goal_label', 'Lifestyle Goal')}")
    lines.append("")
    lines.append(f"- Generated on: {plan.get('generated_on')}")
    lines.append(f"- Template: {plan.get('template_label')}")
    lines.append(f"- Horizon: {plan.get('horizon_weeks', 8)} weeks")
    lines.append("")
    lines.append("## Priority Domains")
    for domain in plan.get("priority_domains", []):
        lines.append(f"- {domain}")
    lines.append("")
    lines.append("## Action Tracks")
    for track in plan.get("tracks", []):
        lines.append(f"### {track.get('title')}")
        for action in track.get("actions", []):
            lines.append(f"- {action}")
        lines.append("")
    lines.append("## Checkpoints")
    for row in plan.get("checkpoints", []):
        lines.append(f"- {row}")
    lines.append("")
    lines.append("## Retest & Review Windows")
    for row in plan.get("retest_windows", []):
        lines.append(f"- {row}")
    lines.append("")
    lines.append("## Evidence Links")
    for topic in plan.get("evidence_topics", []):
        ev = evidence_by_topic.get(topic, {})
        title = ev.get("evidence", "Source")
        link = ev.get("link", "")
        lines.append(f"- {topic}: {title} ({link})")
    lines.append("")
    lines.append("## Clinical Note")
    lines.append(plan.get("disclaimer", ""))
    lines.append("")
    return "\n".join(lines)


def build_precision_plan_weekly_schedule(plan: dict) -> list[dict]:
    """Generate a simple 8-week progression schedule from precision plan tracks."""
    tracks = plan.get("tracks", []) or []
    if not tracks:
        return []

    primary_track = tracks[0].get("title", "Core")
    secondary_track = tracks[1].get("title", tracks[0].get("title", "Core")) if len(tracks) > 1 else primary_track
    tertiary_track = tracks[2].get("title", secondary_track) if len(tracks) > 2 else secondary_track

    weeks = [
        {
            "week": 1,
            "phase": "Baseline & Setup",
            "focus": f"Define minimum viable routine for {primary_track}.",
            "checkpoint": "Complete at least 4 of 7 planned daily actions.",
        },
        {
            "week": 2,
            "phase": "Consistency",
            "focus": f"Stabilize schedule and adherence in {primary_track}.",
            "checkpoint": "Achieve 70% adherence and log barriers.",
        },
        {
            "week": 3,
            "phase": "Progressive Build",
            "focus": f"Increase dose gradually and add {secondary_track} support block.",
            "checkpoint": "No abrupt load spikes; maintain recovery quality.",
        },
        {
            "week": 4,
            "phase": "First Review",
            "focus": "Review trends, simplify what is failing, reinforce what is working.",
            "checkpoint": "Reassess readiness/resilience and adjust one variable only.",
        },
        {
            "week": 5,
            "phase": "Optimization",
            "focus": f"Tune quality and execution in {secondary_track} and {tertiary_track}.",
            "checkpoint": "Keep adherence above week-2 baseline.",
        },
        {
            "week": 6,
            "phase": "Resilience",
            "focus": "Practice fallback strategies under real-life schedule stress.",
            "checkpoint": "Use if-then fallback plan at least twice when needed.",
        },
        {
            "week": 7,
            "phase": "Consolidation",
            "focus": "Reduce friction and lock in sustainable routines.",
            "checkpoint": "Demonstrate stable weekly rhythm with low missed sessions.",
        },
        {
            "week": 8,
            "phase": "Reassessment",
            "focus": "Summarize gains, refresh priorities, and design next 8-week cycle.",
            "checkpoint": "Review labs/scores and publish next-cycle plan.",
        },
    ]
    return weeks


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
