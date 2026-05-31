import services.cpet_service as cpet_service
from services.cpet_service import (
    build_cpet_coach_summary,
    build_zone_rows,
    extract_cpet_from_text,
    get_cpet_reports,
    normalize_cpet_metrics,
    save_cpet_report,
)


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


def test_build_zone_rows_uses_measured_threshold_anchors():
    rows = build_zone_rows(
        {
            "vt1_hr_bpm": 140,
            "vt2_hr_bpm": 168,
            "vt1_power_w": 190,
            "vt2_power_w": 265,
        }
    )

    anchors = {row["Anchor"] for row in rows}
    assert {"HR", "Power"}.issubset(anchors)
    assert any(row["Zone 2 / heavy"] == "140-168 bpm" for row in rows)
    assert any(row["Zone 3 / severe"] == "> 265 W" for row in rows)


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
