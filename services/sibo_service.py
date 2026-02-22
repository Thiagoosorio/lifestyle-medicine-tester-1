"""Service for SIBO & FODMAP Tracker: symptom logging, food diary, phase management, correlations."""

import json
import math
from datetime import date, timedelta
from db.database import get_connection
from config.sibo_data import FODMAP_FOODS, GI_SYMPTOMS, FODMAP_GROUPS


# ══════════════════════════════════════════════════════════════════════════════
# SYMPTOM TRACKING
# ══════════════════════════════════════════════════════════════════════════════

def log_symptoms(user_id, log_date, symptoms_dict, notes=None):
    """Save daily symptom scores. Computes overall_score as rounded mean."""
    vals = [v for v in symptoms_dict.values() if v is not None]
    # Normalize: diarrhea/constipation are 0-3, others 0-10. Scale 0-3 to 0-10 for averaging.
    normalized = []
    for key, val in symptoms_dict.items():
        if val is None:
            continue
        sym = GI_SYMPTOMS.get(key, {})
        max_val = sym.get("max", 10)
        normalized.append(val * 10 / max_val if max_val != 10 else val)
    overall = round(sum(normalized) / len(normalized)) if normalized else 0

    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO sibo_symptom_logs
               (user_id, log_date, bloating, abdominal_pain, gas,
                diarrhea, constipation, nausea, fatigue, overall_score, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, log_date,
             symptoms_dict.get("bloating"),
             symptoms_dict.get("abdominal_pain"),
             symptoms_dict.get("gas"),
             symptoms_dict.get("diarrhea"),
             symptoms_dict.get("constipation"),
             symptoms_dict.get("nausea"),
             symptoms_dict.get("fatigue"),
             overall, notes),
        )
        conn.commit()
    finally:
        conn.close()
    _update_log_counts(user_id)


