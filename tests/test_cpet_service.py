import services.cpet_service as cpet_service
from services.cpet_service import (
    build_cpet_coach_summary,
    build_metabolic_profile,
    build_training_zones,
    extract_cpet_from_text,
    get_cpet_reports,
    normalize_cpet_metrics,
    save_cpet_report,
)
from config.cpet_norms import classify_vo2max


# Reconstructed Cortex MetaSoft / MetaLyzer export (the format the user's lab
# produces). Uses the V'O2 prime notation and the fixed 10-column Summary Table.
CORTEX_TEXT = """CPET Basic Results
Name Al-Janabi, Mariam
Age 25
Sex female
Weight 68.8 kg
Height 163 cm
Date 6/23/2026 12:51 PM
Workload Protocol IHLAD Protocol 15 Watt
Sport Cycling
Device MetaLyzer 3B-R3
Summary Table
V'O2/kg ml/min/kg 4 19 66 53 31 106 85 36 125 29
V'O2/HR ml 6 14 121 92 14 123 94 15 132 11
HR /min 48 95 55 57 151 87 91 167 95 175
WR W 0 99 58 52 164 96 86 190 112 170
V'E/V'O2 26.1 22.3 - 76 24.8 - 85 29.2 - -
V'E/V'CO2 31.9 24.9 - 94 23.8 - 90 26.5 - -
RER 0.82 0.89 - 81 1.04 - 94 1.10 - -
V'E L/min 10.1 29.6 34 38 55.9 65 72 77.5 90 86.1
Slope Values
V'E(V'CO2) Slope: 22.8 Correlation 1.00 V'E = 22.8 * V'CO2 + 4.0
Maximum Oxygen Pulse Wasserman equation 11 ml
Maximum Heart Rate Traditional formula for bicycle test 175 /min
"""


def test_extract_cortex_metasoft_table_reads_peak_and_threshold_columns():
    extracted = extract_cpet_from_text(CORTEX_TEXT)

    assert extracted["source_format"] == "cortex_metasoft"
    m = extracted["metrics"]
    # Peak column (index 7 of the Summary Table), not Rest / %Norm.
    assert m["peak_vo2_ml_kg_min"] == 36.0
    assert m["peak_hr_bpm"] == 167.0
    assert m["peak_power_w"] == 190.0
    assert m["peak_rer"] == 1.10
    assert m["peak_ve_l_min"] == 77.5
    # VT1 / VT2 anchors.
    assert m["vt1_hr_bpm"] == 95.0 and m["vt2_hr_bpm"] == 151.0
    assert m["vt1_power_w"] == 99.0 and m["vt2_power_w"] == 164.0
    assert m["vt1_vo2_ml_kg_min"] == 19.0 and m["vt2_vo2_ml_kg_min"] == 31.0
    # Peak %Norm columns become % predicted; %Max become % of peak VO2.
    assert m["peak_vo2_pct_pred"] == 125.0
    assert m["hr_pct_pred"] == 95.0
    assert m["o2_pulse_pct_pred"] == 132.0
    assert m["vt1_pct_peak_vo2"] == 53.0 and m["vt2_pct_peak_vo2"] == 85.0
    # Demographics + slope from prose.
    assert m["sex"] == "female" and m["age_years"] == 25.0
    assert m["ve_vco2_slope"] == 22.8
    # O2 pulse taken from the VO2/HR peak column (15), NOT the predicted normal (11).
    assert m["o2_pulse_ml_beat"] == 15.0
    # Breathing reserve computed from peak VE vs ventilation ceiling (~10%),
    # never scraped as a spurious value.
    assert m["breathing_reserve_pct"] == 10.0


def test_cortex_notation_folding_matches_vo2_labels():
    normalized = cpet_service._normalize_text("V'O2peak 2.51 L/min and V'E/V'CO2 slope 22.8")
    assert "VO2peak" in normalized
    assert "VE/VCO2" in normalized


def test_cortex_summary_row_missing_trailing_column_is_not_misread():
    # A Summary Table VO2/kg row that lost its blank trailing "Norm" cell (9 tokens)
    # must still map columns by the Summary layout, not fall into the 6-col Test
    # Results layout that would read the VT1 %norm/%max columns as VT2/peak VO2.
    text = (
        "MetaLyzer 3B\n"
        "Summary Table\n"
        "V'O2/kg ml/min/kg 4 19 66 53 31 106 85 36 125\n"  # 9 value tokens (Norm blank)
    )
    m = cpet_service.parse_cortex_report(text)
    assert m["vt1_vo2_ml_kg_min"] == 19.0
    assert m["vt2_vo2_ml_kg_min"] == 31.0
    assert m["peak_vo2_ml_kg_min"] == 36.0


