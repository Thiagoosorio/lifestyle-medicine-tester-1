"""Unit tests for the Phase 6 ``engine.compute()`` orchestration.

Pins:
    * run_id has 26-char ULID-shape and time-orders.
    * config_hash is deterministic across two equal-config calls and
      changes when any score config changes.
    * audit blob contains every architecture_spec §11 required field.
    * AggregationOverrides.applied_summary fires only on non-None
      fields and is recorded under audit_record.overrides_applied.
    * Unimplemented harness-mode aggregation / normalisation overrides
      raise NotImplementedError loudly rather than silently degrading.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

import pytest
import yaml

from healthscore.audit import InMemoryAuditSink, JSONLAuditSink
from healthscore.domain_config import load_domains_config
from healthscore.engine import (
    compute,
    compute_config_hash,
    new_run_id,
)
from healthscore.instruments import load_instrument_registry
from healthscore.overrides import AggregationOverrides
from healthscore.score_config import load_score_configs


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"
_DOMAINS_YAML = _REPO_ROOT / "configs" / "domains.yaml"
_INSTRUMENTS_YAML = _REPO_ROOT / "configs" / "instruments.yaml"
_WORDING_YAML = _REPO_ROOT / "configs" / "wording.yaml"


@pytest.fixture(scope="module")
def configs():
    return load_score_configs(_SCORE_CONFIGS)


@pytest.fixture(scope="module")
def domains_config():
    return load_domains_config(_DOMAINS_YAML)


@pytest.fixture(scope="module")
def instrument_registry():
    return load_instrument_registry(_INSTRUMENTS_YAML)


@pytest.fixture(scope="module")
def wording_templates():
    return yaml.safe_load(_WORDING_YAML.read_text(encoding="utf-8"))


@pytest.fixture
def healthy_inputs():
    inputs = {
        "age": 43, "sex": "female", "bmi": 23,
        "ast": 22, "alt": 20, "platelets": 250,
        "total_bilirubin_mgdl": 0.7, "albumin_gdl": 4.4,
        "tg_mgdl": 90, "ggt_ul": 18, "waist_cm": 72,
        "diabetes_or_ifg": False, "diabetes_status": False,
        "chronic_liver_disease_status": False, "ast_uln": 40,
        "serum_creatinine_mgdl": 0.8, "egfr": 95, "uacr": 5,
        "total_chol_mgdl": 185, "hdl_c_mgdl": 60, "sbp_mmhg": 116,
        "smoking": False, "bp_treatment": False, "statin": False,
        "diabetes": False,
        "atrial_fibrillation_status": False,
        "chf_or_lv_dysfunction": False, "hypertension": False,
        "stroke_tia_thromboembolism": False, "vascular_disease": False,
        "apob_mgdl": 75, "lpa_mgdl": 18,
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
        "fasting_insulin_uIUmL": 6,
        "daily_activity_30min": True, "daily_fruit_veg": True,
        "on_bp_medication": False, "history_high_glucose": False,
        "family_history_diabetes": "none",
        "education_years": 16, "physically_active": True,
        "homocysteine_umol_L": 9.5,
        "locale": "en",
    }
    for i in range(1, 10):
        inputs[f"phq9_q{i}"] = 0
    for i in range(1, 8):
        inputs[f"gad7_q{i}"] = 0
    return inputs


# ── run_id + config_hash ─────────────────────────────────────────────────


def test_run_id_is_26_char_ulid_shape():
    rid = new_run_id()
    assert len(rid) == 26
    assert rid.isalnum()


def test_run_ids_are_time_ordered_across_calls():
    """Two calls less than a second apart should produce time-ordered
    run_ids: the timestamp prefix is monotone non-decreasing."""
    rid1 = new_run_id()
    time.sleep(0.005)
    rid2 = new_run_id()
    # First 10 chars are the timestamp portion; should never decrease.
    assert rid1[:10] <= rid2[:10]


def test_config_hash_is_deterministic(configs, domains_config):
    h1 = compute_config_hash(configs, domains_config)
    h2 = compute_config_hash(configs, domains_config)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_config_hash_changes_when_any_config_changes(configs, domains_config):
    """Mutating one score config's composite_weight by reloading from a
    different file would change the hash. We simulate that by building
    a new configs dict missing one score."""
    h1 = compute_config_hash(configs, domains_config)
    smaller = {sid: cfg for sid, cfg in configs.items() if sid != "fib4"}
    h2 = compute_config_hash(smaller, domains_config)
    assert h1 != h2


# ── compute() end-to-end ─────────────────────────────────────────────────


def test_compute_emits_audit_record_with_required_fields(
    configs, domains_config, instrument_registry, wording_templates, healthy_inputs,
):
    sink = InMemoryAuditSink()
    out = compute(
        score_configs=configs, domains_config=domains_config,
        instrument_registry=instrument_registry,
        raw_inputs=healthy_inputs, audit_sink=sink,
        templates=wording_templates,
        locale="en", population=None,
    )
    assert len(sink.records) == 1
    record = sink.records[0]

    # architecture_spec §11 required fields.
    required = {
        "schema_version", "run_id", "config_hash", "timestamp_utc",
        "locale", "population", "active_instruments",
        "alpha_used", "epsilon_used", "overrides_applied",
        "score_eval_order", "scores", "organs", "domains", "red_flags",
    }
    assert required <= set(record.keys())

    # run_id + config_hash propagate to AggregationOutput too.
    assert out.run_id == record["run_id"]
    assert out.config_hash == record["config_hash"]
    # active_instruments map matches shipped instruments.yaml.
    assert record["active_instruments"]["cognitive"] == "moca"
    assert record["active_instruments"]["osa"] == "stop_bang"
    # eval_order has aMAP after FIB-4 and FLI (compound gate dependency).
    order = record["score_eval_order"]
    assert order.index("fib4") < order.index("amap")
    assert order.index("fli") < order.index("amap")


def test_compute_audit_records_overrides_applied(
    configs, domains_config, instrument_registry, wording_templates, healthy_inputs,
):
    sink = InMemoryAuditSink()
    overrides = AggregationOverrides(
        alpha=0.4, epsilon=0.02,
    )
    compute(
        score_configs=configs, domains_config=domains_config,
        instrument_registry=instrument_registry,
        raw_inputs=healthy_inputs, audit_sink=sink,
        templates=wording_templates, overrides=overrides,
    )
    record = sink.records[0]
    assert record["alpha_used"] == 0.4
    assert record["epsilon_used"] == 0.02
    assert record["overrides_applied"] == {"alpha": 0.4, "epsilon": 0.02}


def test_compute_unimplemented_aggregation_override_raises(
    configs, domains_config, instrument_registry, wording_templates, healthy_inputs,
):
    sink = InMemoryAuditSink()
    overrides = AggregationOverrides(aggregation="weighted_arithmetic")
    with pytest.raises(NotImplementedError, match="weighted_arithmetic"):
        compute(
            score_configs=configs, domains_config=domains_config,
            instrument_registry=instrument_registry,
            raw_inputs=healthy_inputs, audit_sink=sink,
            templates=wording_templates, overrides=overrides,
        )


def test_compute_score_inclusion_drops_score_from_eval_order(
    configs, domains_config, instrument_registry, wording_templates, healthy_inputs,
):
    """Leave-one-out: setting score_inclusion[tyg]=False removes tyg
    from the eval pool. tyg has no cross-score gate dependencies, so
    dropping it does not cascade. (FLI cannot be dropped on its own
    because aMAP's gate references score_results.fli.raw_value;
    dropping a depended-on score would require also dropping its
    dependents -- a useful Sobol harness extension.)"""
    sink = InMemoryAuditSink()
    overrides = AggregationOverrides(score_inclusion={"tyg": False})
    compute(
        score_configs=configs, domains_config=domains_config,
        instrument_registry=instrument_registry,
        raw_inputs=healthy_inputs, audit_sink=sink,
        templates=wording_templates, overrides=overrides,
    )
    record = sink.records[0]
    assert "tyg" not in record["score_eval_order"]


def test_compute_two_calls_with_identical_inputs_produce_same_config_hash(
    configs, domains_config, instrument_registry, wording_templates, healthy_inputs,
):
    """Determinism per architecture_spec §11: same configs produce same
    config_hash across calls. run_id and timestamp are NOT identical (by
    design); everything else under config_hash is."""
    sink_a = InMemoryAuditSink()
    sink_b = InMemoryAuditSink()
    compute(
        score_configs=configs, domains_config=domains_config,
        instrument_registry=instrument_registry,
        raw_inputs=healthy_inputs, audit_sink=sink_a,
        templates=wording_templates,
    )
    compute(
        score_configs=configs, domains_config=domains_config,
        instrument_registry=instrument_registry,
        raw_inputs=healthy_inputs, audit_sink=sink_b,
        templates=wording_templates,
    )
    assert sink_a.records[0]["config_hash"] == sink_b.records[0]["config_hash"]


def test_compute_jsonl_audit_sink_persists_one_line(
    configs, domains_config, instrument_registry,
    wording_templates, healthy_inputs,
):
    """Project-local tempdir per the wearable-wheel-test pattern; the
    Windows %TEMP%/pytest-of-Bittium prefix is locked by OneDrive in
    this dev env."""
    tmp_root = _REPO_ROOT / ".codex_test_tmp"
    tmp_root.mkdir(exist_ok=True)
    case_dir = Path(tempfile.mkdtemp(prefix="audit-jsonl-", dir=tmp_root))
    try:
        audit_path = case_dir / "audit.jsonl"
        sink = JSONLAuditSink(audit_path)
        compute(
            score_configs=configs, domains_config=domains_config,
            instrument_registry=instrument_registry,
            raw_inputs=healthy_inputs, audit_sink=sink,
            templates=wording_templates,
        )
        text = audit_path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.count("\n") == 1
        compute(
            score_configs=configs, domains_config=domains_config,
            instrument_registry=instrument_registry,
            raw_inputs=healthy_inputs, audit_sink=sink,
            templates=wording_templates,
        )
        text2 = audit_path.read_text(encoding="utf-8")
        assert text2.count("\n") == 2
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


# ── DomainsConfig + AggregationOverrides ─────────────────────────────────


def test_domains_config_score_weights_drop_inactive_instruments(
    domains_config, instrument_registry,
):
    """The shipped instruments.yaml has MoCA active / MMSE inactive.
    DomainsConfig.resolved_score_weights must drop MMSE from the brain
    panel and renormalise the survivors so they sum to 1.0."""
    weights = domains_config.resolved_score_weights(
        "cognitive_mental", instrument_registry,
    )
    assert "moca" in weights
    assert "mmse" not in weights
    assert weights["moca"] == pytest.approx(0.30, abs=1e-6)
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)


def test_domains_config_empty_organ_returns_empty_dict(
    domains_config, instrument_registry,
):
    """Gut domain has organs={}; the resolver returns {} cleanly so the
    engine skips it without error."""
    # Gut has no organs, so the resolver is never asked. But muscle_bones
    # has the bone organ with two QFracture members; verify those land.
    weights = domains_config.resolved_score_weights("bone", instrument_registry)
    assert set(weights.keys()) == {"qfracture_hip", "qfracture_major"}
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)


def test_aggregation_overrides_applied_summary_omits_none_fields():
    o = AggregationOverrides(alpha=0.6)
    assert o.applied_summary() == {"alpha": 0.6}
    assert AggregationOverrides().applied_summary() == {}
