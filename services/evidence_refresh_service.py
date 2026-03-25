"""Refresh and rank recent research evidence from PubMed."""

from __future__ import annotations

import json
import os
from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config.evidence import STUDY_TYPES
from db.database import get_connection

PUBMED_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
REQUEST_TIMEOUT_SEC = 30

PILLAR_PUBMED_QUERIES = {
    1: "(Mediterranean diet OR plant-based diet OR DASH OR ultra-processed food) "
       "AND (meta-analysis[Publication Type] OR randomized controlled trial[Publication Type] "
       "OR practice guideline[Publication Type] OR systematic[sb])",
    2: "(physical activity OR exercise training OR resistance training OR aerobic exercise) "
       "AND (meta-analysis[Publication Type] OR randomized controlled trial[Publication Type] "
       "OR practice guideline[Publication Type] OR systematic[sb])",
    3: "(sleep duration OR sleep quality OR insomnia treatment OR circadian) "
       "AND (meta-analysis[Publication Type] OR randomized controlled trial[Publication Type] "
       "OR practice guideline[Publication Type] OR systematic[sb])",
    4: "(mindfulness OR stress reduction OR meditation OR breathing intervention) "
       "AND (meta-analysis[Publication Type] OR randomized controlled trial[Publication Type] "
       "OR practice guideline[Publication Type] OR systematic[sb])",
    5: "(social connection OR loneliness intervention OR social support) "
       "AND (meta-analysis[Publication Type] OR randomized controlled trial[Publication Type] "
       "OR practice guideline[Publication Type] OR systematic[sb])",
    6: "(smoking cessation OR alcohol reduction OR substance use intervention) "
       "AND (meta-analysis[Publication Type] OR randomized controlled trial[Publication Type] "
       "OR practice guideline[Publication Type] OR systematic[sb])",
}

PILLAR_DOMAIN_MAP = {
    1: "nutrition",
    2: "exercise_science",
    3: "sleep_science",
    4: "stress_pni",
    5: "lifestyle_medicine",
    6: "lifestyle_medicine",
}

ELITE_JOURNALS = {
    "n engl j med",
    "the lancet",
    "jama",
    "bmj",
    "nature",
    "science",
    "cell",
    "cochrane database syst rev",
}

# Must match evidence_quality_service._GRADE_SCORE / _TIER_SCORE
_GRADE_SCORES = {"A": 40, "B": 28, "C": 16, "D": 8}
_TIER_SCORES = {"elite": 14, "q1": 9, "q2": 5, "q3": 2, "q4": 1}


def _get_api_key() -> str | None:
    key = os.getenv("NCBI_API_KEY", "").strip()
    return key or None


