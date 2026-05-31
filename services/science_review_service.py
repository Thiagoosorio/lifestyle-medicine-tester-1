"""Scientific governance helpers for score, evidence, and HPR review.

This module does not change clinical formulas. It inventories the current
scientific assets so reviewers can see what is validated, research-only,
stale, missing provenance, or imported from an external model.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from typing import Any

from config.evidence_data import EVIDENCE_LIBRARY
from config.evidence import RESEARCH_DOMAINS
from config.organ_scores_data import ORGAN_SCORE_DEFINITIONS
from config.score_classification import get_classification
from services.hpr_service import (
    SCORE_FORMULA_CAVEAT,
    get_categories,
    get_evidence_audit,
    get_hpr_consistency_warnings,
    get_protocol_rows,
)


FRESH_YEARS = 2
MONITOR_YEARS = 4
STALE_YEARS = 6


def _parse_interpretation(definition: dict[str, Any]) -> dict[str, Any]:
    raw = definition.get("interpretation")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return {}


def _has_source_link(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return "pmid" in lowered or "doi" in lowered or "guideline" in lowered


def evidence_freshness(year: int | None, reference_year: int | None = None) -> dict[str, Any]:
    """Classify evidence currency without judging clinical validity."""
    if reference_year is None:
        reference_year = date.today().year
    if not isinstance(year, int):
        return {
            "status": "undated",
            "age_years": None,
            "priority": 3,
            "summary": "No publication year available.",
        }

    age = max(0, reference_year - year)
    if age <= FRESH_YEARS:
        return {
            "status": "fresh",
            "age_years": age,
            "priority": 0,
            "summary": f"Published {age} year(s) ago.",
        }
    if age <= MONITOR_YEARS:
        return {
            "status": "monitor",
            "age_years": age,
            "priority": 1,
            "summary": f"Published {age} years ago; monitor for updates.",
        }
    if age <= STALE_YEARS:
        return {
            "status": "stale",
            "age_years": age,
            "priority": 2,
            "summary": f"Published {age} years ago; refresh recommended.",
        }
    return {
        "status": "legacy",
        "age_years": age,
        "priority": 3,
        "summary": f"Published {age} years ago; confirm this remains the best source.",
    }


def build_score_science_audit() -> dict[str, Any]:
    """Summarize organ-score formula provenance and lifecycle status."""
    tier_counts: Counter[str] = Counter()
    lifecycle_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    issues: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []

    for definition in ORGAN_SCORE_DEFINITIONS:
        code = definition.get("code", "")
        tier = str(definition.get("tier") or "unknown").lower()
        classification = get_classification(code) or {}
        lifecycle = classification.get("lifecycle", "missing_classification")
        domain = classification.get("primary_domain", "unknown")
        interpretation = _parse_interpretation(definition)
        citation_text = definition.get("citation_text") or ""

        tier_counts[tier] += 1
        lifecycle_counts[lifecycle] += 1
        domain_counts[domain] += 1

        row_issues = []
        if not _has_source_link(citation_text):
            row_issues.append("citation lacks PMID/DOI/guideline marker")
        if not interpretation:
            row_issues.append("missing or unparsable interpretation bands")
        if lifecycle == "missing_classification":
            row_issues.append("missing lifecycle/domain classification")
        if tier == "derived" and lifecycle == "active":
            row_issues.append("derived score marked active; ensure UI labels research limits")
        if lifecycle == "superseded" and not classification.get("superseded_by"):
            row_issues.append("superseded score lacks replacement")

        if row_issues:
            issues.append(
                {
                    "code": code,
                    "name": definition.get("name", code),
                    "tier": tier,
                    "lifecycle": lifecycle,
                    "issues": "; ".join(row_issues),
                }
            )

        score_rows.append(
            {
                "Code": code,
                "Name": definition.get("name", code),
                "Tier": tier,
                "Lifecycle": lifecycle,
                "Primary domain": domain,
                "Formula": definition.get("formula_key"),
                "Citation marker": "yes" if _has_source_link(citation_text) else "needs review",
                "Band count": len(interpretation),
            }
        )

    return {
        "total_scores": len(ORGAN_SCORE_DEFINITIONS),
        "tier_counts": dict(tier_counts),
        "lifecycle_counts": dict(lifecycle_counts),
        "domain_counts": dict(domain_counts),
        "issues": issues,
        "score_rows": score_rows,
    }


def build_evidence_library_audit(reference_year: int | None = None) -> dict[str, Any]:
    """Summarize evidence-library metadata quality and freshness."""
    if reference_year is None:
        reference_year = date.today().year

    grade_counts: Counter[str] = Counter()
    study_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    freshness_counts: Counter[str] = Counter()
    missing_metadata: list[dict[str, Any]] = []
    refresh_candidates: list[dict[str, Any]] = []
    unknown_domains: set[str] = set()

    for entry in EVIDENCE_LIBRARY:
        grade_counts[str(entry.get("evidence_grade") or "unknown")] += 1
        study_counts[str(entry.get("study_type") or "unknown")] += 1
        domain_counts[str(entry.get("domain") or "unknown")] += 1
        domain = entry.get("domain")
        if domain and domain not in RESEARCH_DOMAINS:
            unknown_domains.add(str(domain))

        freshness = evidence_freshness(entry.get("year"), reference_year=reference_year)
        freshness_counts[freshness["status"]] += 1

        missing = [
            field
            for field in ("pmid", "title", "year", "study_type", "evidence_grade", "url", "domain")
            if not entry.get(field)
        ]
        if missing:
            missing_metadata.append(
                {
                    "PMID": entry.get("pmid", ""),
                    "Title": entry.get("title", "Untitled"),
                    "Missing": ", ".join(missing),
                }
            )

        if freshness["priority"] >= 2:
            refresh_candidates.append(
                {
                    "PMID": entry.get("pmid", ""),
                    "Title": entry.get("title", "Untitled"),
                    "Year": entry.get("year"),
                    "Status": freshness["status"],
                    "Age": freshness["age_years"],
                    "Study type": entry.get("study_type"),
                    "Grade": entry.get("evidence_grade"),
                    "URL": entry.get("url", ""),
                }
            )

    refresh_candidates.sort(
        key=lambda item: (
            -1 if item.get("Age") is None else int(item.get("Age") or 0),
            str(item.get("Title") or ""),
        ),
        reverse=True,
    )

    return {
        "total_entries": len(EVIDENCE_LIBRARY),
        "grade_counts": dict(grade_counts),
        "study_counts": dict(study_counts),
        "domain_counts": dict(domain_counts),
        "freshness_counts": dict(freshness_counts),
        "unknown_domains": sorted(unknown_domains),
        "missing_metadata": missing_metadata,
        "refresh_candidates": refresh_candidates[:25],
    }


def build_hpr_science_audit() -> dict[str, Any]:
    """Summarize the imported HPR movement-science dataset."""
    categories = get_categories()
    rows_by_category = {category: len(get_protocol_rows(category)) for category in categories}
    audit = get_evidence_audit()
    total_rows = sum(rows_by_category.values())

    return {
        "categories": categories,
        "rows_by_category": rows_by_category,
        "total_protocol_rows": total_rows,
        "evidence_status": audit.get("status", "unknown"),
        "last_reviewed": audit.get("last_reviewed", "unknown"),
        "score_formula_status": audit.get("score_formula_status", SCORE_FORMULA_CAVEAT),
        "reference_issue_count": len(audit.get("reference_statuses", {})),
        "consistency_warnings": get_hpr_consistency_warnings(),
    }


def build_science_improvement_actions(
    score_audit: dict[str, Any],
    evidence_audit: dict[str, Any],
    hpr_audit: dict[str, Any],
) -> list[dict[str, str]]:
    """Create a short prioritized action list for reviewers."""
    actions: list[dict[str, str]] = []

    score_issue_count = len(score_audit.get("issues", []))
    if score_issue_count:
        actions.append(
            {
                "Priority": "High",
                "Area": "Score governance",
                "Action": f"Review {score_issue_count} score metadata issue(s): citations, lifecycle labels, or band parsing.",
            }
        )

    refresh_count = len(evidence_audit.get("refresh_candidates", []))
    if refresh_count:
        actions.append(
            {
                "Priority": "High",
                "Area": "Evidence library",
                "Action": f"Refresh top {min(refresh_count, 25)} stale/legacy evidence entries against current guidelines and systematic reviews.",
            }
        )

    missing_meta_count = len(evidence_audit.get("missing_metadata", []))
    if missing_meta_count:
        actions.append(
            {
                "Priority": "Medium",
                "Area": "Evidence metadata",
                "Action": f"Complete missing PMID/year/url/domain fields for {missing_meta_count} evidence entries.",
            }
        )

    unknown_domains = evidence_audit.get("unknown_domains", [])
    if unknown_domains:
        actions.append(
            {
                "Priority": "Medium",
                "Area": "Evidence taxonomy",
                "Action": "Add or correct unrecognized evidence domains: " + ", ".join(unknown_domains),
            }
        )

    if hpr_audit.get("evidence_status") != "validated":
        actions.append(
            {
                "Priority": "High",
                "Area": "HPR Movement Lab",
                "Action": "Keep HPR as audit/reference mode until raw normalization and composite scoring formulas are independently validated.",
            }
        )

    if not actions:
        actions.append(
            {
                "Priority": "Low",
                "Area": "Science governance",
                "Action": "No blocking metadata gaps detected; schedule periodic evidence refresh.",
            }
        )

    return actions


def build_science_review(reference_year: int | None = None) -> dict[str, Any]:
    score_audit = build_score_science_audit()
    evidence_audit = build_evidence_library_audit(reference_year=reference_year)
    hpr_audit = build_hpr_science_audit()
    return {
        "scores": score_audit,
        "evidence": evidence_audit,
        "hpr": hpr_audit,
        "actions": build_science_improvement_actions(score_audit, evidence_audit, hpr_audit),
    }


def summarize_counts(counts: dict[str, int]) -> list[dict[str, Any]]:
    """Convert a count mapping into dataframe-friendly rows."""
    return [
        {"Label": key, "Count": value}
        for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
