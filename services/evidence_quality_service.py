"""Evidence quality ranking and contradiction detection helpers."""

from __future__ import annotations

from datetime import date


_GRADE_SCORE = {"A": 40, "B": 28, "C": 16, "D": 8}
_TIER_SCORE = {"elite": 14, "q1": 9, "q2": 5, "q3": 2, "q4": 1}

_GUIDELINE_TERMS = (
    "guideline",
    "consensus",
    "position statement",
    "clinical practice",
    "recommendation",
)
_AUTHORITY_TERMS = (
    "who",
    "cdc",
    "nih",
    "aha",
    "acc",
    "ada",
    "uspstf",
    "nice",
    "esc",
    "acg",
    "aasm",
)

_POSITIVE_TERMS = (
    "reduced",
    "reduces",
    "lower",
    "decrease",
    "improve",
    "improved",
    "effective",
    "benefit",
    "associated with lower",
)
_NEGATIVE_TERMS = (
    "no effect",
    "not associated",
    "ineffective",
    "worse",
    "harm",
    "higher risk",
    "increased risk",
    "did not improve",
)


def _as_text(evidence: dict) -> str:
    parts = [
        str(evidence.get("title", "")),
        str(evidence.get("summary", "")),
        str(evidence.get("key_finding", "")),
        str(evidence.get("journal", "")),
        str(evidence.get("authors", "")),
        str(evidence.get("tags", "")),
    ]
    return " ".join(parts).lower()


def _recency_score(year_value, reference_year: int) -> int:
    if not isinstance(year_value, int):
        return 0
    age = max(0, reference_year - year_value)
    return max(0, 14 - age * 2)


def _guideline_signal_score(evidence: dict) -> int:
    score = 0
    study_type = str(evidence.get("study_type", "")).lower()
    text = _as_text(evidence)

    if study_type == "guideline":
        score += 70
    if any(term in text for term in _GUIDELINE_TERMS):
        score += 25
    if any(term in text for term in _AUTHORITY_TERMS):
        score += 18
    return score


def guideline_priority_score(evidence: dict, reference_year: int | None = None) -> int:
    """Score entries for guideline-first ranking."""
    if reference_year is None:
        reference_year = date.today().year

    grade = str(evidence.get("evidence_grade", "")).upper()
    tier = str(evidence.get("journal_tier", "")).lower()
    study_type = str(evidence.get("study_type", "")).lower()

    base = _GRADE_SCORE.get(grade, 0) + _TIER_SCORE.get(tier, 0)
    recency = _recency_score(evidence.get("year"), reference_year)
    guideline_bonus = _guideline_signal_score(evidence)

    study_bonus = {
        "meta_analysis": 11,
        "systematic_review": 10,
        "rct": 8,
        "guideline": 9,
        "cohort": 4,
        "case_control": 3,
        "cross_sectional": 2,
        "case_report": 1,
        "expert_opinion": 0,
    }.get(study_type, 0)

    return base + recency + study_bonus + guideline_bonus


def sort_guideline_first(evidence_rows: list[dict], reference_year: int | None = None) -> list[dict]:
    """Return entries sorted by guideline-first score (desc)."""
    rows = list(evidence_rows)
    rows.sort(key=lambda ev: guideline_priority_score(ev, reference_year=reference_year), reverse=True)
    return rows


def _parse_tags(tags_value) -> set[str]:
    if tags_value is None:
        return set()
    if isinstance(tags_value, list):
        raw = [str(x).strip().lower() for x in tags_value]
    else:
        raw = [x.strip().lower() for x in str(tags_value).split(",")]
    return {tag for tag in raw if tag}


def _claim_direction(text: str) -> str:
    normalized = text.lower()
    pos = sum(1 for term in _POSITIVE_TERMS if term in normalized)
    neg = sum(1 for term in _NEGATIVE_TERMS if term in normalized)
    if pos > neg and pos > 0:
        return "positive"
    if neg > pos and neg > 0:
        return "negative"
    return "neutral"


def _claim_text(evidence: dict) -> str:
    return f"{evidence.get('summary', '')} {evidence.get('key_finding', '')}".strip()


def _grade_weight(grade: str) -> int:
    return {"A": 4, "B": 3, "C": 2, "D": 1}.get(str(grade).upper(), 0)


def detect_evidence_contradictions(
    evidence_rows: list[dict],
    min_year_gap: int = 1,
    max_results: int = 25,
) -> list[dict]:
    """Find likely contradictions where newer and older evidence disagree."""
    filtered = [
        ev
        for ev in evidence_rows
        if isinstance(ev.get("year"), int)
        and _claim_direction(_claim_text(ev)) in {"positive", "negative"}
    ]
    contradictions = []

    for i, newer in enumerate(filtered):
        for older in filtered[i + 1 :]:
            year_new = newer["year"]
            year_old = older["year"]
            if year_new == year_old:
                continue
            if year_new < year_old:
                newer, older = older, newer
                year_new, year_old = year_old, year_new
            if year_new - year_old < min_year_gap:
                continue

            if newer.get("pillar_id") != older.get("pillar_id"):
                continue

            tags_new = _parse_tags(newer.get("tags"))
            tags_old = _parse_tags(older.get("tags"))
            overlap = tags_new & tags_old
            if not overlap:
                continue

            dir_new = _claim_direction(_claim_text(newer))
            dir_old = _claim_direction(_claim_text(older))
            if dir_new == dir_old:
                continue

            confidence = (
                _grade_weight(newer.get("evidence_grade", ""))
                + _grade_weight(older.get("evidence_grade", ""))
                + min(4, len(overlap))
                + min(4, year_new - year_old)
            )

            contradictions.append(
                {
                    "topic_tags": sorted(overlap),
                    "pillar_id": newer.get("pillar_id"),
                    "newer": newer,
                    "older": older,
                    "newer_direction": dir_new,
                    "older_direction": dir_old,
                    "confidence": confidence,
                    "summary": (
                        f"Newer ({year_new}) evidence suggests {dir_new} effect, "
                        f"while older ({year_old}) suggests {dir_old} effect."
                    ),
                }
            )

    contradictions.sort(key=lambda c: c["confidence"], reverse=True)
    deduped = []
    seen = set()
    for item in contradictions:
        n_id = item["newer"].get("id") or item["newer"].get("pmid")
        o_id = item["older"].get("id") or item["older"].get("pmid")
        key = (n_id, o_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_results:
            break
    return deduped


def contradiction_watchlist_for_display(
    evidence_rows: list[dict],
    min_confidence: int = 8,
    max_results: int = 10,
) -> list[dict]:
    """Return contradiction candidates suitable for UI display."""
    items = detect_evidence_contradictions(
        evidence_rows=evidence_rows,
        min_year_gap=1,
        max_results=max_results * 2,
    )
    return [item for item in items if item["confidence"] >= min_confidence][:max_results]
