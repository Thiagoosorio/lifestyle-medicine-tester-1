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

    Uses deviation-based severity for out-of-range values:
    - Within optimal range → 'optimal' (green)
    - Within standard range → 'normal' (blue)
    - Out of range, deviation ≤ 20% → 'borderline_low'/'borderline_high' (yellow)
    - Out of range, deviation > 20% → 'low'/'high' (red)
    - Beyond critical threshold → 'critical_low'/'critical_high' (red)

    Returns: 'critical_low', 'low', 'borderline_low', 'normal', 'optimal',
             'borderline_high', 'high', 'critical_high', 'unknown'
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

    # Outside standard — classify severity by deviation percentage
    if std_low is not None and value < std_low:
        if std_low > 0:
            deviation_pct = (std_low - value) / std_low * 100
        else:
            deviation_pct = 100
        if deviation_pct <= 20:
            return "borderline_low"
        return "low"

    if std_high is not None and value > std_high:
        if std_high > 0:
            deviation_pct = (value - std_high) / std_high * 100
        else:
            deviation_pct = 100
        if deviation_pct <= 20:
            return "borderline_high"
        return "high"

    return "normal"


def get_classification_display(classification):
    """Return display properties for a classification.

    Color scheme follows clinical lab reporting best practice:
    - Green: optimal range
    - Blue: normal/standard range
    - Yellow: borderline — slightly out of range (≤ 20% deviation)
    - Red: abnormal — significantly out of range (> 20% deviation or critical)
    """
    displays = {
        "optimal": {"label": "Optimal", "color": "#30D158", "icon": "&#10004;"},
        "normal": {"label": "Normal", "color": "#64D2FF", "icon": "&#9679;"},
        "borderline_low": {"label": "Borderline Low", "color": "#FFD60A", "icon": "&#9660;"},
        "borderline_high": {"label": "Borderline High", "color": "#FFD60A", "icon": "&#9650;"},
        "low": {"label": "Low", "color": "#FF453A", "icon": "&#9660;"},
        "high": {"label": "High", "color": "#FF453A", "icon": "&#9650;"},
        "critical_low": {"label": "Critical Low", "color": "#FF453A", "icon": "&#10071;"},
        "critical_high": {"label": "Critical High", "color": "#FF453A", "icon": "&#10071;"},
        "unknown": {"label": "Unknown", "color": "#AEAEB2", "icon": "&#8212;"},
    }
    return displays.get(classification, displays["unknown"])