def test_non_cortex_report_is_not_routed_through_cortex_parser():
    # A COSMED-style report with generic "VO2/kg" and "VO2peak" but no Cortex prime
    # notation or vendor marker must use the generic path, not the Cortex parser.
    text = "COSMED Omnia\nVO2/kg 45 4 22 40 89 100\nVO2peak 3.1 L/min\n"
    assert cpet_service._looks_like_cortex(cpet_service._normalize_text(text), text) is False
    extracted = extract_cpet_from_text(text)
    assert extracted["source_format"] == "generic"


def test_rowing_ergometer_is_not_graded_against_cycle_norms():
    rowing = classify_vo2max(40, "female", 25, "row ergometer")
    assert rowing["modality_used"] == "other"
    assert "cycle" not in rowing["reference"].lower() or "no modality-specific" in rowing["reference"].lower()
    # Bare "ergometer" is treated as an assumed cycle, with a caveat.
    ambiguous = classify_vo2max(40, "female", 25, "ergometer")
    assert ambiguous["modality_used"] == "cycle_assumed"



def test_fitness_classification_is_modality_matched():
    # A cycle VO2peak graded against cycle norms is above average; the same value
    # mis-graded against treadmill norms drops to average -- the classic "fair" error.
    cycle = classify_vo2max(36, "female", 25, "cycle ergometer")
    treadmill = classify_vo2max(36, "female", 25, "treadmill")

    assert cycle["percentile"] > 60 and "Good" in cycle["category"]
    assert treadmill["percentile"] < cycle["percentile"]
    # Missing sex cannot be placed on norms.
    unknown = classify_vo2max(36, None, 25, "cycle")
    assert unknown["insufficient_context"] is True


def _br_flag(summary):
    flags = [f for f in summary["coach_flags"] if f["Area"] == "Breathing reserve"]
    return flags[0] if flags else None


def test_low_breathing_reserve_ceiling_is_routine_only_when_spo2_confirmed_normal():
    base = {"peak_vo2_ml_kg_min": 36, "sex": "female", "age_years": 25, "peak_rer": 1.10}

    # Maximal effort + normal SpO2 -> normal ceiling phenomenon (Routine).
    ok = build_cpet_coach_summary({**base, "breathing_reserve_pct": 10, "spo2_nadir_pct": 96}, modality="cycle ergometer")
    assert _br_flag(ok)["Priority"] == "Routine"

    # Maximal effort but SpO2 NOT recorded -> cannot fully reassure (Medium).
    unknown = build_cpet_coach_summary({**base, "peak_ve_l_min": 77.5, "mvv_l_min": 86.1}, modality="cycle ergometer")
    assert _br_flag(unknown)["Priority"] == "Medium"

    # Low reserve WITH desaturation is escalated (High).
    desat = build_cpet_coach_summary({**base, "breathing_reserve_pct": 10, "spo2_nadir_pct": 88}, modality="cycle ergometer")
    assert _br_flag(desat)["Priority"] == "High"


def test_consistency_checks_pass_for_internally_coherent_report():
    summary = build_cpet_coach_summary(
        {
            "peak_vo2_ml_kg_min": 36,
            "peak_vo2_l_min": 2.51,
            "weight_kg": 68.8,
            "peak_hr_bpm": 167,
            "o2_pulse_ml_beat": 15.0,
            "vt1_vo2_ml_kg_min": 19,
            "vt2_vo2_ml_kg_min": 31,
            "sex": "female",
            "age_years": 25,
            "peak_vo2_pct_pred": 125,
        },
        modality="cycle ergometer",
    )
    statuses = {r["Check"]: r["Status"] for r in summary["consistency_rows"]}
    assert statuses["Threshold ordering"] == "OK"
    assert statuses["Relative vs absolute VO2"] == "OK"
    assert statuses["O2 pulse consistency"] == "OK"
    assert statuses["Percent-predicted vs percentile"] == "Reconciled"


def test_talking_points_flag_cart_label_and_modality():
    summary = build_cpet_coach_summary(
        {"peak_vo2_ml_kg_min": 36, "sex": "female", "age_years": 25, "peak_vo2_pct_pred": 125},
        modality="cycle ergometer",
    )
    joined = " ".join(summary["talking_points"]).lower()
    assert "percentile" in joined
    assert "cart" in joined
    assert "cycle" in joined


SAMPLE_TEXT = """
COSMED CPET Report
Test Date 2026-05-20
Protocol Bike ramp 25 W/min
Cycle ergometer
Age 42 years
Weight 82.0 kg
Exercise Duration 10.4 min
Peak VO2 42.5 mL/kg/min
Peak VO2 absolute 3.49 L/min
Peak VO2 % predicted 118 %
Peak RER 1.12
Resting HR 62 bpm
Peak HR 184 bpm
Predicted HR 188 bpm
VT1 VO2 25.0 mL/kg/min
VT1 HR 142 bpm
VT1 Power 190 W
VT2 VO2 36.0 mL/kg/min
VT2 HR 168 bpm
VT2 Power 265 W
VE/VCO2 slope 28.5
Breathing Reserve 24 %
O2 pulse % predicted 102 %
VO2/work-rate slope 10.1 mL/min/W
PETCO2 at AT 39 mmHg
SpO2 nadir 96 %
OUES 2.9
Peak lactate 8.2 mmol/L
"""


