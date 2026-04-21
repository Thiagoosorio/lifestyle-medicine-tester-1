"""Service for managing biomarker definitions, results, and scoring."""

import os
from pathlib import Path
from db.database import get_connection
from datetime import date
from dotenv import load_dotenv

from config.biomarkers_data import BIOMARKERS_BY_CODE, resolve_reference_range

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _effective_range(definition, age=None, sex=None):
    """Return the age/sex-resolved reference range for a biomarker.

    Falls back to the base ``standard_*`` / ``critical_*`` fields when neither
    ``age`` nor ``sex`` is provided. DB-sourced rows do not carry the
    ``variants`` list, so we look the full static definition up by ``code``.
    """
    if age is None and sex is None:
        return {
            "standard_low": definition.get("standard_low"),
            "standard_high": definition.get("standard_high"),
            "optimal_low": definition.get("optimal_low"),
            "optimal_high": definition.get("optimal_high"),
            "critical_low": definition.get("critical_low"),
            "critical_high": definition.get("critical_high"),
        }
    lookup = BIOMARKERS_BY_CODE.get(definition.get("code")) if definition.get("code") else None
    source = lookup if (lookup and lookup.get("variants")) else definition
    return resolve_reference_range(source, age=age, sex=sex)


def _attach_target_evidence(defn: dict) -> dict:
    """Attach evidence-confidence metadata for interpretation thresholds."""
    from config.biomarkers_data import TARGET_EVIDENCE_BY_CODE, TARGET_EVIDENCE_DEFAULT

    enriched = dict(defn)
    code = enriched.get("code")
    enriched["target_evidence"] = TARGET_EVIDENCE_BY_CODE.get(code, TARGET_EVIDENCE_DEFAULT)
    return enriched


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
    return [_attach_target_evidence(dict(r)) for r in rows]


def get_definitions_by_category(category):
    """Return biomarker definitions for a specific category."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM biomarker_definitions WHERE category = ? ORDER BY sort_order",
        (category,),
    ).fetchall()
    conn.close()
    return [_attach_target_evidence(dict(r)) for r in rows]


def get_definition_by_id(biomarker_id):
    """Return a single biomarker definition."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM biomarker_definitions WHERE id = ?", (biomarker_id,)
    ).fetchone()
    conn.close()
    return _attach_target_evidence(dict(row)) if row else None


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
    return [_attach_target_evidence(dict(r)) for r in rows]


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
    return [_attach_target_evidence(dict(r)) for r in rows]


def classify_result(value, definition, age=None, sex=None):
    """Classify a result value against lab reference and critical thresholds.

    Clinical buckets:
    - Within reference interval -> 'in_range'
    - Below reference interval -> 'low'
    - Above reference interval -> 'high'
    - Beyond critical threshold -> 'critical_low' / 'critical_high'

    When ``age`` and/or ``sex`` are provided, sex/age-specific reference ranges
    are resolved via ``resolve_reference_range`` so biomarkers with variants
    (hemoglobin, ferritin, creatinine, testosterone, etc.) are graded against
    the patient's applicable band.

    Returns: 'critical_low', 'low', 'in_range', 'high', 'critical_high', 'unknown'
    """
    if value is None:
        return "unknown"

    ranges = _effective_range(definition, age=age, sex=sex)
    crit_low = ranges["critical_low"]
    crit_high = ranges["critical_high"]
    std_low = ranges["standard_low"]
    std_high = ranges["standard_high"]

    # Critical checks first
    if crit_low is not None and value < crit_low:
        return "critical_low"
    if crit_high is not None and value > crit_high:
        return "critical_high"

    # Need at least one reference boundary to classify non-critical values
    if std_low is None and std_high is None:
        return "unknown"

    if std_low is not None and value < std_low:
        return "low"

    if std_high is not None and value > std_high:
        return "high"

    return "in_range"


def get_classification_display(classification):
    """Return display properties for a lab classification."""
    displays = {
        "in_range": {"label": "In Range", "color": "#30D158", "icon": "&#10004;"},
        "low": {"label": "Below Range", "color": "#FF9F0A", "icon": "&#9660;"},
        "high": {"label": "Above Range", "color": "#FF9F0A", "icon": "&#9650;"},
        "critical_low": {"label": "Critical Low", "color": "#FF453A", "icon": "&#10071;"},
        "critical_high": {"label": "Critical High", "color": "#FF453A", "icon": "&#10071;"},
        "unknown": {"label": "Unknown", "color": "#AEAEB2", "icon": "&#8212;"},
    }
    return displays.get(classification, displays["unknown"])


