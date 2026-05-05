"""Phase 4 integration test suite.

Exercises the full pipeline (config -> formula -> normaliser -> aggregator)
for five canonical user fixtures, per the Phase 4 acceptance criteria:

    (a) Original panel user: 43yo female, healthy, baseline labs.
        End-to-end produces results for every shipped organ panel.
    (b) UAE-resident variant of the same user: PREVENT must surface the
        Al-Shamsi 2025 calibration banner (commitments_log #18).
    (c) Documented-AF user: CHA2DS2-VASc computes (gate passes) and
        appears alongside the CVD composite without contributing to it
        (composite_member=false).
    (d) CKD G3a user (eGFR < 60): KFRE gate passes and contributes to the
        kidney composite alongside eGFR + KDIGO.
    (e) §1.7 worked liver example continues to land at 39.46 ± 0.05 via
        the full Phase 4 pipeline (engine-driven, not hand-constructed).

Phase 4 ships liver + kidney + cvd + system-wide organ panels.
Metabolic, brain, gut, bone/muscle organ panels are Phase 5+; the
fixtures here therefore do not assert on those domains.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from healthscore.engine import aggregate_organ, evaluate_all_scores
from healthscore.enums import ScoreStatus
from healthscore.instruments import load_instrument_registry
from healthscore.score_config import load_score_configs


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"
_WORDING_YAML = _REPO_ROOT / "configs" / "wording.yaml"
_INSTRUMENTS_YAML = _REPO_ROOT / "configs" / "instruments.yaml"


# ── Composite-member groupings (matches each panel's configs) ────────────

_LIVER_MEMBERS = ("fib4", "albi", "amap", "fli")
_KIDNEY_MEMBERS = ("egfr", "kfre", "kdigo_category")
_CVD_MEMBERS = ("prevent", "apob", "lpa")
# System-Wide post-Option C (methodology §3.7): PhenoAge is non-composite
# (research-grade display only); the four composite members renormalise.
_SYSTEM_WIDE_MEMBERS = ("hb_rdw", "sii", "frail_scale", "stop_bang")
_METABOLIC_MEMBERS = ("homa_ir", "mets_ir", "tyg", "findrisc", "vai", "lap")
_BRAIN_MEMBERS = ("moca", "caide", "phq9", "gad7", "homocysteine")


@pytest.fixture(scope="module")
def configs():
    return load_score_configs(_SCORE_CONFIGS)


@pytest.fixture(scope="module")
def wording_templates():
    return yaml.safe_load(_WORDING_YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def instrument_registry():
    return load_instrument_registry(_INSTRUMENTS_YAML)


def _organ(configs, results, organ_id, domain_id, members, confidence="high"):
    weights = {sid: configs[sid].composite_weight or 0.0 for sid in members}
    return aggregate_organ(
        organ_id=organ_id, domain_id=domain_id,
        member_results=[results[sid] for sid in members],
        weights=weights, confidence=confidence,
    )


def _healthy_43yo_female_inputs() -> dict[str, object]:
    """Fixture (a): the original panel user.

    43yo female, no documented AF, normal eGFR, normal labs across the
    board. Includes raw_inputs for every score the engine will try to
    compute (those needing them) so MISSING_INPUT does not noise the
    integration assertion. Scores whose required raws aren't supplied
    return MISSING_INPUT, which is the correct behaviour but not the
    point being tested here."""
    return {
        # demographics
        "age": 43, "sex": "female", "bmi": 23,
        # liver panel
        "ast": 22, "alt": 20, "platelets": 250,
        "total_bilirubin_mgdl": 0.7, "albumin_gdl": 4.4,
        "tg_mgdl": 90, "ggt_ul": 18, "waist_cm": 72,
        "diabetes_or_ifg": False, "diabetes_status": False,
        "chronic_liver_disease_status": False,
        "ast_uln": 40,
        # kidney panel
        "serum_creatinine_mgdl": 0.8, "egfr": 95, "uacr": 5,
        # cvd panel
        "total_chol_mgdl": 185, "hdl_c_mgdl": 60, "sbp_mmhg": 116,
        "smoking": False, "bp_treatment": False, "statin": False,
        "diabetes": False,
        "atrial_fibrillation_status": False,
        "chf_or_lv_dysfunction": False, "hypertension": False,
        "stroke_tia_thromboembolism": False, "vascular_disease": False,
        "apob_mgdl": 75, "lpa_mgdl": 18,
        # system-wide panel
        "fasting_glucose_mgdl": 92, "creatinine_mgdl": 0.8,
        "hs_crp_mgL": 0.8, "lymphocyte_pct": 32, "mcv_fL": 88,
        "rdw_pct": 12.6, "alkaline_phosphatase_uL": 65,
        "wbc_10e9L": 5.5, "hemoglobin_gdl": 13.5,
        "platelets_k_ul": 250, "neutrophils_k_ul": 3.2,
        "lymphocytes_k_ul": 2.0,
        "fatigue": False, "resistance_difficulty_stairs": False,
        "aerobic_difficulty_walking_block": False, "illness_count": 0,
        "loss_of_weight_5pct": False,
        "neck_circumference_cm": 32,
        "snoring_loud": False, "tired_daytime": False,
        "observed_apnoea": False, "high_bp_or_treated": False,
        "moca_score": 28, "mmse_score": 28,
        # metabolic panel
        "fasting_insulin_uIUmL": 6,
        "daily_activity_30min": True, "daily_fruit_veg": True,
        "on_bp_medication": False, "history_high_glucose": False,
        "family_history_diabetes": "none",
        # brain panel
        "education_years": 16, "physically_active": True,
        "homocysteine_umol_L": 9.5,
        **{f"phq9_q{i}": 0 for i in range(1, 10)},
        **{f"gad7_q{i}": 0 for i in range(1, 8)},
        # locale
        "locale": "en",
    }


# ──────────────────────────────────────────────────────────────────────────
# Fixture (a): original panel user, end-to-end across all built panels
# ──────────────────────────────────────────────────────────────────────────


def test_fixture_a_healthy_43yo_female_full_pipeline(
    configs, wording_templates, instrument_registry,
):
    """Phase 6 Option C reweighting per methodology §3.7
    (commitments_log "System-Wide composite reweighting (Option C;
    PhenoAge dropped from composite)" 4 May 2026): system-wide composite
    weights are Frailty 0.35 / Hb+RDW 0.25 / OSA 0.25 / SII 0.15
    (sum 1.00); PhenoAge is composite_member: false and is computed +
    surfaced to the user with a research-grade caveat but does not
    contribute to the composite. This test verifies (a) the four
    composite members run and aggregate; (b) PhenoAge still computes and
    its audit blob carries composite_member: false so forensic replay
    can distinguish "computed but excluded by policy" from
    "not computed at all."""
    raw_inputs = _healthy_43yo_female_inputs()
    results = evaluate_all_scores(
        configs=configs, raw_inputs=raw_inputs,
        instrument_registry=instrument_registry, templates=wording_templates,
    )

    # Composite-member scores: most are OK, but two are intentionally gated
    # for a healthy user:
    #   - aMAP is gated unless CLD documented OR (FIB-4>=1.3 AND FLI>=60).
    #     A healthy 43F has CLD=False and labs well below the MASLD-evidence
    #     thresholds; aMAP is GATED here, by design.
    #   - KFRE and CHA2DS2-VASc gates are tested separately below.
    for sid in ("fib4", "albi", "fli"):
        assert results[sid].status is ScoreStatus.OK, (
            f"{sid} expected OK; got {results[sid].status} ({results[sid].reason})"
        )
    assert results["amap"].status is ScoreStatus.GATED, (
        "aMAP must be gated for a healthy user without CLD or MASLD evidence "
        "(architecture_spec §6 Pre-launch gate registry)"
    )
    for sid in _KIDNEY_MEMBERS:
        if sid == "kfre":
            continue        # gated for eGFR > 60; tested below
        assert results[sid].status is ScoreStatus.OK, (
            f"{sid} expected OK; got {results[sid].status} ({results[sid].reason})"
        )
    for sid in _CVD_MEMBERS:
        assert results[sid].status is ScoreStatus.OK, (
            f"{sid} expected OK; got {results[sid].status} ({results[sid].reason})"
        )
    # System-wide composite members (Option C): stop_bang (OSA primary,
    # active) must compute; sii / frail / hb_rdw must compute. nosas is
    # inactive (UNAVAILABLE per §7).
    for sid in _SYSTEM_WIDE_MEMBERS:
        assert results[sid].status is ScoreStatus.OK, (
            f"{sid} expected OK; got {results[sid].status} ({results[sid].reason})"
        )
    # The non-active osa instrument is structurally UNAVAILABLE.
    assert results["nosas"].status is ScoreStatus.UNAVAILABLE
    assert results["nosas"].active_instrument == "stop_bang"
    # PhenoAge: still computed; status=OK; composite_member: false at
    # the config level. Forensic replay distinguishes "computed but
    # excluded by policy" (this case) from "not computed" (gated /
    # missing / unavailable).
    assert results["phenoage"].status is ScoreStatus.OK
    assert configs["phenoage"].composite_member is False

    # Metabolic + brain panel composite-member sanity (Phase 5).
    for sid in _METABOLIC_MEMBERS:
        assert results[sid].status is ScoreStatus.OK, (
            f"{sid}: {results[sid].status} ({results[sid].reason})"
        )
    # Active cognitive instrument (MoCA) computes; MMSE UNAVAILABLE.
    for sid in ("caide", "phq9", "gad7", "homocysteine", "moca"):
        assert results[sid].status is ScoreStatus.OK, (
            f"{sid}: {results[sid].status} ({results[sid].reason})"
        )
    assert results["mmse"].status is ScoreStatus.UNAVAILABLE

    # Every shipped organ aggregator produces a value.
    liver = _organ(configs, results, "liver", "heart_metab", _LIVER_MEMBERS)
    kidney = _organ(configs, results, "kidney", "heart_metab", _KIDNEY_MEMBERS)
    cvd = _organ(configs, results, "cvd", "heart_metab", _CVD_MEMBERS)
    system_wide = _organ(
        configs, results, "system_wide", "system_wide", _SYSTEM_WIDE_MEMBERS,
    )
    metabolic = _organ(
        configs, results, "metabolic", "heart_metab", _METABOLIC_MEMBERS,
    )
    brain = _organ(configs, results, "brain", "brain", _BRAIN_MEMBERS)

    # Healthy user should land in upper-band per panel: kidney composite
    # has KFRE GATED (eGFR > 60), but eGFR + KDIGO contribute strongly
    # so the composite should be > 70.
    assert liver.spec_a_value is not None and liver.spec_a_value > 70
    assert kidney.spec_a_value is not None and kidney.spec_a_value > 70
    assert cvd.spec_a_value is not None and cvd.spec_a_value > 70
    assert system_wide.spec_a_value is not None and system_wide.spec_a_value > 60
    assert metabolic.spec_a_value is not None and metabolic.spec_a_value > 70
    assert brain.spec_a_value is not None and brain.spec_a_value > 70

    # Methodology §1.3: spec A == spec B at organ level.
    for o in (liver, kidney, cvd, system_wide, metabolic, brain):
        assert abs(o.spec_a_value - o.spec_b_value) < 0.01

    # Healthy user: KFRE gated; CHA2DS2-VASc gated.
    assert results["kfre"].status is ScoreStatus.GATED
    assert results["cha2ds2vasc"].status is ScoreStatus.GATED