def test_extract_cpet_from_text_finds_core_metrics():
    extracted = extract_cpet_from_text(SAMPLE_TEXT)

    assert extracted["test_date"] == "2026-05-20"
    assert extracted["test_modality"] == "cycle ergometer"
    metrics = extracted["metrics"]
    assert metrics["peak_vo2_ml_kg_min"] == 42.5
    assert metrics["peak_vo2_l_min"] == 3.49
    assert metrics["peak_vo2_pct_pred"] == 118.0
    assert metrics["peak_rer"] == 1.12
    assert metrics["vt1_hr_bpm"] == 142.0
    assert metrics["vt2_power_w"] == 265.0
    assert metrics["ve_vco2_slope"] == 28.5
    assert metrics["breathing_reserve_pct"] == 24.0


def test_normalize_cpet_metrics_derives_hr_vo2_and_threshold_percentages():
    metrics = normalize_cpet_metrics(
        {
            "age_years": 40,
            "weight_kg": 80,
            "peak_vo2_l_min": 3.2,
            "peak_hr_bpm": 176,
            "rest_hr_bpm": 56,
            "vt1_vo2_ml_kg_min": 24,
            "vt2_vo2_ml_kg_min": 36,
            "peak_ve_l_min": 120,
            "mvv_l_min": 160,
        }
    )

    assert metrics["predicted_hr_bpm"] == 180
    assert metrics["hr_pct_pred"] == 97.8
    assert metrics["hr_reserve_bpm"] == 4
    assert metrics["chronotropic_index"] == 0.97
    assert metrics["peak_vo2_ml_kg_min"] == 40.0
    assert metrics["breathing_reserve_pct"] == 25.0
    assert metrics["o2_pulse_ml_beat"] == 18.2
    assert metrics["vt1_pct_peak_vo2"] == 60.0
    assert metrics["vt2_pct_peak_vo2"] == 90.0


def test_cpet_summary_flags_quality_medical_and_zone_items():
    summary = build_cpet_coach_summary(
        {
            "peak_vo2_ml_kg_min": 43,
            "peak_vo2_pct_pred": 108,
            "peak_rer": 1.01,
            "peak_hr_bpm": 150,
            "predicted_hr_bpm": 185,
            "ve_vco2_slope": 38,
            "breathing_reserve_pct": 12,
            "o2_pulse_pct_pred": 74,
            "spo2_nadir_pct": 88,
        },
        client_context="endurance",
    )

    validity_statuses = {row["Status"] for row in summary["validity_gate"]}
    areas = {row["Area"] for row in summary["coach_flags"]}

    assert "Submaximal" in validity_statuses
    assert "Ventilatory efficiency" in areas
    assert "Breathing reserve" in areas
    assert "Exercise oxygen saturation" in areas
    assert "Zone prescription" in areas
    assert "Athlete predicted norms" in areas


def test_cpet_summary_includes_detailed_results_and_next_steps():
    summary = build_cpet_coach_summary(
        {
            "peak_vo2_ml_kg_min": 36,
            "sex": "female",
            "age_years": 25,
            "peak_rer": 1.10,
            "peak_hr_bpm": 167,
            "predicted_hr_bpm": 175,
            "vt1_hr_bpm": 95,
            "vt2_hr_bpm": 151,
            "vt1_power_w": 99,
            "vt2_power_w": 164,
            "peak_power_w": 190,
            "ve_vco2_slope": 22.8,
            "spo2_nadir_pct": 96,
            "fatmax_hr_bpm": 86,
            "fatmax_g_min": 0.53,
        },
        modality="cycle ergometer",
    )

    headline = summary["result_headline"]
    assert headline["Level"] == "Routine"
    assert "Peak VO2 is 36.0" in headline["Headline"]

    domains = {row["Domain"] for row in summary["result_rows"]}
    assert {"Aerobic capacity", "Effort validity", "Training zones", "Medical-pattern clues", "Fuel use"} <= domains

    plan = summary["action_plan"]
    assert any(row["Focus"] == "Base training" and "89-99 W" in row["Dose / target"] for row in plan)
    assert any(row["Focus"] == "Raise the threshold" and "164 W" in row["Dose / target"] for row in plan)
    assert any(row["Focus"] == "Strength and repeat testing" for row in plan)


