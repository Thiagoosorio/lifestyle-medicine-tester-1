"""Service for managing biomarker definitions, results, and scoring."""

from db.database import get_connection
from datetime import date


def seed_biomarker_definitions():
    """Populate biomarker_definitions from config (idempotent).

    Uses INSERT OR IGNORE so new biomarkers added to config are picked up
    on existing databases without duplicating existing rows.
    """
    from config.biomarkers_data import BIOMARKER_DEFINITIONS
    conn = get_connection()
    for bm in BIOMARKER_DEFINITIONS:
        conn.execute(
            """INSERT OR IGNORE INTO biomarker_definitions
               (code, name, category, unit, standard_low, standard_high,
                optimal_low, optimal_high, critical_low, critical_high,
                description, clinical_note, pillar_id, sort_order)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                bm["code"], bm["name"], bm["category"], bm["unit"],
                bm.get("standard_low"), bm.get("standard_high"),
                bm.get("optimal_low"), bm.get("optimal_high"),
                bm.get("critical_low"), bm.get("critical_high"),
                bm.get("description"), bm.get("clinical_note"),
                bm.get("pillar_id"), bm.get("sort_order", 99),
            ),
        )
    conn.commit()
    conn.close()


def get_all_definitions():
    """Return all biomarker definitions ordered by sort_order."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM biomarker_definitions ORDER BY sort_order"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_definitions_by_category(category):
    """Return biomarker definitions for a specific category."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM biomarker_definitions WHERE category = ? ORDER BY sort_order",
        (category,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_definition_by_id(biomarker_id):
    """Return a single biomarker definition."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM biomarker_definitions WHERE id = ?", (biomarker_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def log_biomarker_result(user_id, biomarker_id, value, lab_date, lab_name=None, notes=None):
    """Log a biomarker result. Updates if same user/biomarker/date exists."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO biomarker_results (user_id, biomarker_id, value, lab_date, lab_name, notes)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id, biomarker_id, lab_date) DO UPDATE SET
             value = excluded.value, lab_name = excluded.lab_name, notes = excluded.notes""",
        (user_id, biomarker_id, value, lab_date, lab_name, notes),
    )
    conn.commit()
    conn.close()


def get_latest_results(user_id):
    """Get the most recent result for each biomarker for a user."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT br.*, bd.code, bd.name, bd.category, bd.unit,
                  bd.standard_low, bd.standard_high,
                  bd.optimal_low, bd.optimal_high,
                  bd.critical_low, bd.critical_high,
                  bd.description, bd.clinical_note
           FROM biomarker_results br
           JOIN biomarker_definitions bd ON bd.id = br.biomarker_id
           WHERE br.user_id = ?
             AND br.lab_date = (
               SELECT MAX(br2.lab_date) FROM biomarker_results br2
               WHERE br2.user_id = br.user_id AND br2.biomarker_id = br.biomarker_id
             )
           ORDER BY bd.sort_order""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_results_for_biomarker(user_id, biomarker_id):
    """Get all historical results for a specific biomarker."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT br.*, bd.code, bd.name, bd.unit,
                  bd.standard_low, bd.standard_high,
                  bd.optimal_low, bd.optimal_high,
                  bd.critical_low, bd.critical_high
           FROM biomarker_results br
           JOIN biomarker_definitions bd ON bd.id = br.biomarker_id
           WHERE br.user_id = ? AND br.biomarker_id = ?
           ORDER BY br.lab_date""",
        (user_id, biomarker_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def classify_result(value, definition):
    """Classify a result value against its definition ranges.
    Returns: 'critical_low', 'low', 'normal', 'optimal', 'high', 'critical_high'
    """
    if value is None:
        return "unknown"

    crit_low = definition.get("critical_low")
    crit_high = definition.get("critical_high")
    std_low = definition.get("standard_low")
    std_high = definition.get("standard_high")
    opt_low = definition.get("optimal_low")
    opt_high = definition.get("optimal_high")

    # Critical checks
    if crit_low is not None and value < crit_low:
        return "critical_low"
    if crit_high is not None and value > crit_high:
        return "critical_high"

    # Optimal check
    in_optimal = True
    if opt_low is not None and value < opt_low:
        in_optimal = False
    if opt_high is not None and value > opt_high:
        in_optimal = False
    if in_optimal and (opt_low is not None or opt_high is not None):
        return "optimal"

    # Standard check
    in_standard = True
    if std_low is not None and value < std_low:
        in_standard = False
    if std_high is not None and value > std_high:
        in_standard = False
    if in_standard:
        return "normal"

    # Outside standard
    if std_low is not None and value < std_low:
        return "low"
    return "high"


def get_classification_display(classification):
    """Return display properties for a classification."""
    displays = {
        "optimal": {"label": "Optimal", "color": "#30D158", "icon": "&#10004;"},
        "normal": {"label": "Normal", "color": "#64D2FF", "icon": "&#9679;"},
        "low": {"label": "Low", "color": "#FFD60A", "icon": "&#9660;"},
        "high": {"label": "High", "color": "#FF9F0A", "icon": "&#9650;"},
        "critical_low": {"label": "Critical Low", "color": "#FF453A", "icon": "&#10071;"},
        "critical_high": {"label": "Critical High", "color": "#FF453A", "icon": "&#10071;"},
        "unknown": {"label": "Unknown", "color": "#8E8E93", "icon": "&#8212;"},
    }
    return displays.get(classification, displays["unknown"])


def score_single_result(value, definition):
    """Score a single biomarker result (0-100)."""
    classification = classify_result(value, definition)
    scores = {
        "optimal": 100,
        "normal": 70,
        "low": 40,
        "high": 40,
        "critical_low": 10,
        "critical_high": 10,
        "unknown": 0,
    }
    return scores.get(classification, 0)


def calculate_biomarker_score(user_id):
    """Calculate composite biomarker score (0-100) using category weights."""
    from config.biomarkers_data import CATEGORY_WEIGHTS

    results = get_latest_results(user_id)
    if not results:
        return None

    weighted_sum = 0
    weight_total = 0

    for r in results:
        cat = r.get("category", "")
        cat_weight = CATEGORY_WEIGHTS.get(cat, 1.0)
        score = score_single_result(r["value"], r)
        weighted_sum += score * cat_weight
        weight_total += cat_weight

    if weight_total == 0:
        return None
    return round(weighted_sum / weight_total)


def get_biomarker_summary(user_id):
    """Get summary counts by classification for the latest results."""
    results = get_latest_results(user_id)
    summary = {"optimal": 0, "normal": 0, "low": 0, "high": 0, "critical": 0, "total": len(results)}
    for r in results:
        cls = classify_result(r["value"], r)
        if cls == "optimal":
            summary["optimal"] += 1
        elif cls == "normal":
            summary["normal"] += 1
        elif cls in ("low", "high"):
            summary[cls] += 1
        elif cls.startswith("critical"):
            summary["critical"] += 1
    return summary


def get_results_by_date(user_id, lab_date):
    """Get all biomarker results for a specific lab date."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT br.*, bd.code, bd.name, bd.category, bd.unit,
                  bd.standard_low, bd.standard_high,
                  bd.optimal_low, bd.optimal_high,
                  bd.critical_low, bd.critical_high
           FROM biomarker_results br
           JOIN biomarker_definitions bd ON bd.id = br.biomarker_id
           WHERE br.user_id = ? AND br.lab_date = ?
           ORDER BY bd.sort_order""",
        (user_id, lab_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_lab_dates(user_id):
    """Get all distinct lab dates for a user, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT lab_date FROM biomarker_results WHERE user_id = ? ORDER BY lab_date DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [r["lab_date"] for r in rows]