# ──────────────────────────────────────────────────────────────────────────
# Fixture (b): UAE-resident variant fires the PREVENT calibration banner
# ──────────────────────────────────────────────────────────────────────────


def test_fixture_b_uae_resident_fires_prevent_calibration_banner(
    configs, wording_templates, instrument_registry,
):
    raw_inputs = _healthy_43yo_female_inputs()
    raw_inputs["country_of_residence"] = "UAE"
    results = evaluate_all_scores(
        configs=configs, raw_inputs=raw_inputs,
        instrument_registry=instrument_registry, templates=wording_templates,
    )
    prevent = results["prevent"]
    assert prevent.status is ScoreStatus.OK
    assert prevent.calibration_banner is not None, (
        "commitments_log #18: a UAE-resident PREVENT computation must "
        "surface the Al-Shamsi 2025 recalibration-pending banner"
    )
    assert "Al-Shamsi" in prevent.calibration_banner


# ──────────────────────────────────────────────────────────────────────────
# Fixture (c): documented-AF user has CHA2DS2-VASc computed (not in composite)
# ──────────────────────────────────────────────────────────────────────────


def test_fixture_c_documented_af_user_cha2ds2vasc_computes_outside_composite(
    configs, wording_templates, instrument_registry,
):
    raw_inputs = _healthy_43yo_female_inputs()
    raw_inputs.update({
        "age": 78, "atrial_fibrillation_status": True,
        "hypertension": True, "diabetes": False,
        "chf_or_lv_dysfunction": False,
        "stroke_tia_thromboembolism": False, "vascular_disease": False,
    })
    results = evaluate_all_scores(
        configs=configs, raw_inputs=raw_inputs,
        instrument_registry=instrument_registry, templates=wording_templates,
    )
    cha = results["cha2ds2vasc"]
    assert cha.status is ScoreStatus.OK
    # 78F + AF + HTN = 1 (female) + 2 (>=75) + 1 (HTN) = 4 points.
    assert float(cha.raw_value) == 4.0
    # Non-composite: must not contribute to any organ aggregate.
    assert configs["cha2ds2vasc"].composite_member is False

    # CVD composite still computed from prevent + apob + lpa only.
    cvd = _organ(configs, results, "cvd", "heart_metab", _CVD_MEMBERS)
    assert cvd.spec_a_value is not None
    assert "cha2ds2vasc" not in cvd.weights_used