def score_single_result(value, definition):
    """Score a single biomarker result (0-100)."""
    classification = classify_result(value, definition)
    scores = {
        "optimal": 100,
        "normal": 70,
        "borderline_low": 50,
        "borderline_high": 50,
        "low": 25,
        "high": 25,
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
    summary = {
        "optimal": 0, "normal": 0, "borderline": 0,
        "abnormal": 0, "critical": 0, "total": len(results),
    }
    for r in results:
        cls = classify_result(r["value"], r)
        if cls == "optimal":
            summary["optimal"] += 1
        elif cls == "normal":
            summary["normal"] += 1
        elif cls in ("borderline_low", "borderline_high"):
            summary["borderline"] += 1
        elif cls in ("low", "high"):
            summary["abnormal"] += 1
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


# ── BloodGPT AI Analysis Context ───────────────────────────────────────────

# Human-readable category labels for the AI prompt
_CATEGORY_LABELS = {
    "lipids":       "LIPID PANEL",
    "metabolic":    "METABOLIC PANEL",
    "inflammation": "INFLAMMATION MARKERS",
    "vitamins":     "VITAMINS & MINERALS",
    "hormones":     "HORMONES",
    "thyroid":      "THYROID PANEL",
    "liver":        "LIVER FUNCTION",
    "kidney":       "KIDNEY FUNCTION",
    "blood_count":  "COMPLETE BLOOD COUNT",
    "minerals":     "MINERALS & ELECTROLYTES",
}

_CLASSIFICATION_LABEL = {
    "optimal":        "OPTIMAL",
    "normal":         "NORMAL",
    "borderline_low": "BORDERLINE LOW",
    "borderline_high":"BORDERLINE HIGH",
    "low":            "LOW",
    "high":           "HIGH",
    "critical_low":   "CRITICAL LOW",
    "critical_high":  "CRITICAL HIGH",
    "unknown":        "UNKNOWN",
}


def _format_range(low, high, unit: str) -> str:
    """Format a standard or optimal range as a compact string."""
    if low is not None and high is not None:
        return f"{low}-{high} {unit}"
    if low is not None:
        return f">{low} {unit}"
    if high is not None:
        return f"<{high} {unit}"
    return "N/A"


def _deviation_str(value: float, definition: dict) -> str:
    """Return a +/-% deviation string vs the standard range boundary, or empty."""
    std_low = definition.get("standard_low")
    std_high = definition.get("standard_high")
    if std_low is not None and value < std_low and std_low != 0:
        pct = (std_low - value) / std_low * 100
        return f"-{pct:.0f}% below std"
    if std_high is not None and value > std_high and std_high != 0:
        pct = (value - std_high) / std_high * 100
        return f"+{pct:.0f}% above std"
    return ""


def get_blood_analysis_context(user_id: int, lab_date: str) -> str | None:
    """Assemble a structured text block of biomarker data for the BloodGPT AI prompt.

    Includes:
    - Current panel grouped by category with classification + deviation
    - Delta comparison vs the most recent previous lab date
    - Composite score and summary counts

    Returns None if fewer than 3 results are logged for the selected date.
    """
    results = get_results_by_date(user_id, lab_date)
    if len(results) < 3:
        return None

    # Get lab name from first result (optional field)
    lab_name = results[0].get("lab_name") or ""
    header = f"=== BLOOD PANEL — {lab_date}"
    if lab_name:
        header += f" ({lab_name})"
    header += " ==="

    # Group by category
    by_category: dict[str, list] = {}
    for r in results:
        cat = r.get("category", "other")
        by_category.setdefault(cat, []).append(r)

    lines: list[str] = [header, ""]

    for cat, cat_results in by_category.items():
        lines.append(_CATEGORY_LABELS.get(cat, cat.upper()) + ":")
        for r in cat_results:
            cls = classify_result(r["value"], r)
            cls_label = _CLASSIFICATION_LABEL.get(cls, cls.upper())
            std_range = _format_range(r.get("standard_low"), r.get("standard_high"), r["unit"])
            opt_range = _format_range(r.get("optimal_low"), r.get("optimal_high"), r["unit"])
            dev = _deviation_str(r["value"], r)
            dev_str = f" ({dev})" if dev else ""
            lines.append(
                f"  {r['name']}: {r['value']} {r['unit']}"
                f"  [Std: {std_range}, Optimal: {opt_range}]"
                f"  -> {cls_label}{dev_str}"
            )
        lines.append("")

    # Delta section — compare to the most recent *previous* lab date
    all_dates = get_lab_dates(user_id)
    try:
        current_idx = all_dates.index(lab_date)
        prev_date = all_dates[current_idx + 1] if current_idx + 1 < len(all_dates) else None
    except (ValueError, IndexError):
        prev_date = None

    if prev_date:
        prev_results = get_results_by_date(user_id, prev_date)
        prev_by_code: dict[str, dict] = {r["code"]: r for r in prev_results}

        delta_lines: list[str] = []
        for r in results:
            code = r["code"]
            if code not in prev_by_code:
                continue
            prev_val = prev_by_code[code]["value"]
            curr_val = r["value"]
            if prev_val is None or curr_val is None or prev_val == 0:
                continue
            delta = curr_val - prev_val
            delta_pct = (delta / abs(prev_val)) * 100

            # Only show changes > 5% or critical transitions
            curr_cls = classify_result(curr_val, r)
            prev_cls = classify_result(prev_val, r)
            is_zone_change = (curr_cls != prev_cls)
            if abs(delta_pct) < 5 and not is_zone_change:
                continue

            direction = "Improving" if (
                (curr_cls in ("optimal", "normal") and prev_cls not in ("optimal", "normal")) or
                (curr_cls == "optimal" and prev_cls != "optimal") or
                (delta_pct > 0 and r.get("optimal_low") is not None and curr_val > prev_val and curr_val <= (r.get("optimal_high") or curr_val + 1)) or
                # For high-is-bad markers (LDL, TG, glucose): decreasing is good
                (delta < 0 and curr_cls in ("optimal", "normal", "borderline_high") and prev_cls in ("high", "borderline_high", "critical_high"))
            ) else "Worsening"

            # Simple direction: improving if moving toward optimal, worsening if moving away
            if delta < 0 and curr_cls in ("high", "borderline_high", "critical_high"):
                direction = "Improving"
            elif delta > 0 and curr_cls in ("low", "borderline_low", "critical_low"):
                direction = "Improving"
            elif delta > 0 and curr_cls in ("high", "borderline_high", "critical_high"):
                direction = "Worsening"
            elif delta < 0 and curr_cls in ("low", "borderline_low", "critical_low"):
                direction = "Worsening"
            elif curr_cls in ("optimal", "normal") and prev_cls not in ("optimal", "normal"):
                direction = "Improving"
            elif curr_cls not in ("optimal", "normal") and prev_cls in ("optimal", "normal"):
                direction = "Worsening"
            else:
                direction = "Improving" if delta > 0 else "Worsening"

            arrow = "UP" if direction == "Improving" else "DOWN"
            zone_flag = " [ZONE CHANGE]" if is_zone_change else ""
            delta_lines.append(
                f"  {r['name']}: {prev_val} -> {curr_val} {r['unit']}"
                f"  ({delta:+.1f}, {delta_pct:+.1f}%)"
                f"  {arrow} {direction}{zone_flag}"
            )

        if delta_lines:
            # Calculate months between dates for velocity context
            try:
                from datetime import date as _date
                d1 = _date.fromisoformat(prev_date)
                d2 = _date.fromisoformat(lab_date)
                months = max(1, (d2 - d1).days // 30)
                lines.append(f"=== DELTA vs. PREVIOUS LABS ({prev_date}, ~{months} months ago) ===")
            except Exception:
                lines.append(f"=== DELTA vs. PREVIOUS LABS ({prev_date}) ===")
            lines.extend(delta_lines)
            lines.append("")
    else:
        lines.append("=== DELTA: No previous lab data available for comparison ===")
        lines.append("")

    # Composite score and summary
    score = calculate_biomarker_score(user_id)
    summary = get_biomarker_summary(user_id)
    score_label = "Excellent" if score >= 85 else "Good" if score >= 70 else "Fair" if score >= 50 else "Needs Attention"
    lines.append(
        f"=== COMPOSITE BIOMARKER SCORE: {score}/100 ({score_label}) ==="
    )
    lines.append(
        f"Optimal: {summary['optimal']} | Normal: {summary['normal']} | "
        f"Borderline: {summary['borderline']} | Abnormal: {summary['abnormal']} | "
        f"Critical: {summary['critical']} of {summary['total']} markers"
    )

    return "\n".join(lines)


def get_cached_analysis(user_id: int, lab_date: str):
    """Retrieve a cached BloodGPT analysis for a specific lab date, or None.

    Returns None if the cache table does not yet exist (first deploy before migration).
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT analysis_text, model_used, created_at
               FROM biomarker_ai_analysis
               WHERE user_id = ? AND lab_date = ? AND analysis_text != ''""",
            (user_id, lab_date),
        ).fetchone()
        return dict(row) if row else None
    except Exception:
        return None  # Table may not exist yet on first deploy
    finally:
        conn.close()


def save_blood_analysis(
    user_id: int,
    lab_date: str,
    analysis_text: str,
    model: str = "claude-sonnet-4-5-20250514",
) -> None:
    """Cache or update a BloodGPT AI analysis for a specific lab date.

    Silently no-ops if the cache table does not yet exist (first deploy before migration).
    """
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO biomarker_ai_analysis
               (user_id, lab_date, analysis_text, model_used)
               VALUES (?, ?, ?, ?)""",
            (user_id, lab_date, analysis_text, model),
        )
        conn.commit()
    except Exception:
        pass  # Table may not exist yet on first deploy
    finally:
        conn.close()