def score_single_result(value, definition):
    """Score a single biomarker result (0-100)."""
    classification = classify_result(value, definition)
    scores = {
        "in_range": 100,
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
    summary = {
        "in_range": 0,
        "low": 0,
        "high": 0,
        "abnormal": 0,
        "critical": 0,
        "total": len(results),
    }
    for r in results:
        cls = classify_result(r["value"], r)
        if cls == "in_range":
            summary["in_range"] += 1
        elif cls in ("low", "high"):
            summary[cls] += 1
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
    return [_attach_target_evidence(dict(r)) for r in rows]


def get_lab_dates(user_id):
    """Get all distinct lab dates for a user, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT lab_date FROM biomarker_results WHERE user_id = ? ORDER BY lab_date DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [r["lab_date"] for r in rows]


# ---------------------------- BloodGPT AI Analysis Context ----------------------------

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
    "in_range":       "IN RANGE",
    "low":            "BELOW RANGE",
    "high":           "ABOVE RANGE",
    "critical_low":   "CRITICAL LOW",
    "critical_high":  "CRITICAL HIGH",
    "unknown":        "UNKNOWN",
}

def _format_range(low, high, unit: str) -> str:
    """Format a reference range as a compact string."""
    if low is not None and high is not None:
        return f"{low}-{high} {unit}"
    if low is not None:
        return f">{low} {unit}"
    if high is not None:
        return f"<{high} {unit}"
    return "N/A"


def _deviation_str(value: float, definition: dict, age=None, sex=None) -> str:
    """Return a +/-% deviation string vs the standard range boundary, or empty."""
    ranges = _effective_range(definition, age=age, sex=sex)
    std_low = ranges["standard_low"]
    std_high = ranges["standard_high"]
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
    header = f"=== BLOOD PANEL - {lab_date}"
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
            dev = _deviation_str(r["value"], r)
            dev_str = f" ({dev})" if dev else ""
            lines.append(
                f"  {r['name']}: {r['value']} {r['unit']}"
                f"  [Ref: {std_range}]"
                f"  -> {cls_label}{dev_str}"
            )
        lines.append("")

    # Delta section - compare to the most recent *previous* lab date
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

            high_classes = {"high", "critical_high"}
            low_classes = {"low", "critical_low"}

            if curr_cls == "in_range" and prev_cls != "in_range":
                direction = "Improving"
            elif curr_cls != "in_range" and prev_cls == "in_range":
                direction = "Worsening"
            elif curr_cls in high_classes and prev_cls in high_classes:
                direction = "Improving" if delta < 0 else "Worsening"
            elif curr_cls in low_classes and prev_cls in low_classes:
                direction = "Improving" if delta > 0 else "Worsening"
            else:
                direction = "Improving" if is_zone_change else "Worsening"

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
        f"In range: {summary['in_range']} | Below range: {summary['low']} | "
        f"Above range: {summary['high']} | Abnormal: {summary['abnormal']} | "
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
    model: str = "claude-sonnet-4-20250514",
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


# ---------------------------- PDF Lab Report Extraction ----------------------------

def extract_biomarkers_from_pdf(pdf_bytes: bytes, definitions: list) -> list[dict]:
    """Use Claude to extract biomarker values from a PDF blood test report.

    Strategy:
    1. Extract text from PDF with pypdf (fast, cheap, works for digital PDFs)
    2. Send extracted text to Claude to parse biomarker names + values
    3. Multi-level fuzzy matching against our definitions on our side

    Returns:
        List of dicts: {biomarker_id, code, name, value, unit, lab_date, lab_name}
        lab_date/lab_name are auto-detected from the PDF (may be None).
    Raises:
        Exception: propagated so the UI can display the real error message.
    """
    import anthropic
    import json
    import re
    import io

    # ---- Step 1: Extract text from PDF ----
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for page in reader.pages:
            pages_text.append(page.extract_text() or "")
        pdf_text = "\n".join(pages_text).strip()
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc

    if len(pdf_text) < 20:
        raise ValueError(
            "PDF has no readable text - it may be a scanned image. "
            "Please use a digital PDF (not a photo/scan)."
        )

    # ---- Step 2: Ask Claude to parse the lab text ----
    prompt_text = (
        "Below is text from a blood test lab report PDF.\n"
        "Extract every numeric lab result AND the report metadata.\n\n"
        "Return ONLY a valid JSON object with this structure:\n"
        "{\n"
        '  "lab_date": "YYYY-MM-DD or null",\n'
        '  "lab_name": "laboratory/hospital name or null",\n'
        '  "results": [\n'
        '    {"name": "<biomarker name>", "value": <number>, "unit": "<unit>"},\n'
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "Metadata rules:\n"
        "- lab_date: the SAMPLE COLLECTION date (not print/report date).\n"
        "  Look for 'Collection date:', 'Sampling:', 'Date:', 'Data do exame:'\n"
        "  Convert any format (DD/MM/YYYY, DD Mon YYYY, etc.) to YYYY-MM-DD.\n"
        "- lab_name: the lab or hospital (e.g. 'Cleveland Clinic', 'Cerba Belgium')\n\n"
        "Result rules:\n"
        "- Include ALL numeric results (even if abnormal or flagged)\n"
        "- For '<X' or '>X' values (e.g. '<0.2'), use X as the number\n"
        "- The text may have spaced-out characters (e.g. 'C 3' means 'C3')\n"
        "- Skip text-only results (Positive/Negative/See comment)\n"
        "- Return ONLY the JSON object\n\n"
        "--- LAB REPORT TEXT ---\n"
        f"{pdf_text}"
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt_text}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    # Try to parse as JSON object first, then fall back to array
    detected_date = None
    detected_lab = None
    extracted_raw = []

    # Find JSON object or array
    json_obj_match = re.search(r'\{.*\}', raw, re.DOTALL)
    json_arr_match = re.search(r'\[.*\]', raw, re.DOTALL)

    if json_obj_match:
        try:
            parsed = json.loads(json_obj_match.group())
            if isinstance(parsed, dict) and "results" in parsed:
                detected_date = parsed.get("lab_date")
                detected_lab = parsed.get("lab_name")
                extracted_raw = parsed.get("results", [])
            elif isinstance(parsed, dict):
                # Single result object - wrap in list
                extracted_raw = [parsed]
        except json.JSONDecodeError:
            pass

    if not extracted_raw and json_arr_match:
        try:
            extracted_raw = json.loads(json_arr_match.group())
        except json.JSONDecodeError:
            pass

    if not extracted_raw:
        raise ValueError(f"Could not parse results from response: {raw[:400]}")

    # ---- Lookup tables ----
    def _norm(s: str) -> str:
        """Lowercase, strip all non-alphanumeric for fuzzy comparison."""
        return re.sub(r'[^a-z0-9]', '', s.lower())

    defs_by_code = {d["code"]: d for d in definitions}
    defs_by_name_exact = {d["name"].lower(): d for d in definitions}
    # Normalized name + normalized code-as-words
    defs_by_norm: dict[str, dict] = {}
    for d in definitions:
        defs_by_norm[_norm(d["name"])] = d
        defs_by_norm[_norm(d["code"].replace("_", " "))] = d

    # Common abbreviations / synonyms -> internal code
    ALIASES = {
        # CBC / Haematology
        "wbc": "wbc_count", "rbc": "rbc_count",
        "hgb": "hemoglobin", "hb": "hemoglobin",
        "haemoglobin": "hemoglobin", "hemoglobina": "hemoglobin",
        "hct": "hematocrit", "haematocrit": "hematocrit",
        "plt": "platelet_count", "platelets": "platelet_count",
        "plaquetas": "platelet_count", "thrombocytes": "platelet_count",
        "mcv": "mcv", "mch": "mch", "mchc": "mchc", "rdw": "rdw",
        "neutrophils": "neutrophils", "neutrofilos": "neutrophils",
        "lymphocytes": "lymphocytes", "linfocitos": "lymphocytes",
        "monocytes": "monocytes", "monocitos": "monocytes",
        "eosinophils": "eosinophils", "eosinofilos": "eosinophils",
        "basophils": "basophils", "basofilos": "basophils",
        # Glucose / Diabetes
        "glu": "fasting_glucose", "gluc": "fasting_glucose",
        "glicose": "fasting_glucose", "glucose": "fasting_glucose",
        "fastingglucose": "fasting_glucose",
        "hba1c": "hba1c", "a1c": "hba1c", "hbaic": "hba1c",
        "glycatedhemoglobin": "hba1c", "glycatedhaemoglobin": "hba1c",
        "hemoglobinaglicada": "hba1c",
        # Lipids
        "tg": "triglycerides", "trig": "triglycerides",
        "triglicerides": "triglycerides", "trigliceridos": "triglycerides",
        "hdl": "hdl_cholesterol", "hdlc": "hdl_cholesterol",
        "ldl": "ldl_cholesterol", "ldlc": "ldl_cholesterol",
        "tc": "total_cholesterol", "chol": "total_cholesterol",
        "totalcholesterol": "total_cholesterol", "colesterol": "total_cholesterol",
        "nonhdlcholesterol": "non_hdl_cholesterol", "nonhdl": "non_hdl_cholesterol",
        # Liver
        "alt": "alt", "alat": "alt", "alanineaminotransferase": "alt",
        "ast": "ast", "asat": "ast", "aspartateaminotransferase": "ast",
        "ggt": "ggt", "gammaglutamyltransferase": "ggt",
        "gammaglutamyltranspeptidase": "ggt",
        "alp": "alp", "alkalinephosphatase": "alp", "fosfatasealcalina": "alp",
        "tb": "total_bilirubin", "bilirubin": "total_bilirubin",
        "bilirrubina": "total_bilirubin", "totalbilirubin": "total_bilirubin",
        "alb": "albumin", "albumina": "albumin",
        # Kidney
        "cr": "creatinine", "cre": "creatinine", "creat": "creatinine",
        "creatinina": "creatinine",
        "bun": "bun", "ureianitrogen": "bun", "ureianitrogenio": "bun",
        "urea": "urea",
        "egfr": "egfr", "mdrdegfr": "egfr", "ckdepiegfr": "egfr",
        "uricacid": "uric_acid", "acidourico": "uric_acid",
        # Thyroid
        "tsh": "tsh", "thyroidstimulatinghormone": "tsh",
        "ft4": "free_t4", "freethyroxine": "free_t4", "t4livre": "free_t4",
        "ft3": "free_t3", "freetriiodothyronine": "free_t3", "t3livre": "free_t3",
        # Iron
        "ferr": "ferritin", "ferritina": "ferritin",
        "ironserum": "serum_iron", "serumferrum": "serum_iron",
        "tibc": "tibc", "transferrin": "transferrin",
        # Vitamins / Minerals
        "25ohd": "vitamin_d25", "vitd": "vitamin_d25",
        "vitamind": "vitamin_d25", "calcidiol": "vitamin_d25",
        "b12": "vitamin_b12", "vitb12": "vitamin_b12",
        "cobalamin": "vitamin_b12", "cianocobalamina": "vitamin_b12",
        "folate": "folate", "folicacid": "folate", "acidofolico": "folate",
        "zinc": "zinc", "zinco": "zinc",
        "magnesium": "magnesium", "magnesio": "magnesium",
        # Inflammation / Cardiac
        "crp": "hs_crp", "hscrp": "hs_crp", "hsCRP": "hs_crp",
        "highsensitivitycrp": "hs_crp", "ultrasensiblecrp": "hs_crp",
        "ck": "ck_cpk", "cpk": "ck_cpk", "creatinekinase": "ck_cpk",
        # Hormones
        "freetestosterone": "free_testosterone", "testosteronelivreserum": "free_testosterone",
        "testosterone": "total_testosterone", "testosterona": "total_testosterone",
        "shbg": "shbg", "sexhormonebindingglobulin": "shbg",
        "e2": "estradiol", "estradiol": "estradiol", "oestradiol": "estradiol",
        "prog": "progesterone", "progesterona": "progesterone",
        "fsh": "fsh", "folliclestimulatinghamormone": "fsh",
        "lh": "lh", "luteinizinghormone": "lh",
        "prolactin": "prolactin", "prolactina": "prolactin",
        "cortisol": "cortisol", "cortisola": "cortisol",
        "gh": "growth_hormone", "growthhormone": "growth_hormone",
        "igf1": "igf1", "igf1insulinlikegrowthfactor": "igf1",
        "insulinlikegrowthfactor1": "igf1",
        "dheas": "dhea_s", "dehydroepiandrosterone": "dhea_s",
        "dhea": "dhea_s",
        "psa": "psa", "prostatespecificantigen": "psa",
    }

    results = []
    unmatched = []
    seen_ids: set[int] = set()

    for item in extracted_raw:
        raw_name = str(item.get("name", "")).strip()
        val = item.get("value")
        if not raw_name or val is None:
            continue
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue

        defn = None
        # 1. Exact name match (case-insensitive)
        defn = defs_by_name_exact.get(raw_name.lower())
        # 2. Normalized match (strip all punctuation/spaces)
        if not defn:
            defn = defs_by_norm.get(_norm(raw_name))
        # 3. Alias lookup
        if not defn:
            alias_code = ALIASES.get(_norm(raw_name))
            if alias_code:
                defn = defs_by_code.get(alias_code)
        # 4. Partial containment match (one normalized name contains the other)
        if not defn:
            norm_input = _norm(raw_name)
            if len(norm_input) >= 3:
                for norm_key, d in defs_by_norm.items():
                    if len(norm_key) >= 3 and (norm_input in norm_key or norm_key in norm_input):
                        defn = d
                        break

        if defn and val >= 0 and defn["id"] not in seen_ids:
            seen_ids.add(defn["id"])
            results.append({
                "biomarker_id": defn["id"],
                "code":         defn["code"],
                "name":         defn["name"],
                "value":        val,
                "unit":         defn["unit"],
                "lab_date":     detected_date,
                "lab_name":     detected_lab,
            })
        elif not defn and val >= 0:
            unmatched.append({
                "name": raw_name,
                "value": val,
                "unit": str(item.get("unit", "")),
            })

    return results, unmatched








