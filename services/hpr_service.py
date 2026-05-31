"""Helpers for the imported HPR Movement Lab reference model.

The HPR client exposed protocol rows, norm anchors, references, demo scores,
and exercise prescription examples. It did not expose the raw-to-normalized,
percentile, domain-weighting, or overall score formulas. Functions in this
module keep that distinction explicit for the Streamlit page.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "config" / "hpr_health_model.json"
PROTOCOLS_PATH = ROOT_DIR / "config" / "hpr_testing_protocols.json"

CATEGORY_ORDER = ("sedentary", "trained", "competitive", "elite")
CATEGORY_LABELS = {
    "sedentary": "Sedentary",
    "trained": "Trained",
    "competitive": "Competitive",
    "elite": "Elite",
}

DOMAIN_ORDER = ("strength", "movement", "cardiovascular", "cognitive")
DOMAIN_LABELS = {
    "strength": "Strength",
    "movement": "Movement",
    "cardiovascular": "Cardiovascular",
    "cognitive": "Cognitive",
}

SCORE_FORMULA_CAVEAT = (
    "HPR norm bands, protocol rows, and demo scores are extracted. The public "
    "client did not expose the raw-to-normalized, percentile, composite-domain, "
    "domain weighting, or overall-score formulas. Calculator values are an "
    "anchor-position index inferred from visible norm anchors, not a validated "
    "HPR score."
)

HPR_CONSISTENCY_WARNINGS = [
    {
        "Area": "Anchor calculator",
        "Warning": "The 0-10 display is an anchor-position index only; it is not the hidden HPR metric or composite scoring formula.",
    },
    {
        "Area": "Sample confidence",
        "Warning": "Extracted demo confidence fields are app metadata, not validation confidence for the score model.",
    },
    {
        "Area": "Force symmetry",
        "Warning": "Model metrics use percent symmetry where higher is better; one protocol row uses percent asymmetry where lower is better. Do not mix the units.",
    },
    {
        "Area": "Dual-task cost",
        "Warning": "Imported notes conflict on dual-task cost sign. Use positive cost as (dual-task RT - single-task RT) / single-task RT until independently reviewed.",
    },
]


def clean_text(value: Any) -> Any:
    """Return display-safe ASCII for imported clinical/reference copy."""
    if not isinstance(value, str):
        return value

    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00f7": "/",
        "\u00d7": "x",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2248": "~",
        "\u00b0": " deg",
        "\u00b5": "u",
        "\u03bc": "u",
        "\u00b7": "-",
        "\u00a0": " ",
    }
    cleaned = value
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned


def _clean_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {clean_text(key): _clean_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_data(item) for item in value]
    return clean_text(value)


@lru_cache(maxsize=1)
def get_model() -> dict[str, Any]:
    return _clean_data(json.loads(MODEL_PATH.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def get_protocols_model() -> dict[str, Any]:
    return _clean_data(json.loads(PROTOCOLS_PATH.read_text(encoding="utf-8")))


def get_categories() -> list[str]:
    protocols = get_protocols_model().get("protocols", {})
    return [category for category in CATEGORY_ORDER if category in protocols]


def get_category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category.title())


def get_domain_label(domain: str) -> str:
    return DOMAIN_LABELS.get(domain, domain.replace("_", " ").title())


def get_category_rationale(category: str) -> dict[str, Any]:
    return get_model().get("categoryRationale", {}).get(category, {})


def get_protocol(category: str) -> dict[str, Any]:
    return get_protocols_model().get("protocols", {}).get(category, {})


def get_protocol_rows(category: str, domain: str | None = None) -> list[dict[str, Any]]:
    rows = get_protocol(category).get("rows", [])
    if not domain or domain == "All":
        return rows
    return [row for row in rows if row.get("domain") == domain]


def get_protocol_domains(category: str) -> list[str]:
    rows = get_protocol_rows(category)
    found = {row.get("domain") for row in rows if row.get("domain")}
    ordered_labels = [DOMAIN_LABELS[key] for key in DOMAIN_ORDER]
    return [label for label in ordered_labels if label in found] + sorted(found - set(ordered_labels))


def get_evidence_audit() -> dict[str, Any]:
    return get_model().get("evidenceAudit", {})


def get_evidence_references() -> list[dict[str, Any]]:
    return get_protocols_model().get("evidenceReferences", [])


def get_metrics_by_domain(domain: str | None = None) -> list[dict[str, Any]]:
    metrics = get_model().get("metrics", {})
    selected_domains = [domain] if domain else DOMAIN_ORDER
    output: list[dict[str, Any]] = []
    for domain_key in selected_domains:
        for metric_key, metric in metrics.get(domain_key, {}).items():
            output.append(
                {
                    "key": metric_key,
                    "domain": domain_key,
                    "domain_label": get_domain_label(domain_key),
                    **metric,
                }
            )
    return output


def get_sample_assessment(category: str) -> dict[str, Any]:
    return get_model().get("sampleAssessments", {}).get(category, {})


def get_domain_scores(sample: dict[str, Any]) -> list[dict[str, Any]]:
    scores = []
    for domain in DOMAIN_ORDER:
        score = sample.get(f"{domain}_score")
        confidence = sample.get(f"{domain}_confidence")
        if score is not None:
            scores.append(
                {
                    "domain": domain,
                    "label": get_domain_label(domain),
                    "score": float(score),
                    "confidence": confidence,
                }
            )
    return scores


def infer_metric_score(value: float, norms: dict[str, float] | None) -> float | None:
    """Infer a 0-10 score from visible HPR norm anchors.

    The anchors are mapped as min=5, expected=7, high=8.5, elite=10. This is
    an audit approximation, not the hidden HPR scoring algorithm.
    """
    if not norms:
        return None

    anchors = [
        (norms.get("min"), 5.0),
        (norms.get("expected"), 7.0),
        (norms.get("high"), 8.5),
        (norms.get("elite"), 10.0),
    ]
    points = sorted(
        (float(raw), score) for raw, score in anchors if isinstance(raw, (int, float))
    )
    if len(points) < 2:
        return None

    if value <= points[0][0]:
        score = _interpolate(points[0], points[1], value)
    elif value >= points[-1][0]:
        score = _interpolate(points[-2], points[-1], value)
    else:
        score = None
        for left, right in zip(points, points[1:]):
            if left[0] <= value <= right[0]:
                score = _interpolate(left, right, value)
                break

    if score is None:
        return None
    return round(max(0.0, min(10.0, score)), 1)


def _interpolate(left: tuple[float, float], right: tuple[float, float], value: float) -> float:
    left_value, left_score = left
    right_value, right_score = right
    if right_value == left_value:
        return right_score
    ratio = (value - left_value) / (right_value - left_value)
    return left_score + ratio * (right_score - left_score)


def score_band(score: float | None) -> str:
    if score is None:
        return "No norm anchor"
    if score >= 8.5:
        return "High / elite anchor"
    if score >= 7:
        return "Expected or better"
    if score >= 5:
        return "Meets minimum anchor"
    return "Below visible anchor"


def build_anchor_rows(norms: dict[str, float] | None) -> list[dict[str, Any]]:
    if not norms:
        return []
    return [
        {"Anchor": "Minimum", "Raw value": norms.get("min"), "Anchor index": 5.0},
        {"Anchor": "Expected", "Raw value": norms.get("expected"), "Anchor index": 7.0},
        {"Anchor": "High", "Raw value": norms.get("high"), "Anchor index": 8.5},
        {"Anchor": "Elite", "Raw value": norms.get("elite"), "Anchor index": 10.0},
    ]


def get_hpr_consistency_warnings() -> list[dict[str, str]]:
    return list(HPR_CONSISTENCY_WARNINGS)
