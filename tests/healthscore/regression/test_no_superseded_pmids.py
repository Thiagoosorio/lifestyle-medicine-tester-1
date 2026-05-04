"""Snapshot test for Tier 2 PMID corrections.

Per architecture_spec.md Appendix A Phase 2:

    Snapshot test: no config in configs/scores/ carries the four
    superseded PMIDs (20921437, 22941793, or 29676998 in the panel's
    clinical-chemistry PhenoAge slot).

The corrections committed in commitments_log.md (4 May 2026):

    Hb + RDW Mortality Risk:           20921437  ->  19880817
    QFracture 10-year Hip Fracture:    22941793  ->  22619194
    QFracture 10-year Major Fracture:  22941793  ->  22619194
    Levine PhenoAge (clinical-chemistry):
                                       29676998  ->  30596641

PMID 29676998 is allowed to appear in a calibration_caveat string that
explicitly explains the correction, because the field is *audit prose*
not a citation. The test enforces only the pmid_primary slot is clean.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"

_SUPERSEDED_PMIDS_IN_PMID_PRIMARY = {
    "20921437": "Poole 2010 (pacemaker complications) -- replace with 19880817 (Patel 2010)",
    "22941793": "Webert 2012 (acquired hemophilia A) -- replace with 22619194 (Hippisley-Cox 2012)",
}

#: 29676998 is the DNA-methylation PhenoAge (Levine 2018).  It is a real
#: paper but a *different score* from the clinical-chemistry PhenoAge that
#: this app's input panel matches.  pmid_primary for the score_id "phenoage"
#: must be 30596641 (Liu 2018) -- the clinical-chemistry derivation.
_FORBIDDEN_DNAM_PHENOAGE_FOR_THIS_SLOT = "29676998"


def _config_files() -> list[Path]:
    if not _SCORE_CONFIGS.exists():
        return []
    return sorted(_SCORE_CONFIGS.glob("*.json"))


@pytest.mark.parametrize("config_file", _config_files(), ids=lambda p: p.name)
def test_no_pmid_primary_uses_a_universally_superseded_id(config_file):
    raw = json.loads(config_file.read_text(encoding="utf-8"))
    pmid = str(raw.get("pmid_primary") or "")
    if pmid in _SUPERSEDED_PMIDS_IN_PMID_PRIMARY:
        pytest.fail(
            f"{config_file.name}: pmid_primary={pmid!r} is superseded.\n"
            f"  reason: {_SUPERSEDED_PMIDS_IN_PMID_PRIMARY[pmid]}\n"
            f"  see: commitments_log.md, source-data panel audit 4 May 2026"
        )


def test_phenoage_config_uses_clinical_chemistry_pmid_not_dnam():
    path = _SCORE_CONFIGS / "phenoage.json"
    if not path.exists():
        pytest.skip("configs/scores/phenoage.json not present yet")
    raw = json.loads(path.read_text(encoding="utf-8"))
    pmid = str(raw.get("pmid_primary") or "")
    assert pmid != _FORBIDDEN_DNAM_PHENOAGE_FOR_THIS_SLOT, (
        f"phenoage.json carries the DNAm-PhenoAge PMID 29676998 -- that's "
        f"a different score requiring methylation array data.  Use the "
        f"clinical-chemistry PhenoAge PMID 30596641 (Liu 2018) instead."
    )
    assert pmid == "30596641", (
        f"phenoage.json pmid_primary should be 30596641 (Liu 2018 NHANES-IV "
        f"clinical-chemistry PhenoAge), not {pmid!r}"
    )


def test_hb_rdw_config_uses_patel_2010_pmid():
    path = _SCORE_CONFIGS / "hb_rdw.json"
    if not path.exists():
        pytest.skip("configs/scores/hb_rdw.json not present yet")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert str(raw.get("pmid_primary")) == "19880817", (
        "hb_rdw.json pmid_primary must be 19880817 (Patel 2010 NHANES-III "
        "RDW + mortality), not the prior pacemaker-complications paper"
    )


def test_qfracture_configs_use_hippisley_cox_2012_pmid():
    for fname in ("qfracture_hip.json", "qfracture_major.json"):
        path = _SCORE_CONFIGS / fname
        if not path.exists():
            pytest.skip(f"{path} not present yet")
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert str(raw.get("pmid_primary")) == "22619194", (
            f"{fname} pmid_primary must be 22619194 (Hippisley-Cox 2012 "
            f"QFracture-2012), not the prior acquired-hemophilia paper"
        )
