"""Service for managing the research evidence library and linking evidence to app entities."""

from db.database import get_connection


def seed_evidence():
    """Populate the research_evidence table from config/evidence_data.py (idempotent)."""
    conn = get_connection()
    existing = conn.execute("SELECT COUNT(*) FROM research_evidence").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    from config.evidence_data import EVIDENCE_LIBRARY
    for entry in EVIDENCE_LIBRARY:
        conn.execute(
            """INSERT INTO research_evidence
               (pmid, doi, title, authors, journal, year, study_type,
                evidence_grade, pillar_id, summary, key_finding, effect_size,
                sample_size, population, dose_response, causation_note, tags, url,
                journal_tier, domain)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                entry.get("pmid"),
                entry.get("doi"),
                entry["title"],
                entry.get("authors"),
                entry.get("journal"),
                entry.get("year"),
                entry["study_type"],
                entry["evidence_grade"],
                entry.get("pillar_id"),
                entry["summary"],
                entry.get("key_finding"),
                entry.get("effect_size"),
                entry.get("sample_size"),
                entry.get("population"),
                entry.get("dose_response"),
                entry.get("causation_note"),
                entry.get("tags"),
                entry.get("url"),
                entry.get("journal_tier"),
                entry.get("domain"),
            ),
        )
    conn.commit()

    # Seed evidence links for protocols
    _seed_protocol_evidence_links(conn)
    conn.close()


def _seed_protocol_evidence_links(conn):
    """Link evidence to protocols based on matching tags/pillar."""
    from config.protocols_data import PROTOCOL_LIBRARY
    for proto in PROTOCOL_LIBRARY:
        linked_pmids = proto.get("linked_pmids", [])
        if not linked_pmids:
            continue
        # Get protocol ID
        proto_row = conn.execute(
            "SELECT id FROM protocols WHERE name = ?", (proto["name"],)
        ).fetchone()
        if not proto_row:
            continue
        proto_id = proto_row["id"]
        for pmid in linked_pmids:
            ev_row = conn.execute(
                "SELECT id FROM research_evidence WHERE pmid = ?", (str(pmid),)
            ).fetchone()
            if not ev_row:
                continue
            try:
                conn.execute(
                    """INSERT INTO evidence_links (evidence_id, entity_type, entity_id)
                       VALUES (?, 'protocol', ?)""",
                    (ev_row["id"], proto_id),
                )
            except Exception:
                pass  # duplicate
    conn.commit()


def get_evidence_for_pillar(pillar_id, grade=None):
    """Retrieve evidence for a specific pillar, optionally filtered by grade."""
    conn = get_connection()
    if grade:
        rows = conn.execute(
            "SELECT * FROM research_evidence WHERE pillar_id = ? AND evidence_grade = ? ORDER BY year DESC",
            (pillar_id, grade),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM research_evidence WHERE pillar_id = ? ORDER BY evidence_grade, year DESC",
            (pillar_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_evidence(grade=None):
    """Retrieve all evidence, optionally filtered by grade."""
    conn = get_connection()
    if grade:
        rows = conn.execute(
            "SELECT * FROM research_evidence WHERE evidence_grade = ? ORDER BY pillar_id, year DESC",
            (grade,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM research_evidence ORDER BY pillar_id, evidence_grade, year DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_evidence(query):
    """Full-text search across title, summary, key_finding, and tags."""
    conn = get_connection()
    pattern = f"%{query}%"
    rows = conn.execute(
        """SELECT * FROM research_evidence
           WHERE title LIKE ? OR summary LIKE ? OR key_finding LIKE ? OR tags LIKE ?
           ORDER BY evidence_grade, year DESC""",
        (pattern, pattern, pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_evidence_by_id(evidence_id):
    """Get a single evidence entry by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM research_evidence WHERE id = ?", (evidence_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_evidence_for_entity(entity_type, entity_id):
    """Get all evidence linked to a specific entity (protocol, lesson, etc.)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT re.* FROM research_evidence re
           JOIN evidence_links el ON el.evidence_id = re.id
           WHERE el.entity_type = ? AND el.entity_id = ?
           ORDER BY re.evidence_grade, re.year DESC""",
        (entity_type, entity_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def link_evidence(evidence_id, entity_type, entity_id, relevance_note=None):
    """Create a link between evidence and an entity."""
    conn = get_connection()
    conn.execute(
        """INSERT OR IGNORE INTO evidence_links (evidence_id, entity_type, entity_id, relevance_note)
           VALUES (?, ?, ?, ?)""",
        (evidence_id, entity_type, entity_id, relevance_note),
    )
    conn.commit()
    conn.close()


def get_evidence_for_domain(domain, grade=None):
    """Retrieve evidence for a specific research domain."""
    conn = get_connection()
    if grade:
        rows = conn.execute(
            "SELECT * FROM research_evidence WHERE domain = ? AND evidence_grade = ? ORDER BY year DESC",
            (domain, grade),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM research_evidence WHERE domain = ? ORDER BY evidence_grade, year DESC",
            (domain,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_evidence_stats():
    """Get summary statistics for the evidence library."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM research_evidence").fetchone()[0]
    by_grade = {}
    for row in conn.execute(
        "SELECT evidence_grade, COUNT(*) as cnt FROM research_evidence GROUP BY evidence_grade"
    ).fetchall():
        by_grade[row["evidence_grade"]] = row["cnt"]
    by_pillar = {}
    for row in conn.execute(
        """SELECT p.display_name, COUNT(re.id) as cnt
           FROM research_evidence re
           JOIN pillars p ON p.id = re.pillar_id
           GROUP BY re.pillar_id"""
    ).fetchall():
        by_pillar[row["display_name"]] = row["cnt"]
    by_tier = {}
    for row in conn.execute(
        "SELECT journal_tier, COUNT(*) as cnt FROM research_evidence WHERE journal_tier IS NOT NULL GROUP BY journal_tier"
    ).fetchall():
        by_tier[row["journal_tier"]] = row["cnt"]
    by_domain = {}
    for row in conn.execute(
        "SELECT domain, COUNT(*) as cnt FROM research_evidence WHERE domain IS NOT NULL GROUP BY domain"
    ).fetchall():
        by_domain[row["domain"]] = row["cnt"]
    conn.close()
    return {"total": total, "by_grade": by_grade, "by_pillar": by_pillar, "by_tier": by_tier, "by_domain": by_domain}
