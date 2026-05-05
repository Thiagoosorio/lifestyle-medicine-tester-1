"""Unit tests for instrument-slot loading + runtime resolution
(architecture_spec.md §7).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from healthscore.errors import ConfigValidationError
from healthscore.instruments import (
    InstrumentRegistry,
    load_instrument_registry,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SHIPPED_YAML = _REPO_ROOT / "configs" / "instruments.yaml"


def test_shipped_instruments_yaml_loads():
    reg = load_instrument_registry(_SHIPPED_YAML)
    assert "cognitive" in reg.by_slot
    assert "osa" in reg.by_slot
    assert reg.by_slot["cognitive"].primary == "moca"
    assert reg.by_slot["cognitive"].fallback == "mmse"
    assert reg.by_slot["cognitive"].active == "moca"
    assert reg.by_slot["osa"].primary == "stop_bang"
    assert reg.by_slot["osa"].fallback == "nosas"
    assert reg.by_slot["osa"].active == "stop_bang"


def test_shipped_yaml_has_no_fallback_active():
    reg = load_instrument_registry(_SHIPPED_YAML)
    assert reg.by_slot["cognitive"].fallback_active is False
    assert reg.by_slot["osa"].fallback_active is False
    assert reg.by_slot["cognitive"].fallback_reason is None


def test_score_to_slot_routes_both_primary_and_fallback():
    reg = load_instrument_registry(_SHIPPED_YAML)
    assert reg.score_to_slot["moca"] == "cognitive"
    assert reg.score_to_slot["mmse"] == "cognitive"
    assert reg.score_to_slot["stop_bang"] == "osa"
    assert reg.score_to_slot["nosas"] == "osa"


def test_inactive_instrument_correctly_identified():
    reg = load_instrument_registry(_SHIPPED_YAML)
    # Active in shipped config: moca + stop_bang.
    assert reg.is_inactive_instrument("moca") is False
    assert reg.is_inactive_instrument("mmse") is True
    assert reg.is_inactive_instrument("stop_bang") is False
    assert reg.is_inactive_instrument("nosas") is True


def test_score_outside_any_slot_is_not_inactive():
    """A regular composite score (e.g. fib4) is not in any slot, so is
    not 'inactive' — it should compute normally."""
    reg = load_instrument_registry(_SHIPPED_YAML)
    assert reg.is_inactive_instrument("fib4") is False
    assert reg.resolution_for_score("fib4") is None


# ── Fallback activation behaviour ────────────────────────────────────────


def _write_yaml(content: str) -> Path:
    tmp_root = _REPO_ROOT / ".codex_test_tmp"
    tmp_root.mkdir(exist_ok=True)
    case_dir = Path(tempfile.mkdtemp(prefix="instruments-yaml-", dir=tmp_root))
    yaml_path = case_dir / "instruments.yaml"
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


def test_fallback_active_demotes_to_low_with_reason():
    yaml_text = """
slots:
  cognitive:
    primary: moca
    fallback: mmse
    active: mmse
    fallback_reason: null
  osa:
    primary: stop_bang
    fallback: nosas
    active: stop_bang
    fallback_reason: null
"""
    yaml_path = _write_yaml(yaml_text)
    try:
        reg = load_instrument_registry(yaml_path)
        slot = reg.by_slot["cognitive"]
        assert slot.fallback_active is True
        assert slot.active == "mmse"
        assert slot.fallback_reason == "fallback_active:moca->>mmse"
        assert reg.is_inactive_instrument("moca") is True
        assert reg.is_inactive_instrument("mmse") is False
    finally:
        shutil.rmtree(yaml_path.parent, ignore_errors=True)


def test_invalid_active_raises_config_validation_error():
    yaml_text = """
slots:
  cognitive:
    primary: moca
    fallback: mmse
    active: not_a_real_score
"""
    yaml_path = _write_yaml(yaml_text)
    try:
        with pytest.raises(ConfigValidationError, match="active.*must equal primary or fallback"):
            load_instrument_registry(yaml_path)
    finally:
        shutil.rmtree(yaml_path.parent, ignore_errors=True)


def test_score_in_two_slots_raises_config_validation_error():
    """A score_id can appear in only one slot."""
    yaml_text = """
slots:
  cognitive:
    primary: moca
    fallback: mmse
    active: moca
  osa:
    primary: moca
    fallback: nosas
    active: moca
"""
    yaml_path = _write_yaml(yaml_text)
    try:
        with pytest.raises(ConfigValidationError, match="multiple instrument slots"):
            load_instrument_registry(yaml_path)
    finally:
        shutil.rmtree(yaml_path.parent, ignore_errors=True)


def test_missing_yaml_raises_config_validation_error():
    bogus = Path(__file__).parent / "this_does_not_exist.yaml"
    with pytest.raises(ConfigValidationError, match="not found"):
        load_instrument_registry(bogus)
