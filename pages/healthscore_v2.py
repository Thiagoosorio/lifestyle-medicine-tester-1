"""Health Score v2 (greenfield) -- parallel page running engine.compute().

Wires the greenfield ``src/healthscore/`` engine into the Streamlit app
without touching the existing pages or the existing service. Pulls the
logged-in user's biomarkers + clinical profile via the same data path
the existing organ_health page uses, translates them to the greenfield
``raw_inputs`` schema, and renders the full ``AggregationOutput`` with
audit metadata.

Side-by-side comparison: shows the existing service's per-score values
next to the greenfield values for every score where both implementations
exist, so any divergence is visible.

This page is **non-destructive**. The existing ``pages/organ_health.py``
remains the user-facing page until cutover; this page is opt-in
("Health Score v2" in the page nav) for testing, comparison, and
internal review.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make src/healthscore/ importable from the Streamlit pages tree.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

import streamlit as st
import yaml

from healthscore.audit import InMemoryAuditSink
from healthscore.domain_config import load_domains_config
from healthscore.engine import compute
from healthscore.enums import ScoreStatus
from healthscore.instruments import load_instrument_registry
from healthscore.score_config import load_score_configs

from components.custom_theme import APPLE, render_section_header
from services.organ_score_service import (
    _get_clinical_data,
    _get_latest_biomarkers_as_dict,
    compute_all_scores,
)


_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"
_DOMAINS_YAML = _REPO_ROOT / "configs" / "domains.yaml"
_INSTRUMENTS_YAML = _REPO_ROOT / "configs" / "instruments.yaml"
_WORDING_YAML = _REPO_ROOT / "configs" / "wording.yaml"


# ── Translator: existing-app biomarker / profile codes -> greenfield raw_inputs ──

_BIOMARKER_TO_GREENFIELD = {
    # liver
    "ast": "ast",
    "alt": "alt",
    "platelets": "platelets",
    "total_bilirubin": "total_bilirubin_mgdl",
    "albumin": "albumin_gdl",
    "triglycerides": "tg_mgdl",
    "ggt": "ggt_ul",
    "alkaline_phosphatase": "alkaline_phosphatase_uL",
    # kidney
    "creatinine": "serum_creatinine_mgdl",
    "egfr": "egfr",
    "uacr": "uacr",
    # cvd
    "total_cholesterol": "total_chol_mgdl",
    "hdl_cholesterol": "hdl_c_mgdl",
    "apob": "apob_mgdl",
    "lpa": "lpa_mgdl",
    # metabolic
    "fasting_glucose": "fasting_glucose_mgdl",
    "fasting_insulin": "fasting_insulin_uIUmL",
    # system-wide
    "hs_crp": "hs_crp_mgL",
    "hemoglobin": "hemoglobin_gdl",
    "mcv": "mcv_fL",
    "rdw": "rdw_pct",
    "wbc": "wbc_10e9L",
    "neutrophils_abs": "neutrophils_k_ul",
    "lymphocytes_abs": "lymphocytes_k_ul",
    "homocysteine": "homocysteine_umol_L",
}


def _build_raw_inputs(biomarkers: dict, clinical: dict) -> dict:
    """Translate the existing-app data shape into greenfield raw_inputs.

    Missing fields are simply absent from the returned dict; the
    greenfield engine reports them as MISSING_INPUT per score. This is
    transparent to the user via the audit blob.
    """
    raw_inputs: dict[str, object] = {}
    for src_code, value in biomarkers.items():
        gf_key = _BIOMARKER_TO_GREENFIELD.get(src_code)
        if gf_key is not None and value is not None:
            raw_inputs[gf_key] = value

    # platelets duplicates: SII / NLR want platelets_k_ul (numerically
    # identical to platelets count in 10^9/L).
    if "platelets" in raw_inputs:
        raw_inputs["platelets_k_ul"] = raw_inputs["platelets"]

    # creatinine: PhenoAge uses creatinine_mgdl key as well.
    if "serum_creatinine_mgdl" in raw_inputs:
        raw_inputs["creatinine_mgdl"] = raw_inputs["serum_creatinine_mgdl"]

    # demographics
    raw_inputs["age"] = clinical.get("age")
    raw_inputs["sex"] = clinical.get("sex")
    raw_inputs["bmi"] = clinical.get("bmi")
    if clinical.get("waist_cm") is not None:
        raw_inputs["waist_cm"] = clinical.get("waist_cm")

    # eGFR derivation: the existing biomarker store carries `creatinine`
    # but not always `egfr`. KDIGO / PREVENT / KFRE all need `egfr` as
    # a raw_input (in mL/min/1.73m^2), so derive it from creatinine +
    # age + sex via CKD-EPI 2021 when not already supplied.
    if "egfr" not in raw_inputs:
        scr = raw_inputs.get("serum_creatinine_mgdl")
        age = raw_inputs.get("age")
        sex = raw_inputs.get("sex")
        if scr is not None and age is not None and isinstance(sex, str):
            try:
                from healthscore.scores.kidney import _calc_ckd_epi_2021
                female = sex.strip().lower().startswith("f")
                raw_inputs["egfr"] = _calc_ckd_epi_2021(
                    float(scr), float(age), sex_is_female=female,
                )
            except (TypeError, ValueError, ZeroDivisionError):
                pass

    # ── Clinical-profile field mapping ──
    # The existing app's clinical_profile schema uses different field
    # names than the greenfield raw_inputs. Map explicitly so a missing
    # mapping is visible as a code change, not a silent data drop.
    # Existing-app key  ->  greenfield raw_inputs key (one entry per
    # mapping; both directions if greenfield uses two names).
    flag_map = {
        "diabetes_status":          ("diabetes",),
        "smoking_status":           None,           # special-cased below
        "on_bp_medication":         ("bp_treatment", "on_bp_medication"),
        "on_statin":                ("statin",),
        "atrial_fibrillation":      ("atrial_fibrillation_status",),
        "congestive_heart_failure": ("chf_or_lv_dysfunction",),
        "vascular_disease":         ("vascular_disease",),
        "prior_stroke_tia":         ("stroke_tia_thromboembolism",),
        "chronic_liver_disease":    ("chronic_liver_disease_status",),
        "loud_snoring":             ("snoring_loud",),
        "physical_activity_level":  None,           # special-cased below
        "family_history_diabetes":  ("family_history_diabetes",),
        "daily_activity_30min":     ("daily_activity_30min",),
        "daily_fruit_veg":          ("daily_fruit_veg",),
        "history_high_glucose":     ("history_high_glucose",),
        "education_years":          ("education_years",),
        "neck_circumference_cm":    ("neck_circumference_cm",),
    }
    for src_key, dst_keys in flag_map.items():
        if dst_keys is None:
            continue
        v = clinical.get(src_key)
        if v is None:
            continue
        # Coerce 0/1 int flags to bool for greenfield's _flag() helper.
        if isinstance(v, int) and not isinstance(v, bool) and v in (0, 1):
            v = bool(v)
        for dst in dst_keys:
            raw_inputs[dst] = v

    # smoking: existing app's smoking_status is 'never' / 'former' /
    # 'current'; greenfield wants a bool meaning "currently smoking."
    smoking_status = (clinical.get("smoking_status") or "").strip().lower()
    raw_inputs["smoking"] = smoking_status == "current"

    # physically_active: existing app has 'sedentary' / 'light' / 'active' /
    # 'very_active'. CAIDE wants True if user is active.
    activity = (clinical.get("physical_activity_level") or "").strip().lower()
    raw_inputs["physically_active"] = activity in ("active", "very_active")

    # systolic BP -> sbp_mmhg
    if clinical.get("systolic_bp") is not None:
        raw_inputs["sbp_mmhg"] = clinical["systolic_bp"]

    # Derive composite flags greenfield expects:
    #   hypertension = SBP >= 140 OR on BP medication
    #   high_bp_or_treated = same (STOP-BANG input)
    sbp = raw_inputs.get("sbp_mmhg")
    on_bp = raw_inputs.get("on_bp_medication", False)
    hypertensive = bool(on_bp) or (sbp is not None and float(sbp) >= 140)
    raw_inputs["hypertension"] = hypertensive
    raw_inputs["high_bp_or_treated"] = hypertensive

    # diabetes_or_ifg = diabetes diagnosed OR history of high glucose.
    raw_inputs["diabetes_or_ifg"] = bool(
        raw_inputs.get("diabetes")
        or raw_inputs.get("history_high_glucose")
    )

    # locale (default to en; existing app does not yet store locale per user)
    raw_inputs["locale"] = clinical.get("locale") or "en"

    return raw_inputs


# ── Page ─────────────────────────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def _bootstrap_engine_configs():
    """Load and cache the engine configs once per Streamlit session."""
    return (
        load_score_configs(_SCORE_CONFIGS),
        load_domains_config(_DOMAINS_YAML),
        load_instrument_registry(_INSTRUMENTS_YAML),
        yaml.safe_load(_WORDING_YAML.read_text(encoding="utf-8")),
    )


def main() -> None:
    if "user_id" not in st.session_state:
        st.error("Please log in first (see Dashboard).")
        st.stop()
    user_id = st.session_state.user_id

    A = APPLE
    render_section_header(
        "Health Score v2 (greenfield)",
        "engine.compute() running parallel to the existing organ-health page.",
    )

    # 1. Pull user data + assemble raw_inputs.
    biomarkers = _get_latest_biomarkers_as_dict(user_id)
    clinical = _get_clinical_data(user_id)
    raw_inputs = _build_raw_inputs(biomarkers, clinical)

    if raw_inputs.get("age") is None or raw_inputs.get("sex") is None:
        st.warning(
            "User profile is missing age or sex. Open the Clinical Profile "
            "form on the Organ Health page first; this page reads the same "
            "profile."
        )
        st.stop()

    # 2. Load engine configs + run compute().
    score_configs, domains_config, instrument_registry, templates = (
        _bootstrap_engine_configs()
    )
    sink = InMemoryAuditSink()
    output = compute(
        score_configs=score_configs,
        domains_config=domains_config,
        instrument_registry=instrument_registry,
        raw_inputs=raw_inputs,
        audit_sink=sink,
        templates=templates,
        locale=str(raw_inputs.get("locale", "en")),
    )
    audit = sink.records[0]

    # 3. Run-id banner + active instruments.
    cols = st.columns(3)
    with cols[0]:
        st.metric("Run id", audit["run_id"][-12:], help=audit["run_id"])
    with cols[1]:
        st.metric("Config hash", audit["config_hash"][:18] + "...", help=audit["config_hash"])
    with cols[2]:
        active = ", ".join(f"{k}: {v}" for k, v in audit["active_instruments"].items())
        st.metric("Active instruments", active or "—")

    # 4. Domain composites — Spec A vs Spec B side by side.
    st.subheader("Domain composites")
    if not output.domains:
        st.info("No domains produced a composite for this user (insufficient data).")
    else:
        domain_rows = []
        for d in output.domains:
            spec_a = d.spec_a_value
            spec_b = d.spec_b_value
            domain_rows.append({
                "Domain": d.domain_id.replace("_", " ").title(),
                "Spec A": f"{spec_a:.1f}" if spec_a is not None else "—",
                "Spec B": f"{spec_b:.1f}" if spec_b is not None else "—",
                "Disagreement": (
                    f"{d.disagreement:.2f}" if d.disagreement is not None else "—"
                ),
                "Flag": "⚠ >5pt" if d.disagreement_flag else "ok",
            })
        st.table(domain_rows)

    # 5. Per-organ aggregator detail.
    st.subheader("Per-organ aggregates")
    organ_rows = []
    for o in audit["organs"]:
        organ_rows.append({
            "Organ": o["organ_id"],
            "Domain": o["domain_id"],
            "Spec A": f"{o['spec_a']:.1f}" if o["spec_a"] is not None else "—",
            "Spec B": f"{o['spec_b']:.1f}" if o["spec_b"] is not None else "—",
            "Members": ", ".join(o["weights_used"].keys()),
            "Eps fired": ", ".join(o["epsilon_activations"]) or "—",
        })
    st.table(organ_rows)

    # 6. Per-score detail. Status × policy combinations are colour-coded.
    st.subheader("Per-score detail")
    status_emoji = {
        "ok": "✅",
        "gated": "🔒",
        "unavailable": "—",
        "missing_input": "❓",
        "out_of_range": "⚠️",
        "normalisation_breakdown": "🛑",
    }
    score_rows = []
    for s in audit["scores"]:
        composite = s["composite_member"]
        if composite is True and s["status"] == "ok":
            policy = "in composite"
        elif composite is False and s["status"] == "ok":
            policy = "display only"
        else:
            policy = "—"
        score_rows.append({
            "": status_emoji.get(s["status"], "?"),
            "Score": s["score_id"],
            "Status": s["status"],
            "Policy": policy,
            "Raw": s["raw_value"] if s["raw_value"] is not None else "—",
            "q": (
                f"{s['normalised_q']:.3f}"
                if s["normalised_q"] is not None else "—"
            ),
            "Band": s["risk_band"] or "—",
            "Confidence": s["confidence"] or "—",
            "Locale": s["language_cutoff_active"] or "—",
            "Calibration banner": s["calibration_banner"] or "",
            "Reason": s["reason"] or "",
        })
    st.dataframe(score_rows, use_container_width=True, hide_index=True)

    # 7. Side-by-side: greenfield vs existing service.
    st.subheader("Side-by-side: existing service vs greenfield engine")
    st.caption(
        "Same user, same labs. Mismatches reveal places where the two "
        "implementations diverge -- typically due to formula differences "
        "(e.g. existing TyG bug fix in greenfield) or different defaults."
    )
    try:
        existing_results = compute_all_scores(user_id) or []
    except Exception as exc:                         # noqa: BLE001
        existing_results = []
        st.warning(f"Existing service failed: {exc!r} — showing greenfield only.")

    existing_by_code = {r.get("code"): r for r in existing_results}
    gf_by_id = {s["score_id"]: s for s in audit["scores"]}
    # Score-id mapping where the two systems share a concept.
    pairs = [
        ("FIB-4", "fib4", "fib4"),
        ("ALBI", "albi", "albi"),
        ("FLI", "fli", "fli"),
        ("aMAP", "amap", "amap"),
        ("eGFR (CKD-EPI)", "egfr_ckd_epi", "egfr"),
        ("KFRE", "kfre_5yr", "kfre"),
        ("AHA PREVENT 10-yr", "prevent_10yr_ascvd", "prevent"),
        ("ApoB", "apob", "apob"),
        ("Lp(a)", "lpa", "lpa"),
        ("HOMA-IR", "homa_ir", "homa_ir"),
        ("METS-IR", "mets_ir", "mets_ir"),
        ("TyG Index", "tyg", "tyg"),
        ("FINDRISC", "findrisc", "findrisc"),
        ("VAI", "vai", "vai"),
        ("LAP", "lap", "lap"),
        ("PhenoAge", "phenoage_acceleration", "phenoage"),
        ("SII", "sii", "sii"),
        ("NLR", "nlr", "nlr"),
        ("STOP-BANG", "stop_bang", "stop_bang"),
        ("CHA2DS2-VASc", "cha2ds2_vasc", "cha2ds2vasc"),
        ("QFracture (hip)", "qfracture_hip", "qfracture_hip"),
        ("QFracture (major)", "qfracture_major", "qfracture_major"),
    ]
    compare_rows = []
    for label, existing_code, gf_id in pairs:
        existing = existing_by_code.get(existing_code)
        gf = gf_by_id.get(gf_id)
        existing_val = existing.get("value") if existing else None
        gf_val = gf["raw_value"] if gf else None
        gf_status = gf["status"] if gf else "—"
        if existing_val is None and gf_val is None:
            continue            # both missing -- skip noise.
        compare_rows.append({
            "Score": label,
            "Existing service": (
                f"{float(existing_val):.3f}" if existing_val is not None else "—"
            ),
            "Greenfield": gf_val if gf_val is not None else "—",
            "Greenfield status": gf_status,
        })
    if compare_rows:
        st.dataframe(compare_rows, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No score yet present in both implementations for this user. "
            "(Either the existing service has not computed any scores or "
            "the greenfield finds all required inputs missing.)"
        )

    # 8. Audit footer.
    with st.expander("Audit metadata (engine.compute() blob)"):
        st.caption(
            "This is what gets written to JSONLAuditSink in production. "
            "Architecture spec §11."
        )
        st.json(
            {
                k: v for k, v in audit.items()
                if k not in ("scores", "organs", "domains")
            }
        )
        st.write("**score_eval_order**")
        st.code(" → ".join(audit["score_eval_order"]), language="text")

    # 9. Disclaimer.
    st.caption(
        "Disclaimer (§5.3): " + output.disclaimer
    )


main()
