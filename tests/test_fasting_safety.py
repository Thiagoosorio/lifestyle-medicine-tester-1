import pytest

from config.fasting_data import FASTING_SAFETY, FASTING_ZONES
import services.fasting_service as fasting_service


SAFE_SCREEN = {
    "acknowledged": True,
    "contraindications": [],
    "glucose_lowering_medication": False,
    "clinician_reviewed": False,
}


@pytest.mark.parametrize(
    ("target_hours", "screen", "expected_code"),
    [
        (16, None, "acknowledgement_required"),
        (
            16,
            {**SAFE_SCREEN, "contraindications": ["Pregnancy or breastfeeding"]},
            "contraindication",
        ),
        (
            16,
            {**SAFE_SCREEN, "glucose_lowering_medication": True},
            "clinician_review_required",
        ),
        (36, SAFE_SCREEN, "clinician_review_required"),
    ],
)
def test_start_fast_rejects_unsafe_screen_before_database_access(
    monkeypatch, target_hours, screen, expected_code
):
    def unexpected_connection():
        raise AssertionError("safety failure must occur before database access")

    monkeypatch.setattr(fasting_service, "get_connection", unexpected_connection)

    with pytest.raises(fasting_service.FastingSafetyError) as exc_info:
        fasting_service.start_fast(
            1, "16:8", target_hours=target_hours, safety_screen=screen
        )

    assert exc_info.value.code == expected_code


def test_start_fast_persists_after_required_acknowledgements(
    db_conn, test_user, monkeypatch
):
    monkeypatch.setattr(fasting_service, "get_connection", db_conn)
    reviewed_screen = {**SAFE_SCREEN, "clinician_reviewed": True}

    session_id = fasting_service.start_fast(
        test_user, "36h", safety_screen=reviewed_screen
    )

    conn = db_conn()
    row = conn.execute(
        "SELECT target_hours, fasting_type FROM fasting_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    conn.close()
    assert row["target_hours"] == 36
    assert row["fasting_type"] == "36h"


def test_fasting_phase_copy_is_explicitly_approximate_and_unmeasured():
    notice = FASTING_SAFETY["phase_notice"].lower()
    assert "approximate" in notice
    assert "does not measure" in notice

    extended = next(zone for zone in FASTING_ZONES if zone["id"] == "deep_ketosis")
    copy = " ".join(
        [extended["name"], extended["description"], extended["mechanism"]]
    ).lower()
    assert "does not establish" in copy
    assert "autophagy" in copy
    assert "autophagy" not in extended["name"].lower()
