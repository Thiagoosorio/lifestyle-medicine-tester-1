"""Risk-band wording renderer + forbidden-lemma scanner.

Per architecture_spec.md §8 (Output language constraints):

Forbidden lemmas in any output string, function name, public API field,
or UI label, as anchored to the commitments_log entry on regulatory
positioning:

    diagnose, diagnosis, diagnostic
    predict, prediction, predicts          (when paired with disease/condition object)
    prognosis, prognostic, prognose
    recommend                              (treatment-direction sense)
    prescribe, prescription
    treatment, therapy                     (when paired with start/begin/initiate/stop)
    cure, curative

Allow-list (case-insensitive):

    "lifestyle recommendations"
    "screening recommendations"
    "AHA PREVENT"                  (proper noun)
    "screening for ..."
    "diagnostic accuracy"          (internal audit fields only)

Phase 1 scope:
    - Strict-forbidden lemmas (the seven without context-aware caveats)
      are enforced via word-boundary regex matching, modulo allow-list
      mask-out.
    - Context-aware lemmas (predict / recommend / treatment / therapy)
      are enforced via the same word-boundary check; the user-facing
      wording.yaml lands in Phase 2 with the per-score templates and
      narrows context-handling at that point.

The renderer itself is a stub: for any ScoreResult whose status is not OK,
it returns None (gated / missing scores carry no wording per §6 + §8).
For OK scores it returns the resolved template string from a templates
mapping; templates land in Phase 2 with ``configs/wording.yaml``.

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

import re
from typing import Mapping

from healthscore.enums import ScoreStatus
from healthscore.types import ScoreResult


# ──────────────────────────────────────────────────────────────────────────
# Renderer
# ──────────────────────────────────────────────────────────────────────────


def render_wording(
    score_result: ScoreResult,
    *,
    templates: Mapping[str, Mapping[str, str]] | None = None,
) -> str | None:
    """Render the user-facing wording for a score result.

    Returns None when:
        - status != OK  (gated / missing / out-of-range scores carry no wording)
        - templates is None  (Phase 1 default; Phase 2+ wires wording.yaml)
        - the score / risk-band combination has no template

    Returns the literal template otherwise. Templates are NOT scanned for
    forbidden lemmas at render time -- that's the linter's job at CI time
    (via ``scan_text_for_forbidden_lemmas``).
    """
    if score_result.status is not ScoreStatus.OK:
        return None
    if templates is None:
        return None
    score_templates = templates.get(score_result.score_id)
    if not score_templates:
        return None
    if score_result.risk_band is None:
        return None
    return score_templates.get(score_result.risk_band.value)


# ──────────────────────────────────────────────────────────────────────────
# Forbidden-lemma scanner
# ──────────────────────────────────────────────────────────────────────────

# Strict-forbidden lemmas. These never have a defensible user-facing use.
_STRICT_FORBIDDEN = (
    "diagnose",
    "diagnosis",
    "diagnostic",
    "prognosis",
    "prognostic",
    "prognose",
    "prescribe",
    "prescription",
    "cure",
    "curative",
)

# Context-aware lemmas. Forbidden in user-facing strings, allowed in
# specific narrow internal contexts (caught via the allow-list).
_CONTEXT_AWARE = (
    "predict",
    "predicts",
    "prediction",
    "recommend",
    "recommends",
    "recommended",
    "treatment",
    "therapy",
)

#: Lemmas whose substring may legitimately appear inside an allow-listed phrase.
FORBIDDEN_LEMMAS: tuple[str, ...] = _STRICT_FORBIDDEN + _CONTEXT_AWARE

#: Phrases that may legitimately contain a forbidden substring.
ALLOW_LIST: tuple[str, ...] = (
    "lifestyle recommendations",
    "screening recommendations",
    "aha prevent",
    "screening for",
    "diagnostic accuracy",
)


def _mask_allow_list(text_lower: str) -> str:
    """Replace every allow-listed phrase with neutral placeholders.

    Keeps overall string length stable so reported line/column numbers
    don't shift when the linter reports the original text.
    """
    out = text_lower
    for phrase in ALLOW_LIST:
        if phrase in out:
            out = out.replace(phrase, "_" * len(phrase))
    return out


def scan_text_for_forbidden_lemmas(text: str) -> list[str]:
    """Return the list of forbidden lemmas found in ``text``.

    Word-boundary matches only -- 'cure' does not match inside 'cured' or
    'pedicure' (note: 'cured' would match because of the trailing 'd' word
    boundary; this is intentional). Allow-listed phrases are masked out
    before scanning.
    """
    text_lower = text.lower()
    masked = _mask_allow_list(text_lower)
    found: list[str] = []
    for lemma in FORBIDDEN_LEMMAS:
        if re.search(rf"\b{re.escape(lemma)}\b", masked):
            found.append(lemma)
    return found
