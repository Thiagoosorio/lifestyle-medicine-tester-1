"""Health Score v2 (greenfield) -- parallel page running engine.compute().

Mirrors the visual style of the existing pages/organ_health.py page
(card-per-score layout, colored value, risk-band caption, severity bar,
inputs row, PMID + audit expander) while running entirely on the
greenfield ``src/healthscore/`` engine.

Pulls the logged-in user's biomarkers + clinical profile via the same
data path the existing page uses, translates them to the greenfield
``raw_inputs`` schema, calls ``engine.compute()``, and renders the
``AggregationOutput`` grouped by domain → organ → score.

Non-destructive: existing pages/organ_health.py keeps its place as the
user-facing page. This page is opt-in via the sidebar nav.
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


# ── Translator: existing-app codes -> greenfield raw_inputs ──────────────


_BIOMARKER_TO_GREENFIELD = {
    "ast": "ast", "alt": "alt", "platelets": "platelets",
    "total_bilirubin": "total_bilirubin_mgdl", "albumin": "albumin_gdl",
    "triglycerides": "tg_mgdl", "ggt": "ggt_ul",
    "alkaline_phosphatase": "alkaline_phosphatase_uL",
    "creatinine": "serum_creatinine_mgdl", "egfr": "egfr", "uacr": "uacr",
    "total_cholesterol": "total_chol_mgdl",
    "hdl_cholesterol": "hdl_c_mgdl", "apob": "apob_mgdl", "lpa": "lpa_mgdl",
    "fasting_glucose": "fasting_glucose_mgdl",
    "fasting_insulin": "fasting_insulin_uIUmL",
    "hs_crp": "hs_crp_mgL", "hemoglobin": "hemoglobin_gdl",
    "mcv": "mcv_fL", "rdw": "rdw_pct", "wbc": "wbc_10e9L",
    "neutrophils_abs": "neutrophils_k_ul",
    "lymphocytes_abs": "lymphocytes_k_ul",
    "homocysteine": "homocysteine_umol_L",
}


def _build_raw_inputs(biomarkers: dict, clinical: dict) -> dict:
    raw_inputs: dict[str, object] = {}
    for src_code, value in biomarkers.items():
        gf_key = _BIOMARKER_TO_GREENFIELD.get(src_code)
        if gf_key is not None and value is not None:
            raw_inputs[gf_key] = value
    if "platelets" in raw_inputs:
        raw_inputs["platelets_k_ul"] = raw_inputs["platelets"]
    if "serum_creatinine_mgdl" in raw_inputs:
        raw_inputs["creatinine_mgdl"] = raw_inputs["serum_creatinine_mgdl"]

    raw_inputs["age"] = clinical.get("age")
    raw_inputs["sex"] = clinical.get("sex")
    raw_inputs["bmi"] = clinical.get("bmi")
    if clinical.get("waist_cm") is not None:
        raw_inputs["waist_cm"] = clinical.get("waist_cm")

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

    flag_map = {
        "diabetes_status":          ("diabetes",),
        "smoking_status":           None,
        "on_bp_medication":         ("bp_treatment", "on_bp_medication"),
        "on_statin":                ("statin",),
        "atrial_fibrillation":      ("atrial_fibrillation_status",),
        "congestive_heart_failure": ("chf_or_lv_dysfunction",),
        "vascular_disease":         ("vascular_disease",),
        "prior_stroke_tia":         ("stroke_tia_thromboembolism",),
        "chronic_liver_disease":    ("chronic_liver_disease_status",),
        "loud_snoring":             ("snoring_loud",),
        "physical_activity_level":  None,
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
        if isinstance(v, int) and not isinstance(v, bool) and v in (0, 1):
            v = bool(v)
        for dst in dst_keys:
            raw_inputs[dst] = v

    smoking_status = (clinical.get("smoking_status") or "").strip().lower()
    raw_inputs["smoking"] = smoking_status == "current"
    activity = (clinical.get("physical_activity_level") or "").strip().lower()
    raw_inputs["physically_active"] = activity in ("active", "very_active")

    if clinical.get("systolic_bp") is not None:
        raw_inputs["sbp_mmhg"] = clinical["systolic_bp"]

    sbp = raw_inputs.get("sbp_mmhg")
    on_bp = raw_inputs.get("on_bp_medication", False)
    hypertensive = bool(on_bp) or (sbp is not None and float(sbp) >= 140)
    raw_inputs["hypertension"] = hypertensive
    raw_inputs["high_bp_or_treated"] = hypertensive
    raw_inputs["diabetes_or_ifg"] = bool(
        raw_inputs.get("diabetes")
        or raw_inputs.get("history_high_glucose")
    )
    raw_inputs["locale"] = clinical.get("locale") or "en"
    return raw_inputs


# ── Visual tokens ────────────────────────────────────────────────────────

A = APPLE

# Risk-band colours (matches existing app's severity colour family).
_BAND_COLOURS = {
    "low":           "#30D158",     # green: low risk
    "indeterminate": "#FFD60A",     # yellow: borderline
    "high":          "#FF453A",     # red: high risk
}
_BAND_LABEL = {
    "low": "Lower-risk band",
    "indeterminate": "Intermediate band",
    "high": "Higher-risk band",
}
# Colour for non-OK ScoreResult states.
_NEUTRAL_GREY = "#8E8E93"

# Composite-policy badge colours.
_POLICY_BADGES = {
    "in_composite":  ("In composite",   "#30D158", "#30D15820"),
    "display_only":  ("Display only",   "#0A84FF", "#0A84FF20"),
    "gated":         ("Gated",          "#FF9F0A", "#FF9F0A20"),
    "unavailable":   ("Unavailable",    _NEUTRAL_GREY, "#8E8E9320"),
    "missing":       ("Insufficient data", _NEUTRAL_GREY, "#8E8E9320"),
    "out_of_range":  ("Out of range",   "#FF453A", "#FF453A20"),
}


def _policy_for(score_audit: dict) -> str:
    s = score_audit["status"]
    if s == "ok":
        return "in_composite" if score_audit.get("composite_member") else "display_only"
    if s == "gated":
        return "gated"
    if s == "unavailable":
        return "unavailable"
    if s == "out_of_range":
        return "out_of_range"
    return "missing"


def _format_raw(raw: object) -> str:
    if raw is None or raw == "":
        return "—"
    try:
        f = float(raw)
        if abs(f) >= 100:
            return f"{f:.1f}"
        if abs(f) >= 1 or f == int(f):
            return f"{f:.2f}"
        return f"{f:.3f}"
    except (TypeError, ValueError):
        return str(raw)


def _render_band_bar(active_band: str | None) -> None:
    """Three-band horizontal bar (low / indeterminate / high). The active
    band lights up; the others fade. Mirrors the 5-band severity bar
    in components/organ_health_display.py but with greenfield's three-
    risk-band convention."""
    bands = ("low", "indeterminate", "high")
    cols = st.columns(len(bands))
    for col, band in zip(cols, bands):
        colour = _BAND_COLOURS[band]
        opacity = "1.0" if band == active_band else "0.2"
        col.markdown(
            f'<div style="height:4px;background:{colour};opacity:{opacity};border-radius:2px;"></div>',
            unsafe_allow_html=True,
        )


def _render_policy_badge(policy_key: str) -> None:
    label, colour, bg = _POLICY_BADGES[policy_key]
    st.markdown(
        f'<span style="background:{bg};color:{colour};padding:2px 8px;border-radius:12px;font-size:0.7em;font-weight:600;">{label}</span>',
        unsafe_allow_html=True,
    )


def _render_score_card(score_audit: dict, score_config) -> None:
    """One card per score, mirroring the existing organ_health page card."""
    status = score_audit["status"]
    band = score_audit["risk_band"]
    policy = _policy_for(score_audit)

    # Pick value colour: risk-band colour when OK, neutral grey otherwise.
    if status == "ok" and band in _BAND_COLOURS:
        value_colour = _BAND_COLOURS[band]
        band_text = score_audit.get("wording") or _BAND_LABEL.get(band, band.title())
    else:
        value_colour = _NEUTRAL_GREY
        band_text = {
            "gated": "Gate not met — score does not apply",
            "unavailable": "Inactive instrument slot",
            "missing_input": "Insufficient input data",
            "out_of_range": "Input outside physiological range",
            "normalisation_breakdown": "Normalisation could not run",
        }.get(status, status)

    with st.container(border=True):
        # Header row: name + composite-policy pill.
        col_name, col_badge = st.columns([3, 1])
        with col_name:
            st.markdown(f"**{score_config.display_name}**")
        with col_badge:
            _render_policy_badge(policy)

        # Value column + interpretation column.
        col_val, col_interp = st.columns([1, 2])
        with col_val:
            display_val = _format_raw(score_audit.get("raw_value"))
            st.markdown(
                f'<div style="font-size:2em;font-weight:700;color:{value_colour};line-height:1.2;">{display_val}</div>',
                unsafe_allow_html=True,
            )
            # Show q-value beneath as a small caption when OK.
            if status == "ok" and score_audit.get("normalised_q") is not None:
                q = score_audit["normalised_q"]
                st.caption(f"q = {q:.3f}")
        with col_interp:
            st.markdown(
                f'<div style="color:{value_colour};font-weight:600;margin-top:8px;">{band_text}</div>',
                unsafe_allow_html=True,
            )
            # Confidence + locale + calibration banner caveats.
            conf = score_audit.get("confidence")
            locale = score_audit.get("language_cutoff_active")
            banner = score_audit.get("calibration_banner")
            sub_bits: list[str] = []
            if conf:
                sub_bits.append(f"Confidence: {conf}")
            if locale and locale != "en":
                sub_bits.append(f"Anchors: {locale}")
            if score_audit.get("output_clamped"):
                sub_bits.append("Output clamped (Gompertz tail)")
            if sub_bits:
                st.caption(" · ".join(sub_bits))
            if banner:
                st.warning(banner, icon="⚠️")

        _render_band_bar(band if status == "ok" else None)

        # Inputs row: only show inputs that materially affect the score
        # (i.e. those listed in the config's input_variables).
        cfg_inputs = [v.name for v in score_config.input_variables]
        all_inputs = score_audit.get("raw_inputs", {})
        inputs_used = {
            k: all_inputs.get(k) for k in cfg_inputs
            if all_inputs.get(k) not in (None, "")
        }
        if inputs_used:
            inputs_text = " | ".join(
                f"{k}: {v}" for k, v in inputs_used.items()
            )
            st.caption(f"Inputs: {inputs_text}")

        # Footer: PMID + (if gated) gate-failure reason chips.
        footer_parts: list[str] = []
        pmid = score_audit.get("pmid_primary")
        if pmid:
            footer_parts.append(f"PMID: {pmid}")
        if status == "gated" and score_audit.get("gate_failures"):
            footer_parts.append(
                "Gate: " + ", ".join(score_audit["gate_failures"])
            )
        if footer_parts:
            st.caption(" | ".join(footer_parts))

        # Audit-detail expander (mirrors "Details & Citation" expander).
        with st.expander("Details & Audit"):
            if score_config.guideline_anchor:
                st.markdown(f"**Guideline anchor:** {score_config.guideline_anchor}")
            if score_config.derivation_cohort and score_config.derivation_cohort.study:
                st.markdown(
                    f"**Derivation cohort:** {score_config.derivation_cohort.study}"
                    + (f" (n={score_config.derivation_cohort.n})" if score_config.derivation_cohort.n else "")
                )
            if (
                score_config.applicable_population
                and score_config.applicable_population.calibration_caveat
            ):
                st.caption(score_config.applicable_population.calibration_caveat)
            # Audit fields that aid forensic replay.
            with st.popover("Engine audit blob (per-score)") if hasattr(st, "popover") else st.container():
                st.json({
                    k: v for k, v in score_audit.items()
                    if k not in ("raw_inputs",)
                })


# ── Page ─────────────────────────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def _bootstrap_engine_configs():
    return (
        load_score_configs(_SCORE_CONFIGS),
        load_domains_config(_DOMAINS_YAML),
        load_instrument_registry(_INSTRUMENTS_YAML),
        yaml.safe_load(_WORDING_YAML.read_text(encoding="utf-8")),
    )


_DOMAIN_DISPLAY = {
    "heart_metab":  ("Heart & Metabolism", "❤️"),
    "brain":        ("Brain Health",       "🧠"),
    "muscle_bones": ("Muscle & Bones",     "🦴"),
    "system_wide":  ("System-Wide",        "🌐"),
    "gut":          ("Gut & Digestion",    "🍃"),
}
_ORGAN_DISPLAY = {
    "liver":            ("Liver",                  "🫀"),
    "kidney":           ("Kidney",                 "💧"),
    "cvd":              ("Cardiovascular",         "❤️"),
    "metabolic":        ("Metabolic",              "⚙️"),
    "cognitive_mental": ("Cognitive & Mental",     "🧠"),
    "bone":             ("Bone",                   "🦴"),
    "integrative":      ("Integrative / System-Wide", "🌐"),
}


def _domain_score_color(value: float | None) -> str:
    if value is None:
        return _NEUTRAL_GREY
    if value >= 75:
        return _BAND_COLOURS["low"]
    if value >= 50:
        return _BAND_COLOURS["indeterminate"]
    return _BAND_COLOURS["high"]


def main() -> None:
    if "user_id" not in st.session_state:
        st.error("Please log in first (see Dashboard).")
        st.stop()
    user_id = st.session_state.user_id

    render_section_header(
        "Health Score v2",
        "Greenfield engine.compute() — running parallel to the existing Organ Scores page.",
    )

    biomarkers = _get_latest_biomarkers_as_dict(user_id)
    clinical = _get_clinical_data(user_id)
    raw_inputs = _build_raw_inputs(biomarkers, clinical)
    if raw_inputs.get("age") is None or raw_inputs.get("sex") is None:
        st.warning(
            "User profile is missing age or sex. Open the Clinical Profile "
            "form on the Organ Scores page first; this page reads the same "
            "profile."
        )
        st.stop()

    score_configs, domains_config, instrument_registry, templates = (
        _bootstrap_engine_configs()
    )
    sink = InMemoryAuditSink()
    output = compute(
        score_configs=score_configs, domains_config=domains_config,
        instrument_registry=instrument_registry, raw_inputs=raw_inputs,
        audit_sink=sink, templates=templates,
        locale=str(raw_inputs.get("locale", "en")),
    )
    audit = sink.records[0]
    score_by_id = {s["score_id"]: s for s in audit["scores"]}
    organ_by_id = {o["organ_id"]: o for o in audit["organs"]}
    domain_by_id = {d["domain_id"]: d for d in audit["domains"]}

    # ── Engine metadata strip ─────────────────────────────────────────────
    cols = st.columns(3)
    with cols[0]:
        st.metric("Run ID", audit["run_id"][-12:], help=audit["run_id"])
    with cols[1]:
        st.metric(
            "Config hash", audit["config_hash"][:18] + "…",
            help=audit["config_hash"],
        )
    with cols[2]:
        active = ", ".join(f"{k}: {v}" for k, v in audit["active_instruments"].items())
        st.metric("Active instruments", active or "—")

    # ── Domain composite cards ────────────────────────────────────────────
    st.subheader("Domain composites")
    if not output.domains:
        st.info("No domain produced a composite for this user (insufficient data).")
    else:
        domain_cols = st.columns(min(len(output.domains), 4))
        for col, d in zip(domain_cols, output.domains):
            display_name, icon = _DOMAIN_DISPLAY.get(
                d.domain_id, (d.domain_id.replace("_", " ").title(), "📊")
            )
            spec_a = d.spec_a_value
            spec_b = d.spec_b_value
            colour_a = _domain_score_color(spec_a)
            colour_b = _domain_score_color(spec_b)
            with col, st.container(border=True):
                st.markdown(f"**{icon} {display_name}**")
                if spec_a is None and spec_b is None:
                    st.markdown(
                        f'<div style="font-size:2em;color:{_NEUTRAL_GREY};">—</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div style="line-height:1.2;">'
                        f'<span style="font-size:2em;font-weight:700;color:{colour_a};">{spec_a:.0f}</span>'
                        f' <span style="color:#79747E;font-size:1.0em;">/ {spec_b:.0f}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(f"Spec A · Spec B")
                if d.disagreement_flag:
                    st.warning(
                        f"|A − B| = {d.disagreement:.1f} — scores point in different directions.",
                        icon="⚠️",
                    )

    # ── Per-domain detail: organ aggregates + per-score cards ─────────────
    domain_to_organs: dict[str, list[dict]] = {}
    for o in audit["organs"]:
        domain_to_organs.setdefault(o["domain_id"], []).append(o)

    for domain_id, organs in domain_to_organs.items():
        domain_label, domain_icon = _DOMAIN_DISPLAY.get(
            domain_id, (domain_id.replace("_", " ").title(), "📊"),
        )
        st.markdown("---")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:8px 0 12px 0;">'
            f'<span style="font-size:1.5em;">{domain_icon}</span>'
            f'<span style="font-size:1.25em;font-weight:700;color:{A["label_primary"]};">{domain_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for organ in organs:
            organ_label, organ_icon = _ORGAN_DISPLAY.get(
                organ["organ_id"],
                (organ["organ_id"].replace("_", " ").title(), "·"),
            )
            spec_a = organ["spec_a"]
            spec_b = organ["spec_b"]
            colour = _domain_score_color(spec_a)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin:14px 0 6px 0;">'
                f'<span style="font-size:1.1em;">{organ_icon}</span>'
                f'<span style="font-size:1.0em;font-weight:600;color:{A["label_primary"]};">{organ_label}</span>'
                f'<span style="color:{colour};font-weight:700;">{spec_a:.0f} / {spec_b:.0f}</span>'
                f'<span style="color:#79747E;font-size:0.85em;">Spec A · Spec B</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Cards for every config-listed score whose organ matches this
            # one. We use domains.yaml -> organs[organ_id] -> scores list
            # for the strict ordering (composite members + display-only).
            domain_spec = domains_config.domains.get(domain_id)
            organ_spec = (
                domain_spec.organs.get(organ["organ_id"])
                if domain_spec is not None else None
            )
            if organ_spec is None:
                continue
            for score_id in organ_spec.scores:
                s_audit = score_by_id.get(score_id)
                cfg = score_configs.get(score_id)
                if s_audit is None or cfg is None:
                    continue
                _render_score_card(s_audit, cfg)

    # ── Scores not in any organ panel (e.g. CHA2DS2-VASc, NLR, PhenoAge) ──
    rendered_ids = set()
    for organ in audit["organs"]:
        domain_spec = domains_config.domains.get(organ["domain_id"])
        if domain_spec is None:
            continue
        organ_spec = domain_spec.organs.get(organ["organ_id"])
        if organ_spec is None:
            continue
        rendered_ids.update(organ_spec.scores.keys())
    leftover = [
        s for s in audit["scores"]
        if s["score_id"] not in rendered_ids and s["status"] != "unavailable"
    ]
    if leftover:
        st.markdown("---")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:8px 0 12px 0;">'
            f'<span style="font-size:1.5em;">📋</span>'
            f'<span style="font-size:1.25em;font-weight:700;color:{A["label_primary"]};">Display-only / non-composite scores</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "These scores are computed and shown for clinical context but do "
            "not contribute to any composite — methodology §1.5 redundancy "
            "reduction or §3.7 PhenoAge non-composite policy."
        )
        for s_audit in leftover:
            cfg = score_configs.get(s_audit["score_id"])
            if cfg is None:
                continue
            _render_score_card(s_audit, cfg)

    # ── Side-by-side comparison ────────────────────────────────────────────
    with st.expander("Side-by-side: existing service vs greenfield engine"):
        st.caption(
            "Same user, same labs. Mismatches reveal places where the two "
            "implementations diverge — typically formula differences (e.g. "
            "TyG canonical-form fix in greenfield) or different defaults."
        )
        try:
            existing_results = compute_all_scores(user_id) or []
        except Exception as exc:                         # noqa: BLE001
            existing_results = []
            st.warning(f"Existing service failed: {exc!r}")
        existing_by_code = {r.get("code"): r for r in existing_results}
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
        rows = []
        for label, existing_code, gf_id in pairs:
            existing = existing_by_code.get(existing_code)
            gf = score_by_id.get(gf_id)
            if not existing and not gf:
                continue
            existing_val = existing.get("value") if existing else None
            gf_val = gf["raw_value"] if gf else None
            rows.append({
                "Score": label,
                "Existing service": (
                    f"{float(existing_val):.3f}"
                    if existing_val is not None else "—"
                ),
                "Greenfield": gf_val if gf_val is not None else "—",
                "Greenfield status": gf["status"] if gf else "—",
            })
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info(
                "No score yet present in both implementations for this user."
            )

    # ── Audit metadata expander ───────────────────────────────────────────
    with st.expander("Engine audit metadata"):
        st.caption(
            "What gets written to JSONLAuditSink in production. "
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

    # ── Disclaimer (§5.3) ─────────────────────────────────────────────────
    st.caption(f"Disclaimer (§5.3): {output.disclaimer}")


main()