def test_cpet_action_plan_prioritizes_safety_review_for_clinical_flags():
    summary = build_cpet_coach_summary(
        {
            "peak_vo2_ml_kg_min": 24,
            "sex": "male",
            "age_years": 58,
            "peak_rer": 1.11,
            "vt1_hr_bpm": 105,
            "vt2_hr_bpm": 138,
            "breathing_reserve_pct": 8,
            "spo2_nadir_pct": 88,
            "o2_pulse_pct_pred": 72,
        },
        modality="treadmill",
    )

    assert summary["result_headline"]["Level"] == "High"
    first_step = summary["action_plan"][0]
    assert first_step["Focus"] == "Safety handoff"
    assert "Breathing reserve" in first_step["Dose / target"]
    assert "clinician" in first_step["Do this"].lower()


def test_training_zone2_tops_out_at_vt1_not_vt2():
    # The core fix: endurance Zone 2 must end at VT1, never span to VT2.
    zones = build_training_zones(
        {
            "vt1_hr_bpm": 95, "vt2_hr_bpm": 151,
            "vt1_power_w": 99, "vt2_power_w": 164,
            "fatmax_hr_bpm": 86, "fatmax_hr_low_bpm": 84, "fatmax_hr_high_bpm": 87,
        },
        modality="cycle ergometer",
    )
    assert zones["has_zones"]
    z2 = next(r for r in zones["zone_table"] if r["Zone"].startswith("Z2"))
    z3 = next(r for r in zones["zone_table"] if r["Zone"].startswith("Z3"))
    # Zone 2 HR ends at VT1 (95); Zone 3 (tempo) begins at VT1.
    assert z2["HR (bpm)"].endswith("-95")
    assert z3["HR (bpm)"].startswith("95-")
    # Zone 2 is NOT the whole VT1-VT2 span.
    assert z2["HR (bpm)"] != "95-151"
    z2d = zones["zone2"]
    # Ceiling = VT1 (LT1/~2 mmol); target is JUST UNDER LT1 (VT1-6 = 89), not FatMax.
    assert z2d["ceiling_hr"] == 95
    assert z2d["target_hr"] == "~89 bpm"
    assert z2d["fatmax_floor"] == "84-87 bpm"  # FatMax is the FLOOR marker, not the target
    # FatMax 9 bpm below VT1 -> divergent (recreational) pattern.
    assert z2d["training_pattern"] == "divergent"
    assert zones["primary_anchor"] == "power"
    # Polarized 3-zone view is separate.
    assert zones["polarized_rows"]


def test_training_zones_incomplete_without_two_thresholds():
    zones = build_training_zones({"vt1_hr_bpm": 95})  # no VT2
    assert zones["has_zones"] is False
    assert "incomplete_note" in zones


def test_metabolic_profile_classifies_mfo_and_flags_high_rer():
    profile = build_metabolic_profile(
        {"fatmax_g_min": 0.53, "fatmax_hr_bpm": 86, "vt1_hr_bpm": 95, "peak_rer": 1.10}
    )
    assert profile["mfo_class"] == "Typical (recreational)"
    assert profile["mfo_g_h"] == 32
    assert "just below" in profile["fatmax_vs_vt1"]
    assert any("not valid" in n for n in profile["interpretation"])  # RER>=1.0 caveat

    low = build_metabolic_profile({"fatmax_g_min": 0.30, "fatmax_hr_bpm": 110, "vt1_hr_bpm": 120})
    assert low["mfo_class"] == "Low"
    assert any("metabolic inflexibility" in n for n in low["interpretation"])


def test_save_cpet_report_persists_json_snapshot(db_conn, test_user, monkeypatch):
    monkeypatch.setattr(cpet_service, "get_connection", db_conn)

    save_cpet_report(
        user_id=test_user,
        test_date="2026-05-20",
        client_context="hybrid",
        source_filename="cpet.pdf",
        test_modality="treadmill",
        protocol="ramp",
        metrics={"peak_vo2_ml_kg_min": 51.0, "peak_rer": 1.13, "vt1_hr_bpm": 145},
        notes="Strong effort",
    )

    reports = get_cpet_reports(test_user)
    assert len(reports) == 1
    assert reports[0]["client_context"] == "hybrid"
    assert reports[0]["metrics"]["peak_vo2_ml_kg_min"] == 51.0
    assert reports[0]["metrics"]["peak_rer"] == 1.13


def test_cpet_report_reader_self_heals_missing_table(db_conn, test_user, monkeypatch):
    monkeypatch.setattr(cpet_service, "get_connection", db_conn)
    conn = db_conn()
    try:
        conn.execute("DROP TABLE IF EXISTS cpet_reports")
        conn.commit()
    finally:
        conn.close()

    assert get_cpet_reports(test_user) == []

    conn = db_conn()
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'cpet_reports'"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
