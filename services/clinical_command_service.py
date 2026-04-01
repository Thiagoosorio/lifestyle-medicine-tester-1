"""Clinical command-center snapshot service.

Builds a physician-style summary from structured and computed app data:
- patient profile
- confirmed diagnoses
- confirmed interventions
- labs requiring attention
- organ score risk summary
- key objective tests (DEXA + clinician-entered tests + wearable)
- evidence trace (validated Q1/Q2 + guideline organizations)
- priority problem list with action deadlines
- longitudinal clinical timeline
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import re

from models.user import get_user
from models.clinical_profile import get_profile, get_age, get_bmi
from models.clinical_registry import (
    list_diagnoses,
    list_interventions,
    list_test_results,
)
from services.biomarker_service import (
    classify_result,
    get_lab_dates,
    get_latest_results,
    get_results_by_date,
)
from services.protocol_service import get_user_protocols
from services.exercise_prescription_service import get_saved_program
from services.cycling_service import get_cycling_profile, get_active_plan
from services.body_metrics_service import get_latest_dexa, get_latest_metrics
from services.organ_score_service import get_latest_computed_scores
from services.critical_lab_policy_service import build_critical_communication_plan

try:
    from services.organ_score_service import compute_overall_organ_score
except Exception:  # pragma: no cover - backward-compatible for older deploys
    compute_overall_organ_score = None

try:
    from services.wearable_wheel_service import compute_wearable_wheel
except Exception:  # pragma: no cover - optional dependency in older deploys
    compute_wearable_wheel = None


_LAB_CLASS_SEVERITY_RANK = {
    "critical_high": 0,
    "critical_low": 0,
    "high": 1,
    "low": 1,
}

_PROBLEM_SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "moderate": 2,
    "low": 3,
}

_EVIDENCE_ORG_TERMS = (
    "who",
    "cdc",
    "nih",
    "aha",
    "acc",
    "ada",
    "uspstf",
    "nice",
    "esc",
    "kdigo",
    "aasld",
    "easl",
    "acg",
)

_DOMAIN_META = {
    "heart_metabolism": {
        "name": "Heart & Metabolism",
        "description": "Cardiovascular and metabolic validated formulas",
        "expected_organs": ("cardiovascular", "metabolic"),
    },
    "muscle_bones": {
        "name": "Muscle & Bones",
        "description": "Body composition and bone-health signals",
        "expected_organs": (),
    },
    "gut_digestion": {
        "name": "Gut & Digestion",
        "description": "Liver-linked and digestive-system proxies",
        "expected_organs": ("liver",),
    },
    "brain_health": {
        "name": "Brain Health",
        "description": "Neurovascular and cognitive-risk formulas",
        "expected_organs": ("neurological",),
    },
    "system_wide": {
        "name": "System Wide (incl. Hormone Health)",
        "description": "Kidney, inflammatory, hematologic, thyroid, biological-age systems",
        "expected_organs": ("kidney", "inflammatory", "hematologic", "thyroid", "biological_age"),
    },
}


def _fmt_range(low, high, unit) -> str:
    unit_str = unit or ""
    if low is not None and high is not None:
        return f"{low}-{high} {unit_str}".strip()
    if low is not None:
        return f">={low} {unit_str}".strip()
    if high is not None:
        return f"<={high} {unit_str}".strip()
    return "N/A"


def _parse_date_like(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(text).lower())
        if len(token) >= 4
    }


def _classify_source_class(citation_text: str | None) -> str:
    text = (citation_text or "").lower()
    if any(term in text for term in _EVIDENCE_ORG_TERMS):
        return "Guideline / National Organization"
    if "q1" in text:
        return "Q1 Journal"
    if "q2" in text:
        return "Q2 Journal"
    return "Unclassified"


def _classify_source_rank(source_class: str) -> int:
    if source_class == "Guideline / National Organization":
        return 0
    if source_class == "Q1 Journal":
        return 1
    if source_class == "Q2 Journal":
        return 2
    return 9


def _build_evidence_trace(organ_scores: list[dict]) -> dict:
    """Build evidence trace constrained to validated + Q1/Q2 + guideline orgs."""
    allowed: list[dict] = []
    excluded: list[dict] = []
    seen_codes: set[str] = set()

    for score in organ_scores:
        code = score.get("code")
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)

        source_class = _classify_source_class(score.get("citation_text"))
        pmid = score.get("citation_pmid")
        tier = str(score.get("tier", "")).lower()

        allowed_source = source_class in {
            "Guideline / National Organization",
            "Q1 Journal",
            "Q2 Journal",
        }

        if tier == "validated" and pmid and allowed_source:
            allowed.append(
                {
                    "code": code,
                    "score_name": score.get("name"),
                    "organ_system": score.get("organ_system"),
                    "source_class": source_class,
                    "tier": score.get("tier"),
                    "pmid": str(pmid),
                    "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "citation_text": score.get("citation_text"),
                }
            )
        else:
            if tier != "validated":
                reason = "Excluded: non-validated score tier"
            elif not pmid:
                reason = "Excluded: missing PMID"
            else:
                reason = "Excluded: source not tagged Q1/Q2 or guideline organization"
            excluded.append(
                {
                    "code": code,
                    "score_name": score.get("name"),
                    "tier": score.get("tier"),
                    "source_class": source_class,
                    "reason": reason,
                }
            )

    allowed.sort(
        key=lambda row: (
            _classify_source_rank(row["source_class"]),
            str(row.get("score_name", "")),
        )
    )

    return {
        "policy": "Only validated scores with PMID and Q1/Q2 or guideline-organization source tags are surfaced.",
        "allowed_sources": allowed,
        "excluded_sources": excluded,
        "counts": {
            "allowed": len(allowed),
            "excluded": len(excluded),
            "total_unique_scores": len(seen_codes),
        },
    }


def _build_organ_domain_categories(overall_organ: dict | None, latest_dexa: dict | None) -> list[dict]:
    """Map organ-system composites into the requested 5 clinical domains."""
    organ_rows = (overall_organ or {}).get("organ_breakdown", [])
    by_organ = {row.get("organ_system"): row for row in organ_rows}
    categories: list[dict] = []

    for code, meta in _DOMAIN_META.items():
        expected = list(meta.get("expected_organs", ()))
        covered = [by_organ[o] for o in expected if o in by_organ]

        if covered:
            avg_score_10 = round(sum(r.get("score_10", 0) for r in covered) / len(covered), 1)
            elevated_count = sum(int(r.get("elevated_or_worse") or 0) for r in covered)
            avg_conf = sum(float(r.get("confidence_0_1", 0)) for r in covered) / len(covered)
            confidence_pct = int(round(avg_conf * 100))
        else:
            avg_score_10 = None
            elevated_count = 0
            confidence_pct = 0

        if expected:
            coverage_pct = int(round((len(covered) / len(expected)) * 100))
        else:
            coverage_pct = 0

        note = ""
        if code == "muscle_bones":
            if latest_dexa:
                note = "DEXA present; no validated organ-formula composite is mapped yet."
            else:
                note = "Add DEXA/body-composition data to enrich this domain."
        elif not covered:
            note = "No mapped validated formulas computed yet."

        categories.append(
            {
                "domain_code": code,
                "domain_name": meta["name"],
                "description": meta["description"],
                "score_10": avg_score_10,
                "coverage_pct": coverage_pct,
                "confidence_pct": confidence_pct,
                "elevated_or_worse": elevated_count,
                "systems_covered": [r.get("name") for r in covered],
                "systems_expected": expected,
                "note": note,
            }
        )

    return categories


def _diagnosis_has_intervention_link(diagnosis_name: str, interventions_active: list[dict]) -> bool:
    diag_tokens = _tokenize(diagnosis_name)
    if not diag_tokens:
        return False

    for iv in interventions_active:
        combined = " ".join(
            [
                str(iv.get("name", "")),
                str(iv.get("notes", "")),
                str(iv.get("dose", "")),
                str(iv.get("schedule", "")),
            ]
        )
        if not combined.strip():
            continue
        iv_tokens = _tokenize(combined)
        if diag_tokens & iv_tokens:
            return True
    return False


def _build_priority_problem_list(
    diagnoses_active: list[dict],
    interventions_active: list[dict],
    labs_attention: dict,
    organ_high_risk_scores: list[dict],
    evidence_trace: dict,
) -> list[dict]:
    """Create sorted prevention-first priority list with action windows."""
    items: list[dict] = []
    today = date.today()
    evidence_by_code = {
        row["code"]: row
        for row in evidence_trace.get("allowed_sources", [])
    }

    for row in labs_attention.get("critical", []):
        due_days = 7
        items.append(
            {
                "problem_type": "Lab Critical",
                "problem": f"{row.get('name')}: {row.get('classification')}",
                "severity": "critical",
                "recommended_action": "Repeat/confirm test and review urgent clinical context.",
                "due_in_days": due_days,
                "target_date": (today + timedelta(days=due_days)).isoformat(),
                "evidence_source": "Lab reference threshold",
            }
        )

    for row in labs_attention.get("abnormal", []):
        due_days = 14
        items.append(
            {
                "problem_type": "Lab Abnormal",
                "problem": f"{row.get('name')}: {row.get('classification')}",
                "severity": "high",
                "recommended_action": "Address modifiable drivers and schedule near-term recheck.",
                "due_in_days": due_days,
                "target_date": (today + timedelta(days=due_days)).isoformat(),
                "evidence_source": "Lab reference threshold",
            }
        )

    for score in organ_high_risk_scores:
        severity = "critical" if score.get("severity") == "critical" else "high"
        due_days = 7 if severity == "critical" else 14
        src = evidence_by_code.get(score.get("code"))
        src_label = (
            f"{src.get('source_class')} (PMID {src.get('pmid')})"
            if src
            else "Validated score source not yet classified"
        )
        items.append(
            {
                "problem_type": "Organ Score Risk",
                "problem": f"{score.get('name')}: {score.get('label')}",
                "severity": severity,
                "recommended_action": "Review contributing biomarkers and update prevention plan.",
                "due_in_days": due_days,
                "target_date": (today + timedelta(days=due_days)).isoformat(),
                "evidence_source": src_label,
            }
        )

    unresolved = []
    for dx in diagnoses_active:
        if not _diagnosis_has_intervention_link(dx.get("diagnosis_name", ""), interventions_active):
            unresolved.append(dx)

    for dx in unresolved:
        due_days = 30
        items.append(
            {
                "problem_type": "Diagnosis Follow-up",
                "problem": f"{dx.get('diagnosis_name')} has no linked active intervention",
                "severity": "moderate",
                "recommended_action": "Confirm whether active treatment, monitoring, or watchful waiting is intended.",
                "due_in_days": due_days,
                "target_date": (today + timedelta(days=due_days)).isoformat(),
                "evidence_source": "Clinical workflow safety check",
            }
        )

    items.sort(
        key=lambda row: (
            _PROBLEM_SEVERITY_RANK.get(row["severity"], 9),
            int(row.get("due_in_days") or 999),
            row.get("problem", ""),
        )
    )

    for idx, row in enumerate(items, start=1):
        row["priority_rank"] = idx

    return items[:40]


def _build_clinical_timeline(
    user_id: int,
    diagnoses_all: list[dict],
    interventions_all: list[dict],
    tests_all: list[dict],
    organ_scores: list[dict],
) -> list[dict]:
    """Build a unified timeline for clinical reasoning and follow-up."""
    events: list[dict] = []

    def add_event(
        when: str | None,
        event_type: str,
        title: str,
        details: str,
        severity: str = "info",
        source: str = "",
    ) -> None:
        dt = _parse_date_like(when)
        if not dt:
            return
        events.append(
            {
                "date": dt.date().isoformat(),
                "date_time": dt.isoformat(sep=" ", timespec="seconds"),
                "event_type": event_type,
                "title": title,
                "details": details,
                "severity": severity,
                "source": source,
            }
        )

    for dx in diagnoses_all:
        when = dx.get("confirmed_date") or dx.get("updated_at") or dx.get("created_at")
        add_event(
            when,
            "Diagnosis",
            str(dx.get("diagnosis_name") or "Diagnosis"),
            f"Status: {dx.get('status')}",
            severity="high" if dx.get("status") == "active" else "info",
            source="clinical_diagnoses",
        )

    for iv in interventions_all:
        when = iv.get("start_date") or iv.get("updated_at") or iv.get("created_at")
        add_event(
            when,
            "Intervention",
            str(iv.get("name") or "Intervention"),
            f"{iv.get('intervention_type')} | Status: {iv.get('status')}",
            severity="info",
            source="clinical_interventions",
        )
        if iv.get("end_date"):
            add_event(
                iv.get("end_date"),
                "Intervention End",
                str(iv.get("name") or "Intervention"),
                f"Status: {iv.get('status')}",
                severity="info",
                source="clinical_interventions",
            )

    for test in tests_all:
        when = test.get("test_date") or test.get("updated_at") or test.get("created_at")
        add_event(
            when,
            "Test / Imaging",
            str(test.get("test_type") or "Test"),
            str(test.get("summary") or test.get("risk_flag") or "Recorded"),
            severity="high" if test.get("risk_flag") in {"high", "critical"} else "info",
            source="clinical_test_results",
        )

    for lab_date in get_lab_dates(user_id)[:12]:
        panel = get_results_by_date(user_id, lab_date)
        flagged = [
            row
            for row in panel
            if classify_result(row.get("value"), row) not in {"in_range", "unknown"}
        ]
        add_event(
            lab_date,
            "Lab Panel",
            "Lab panel recorded",
            f"{len(panel)} markers, {len(flagged)} flagged",
            severity="high" if flagged else "info",
            source="biomarker_results",
        )

    score_batches: dict[str, dict] = {}
    for row in organ_scores:
        when = row.get("computed_at") or row.get("lab_date")
        dt = _parse_date_like(when)
        if not dt:
            continue
        key = dt.isoformat(sep=" ", timespec="seconds")
        batch = score_batches.setdefault(
            key,
            {"total": 0, "high_risk": 0},
        )
        batch["total"] += 1
        if row.get("severity") in {"high", "critical"}:
            batch["high_risk"] += 1

    for when, batch in score_batches.items():
        add_event(
            when,
            "Organ Score Batch",
            "Organ scores recomputed",
            f"{batch['total']} computed, {batch['high_risk']} high-risk",
            severity="high" if batch["high_risk"] else "info",
            source="organ_score_results",
        )

    events.sort(
        key=lambda row: (
            _parse_date_like(row["date_time"]) or datetime.min,
            row.get("title", ""),
        ),
        reverse=True,
    )
    return events[:150]


def get_labs_requiring_attention(user_id: int) -> dict:
    """Return latest lab markers that are outside lab reference ranges."""
    latest = get_latest_results(user_id)
    flagged = []
    for row in latest:
        value = row.get("value")
        cls = classify_result(value, row)
        if cls in {"in_range", "unknown"}:
            continue
        flagged.append(
            {
                "code": row.get("code"),
                "name": row.get("name"),
                "value": value,
                "unit": row.get("unit"),
                "classification": cls,
                "lab_date": row.get("lab_date"),
                "standard_range": _fmt_range(row.get("standard_low"), row.get("standard_high"), row.get("unit")),
                "critical_low": row.get("critical_low"),
                "critical_high": row.get("critical_high"),
            }
        )

    flagged.sort(key=lambda r: (_LAB_CLASS_SEVERITY_RANK.get(r["classification"], 9), r["name"] or ""))
    return {
        "critical": [r for r in flagged if r["classification"].startswith("critical")],
        "abnormal": [r for r in flagged if r["classification"] in {"high", "low"}],
        "all": flagged,
    }


def _build_intervention_rollup(user_id: int) -> list[dict]:
    interventions = list_interventions(user_id, active_only=True)

    # Lifestyle protocols actively adopted by the user.
    for proto in get_user_protocols(user_id):
        interventions.append(
            {
                "id": f"protocol_{proto['protocol_id']}",
                "intervention_type": "lifestyle",
                "name": proto.get("name"),
                "dose": None,
                "schedule": proto.get("timing") or proto.get("frequency"),
                "start_date": proto.get("started_at"),
                "status": "active",
                "prescriber": None,
                "notes": "From Daily Protocols",
                "source": "protocols",
            }
        )

    # Saved training programs are shown as interventions.
    saved_program = get_saved_program(user_id)
    if saved_program:
        interventions.append(
            {
                "id": f"training_strength_{saved_program.get('_db_id', 'latest')}",
                "intervention_type": "training",
                "name": "Strength Program",
                "dose": saved_program.get("goal"),
                "schedule": saved_program.get("schedule_info", {}).get("label"),
                "start_date": saved_program.get("_created_at"),
                "status": "active",
                "prescriber": None,
                "notes": "From Exercise Prescription",
                "source": "exercise_prescription",
            }
        )

    cycling_profile = get_cycling_profile(user_id)
    if cycling_profile:
        interventions.append(
            {
                "id": f"training_cycling_{cycling_profile.get('id', 'latest')}",
                "intervention_type": "training",
                "name": "Cycling Plan",
                "dose": f"FTP {cycling_profile.get('ftp_watts')} W",
                "schedule": cycling_profile.get("athlete_type"),
                "start_date": cycling_profile.get("updated_at"),
                "status": "active",
                "prescriber": None,
                "notes": "From Cycling Training",
                "source": "cycling",
            }
        )
    else:
        active_cycling_plan = get_active_plan(user_id)
        if active_cycling_plan:
            interventions.append(
                {
                    "id": f"training_cycling_{active_cycling_plan.get('id', 'latest')}",
                    "intervention_type": "training",
                    "name": "Cycling Plan",
                    "dose": active_cycling_plan.get("phase"),
                    "schedule": f"{active_cycling_plan.get('days_per_week', 0)} days/week",
                    "start_date": active_cycling_plan.get("start_date"),
                    "status": "active",
                    "prescriber": None,
                    "notes": "From Cycling Training",
                    "source": "cycling",
                }
            )

    return interventions


def build_clinical_snapshot(user_id: int) -> dict:
    """Build one structured physician-style summary payload."""
    user = get_user(user_id) or {}
    profile = get_profile(user_id) or {}
    age = get_age(user_id)
    bmi = get_bmi(user_id)
    latest_body = get_latest_metrics(user_id)
    latest_dexa = get_latest_dexa(user_id)

    diagnoses_active = list_diagnoses(user_id, active_only=True)
    diagnoses_all = list_diagnoses(user_id, active_only=False)
    interventions_active = _build_intervention_rollup(user_id)
    interventions_all = list_interventions(user_id, active_only=False)
    lab_attention = get_labs_requiring_attention(user_id)
    test_results = list_test_results(user_id, confirmed_only=False, limit=120)
    organ_scores = get_latest_computed_scores(user_id)
    high_risk_organs = [
        score for score in organ_scores if score.get("severity") in {"high", "critical"}
    ]

    overall_organ = None
    if compute_overall_organ_score:
        try:
            overall_organ = compute_overall_organ_score(user_id)
        except Exception:
            overall_organ = None

    wearable = None
    if compute_wearable_wheel:
        try:
            wearable = compute_wearable_wheel(user_id)
        except Exception:
            wearable = None

    profile_summary = {
        "display_name": user.get("display_name") or user.get("username") or "Patient",
        "email": user.get("email"),
        "age": age,
        "sex": profile.get("sex"),
        "bmi": bmi,
        "weight_kg": (latest_body or {}).get("weight_kg") or profile.get("weight_kg"),
        "height_cm": (latest_body or {}).get("height_cm") or profile.get("height_cm"),
        "systolic_bp": profile.get("systolic_bp"),
        "diastolic_bp": profile.get("diastolic_bp"),
        "smoking_status": profile.get("smoking_status"),
        "diabetes_status": profile.get("diabetes_status"),
    }

    key_tests = []
    if latest_dexa:
        key_tests.append(
            {
                "test_type": "DEXA",
                "test_date": latest_dexa.get("scan_date"),
                "summary": (
                    f"Body fat {latest_dexa.get('total_fat_pct')}%, "
                    f"lean mass {round((latest_dexa.get('lean_mass_g') or 0) / 1000, 1)} kg, "
                    f"BMD {latest_dexa.get('bmd_g_cm2')}"
                ),
                "risk_flag": "unknown",
                "source": "dexa_scans",
            }
        )

    preferred_types = {"CPET", "KINEMO", "CAROTID ULTRASOUND", "CAROTID", "ULTRASOUND"}
    for test in test_results:
        t_type = (test.get("test_type") or "").upper()
        if t_type in preferred_types and test.get("status") == "confirmed":
            key_tests.append(
                {
                    "test_type": test.get("test_type"),
                    "test_date": test.get("test_date"),
                    "summary": test.get("summary"),
                    "risk_flag": test.get("risk_flag"),
                    "source": "clinical_test_results",
                }
            )

    evidence_trace = _build_evidence_trace(organ_scores)
    critical_lab_communication = build_critical_communication_plan(lab_attention["critical"])
    domain_categories = _build_organ_domain_categories(overall_organ, latest_dexa)
    priority_list = _build_priority_problem_list(
        diagnoses_active=diagnoses_active,
        interventions_active=interventions_active,
        labs_attention=lab_attention,
        organ_high_risk_scores=high_risk_organs,
        evidence_trace=evidence_trace,
    )
    timeline = _build_clinical_timeline(
        user_id=user_id,
        diagnoses_all=diagnoses_all,
        interventions_all=interventions_all,
        tests_all=test_results,
        organ_scores=organ_scores,
    )

    return {
        "patient": profile_summary,
        "diagnoses_active": diagnoses_active,
        "diagnoses_all": diagnoses_all,
        "interventions_active": interventions_active,
        "interventions_all": interventions_all,
        "labs_attention": lab_attention,
        "critical_lab_communication": critical_lab_communication,
        "organ_overall": overall_organ,
        "organ_high_risk_count": len(high_risk_organs),
        "organ_high_risk_scores": high_risk_organs,
        "organ_domain_categories": domain_categories,
        "wearable": wearable,
        "key_tests": key_tests,
        "test_results": test_results,
        "priority_problem_list": priority_list,
        "timeline": timeline,
        "evidence_trace": evidence_trace,
        "counts": {
            "diagnoses_active": len(diagnoses_active),
            "interventions_active": len(interventions_active),
            "labs_flagged": len(lab_attention["all"]),
            "labs_critical": len(lab_attention["critical"]),
            "labs_abnormal": len(lab_attention["abnormal"]),
            "tests_total": len(test_results),
            "organ_scores_total": len(organ_scores),
            "organ_scores_high_risk": len(high_risk_organs),
            "priority_open": len(priority_list),
            "timeline_events": len(timeline),
            "evidence_allowed": evidence_trace["counts"]["allowed"],
            "evidence_excluded": evidence_trace["counts"]["excluded"],
        },
    }
