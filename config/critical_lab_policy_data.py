"""Critical laboratory value communication policy metadata.

Scope:
- Defines operational communication rules for critical lab findings.
- Supports urgent workflow in a prevention-focused app.

Notes:
- This policy layer is workflow guidance, not diagnosis.
- Threshold ownership remains in biomarker definitions (`critical_low/high`).
"""

CRITICAL_COMMUNICATION_POLICY = {
    "policy_name": "Critical Laboratory Results - Urgent Communication Policy",
    "version_date": "2026-04-01",
    "default_notify_within_minutes": 60,
    "default_escalate_after_minutes": 30,
    "read_back_required": True,
    "documentation_required": True,
    "documentation_fields": [
        "date_time_detected",
        "date_time_notified",
        "recipient_name",
        "communication_channel",
        "read_back_confirmed",
        "action_plan",
    ],
    "workflow_steps": [
        "Verify result integrity (sample identity, unit, obvious pre-analytical issues).",
        "Notify responsible clinician within the configured time window.",
        "Require read-back confirmation of marker, value, and units.",
        "Escalate if no acknowledgment within escalation window.",
        "Document contact trail and immediate action plan.",
    ],
    "disclaimer": (
        "Critical findings require clinician-led triage. This app supports communication workflow "
        "and does not replace emergency services or direct medical judgment."
    ),
    "evidence_sources": [
        {
            "title": "National Patient Safety Goals - NPSG.02.03.01",
            "year": 2024,
            "source_type": "National organization standard",
            "link": "https://www.jointcommission.org/standards/-/media/165e86f799754481bdd1d554e92b8581.ashx",
        },
        {
            "title": "CLSI GP47: Management of Critical- and Significant-Risk Results",
            "year": 2015,
            "source_type": "Laboratory guideline",
            "link": "https://clsi.org/shop/standards/gp47/",
        },
        {
            "title": "Harmonization of critical result management in laboratory medicine",
            "year": 2014,
            "source_type": "Consensus review",
            "link": "https://pubmed.ncbi.nlm.nih.gov/24246790/",
        },
    ],
}


# Per-analyte communication windows for clearly acute-risk patterns.
# All unspecified markers fall back to the default policy timings.
CRITICAL_ANALYTE_PROTOCOL = {
    "potassium": {
        "urgency_level": "immediate",
        "notify_within_minutes": 15,
        "escalate_after_minutes": 10,
        "recommended_action": "Immediate clinician callback; confirm ECG/arrhythmia risk triage.",
    },
    "sodium": {
        "urgency_level": "immediate",
        "notify_within_minutes": 15,
        "escalate_after_minutes": 10,
        "recommended_action": "Immediate clinician callback; assess acute neurologic risk and volume status.",
    },
    "calcium": {
        "urgency_level": "immediate",
        "notify_within_minutes": 15,
        "escalate_after_minutes": 10,
        "recommended_action": "Immediate clinician callback; triage for neuromuscular/cardiac instability.",
    },
    "hemoglobin": {
        "urgency_level": "urgent",
        "notify_within_minutes": 30,
        "escalate_after_minutes": 15,
        "recommended_action": "Urgent clinician callback; assess bleeding/hemodynamic context.",
    },
    "platelets": {
        "urgency_level": "urgent",
        "notify_within_minutes": 30,
        "escalate_after_minutes": 15,
        "recommended_action": "Urgent clinician callback; assess bleeding/thrombotic risk context.",
    },
}


DEFAULT_CRITICAL_PROTOCOL = {
    "urgency_level": "urgent_review",
    "notify_within_minutes": CRITICAL_COMMUNICATION_POLICY["default_notify_within_minutes"],
    "escalate_after_minutes": CRITICAL_COMMUNICATION_POLICY["default_escalate_after_minutes"],
    "recommended_action": "Notify responsible clinician promptly and document read-back.",
}