# ──────────────────────────────────────────────────────────────────────────
# Fixture (d): CKD G3a user, KFRE contributes to kidney composite
# ──────────────────────────────────────────────────────────────────────────


def test_fixture_d_ckd_g3a_user_kfre_contributes_to_kidney_composite(
    configs, wording_templates, instrument_registry,
):
    raw_inputs = _healthy_43yo_female_inputs()
    raw_inputs.update({
        "age": 65, "sex": "male", "serum_creatinine_mgdl": 1.85,
        "egfr": 40,                # G3b — gate passes (eGFR <= 60)
        "uacr": 120,               # A2 albuminuria
    })
    results = evaluate_all_scores(
        configs=configs, raw_inputs=raw_inputs,
        instrument_registry=instrument_registry, templates=wording_templates,
    )
    assert results["egfr"].status is ScoreStatus.OK
    assert results["kfre"].status is ScoreStatus.OK
    assert results["kdigo_category"].status is ScoreStatus.OK

    kidney = _organ(configs, results, "kidney", "heart_metab", _KIDNEY_MEMBERS)
    # All three weights now contribute (no gating drops out).
    assert set(kidney.weights_used.keys()) >= {"egfr", "kfre", "kdigo_category"}
    assert kidney.spec_a_value is not None


# ──────────────────────────────────────────────────────────────────────────
# Fixture (e): §1.7 worked liver continues to land 39.46 ± 0.05
# ──────────────────────────────────────────────────────────────────────────
# Note on §1.7 reproducibility: the methodology document's §1.7 worked
# example uses per-formula raws that are mutually inconsistent (FIB-4
# uses age=50 + plt=200; aMAP uses age=65 + plt=150). A single unified
# raw_inputs dict cannot reproduce both q values simultaneously. The
# canonical Phase 2 regression
# (tests/healthscore/regression/test_liver_worked_example_full_pipeline.py)
# preserves the 39.46 target by calling evaluate_score once per score
# with the per-formula raws. This integration test therefore delegates
# to that regression suite for the §1.7 pin and asserts here only that
# the engine path itself does not break it -- a separate pytest
# invocation of the Phase 2 regression test as a child process would
# duplicate work already covered. Kept as a structural reminder.