def _request_json(endpoint: str, params: dict) -> dict:
    import logging
    logger = logging.getLogger(__name__)

    full_params = dict(params)
    api_key = _get_api_key()
    if api_key:
        full_params["api_key"] = api_key

    url = f"{PUBMED_EUTILS_BASE}/{endpoint}?{urlencode(full_params)}"
    req = Request(
        url,
        headers={
            "User-Agent": "LifestyleMedicineCoach/1.0 (evidence refresh)",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("PubMed API request failed (%s): %s", endpoint, exc)
        return {}


def _extract_year(value: str | None) -> int | None:
    if not value:
        return None
    for chunk in value.split():
        if len(chunk) == 4 and chunk.isdigit():
            return int(chunk)
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 4:
        return int(digits[:4])
    return None


def _map_pub_types_to_study_type(pub_types: list[str]) -> str:
    lowered = [p.lower() for p in (pub_types or [])]
    if any("meta-analysis" in p for p in lowered):
        return "meta_analysis"
    if any("systematic review" in p for p in lowered):
        return "systematic_review"
    if any("randomized controlled trial" in p for p in lowered):
        return "rct"
    if any("practice guideline" in p or "guideline" in p for p in lowered):
        return "guideline"
    if any("case-control" in p for p in lowered):
        return "case_control"
    if any("cross-sectional" in p for p in lowered):
        return "cross_sectional"
    if any("cohort" in p for p in lowered):
        return "cohort"
    if any("review" in p for p in lowered):
        return "systematic_review"
    return "cohort"


def _infer_journal_tier(journal: str | None) -> str | None:
    if not journal:
        return None
    j = journal.strip().lower()
    if j in ELITE_JOURNALS:
        return "elite"
    if any(k in j for k in ("circulation", "jama", "lancet", "nature", "cochrane")):
        return "elite"
    if any(k in j for k in ("sports med", "sleep", "j clin", "diabetes care", "eur j", "nutrients")):
        return "q1"
    return None


def _extract_doi(article_ids: list[dict]) -> str | None:
    for aid in article_ids or []:
        if str(aid.get("idtype", "")).lower() == "doi":
            value = str(aid.get("value", "")).strip()
            if value:
                return value
    return None


def search_recent_pubmed_ids(query: str, years_back: int = 2, retmax: int = 20) -> list[str]:
    start_year = max(1900, date.today().year - max(1, years_back))
    payload = _request_json(
        "esearch.fcgi",
        {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max(1, min(retmax, 100)),
            "datetype": "pdat",
            "mindate": f"{start_year}/01/01",
            "maxdate": date.today().isoformat(),
            "sort": "date",
        },
    )
    return payload.get("esearchresult", {}).get("idlist", [])


def fetch_pubmed_summaries(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    payload = _request_json(
        "esummary.fcgi",
        {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
            "version": "2.0",
        },
    )
    result = payload.get("result", {})
    docs = []
    for uid in result.get("uids", []):
        doc = result.get(uid)
        if doc:
            docs.append(doc)
    return docs


def score_evidence_priority(evidence: dict, reference_year: int | None = None) -> int:
    """Score evidence for ranking (quality + recency)."""
    if reference_year is None:
        reference_year = date.today().year

    grade_score = _GRADE_SCORES.get(evidence.get("evidence_grade"), 0)
    tier_score = _TIER_SCORES.get(evidence.get("journal_tier"), 0)

    study_type = evidence.get("study_type")
    study_bonus = {
        "meta_analysis": 12,
        "systematic_review": 10,
        "rct": 8,
        "guideline": 7,
        "cohort": 5,
        "case_control": 4,
        "cross_sectional": 3,
        "case_report": 2,
        "expert_opinion": 1,
    }.get(study_type, 0)

    year_val = evidence.get("year")
    recency_bonus = 0
    if isinstance(year_val, int):
        age = max(0, reference_year - year_val)
        recency_bonus = max(0, 12 - age * 2)

    return grade_score + tier_score + study_bonus + recency_bonus


def _build_auto_summary(study_type: str, journal: str | None, year: int | None) -> str:
    study_label = STUDY_TYPES.get(study_type, {}).get("label", "Study")
    journal_text = journal or "peer-reviewed journal"
    year_text = str(year) if year else "recent year"
    return (
        f"Auto-imported from PubMed on {date.today().isoformat()}. "
        f"{study_label} published in {journal_text} ({year_text}). "
        "Review abstract on PubMed before clinical application."
    )


def _upsert_auto_evidence(pillar_id: int, doc: dict) -> str:
    pmid = str(doc.get("uid", "")).strip()
    title = str(doc.get("title", "")).strip()
    if not pmid or not title:
        return "skipped"

    pub_types = doc.get("pubtype", []) or []
    study_type = _map_pub_types_to_study_type(pub_types)
    evidence_grade = STUDY_TYPES.get(study_type, {}).get("default_grade", "C")

    pubdate = doc.get("pubdate") or doc.get("sortpubdate")
    year = _extract_year(str(pubdate)) or date.today().year
    journal = doc.get("fulljournalname") or doc.get("source")
    authors = ", ".join(a.get("name", "") for a in doc.get("authors", []) if a.get("name"))
    doi = _extract_doi(doc.get("articleids", []))
    journal_tier = _infer_journal_tier(journal)
    domain = PILLAR_DOMAIN_MAP.get(pillar_id, "lifestyle_medicine")
    summary = _build_auto_summary(study_type, journal, year)
    tags = f"auto_pubmed,recent_evidence,pillar_{pillar_id}"
    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id, tags FROM research_evidence WHERE pmid = ?",
            (pmid,),
        ).fetchone()
        if existing:
            existing_tags = (existing["tags"] or "").lower()
            if "auto_pubmed" not in existing_tags:
                return "skipped"
            conn.execute(
                """UPDATE research_evidence
                   SET title = ?, authors = ?, journal = ?, year = ?, study_type = ?,
                       evidence_grade = ?, pillar_id = ?, summary = ?, tags = ?,
                       url = ?, doi = COALESCE(?, doi), journal_tier = COALESCE(?, journal_tier),
                       domain = COALESCE(?, domain)
                   WHERE id = ?""",
                (
                    title,
                    authors or None,
                    journal or None,
                    year,
                    study_type,
                    evidence_grade,
                    pillar_id,
                    summary,
                    tags,
                    url,
                    doi,
                    journal_tier,
                    domain,
                    existing["id"],
                ),
            )
            conn.commit()
            return "updated"

        conn.execute(
            """INSERT INTO research_evidence
               (pmid, doi, title, authors, journal, year, study_type,
                evidence_grade, pillar_id, summary, key_finding, effect_size,
                sample_size, population, dose_response, causation_note, tags, url,
                journal_tier, domain)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pmid,
                doi,
                title,
                authors or None,
                journal or None,
                year,
                study_type,
                evidence_grade,
                pillar_id,
                summary,
                None,
                None,
                None,
                None,
                None,
                "Auto-imported metadata only; validate abstract/full text before decision-making.",
                tags,
                url,
                journal_tier,
                domain,
            ),
        )
        conn.commit()
        return "inserted"
    finally:
        conn.close()


def refresh_recent_evidence_for_pillar(
    pillar_id: int,
    years_back: int = 2,
    retmax: int = 20,
) -> dict:
    query = PILLAR_PUBMED_QUERIES.get(pillar_id)
    if not query:
        return {"pillar_id": pillar_id, "inserted": 0, "updated": 0, "skipped": 0, "fetched": 0}

    pmids = search_recent_pubmed_ids(query, years_back=years_back, retmax=retmax)
    docs = fetch_pubmed_summaries(pmids)

    stats = {"pillar_id": pillar_id, "inserted": 0, "updated": 0, "skipped": 0, "fetched": len(docs)}
    for doc in docs:
        outcome = _upsert_auto_evidence(pillar_id, doc)
        if outcome in stats:
            stats[outcome] += 1
    return stats


def refresh_recent_evidence_for_all_pillars(
    years_back: int = 2,
    retmax_per_pillar: int = 10,
) -> dict:
    aggregate = {"inserted": 0, "updated": 0, "skipped": 0, "fetched": 0, "by_pillar": []}
    for pillar_id in sorted(PILLAR_PUBMED_QUERIES.keys()):
        stats = refresh_recent_evidence_for_pillar(
            pillar_id,
            years_back=years_back,
            retmax=retmax_per_pillar,
        )
        aggregate["by_pillar"].append(stats)
        for key in ("inserted", "updated", "skipped", "fetched"):
            aggregate[key] += stats.get(key, 0)
    return aggregate


def get_latest_auto_evidence(limit: int = 50, pillar_id: int | None = None) -> list[dict]:
    conn = get_connection()
    try:
        if pillar_id:
            rows = conn.execute(
                """SELECT * FROM research_evidence
                   WHERE tags LIKE '%auto_pubmed%' AND pillar_id = ?
                   ORDER BY year DESC, created_at DESC
                   LIMIT ?""",
                (pillar_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM research_evidence
                   WHERE tags LIKE '%auto_pubmed%'
                   ORDER BY year DESC, created_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
