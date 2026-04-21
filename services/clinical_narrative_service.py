"""Detect cross-domain clinical patterns from a set of organ-score results.

A pattern activates when every trigger group in its definition is satisfied by
at least one (or min_count) matching organ-score result at the required
severity. The result ties together the relevant scores into a narrative
explaining the shared mechanism and the recommended next steps.

This is workflow guidance for the clinician, not a diagnosis.
"""

from __future__ import annotations

from config.cross_domain_patterns import CROSS_DOMAIN_PATTERNS

_SEVERITY_RANK = {
    "optimal": 0,
    "normal": 1,
    "elevated": 2,
    "high": 3,
    "critical": 4,
}

_DEFAULT_SEVERITY_FLOOR = "elevated"


def _meets_severity(score_severity: str | None, required: str) -> bool:
    return _SEVERITY_RANK.get(score_severity or "", 0) >= _SEVERITY_RANK.get(required, 0)


def detect_cross_domain_patterns(organ_scores: list[dict]) -> list[dict]:
    """Return the cross-domain patterns triggered by the current organ scores.

    ``organ_scores`` is the list returned by ``get_latest_computed_scores`` —
    each row carries at least ``code``, ``name``, and ``severity``.
    """
    by_code = {s.get("code"): s for s in (organ_scores or []) if s.get("code")}
    active: list[dict] = []

    for pattern in CROSS_DOMAIN_PATTERNS:
        severity_floor = pattern.get("severity_floor", _DEFAULT_SEVERITY_FLOOR)
        triggering: list[dict] = []
        all_groups_match = True

        for group in pattern.get("trigger_groups", []):
            required_sev = group.get("min_severity", severity_floor)
            min_count = int(group.get("min_count", 1))
            matches = []
            for code in group.get("any_of", []):
                score = by_code.get(code)
                if not score:
                    continue
                if _meets_severity(score.get("severity"), required_sev):
                    matches.append(score)
            if len(matches) < min_count:
                all_groups_match = False
                break
            triggering.extend(matches)

        if not all_groups_match or not triggering:
            continue

        # Deduplicate while preserving order
        seen_codes: set[str] = set()
        unique_triggers = []
        for score in triggering:
            code = score.get("code")
            if code in seen_codes:
                continue
            seen_codes.add(code)
            unique_triggers.append(score)

        peak_severity = max(
            (_SEVERITY_RANK.get(s.get("severity") or "", 0) for s in unique_triggers),
            default=0,
        )
        peak_label = next(
            (k for k, v in _SEVERITY_RANK.items() if v == peak_severity),
            "elevated",
        )

        active.append(
            {
                "code": pattern["code"],
                "name": pattern["name"],
                "narrative": pattern["narrative"],
                "action": pattern["action"],
                "citation_pmid": pattern.get("citation_pmid"),
                "citation_text": pattern.get("citation_text"),
                "severity": peak_label,
                "triggering_scores": [
                    {
                        "code": s.get("code"),
                        "name": s.get("name"),
                        "severity": s.get("severity"),
                        "label": s.get("label"),
                        "value": s.get("value"),
                    }
                    for s in unique_triggers
                ],
            }
        )

    # Highest-severity patterns first
    active.sort(
        key=lambda p: -_SEVERITY_RANK.get(p.get("severity") or "", 0)
    )
    return active