def get_symptom_log(user_id, log_date):
    """Get a single day's symptom log."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM sibo_symptom_logs WHERE user_id = ? AND log_date = ?",
            (user_id, log_date),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_symptom_history(user_id, days=30):
    """Get recent symptom logs."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM sibo_symptom_logs
               WHERE user_id = ? AND log_date >= ?
               ORDER BY log_date DESC""",
            (user_id, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_symptom_averages(user_id, days=30):
    """Compute mean per symptom over a period."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT
                  COUNT(*) as n,
                  COALESCE(AVG(bloating), 0) as avg_bloating,
                  COALESCE(AVG(abdominal_pain), 0) as avg_pain,
                  COALESCE(AVG(gas), 0) as avg_gas,
                  COALESCE(AVG(diarrhea), 0) as avg_diarrhea,
                  COALESCE(AVG(constipation), 0) as avg_constipation,
                  COALESCE(AVG(nausea), 0) as avg_nausea,
                  COALESCE(AVG(fatigue), 0) as avg_fatigue,
                  COALESCE(AVG(overall_score), 0) as avg_overall
               FROM sibo_symptom_logs
               WHERE user_id = ? AND log_date >= ?""",
            (user_id, cutoff),
        ).fetchone()
        if not row or row["n"] == 0:
            return None
        return {
            "n": row["n"],
            "bloating": round(row["avg_bloating"], 1),
            "abdominal_pain": round(row["avg_pain"], 1),
            "gas": round(row["avg_gas"], 1),
            "diarrhea": round(row["avg_diarrhea"], 1),
            "constipation": round(row["avg_constipation"], 1),
            "nausea": round(row["avg_nausea"], 1),
            "fatigue": round(row["avg_fatigue"], 1),
            "overall": round(row["avg_overall"], 1),
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# FODMAP FOOD DIARY
# ══════════════════════════════════════════════════════════════════════════════

def log_fodmap_food(user_id, log_date, meal_type, food_name,
                    food_category=None, serving_size=None, serving_unit=None,
                    fodmap_rating=None, fodmap_groups=None, notes=None):
    """Save a food entry with FODMAP metadata."""
    groups_json = json.dumps(fodmap_groups) if fodmap_groups else "[]"
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO sibo_food_logs
               (user_id, log_date, meal_type, food_name, food_category,
                serving_size, serving_unit, fodmap_rating, fodmap_groups, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, log_date, meal_type, food_name, food_category,
             serving_size, serving_unit, fodmap_rating, groups_json, notes),
        )
        conn.commit()
    finally:
        conn.close()
    _update_log_counts(user_id)


def get_food_log(user_id, log_date):
    """Get all foods logged for a day."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM sibo_food_logs
               WHERE user_id = ? AND log_date = ?
               ORDER BY created_at""",
            (user_id, log_date),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["fodmap_groups_list"] = json.loads(d.get("fodmap_groups", "[]"))
            except (json.JSONDecodeError, TypeError):
                d["fodmap_groups_list"] = []
            result.append(d)
        return result
    finally:
        conn.close()


def get_food_history(user_id, days=30):
    """Get recent food log entries."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM sibo_food_logs
               WHERE user_id = ? AND log_date >= ?
               ORDER BY log_date DESC, created_at DESC""",
            (user_id, cutoff),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["fodmap_groups_list"] = json.loads(d.get("fodmap_groups", "[]"))
            except (json.JSONDecodeError, TypeError):
                d["fodmap_groups_list"] = []
            result.append(d)
        return result
    finally:
        conn.close()


def search_fodmap_foods(query):
    """Search FODMAP_FOODS config by name (case-insensitive)."""
    q = query.lower().strip()
    if not q:
        return FODMAP_FOODS
    return [f for f in FODMAP_FOODS if q in f[0].lower()]


def get_daily_fodmap_exposure(user_id, log_date):
    """Compute daily FODMAP group exposure from food logs."""
    foods = get_food_log(user_id, log_date)
    exposure = {g: 0 for g in FODMAP_GROUPS}
    for f in foods:
        for group in f.get("fodmap_groups_list", []):
            if group in exposure:
                servings = f.get("serving_size") or 1
                exposure[group] += servings
    return exposure


# ══════════════════════════════════════════════════════════════════════════════
# PHASE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def start_fodmap_phase(user_id, phase, reintro_group=None, notes=None):
    """Begin a new Low-FODMAP phase. Closes any previous active phase."""
    today_str = date.today().isoformat()
    conn = get_connection()
    try:
        # Close any open phase
        conn.execute(
            """UPDATE sibo_fodmap_phase SET ended_date = ?
               WHERE user_id = ? AND ended_date IS NULL""",
            (today_str, user_id),
        )
        conn.execute(
            """INSERT INTO sibo_fodmap_phase
               (user_id, phase, started_date, reintro_group, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, phase, today_str, reintro_group, notes),
        )
        # Update user state
        _ensure_user_state(conn, user_id)
        conn.execute(
            """UPDATE sibo_user_state
               SET current_phase = ?, phase_start = ?, active_diet = 'low_fodmap',
                   updated_at = datetime('now')
               WHERE user_id = ?""",
            (phase, today_str, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_current_phase(user_id):
    """Get the active (un-ended) phase record."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT * FROM sibo_fodmap_phase
               WHERE user_id = ? AND ended_date IS NULL
               ORDER BY started_date DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def end_fodmap_phase(user_id):
    """Close the current active phase."""
    today_str = date.today().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE sibo_fodmap_phase SET ended_date = ?
               WHERE user_id = ? AND ended_date IS NULL""",
            (today_str, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def is_in_washout(user_id):
    """Check if currently in a 3-day washout period after a reintroduction challenge."""
    today_str = date.today().isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT washout_end FROM sibo_reintro_challenges
               WHERE user_id = ? AND washout_end >= ?
               ORDER BY washout_end DESC LIMIT 1""",
            (user_id, today_str),
        ).fetchone()
        if row:
            return {"in_washout": True, "washout_end": row["washout_end"]}
        return {"in_washout": False, "washout_end": None}
    finally:
        conn.close()


def get_phase_history(user_id):
    """Get all phase records for a user."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM sibo_fodmap_phase
               WHERE user_id = ? ORDER BY started_date DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# REINTRODUCTION CHALLENGES
# ══════════════════════════════════════════════════════════════════════════════

def start_reintro_challenge(user_id, fodmap_group, challenge_food):
    """Begin a 3-day reintroduction challenge. Returns challenge ID or None if in washout."""
    washout = is_in_washout(user_id)
    if washout["in_washout"]:
        return None

    today = date.today()
    start_str = today.isoformat()
    washout_end = (today + timedelta(days=6)).isoformat()  # 3 challenge + 3 washout

    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO sibo_reintro_challenges
               (user_id, fodmap_group, challenge_food, start_date, washout_end)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, fodmap_group, challenge_food, start_str, washout_end),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def log_challenge_day(user_id, challenge_id, day_num, symptoms_dict):
    """Log symptoms for a challenge day (1, 2, or 3)."""
    col_map = {1: "day1_symptoms", 2: "day2_symptoms", 3: "day3_symptoms"}
    col = col_map.get(day_num)
    if not col:
        return
    symptoms_json = json.dumps(symptoms_dict)
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE sibo_reintro_challenges SET {col} = ? WHERE id = ? AND user_id = ?",
            (symptoms_json, challenge_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def complete_challenge(user_id, challenge_id, tolerance):
    """Mark a challenge as complete with tolerance result."""
    today_str = date.today().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE sibo_reintro_challenges
               SET end_date = ?, tolerance = ?
               WHERE id = ? AND user_id = ?""",
            (today_str, tolerance, challenge_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_active_challenge(user_id):
    """Get the currently active (un-completed) challenge."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT * FROM sibo_reintro_challenges
               WHERE user_id = ? AND tolerance IS NULL
               ORDER BY start_date DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ("day1_symptoms", "day2_symptoms", "day3_symptoms"):
            try:
                d[key + "_parsed"] = json.loads(d[key]) if d[key] else None
            except (json.JSONDecodeError, TypeError):
                d[key + "_parsed"] = None
        return d
    finally:
        conn.close()


def get_challenge_history(user_id):
    """Get all completed challenges."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM sibo_reintro_challenges
               WHERE user_id = ? AND tolerance IS NOT NULL
               ORDER BY start_date DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_tolerance_summary(user_id):
    """Get per-FODMAP-group tolerance results from completed challenges."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT fodmap_group, tolerance, challenge_food, start_date
               FROM sibo_reintro_challenges
               WHERE user_id = ? AND tolerance IS NOT NULL
               ORDER BY start_date DESC""",
            (user_id,),
        ).fetchall()
        summary = {}
        for r in rows:
            group = r["fodmap_group"]
            if group not in summary:
                summary[group] = {
                    "tolerance": r["tolerance"],
                    "food": r["challenge_food"],
                    "date": r["start_date"],
                }
        return summary
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# CORRELATION ENGINE — Spearman rho (pure Python, no scipy)
# ══════════════════════════════════════════════════════════════════════════════

def compute_correlations(user_id, days=90):
    """Compute Spearman rho between FODMAP group daily exposure and symptom scores.

    Returns a list of dicts: [{group, symptom, rho, p, n, strength}, ...]
    Only returns results where n >= 10.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    try:
        # Get daily symptom data
        symptom_rows = conn.execute(
            """SELECT log_date, bloating, abdominal_pain, gas, nausea, fatigue, overall_score
               FROM sibo_symptom_logs
               WHERE user_id = ? AND log_date >= ?""",
            (user_id, cutoff),
        ).fetchall()

        # Get daily food data
        food_rows = conn.execute(
            """SELECT log_date, fodmap_groups, serving_size
               FROM sibo_food_logs
               WHERE user_id = ? AND log_date >= ?""",
            (user_id, cutoff),
        ).fetchall()
    finally:
        conn.close()

    if not symptom_rows or not food_rows:
        return []

    # Build per-day symptom lookup
    symptom_by_date = {}
    for r in symptom_rows:
        symptom_by_date[r["log_date"]] = dict(r)

    # Build per-day FODMAP group exposure
    exposure_by_date = {}
    for r in food_rows:
        d = r["log_date"]
        if d not in exposure_by_date:
            exposure_by_date[d] = {g: 0.0 for g in FODMAP_GROUPS}
        try:
            groups = json.loads(r["fodmap_groups"]) if r["fodmap_groups"] else []
        except (json.JSONDecodeError, TypeError):
            groups = []
        servings = r["serving_size"] if r["serving_size"] else 1.0
        for g in groups:
            if g in exposure_by_date[d]:
                exposure_by_date[d][g] += servings

    # Find dates with both symptom and food data
    common_dates = sorted(set(symptom_by_date.keys()) & set(exposure_by_date.keys()))

    results = []
    symptom_keys = ["bloating", "abdominal_pain", "gas", "nausea", "fatigue", "overall_score"]

    for group in FODMAP_GROUPS:
        for symptom in symptom_keys:
            x = []
            y = []
            for d in common_dates:
                exp = exposure_by_date[d].get(group, 0)
                sym = symptom_by_date[d].get(symptom)
                if sym is not None:
                    x.append(exp)
                    y.append(float(sym))

            if len(x) < 10:
                continue

            rho, p = _spearman_rho(x, y)
            if rho is None:
                continue

            strength = _interpret_strength(abs(rho))
            results.append({
                "group": group,
                "symptom": symptom,
                "rho": round(rho, 3),
                "p": round(p, 4) if p is not None else None,
                "n": len(x),
                "strength": strength,
            })

    # Sort by absolute rho descending
    results.sort(key=lambda r: abs(r["rho"]), reverse=True)
    return results


def _spearman_rho(x, y):
    """Compute Spearman rank correlation coefficient (pure Python)."""
    n = len(x)
    if n < 10:
        return None, None

    rx = _rank(x)
    ry = _rank(y)
    d_sq = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    rho = 1 - (6 * d_sq) / (n * (n ** 2 - 1))

    # t-approximation for two-tailed p-value
    if abs(rho) >= 1.0:
        return rho, 0.0
    t_stat = rho * math.sqrt((n - 2) / (1 - rho ** 2))
    df = n - 2
    p = 2.0 * (1.0 - _t_cdf(abs(t_stat), df))
    return rho, p


def _rank(arr):
    """Assign ranks to an array, averaging ties."""
    n = len(arr)
    sorted_idx = sorted(range(n), key=lambda i: arr[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and arr[sorted_idx[j + 1]] == arr[sorted_idx[j]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[sorted_idx[k]] = avg_rank
        i = j + 1
    return ranks


def _t_cdf(t, df):
    """Approximate the CDF of the t-distribution using the regularized incomplete beta function.

    Uses a simple series approximation sufficient for display purposes.
    """
    x = df / (df + t * t)
    # Use the regularized incomplete beta function I_x(df/2, 1/2)
    # Approximate with a continued fraction / series for large enough df
    a = df / 2.0
    b = 0.5
    result = _regularized_beta(x, a, b)
    return 1.0 - 0.5 * result


def _regularized_beta(x, a, b, max_iter=200, tol=1e-10):
    """Regularized incomplete beta function I_x(a, b) via continued fraction."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    # Use the continued fraction representation
    # First compute the log of the front factor
    lbeta = _log_beta(a, b)
    front = math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta) / a

    # Lentz's method for continued fraction
    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    f = d

    for m in range(1, max_iter + 1):
        # Even step
        m2 = 2 * m
        num = m * (b - m) * x / ((a + m2 - 1) * (a + m2))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        f *= c * d

        # Odd step
        num = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = c * d
        f *= delta

        if abs(delta - 1.0) < tol:
            break

    return front * f


def _log_beta(a, b):
    """Log of the beta function B(a, b) = Gamma(a)*Gamma(b)/Gamma(a+b)."""
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _interpret_strength(abs_rho):
    """Interpret the strength of a Spearman correlation coefficient."""
    if abs_rho < 0.1:
        return "negligible"
    elif abs_rho < 0.3:
        return "weak"
    elif abs_rho < 0.5:
        return "moderate"
    elif abs_rho < 0.7:
        return "strong"
    else:
        return "very_strong"


# ══════════════════════════════════════════════════════════════════════════════
# USER STATE
# ══════════════════════════════════════════════════════════════════════════════

def get_or_create_state(user_id):
    """Get or create the sibo_user_state row."""
    conn = get_connection()
    try:
        _ensure_user_state(conn, user_id)
        row = conn.execute(
            "SELECT * FROM sibo_user_state WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _ensure_user_state(conn, user_id):
    """Ensure a sibo_user_state row exists."""
    conn.execute(
        """INSERT OR IGNORE INTO sibo_user_state (user_id) VALUES (?)""",
        (user_id,),
    )
    conn.commit()


def _update_log_counts(user_id):
    """Refresh cached log counts in sibo_user_state."""
    conn = get_connection()
    try:
        _ensure_user_state(conn, user_id)
        sym_count = conn.execute(
            "SELECT COUNT(*) FROM sibo_symptom_logs WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        food_count = conn.execute(
            "SELECT COUNT(*) FROM sibo_food_logs WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        conn.execute(
            """UPDATE sibo_user_state
               SET total_symptom_logs = ?, total_food_logs = ?, updated_at = datetime('now')
               WHERE user_id = ?""",
            (sym_count, food_count, user_id),
        )
        conn.commit()
    finally:
        conn.close()