def test_fixture_e_phase_2_section_1_7_regression_still_passes(
    configs, wording_templates, instrument_registry,
):
    """Sanity check: under the Phase 4 engine, the four liver formulae
    plus aggregator continue to produce the §1.7 organ score 39.46 when
    fed the per-formula raws (the canonical regression input). This
    asserts the engine wrapper has not broken the Phase 0+2 pin."""
    from healthscore.score_eval import evaluate_score
    from healthscore.scores import lookup_formula
    from healthscore.score_config import parse_gate_spec

    per_score_inputs = {
        "fib4":  {"age": 50, "ast": 43.818, "alt": 30.0, "platelets": 200},
        "albi":  {"total_bilirubin_mgdl": 1.0, "albumin_gdl": 3.162},
        "amap":  {
            "age": 65, "sex": "male", "total_bilirubin_mgdl": 2.0,
            "albumin_gdl": 3.805, "platelets": 150,
            "chronic_liver_disease_status": True,
        },
        "fli":   {"tg_mgdl": 138, "bmi": 28, "ggt_ul": 30, "waist_cm": 92},
    }
    results = []
    prior: dict = {}
    for sid in ("fib4", "albi", "amap", "fli"):
        cfg = configs[sid]
        res = evaluate_score(
            cfg, raw_inputs=per_score_inputs[sid], prior_results=prior,
            formula=lookup_formula(cfg.formula),
            gate=parse_gate_spec(cfg.gate_requirements),
            templates=wording_templates,
            instrument_registry=instrument_registry,
        )
        results.append(res)
        prior[sid] = res
        assert res.status is ScoreStatus.OK, f"{sid}: {res.status} {res.reason}"

    liver = _organ(
        configs, {r.score_id: r for r in results},
        "liver", "heart_metab", _LIVER_MEMBERS,
    )
    assert liver.spec_a_value == pytest.approx(39.46, abs=0.05)
    assert liver.spec_b_value == pytest.approx(39.46, abs=0.05)
    assert abs(liver.spec_a_value - liver.spec_b_value) < 0.01
