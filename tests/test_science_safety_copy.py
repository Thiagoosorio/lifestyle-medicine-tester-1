import json

import config.evidence_data as evidence_data_module
from config.evidence import RESEARCH_DOMAINS
from config.evidence_data import EVIDENCE_LIBRARY
from config.organ_scores_data import ORGAN_SCORE_DEFINITIONS
from config.prompts import BASE_SYSTEM_PROMPT, GPTCOACH_PHYSICAL_ACTIVITY_PROMPT
from services.hpr_service import build_anchor_rows, get_hpr_consistency_warnings


def test_every_evidence_domain_is_registered():
    unknown = {
        entry.get("domain")
        for entry in EVIDENCE_LIBRARY
        if entry.get("domain") and entry.get("domain") not in RESEARCH_DOMAINS
    }
    assert unknown == set()


def test_research_library_header_no_longer_claims_global_verification():
    assert "All 70 entries verified" not in (evidence_data_module.__doc__ or "")


def test_cha2ds2_vasc_legacy_copy_is_clinician_review_not_treatment_command():
    definition = next(row for row in ORGAN_SCORE_DEFINITIONS if row["code"] == "cha2ds2_vasc")
    text = definition["description"] + " " + json.dumps(definition["interpretation"])
    forbidden = ["anticoagulation recommended", "anticoagulation essential", "no anticoagulation needed"]
    assert all(term not in text.lower() for term in forbidden)
    assert "clinician review" in text.lower()


def test_ai_coach_prompts_include_crisis_and_emergency_guardrails():
    prompt = BASE_SYSTEM_PROMPT.lower()
    assert "emergency" in prompt
    assert "suicidal" in prompt
    assert "not medical care" in prompt
    assert "not medical treatment" in GPTCOACH_PHYSICAL_ACTIVITY_PROMPT.lower()


def test_hpr_anchor_table_avoids_score_label_and_warns_on_known_conflicts():
    rows = build_anchor_rows({"min": 1, "expected": 2, "high": 3, "elite": 4})
    assert "Anchor index" in rows[0]
    assert "Inferred score" not in rows[0]
    warnings = get_hpr_consistency_warnings()
    assert any("hidden HPR" in row["Warning"] for row in warnings)
    assert any("Dual-task cost" in row["Area"] for row in warnings)
