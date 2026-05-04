"""Unit tests for score_config.py: pydantic schema, JSON loader,
parse_gate_spec deserialiser, and end-to-end load of every shipped config.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from healthscore.enums import AnchorSource, ScoreKind
from healthscore.errors import ConfigValidationError
from healthscore.gates import GateAllOf, GateAnyOf, GateLeaf
from healthscore.score_config import (
    ScoreConfig,
    load_score_config,
    load_score_configs,
    parse_gate_spec,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"


# ── parse_gate_spec ────────────────────────────────────────────────────────


@pytest.mark.parametrize("spec", [None, [], {}])
def test_parse_gate_spec_returns_none_for_empty(spec):
    assert parse_gate_spec(spec) is None


def test_parse_gate_spec_round_trips_a_leaf():
    spec = {
        "field": "raw_inputs.atrial_fibrillation_status",
        "predicate": "equals",
        "expected": True,
        "missing_policy": "fail",
        "failure_reason_code": "af_not_documented",
    }
    gate = parse_gate_spec(spec)
    assert isinstance(gate, GateLeaf)
    assert gate.field == "raw_inputs.atrial_fibrillation_status"
    assert gate.expected is True


def test_parse_gate_spec_handles_compound_amap_form():
    spec = {
        "any_of": [
            {
                "field": "raw_inputs.cld",
                "predicate": "equals", "expected": True,
                "missing_policy": "skip", "failure_reason_code": "cld_no",
            },
            {
                "all_of": [
                    {"field": "score_results.fib4.raw_value", "predicate": "ge",
                     "expected": 1.3, "missing_policy": "fail",
                     "failure_reason_code": "fib4_low"},
                    {"field": "score_results.fli.raw_value", "predicate": "ge",
                     "expected": 60, "missing_policy": "fail",
                     "failure_reason_code": "fli_low"},
                ]
            },
        ]
    }
    gate = parse_gate_spec(spec)
    assert isinstance(gate, GateAnyOf)
    assert len(gate.any_of) == 2
    assert isinstance(gate.any_of[1], GateAllOf)


def test_parse_gate_spec_rejects_garbage():
    with pytest.raises(ConfigValidationError):
        parse_gate_spec({"weird_key": 42})


# ── ScoreConfig validation rules ───────────────────────────────────────────


def _minimal_config_dict(**overrides) -> dict:
    base = {
        "score_id": "fib4",
        "display_name": "FIB-4",
        "kind": "continuous_3anchor",
        "pmid_primary": "16729309",
        "input_variables": [
            {"name": "age", "unit": "years", "physio_min": 18, "physio_max": 120},
            {"name": "ast", "unit": "U/L"},
            {"name": "alt", "unit": "U/L"},
            {"name": "platelets", "unit": "10^9/L"},
        ],
        "formula": "fib4",
        "anchors": {
            "low":           {"value": 1.30, "q": 1.0, "source": "published"},
            "indeterminate": {"value": 1.985, "q": 0.5, "source": "constructed_midpoint"},
            "high":          {"value": 2.67, "q": 0.0, "source": "published"},
        },
        "anchors_unit": "fib4_units",
        "confidence": "high",
        "version": "2026.1",
        "composite_member": True,
        "composite_weight": 0.40,
    }
    base.update(overrides)
    return base


def test_minimal_score_config_loads():
    cfg = ScoreConfig.model_validate(_minimal_config_dict())
    assert cfg.score_id == "fib4"
    assert cfg.kind is ScoreKind.CONTINUOUS_3ANCHOR
    assert cfg.anchors.low.source is AnchorSource.PUBLISHED
    assert cfg.anchors.indeterminate.source is AnchorSource.CONSTRUCTED_MIDPOINT


def test_anchors_must_be_strictly_increasing():
    bad = _minimal_config_dict()
    bad["anchors"]["high"]["value"] = 0.0   # below low
    with pytest.raises(Exception):
        ScoreConfig.model_validate(bad)


def test_anchor_q_values_must_be_canonical():
    bad = _minimal_config_dict()
    bad["anchors"]["low"]["q"] = 0.99       # not 1.0
    with pytest.raises(Exception):
        ScoreConfig.model_validate(bad)


def test_composite_member_requires_weight():
    bad = _minimal_config_dict(composite_weight=None)
    with pytest.raises(Exception):
        ScoreConfig.model_validate(bad)


def test_negative_composite_weight_rejected():
    bad = _minimal_config_dict(composite_weight=-0.1)
    with pytest.raises(Exception):
        ScoreConfig.model_validate(bad)


# ── End-to-end: every shipped config loads and is internally consistent ──


def test_every_shipped_score_config_loads_cleanly():
    """Every JSON config under configs/scores/ must validate at load time."""
    configs = load_score_configs(_SCORE_CONFIGS)
    assert configs, "expected at least one config file under configs/scores/"
    # Spot-check the four liver composite scores are present.
    for required in ("fib4", "albi", "amap", "fli"):
        assert required in configs, f"liver composite score {required!r} missing"


def test_amap_config_carries_compound_gate():
    cfg = load_score_config(_SCORE_CONFIGS / "amap.json")
    assert cfg.gate_requirements is not None
    gate = parse_gate_spec(cfg.gate_requirements)
    assert isinstance(gate, GateAnyOf)


def test_liver_composite_weights_sum_to_one():
    """The four liver composite scores carry weights 0.40 / 0.20 / 0.20 / 0.20."""
    configs = load_score_configs(_SCORE_CONFIGS)
    composite = [
        c for c in configs.values()
        if c.composite_member and c.score_id in ("fib4", "albi", "amap", "fli")
    ]
    assert len(composite) == 4
    total = sum(c.composite_weight for c in composite)
    assert total == pytest.approx(1.0, abs=1e-6)


def test_confirmatory_scores_are_excluded_from_composite():
    """NAFLD-FS, APRI, HSI compute but are not in the composite per §1.5."""
    configs = load_score_configs(_SCORE_CONFIGS)
    for sid in ("nafld_fs", "apri", "hsi"):
        if sid in configs:
            assert not configs[sid].composite_member, (
                f"{sid} must be confirmatory-only (composite_member=false)"
            )


def test_fib4_indeterminate_anchor_is_constructed_midpoint():
    """Pin the §1.2 anchor-source rule: FIB-4's indeterminate is constructed,
    enforcing two-anchor PWL."""
    cfg = load_score_config(_SCORE_CONFIGS / "fib4.json")
    assert cfg.anchors.indeterminate.source is AnchorSource.CONSTRUCTED_MIDPOINT
    assert cfg.anchors.low.source is AnchorSource.PUBLISHED
    assert cfg.anchors.high.source is AnchorSource.PUBLISHED


def test_load_score_configs_detects_duplicate_score_id():
    """Engine refuses to start if two configs claim the same score_id.

    Uses a project-local tempdir to dodge the Windows-specific
    PermissionError on ``%TEMP%\\pytest-of-<user>`` we observed in earlier
    Phase 2 runs (same workaround as the wearable_wheel legacy-table test
    in the existing app suite)."""
    tmp_root = _REPO_ROOT / ".codex_test_tmp"
    tmp_root.mkdir(exist_ok=True)
    case_dir = Path(tempfile.mkdtemp(prefix="score-config-dup-", dir=tmp_root))
    try:
        cfg = _minimal_config_dict()
        (case_dir / "a.json").write_text(json.dumps(cfg), encoding="utf-8")
        (case_dir / "b.json").write_text(json.dumps(cfg), encoding="utf-8")
        with pytest.raises(ConfigValidationError, match="duplicate score_id"):
            load_score_configs(case_dir)
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
