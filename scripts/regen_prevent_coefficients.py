"""Regenerate config/prevent_coefficients.py from the AHA PREVENT equations.

Source: preventr R package sysdata.rda (https://github.com/martingmayer/preventr)
which transcribes the Table S12 A-J coefficients from the Khan 2024 Circulation
paper supplement (PMID 37947085).

Run:
    pip install pyreadr requests
    python scripts/regen_prevent_coefficients.py
"""

from __future__ import annotations

import pprint
import sys
from pathlib import Path
from urllib.request import urlopen

import pyreadr

RDA_URL = "https://github.com/martingmayer/preventr/raw/main/R/sysdata.rda"
OUT_PATH = Path(__file__).resolve().parent.parent / "config" / "prevent_coefficients.py"

PREDICTOR_KEY_MAP = {
    "Age, per 10 years": "age",
    "Age, 10 years": "age",
    "non-HDL-C per 1 mmol/L": "non_hdl_c",
    "HDL-C per 0.3 mmol/L": "hdl_c",
    "SBP <110 per 20 mmHg": "sbp_lt_110",
    "SBP \u2265110 per 20 mmHg": "sbp_gte_110",
    "Diabetes": "dm",
    "Current smoking": "smoking",
    "BMI <30, per 5 kg/m2": "bmi_lt_30",
    "BMI 30+, per 5 kg/m2": "bmi_gte_30",
    "eGFR <60, per -15 ml": "egfr_lt_60",
    "eGFR 60+, per -15 ml": "egfr_gte_60",
    "Anti-hypertensive use": "bp_tx",
    "Statin use": "statin",
    "Treated SBP \u2265110 mm Hg per 20 mm Hg": "bp_tx_sbp_gte_110",
    "Treated non-HDL-C": "statin_non_hdl_c",
    "Age per 10yr * non-HDL-C per 1 mmol/L": "age_non_hdl_c",
    "Age per 10yr * HDL-C per 1 mml/L": "age_hdl_c",
    "Age per 10yr * SBP \u2265110 mm Hg per 20 mmHg": "age_sbp_gte_110",
    "Age per 10yr * diabetes": "age_dm",
    "Age per 10yr * current smoking": "age_smoking",
    "Age per 10yr * BMI 30+ per 5 kg/m2": "age_bmi_gte_30",
    "Age per 10yr * eGFR <60, per -15 ml": "age_egfr_lt_60",
    "SDI decile categories 4-6 vs. 1-3": "sdi_4_to_6",
    "SDI decile categories 7-10 vs. 1-3": "sdi_7_to_10",
    "Missing SDI": "missing_sdi",
    "ln-ACR, mg/g, per 1 ln unit": "ln_uacr",
    "Missing ACR/PCR/Dipstick": "missing_uacr",
    "HbA1c in DM, per 1%": "hba1c_dm",
    "HbA1c no DM, per 1%": "hba1c_no_dm",
    "Missing HbA1c": "missing_hba1c",
    "Constant": "constant",
}


def main() -> None:
    cache = Path(__file__).resolve().parent / "_sysdata.rda"
    if not cache.exists():
        print(f"Downloading {RDA_URL} -> {cache}")
        cache.write_bytes(urlopen(RDA_URL).read())

    result = pyreadr.read_r(str(cache))

    lines = [
        "# AUTO-GENERATED from the American Heart Association PREVENT equations",
        "# supplementary Excel file associated with",
        "# Khan SS et al. Circulation 2024;149(6):430-449 (PMID: 37947085)",
        "# Coefficient values retrieved from the preventr R package sysdata.rda",
        "# (https://github.com/martingmayer/preventr) which transcribes the",
        "# official AHA Table S12 A-J simplified coefficient tables.",
        "# DO NOT hand-edit coefficients -- regenerate with scripts/regen_prevent_coefficients.py",
        "",
        '"""Official AHA PREVENT equation coefficients (Khan 2024 Circulation)."""',
        "",
        "from __future__ import annotations",
        "",
        "# Outcome keys: total_cvd, ascvd, heart_failure, chd, stroke",
        "# Sex keys: female, male",
        "# Model keys: base, hba1c, uacr, full",
        "",
    ]

    models_py: dict[str, dict] = {}
    for model_key in ["base_10yr", "hba1c_10yr", "uacr_10yr", "full_10yr"]:
        df = result[model_key]
        preds = df["beta_coefficients"].tolist()
        keys = [PREDICTOR_KEY_MAP[p] for p in preds]
        model_data: dict[str, dict] = {}
        for col in df.columns:
            if col == "beta_coefficients":
                continue
            sex, _, outcome = col.partition("_")
            model_data.setdefault(sex, {})[outcome] = dict(
                zip(keys, [float(x) for x in df[col].tolist()])
            )
        models_py[model_key] = model_data

    for model_key, data in models_py.items():
        var_name = f"PREVENT_{model_key.upper()}"
        lines.append(f"{var_name} = {pprint.pformat(data, sort_dicts=False, width=100)}")
        lines.append("")

    lines.append("")
    lines.append("PREVENT_MODELS = {")
    for model_key in models_py:
        friendly = model_key.replace("_10yr", "")
        lines.append(f'    "{friendly}": PREVENT_{model_key.upper()},')
    lines.append("}")
    lines.append("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({sum(1 for _ in lines)} lines)")


if __name__ == "__main__":
    sys.exit(main())
