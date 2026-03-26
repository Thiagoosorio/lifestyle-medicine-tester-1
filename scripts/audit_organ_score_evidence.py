"""Audit organ score citations against PubMed (PMID existence + sentinel title checks).

Usage:
    python scripts/audit_organ_score_evidence.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

# Ensure project root is importable when running as a script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.organ_scores_data import ORGAN_SCORE_DEFINITIONS

PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_PMID_URL = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

# Sentinel checks for previously broken mappings.
EXPECTED_TITLE_SNIPPETS = {
    "remnant_cholesterol": ["remnant cholesterol"],
    "plr": ["platelet", "lymphocyte"],
}


def _fetch_pubmed_summaries(pmids: list[str]) -> dict[str, dict]:
    if not pmids:
        return {}
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
    with urlopen(f"{PUBMED_SUMMARY_URL}?{urlencode(params)}", timeout=30) as response:
        payload = json.load(response)
    result = payload.get("result", {})
    return {pmid: result.get(pmid, {}) for pmid in pmids}


def _status_for_score(score: dict, meta: dict | None) -> str:
    pmid = score.get("citation_pmid")
    if not pmid:
        if score.get("tier") == "validated":
            return "unknown - not found in search or files"
        return "uncertain - no direct evidence"
    if not meta:
        return "unknown - not found in search or files"

    snippets = EXPECTED_TITLE_SNIPPETS.get(score["code"], [])
    if snippets:
        title = (meta.get("title") or "").lower()
        if not all(snippet in title for snippet in snippets):
            return "uncertain - single source"
    return "verified"


def _build_report() -> str:
    pmids = sorted({d["citation_pmid"] for d in ORGAN_SCORE_DEFINITIONS if d.get("citation_pmid")})
    summaries = _fetch_pubmed_summaries(pmids)

    lines = []
    lines.append(f"# Organ Score Evidence Audit ({date.today().isoformat()})")
    lines.append("")
    lines.append("Legend: `verified`, `uncertain - single source`, `uncertain - no direct evidence`, `unknown - not found in search or files`")
    lines.append("")

    status_counts: dict[str, int] = {}
    for score in ORGAN_SCORE_DEFINITIONS:
        pmid = score.get("citation_pmid")
        meta = summaries.get(pmid) if pmid else None
        status = _status_for_score(score, meta)
        status_counts[status] = status_counts.get(status, 0) + 1

        title = (meta or {}).get("title", "N/A")
        journal = (meta or {}).get("source", "N/A")
        pubdate = (meta or {}).get("pubdate", "N/A")
        pmid_link = PUBMED_PMID_URL.format(pmid=pmid) if pmid else "N/A"

        lines.append(
            f"- `{score['code']}` ({score['tier']}) | PMID: `{pmid or 'None'}` | {status}"
        )
        lines.append(f"  Title: {title}")
        lines.append(f"  Journal/Date: {journal} ({pubdate})")
        lines.append(f"  Link: {pmid_link}")
        lines.append("")

    lines.append("## Summary")
    for label, count in sorted(status_counts.items()):
        lines.append(f"- {label}: {count}")
    lines.append("")
    lines.append("Retraction status: unverified (manual step required per-paper).")
    return "\n".join(lines)


def main() -> int:
    report = _build_report()
    out_dir = Path("reports") / "evidence_audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"organ_score_evidence_audit_{date.today().isoformat()}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

