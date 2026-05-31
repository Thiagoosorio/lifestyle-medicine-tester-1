import services.inbody_service as inbody_service
from services.inbody_service import (
    build_inbody_coach_summary,
    extract_inbody_from_text,
    normalize_inbody_metrics,
    save_inbody_report,
    get_inbody_reports,
)


SAMPLE_TEXT = """
InBody 770 Result Sheet
Test Date 2026-05-20
Height 176.0 cm
Weight 82.4 kg
Total Body Water 46.2 L
Intracellular Water 29.8 L
Extracellular Water 16.4 L
ECW/TBW 0.392
Skeletal Muscle Mass 34.1 kg
Body Fat Mass 18.2 kg
Percent Body Fat 22.1 %
Basal Metabolic Rate 1710 kcal
Visceral Fat Area 104 cm2
Phase Angle 6.2
InBody Score 78
"""


def test_extract_inbody_from_text_finds_core_metrics():
    extracted = extract_inbody_from_text(SAMPLE_TEXT)

    assert extracted["scan_date"] == "2026-05-20"
    assert extracted["device_model"] == "InBody 770"
    metrics = extracted["metrics"]
    assert metrics["weight_kg"] == 82.4
    assert metrics["total_body_water_l"] == 46.2
    assert metrics["intracellular_water_l"] == 29.8
    assert metrics["extracellular_water_l"] == 16.4
    assert metrics["ecw_tbw_ratio"] == 0.392
    assert metrics["phase_angle_deg"] == 6.2
    assert metrics["skeletal_muscle_mass_kg"] == 34.1
    assert metrics["body_fat_pct"] == 22.1
    assert metrics["visceral_fat_area_cm2"] == 104.0


def test_normalize_inbody_metrics_derives_ecw_ratio_and_bmi():
    metrics = normalize_inbody_metrics(
        {
            "height_cm": 180,
            "weight_kg": 81,
            "intracellular_water_l": 30,
            "extracellular_water_l": 15,
        }
    )

    assert metrics["total_body_water_l"] == 45.0
    assert metrics["ecw_tbw_ratio"] == 0.333
    assert metrics["bmi"] == 25.0


def test_coach_summary_flags_high_value_inbody_signals():
    summary = build_inbody_coach_summary(
        {
            "ecw_tbw_ratio": 0.401,
            "phase_angle_deg": 4.8,
            "body_fat_pct": 31.0,
            "inbody_score": 72,
            "segmental_ecw_ratio": {"right_leg": 0.402, "left_leg": 0.381},
        }
    )

    areas = {row["Area"] for row in summary["coach_flags"]}
    assert "Fluid balance" in areas
    assert "Segmental ECW" in areas
    assert "Cell health trend" in areas
    assert "InBody score" in areas
    assert any(row["Tier"] == "Tier 1" for row in summary["trust_rows"])


def test_save_inbody_report_persists_and_syncs_body_metrics(db_conn, test_user, monkeypatch):
    monkeypatch.setattr(inbody_service, "get_connection", db_conn)

    save_inbody_report(
        user_id=test_user,
        scan_date="2026-05-20",
        source_filename="sample.pdf",
        device_model="InBody 770",
        metrics={"weight_kg": 82.4, "height_cm": 176, "body_fat_pct": 22.1},
        notes="Morning fasted scan",
    )

    reports = get_inbody_reports(test_user)
    assert len(reports) == 1
    assert reports[0]["metrics"]["weight_kg"] == 82.4

    conn = db_conn()
    try:
        row = conn.execute(
            "SELECT weight_kg, height_cm, body_fat_pct, notes FROM body_metrics WHERE user_id = ?",
            (test_user,),
        ).fetchone()
    finally:
        conn.close()

    assert row["weight_kg"] == 82.4
    assert row["height_cm"] == 176
    assert row["body_fat_pct"] == 22.1
    assert "InBody" in row["notes"]
