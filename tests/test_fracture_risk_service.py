from models.clinical_profile import save_profile
from services.body_metrics_service import save_dexa_scan
from services.fracture_risk_service import build_frax_workflow_context


def test_build_frax_context_ready_with_femoral_neck_dxa(db_conn, test_user):
    save_profile(
        test_user,
        {
            "date_of_birth": "1970-05-01",
            "sex": "female",
            "height_cm": 165.0,
            "weight_kg": 62.0,
            "smoking_status": "never",
            "prior_fragility_fracture": 1,
            "parent_hip_fracture": 1,
            "corticosteroid_use": 0,
            "rheumatoid_arthritis": 0,
            "alcohol_intake_level": "none",
        },
    )
    save_dexa_scan(
        test_user,
        "2026-04-01",
        scanner_model="Hologic Horizon",
        t_score=-1.7,
        bmd_g_cm2=0.901,
        femoral_neck_bmd_g_cm2=0.741,
        femoral_neck_t_score=-2.2,
    )

    ctx = build_frax_workflow_context(test_user)

    assert ctx["status_label"] == "Ready with femoral-neck DXA"
    assert ctx["bmd_ready"] is True
    assert ctx["missing_core"] == []
    assert ctx["generic_dexa_without_femoral_neck"] is False
    prepared = dict(ctx["prepared_inputs"])
    bone = dict(ctx["bone_inputs"])
    assert prepared["Parent hip fracture"] == "Yes"
    assert bone["Femoral-neck T-score"] == "-2.20"
    assert bone["Scanner"] == "Hologic Horizon"


def test_build_frax_context_flags_missing_core_and_secondary_osteoporosis(db_conn, test_user):
    save_profile(
        test_user,
        {
            "date_of_birth": "1995-01-10",
            "sex": "male",
            "diabetes_type": "type1",
            "malabsorption": 1,
            "smoking_status": None,
        },
    )
    save_dexa_scan(
        test_user,
        "2026-04-02",
        t_score=-2.4,
        bmd_g_cm2=0.812,
    )

    ctx = build_frax_workflow_context(test_user)

    assert ctx["status_label"] == "Missing core inputs"
    assert "Height and Weight" in ctx["missing_core"]
    assert ctx["generic_dexa_without_femoral_neck"] is True
    assert ctx["secondary_osteoporosis"] is True
    assert "Type 1 diabetes" in ctx["secondary_reasons"]
    assert "Malabsorption" in ctx["secondary_reasons"]
