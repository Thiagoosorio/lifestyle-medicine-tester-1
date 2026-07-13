import config.biomarkers_data as biomarker_data
import services.biomarker_service as biomarker_service


def _definition(**overrides):
    definition = {
        "code": "seed_regression_marker",
        "name": "Stale Marker Name",
        "category": "metabolic",
        "unit": "stale-unit",
        "standard_low": 1.0,
        "standard_high": 2.0,
        "optimal_low": 1.2,
        "optimal_high": 1.8,
        "critical_low": 0.5,
        "critical_high": 2.5,
        "description": "Stale description",
        "clinical_note": "Stale evidence note",
        "pillar_id": None,
        "sort_order": 90,
    }
    definition.update(overrides)
    return definition


def test_reseed_updates_metadata_without_replacing_linked_definition(
    db_conn, test_user, monkeypatch
):
    monkeypatch.setattr(biomarker_service, "get_connection", db_conn)
    monkeypatch.setattr(
        biomarker_data, "BIOMARKER_DEFINITIONS", [_definition()]
    )
    biomarker_service.seed_biomarker_definitions()

    conn = db_conn()
    original_definition_id = conn.execute(
        "SELECT id FROM biomarker_definitions WHERE code = ?",
        ("seed_regression_marker",),
    ).fetchone()["id"]
    result_id = conn.execute(
        """INSERT INTO biomarker_results
           (user_id, biomarker_id, value, lab_date, lab_name)
           VALUES (?, ?, ?, ?, ?)""",
        (test_user, original_definition_id, 7.5, "2026-07-13", "Regression Lab"),
    ).lastrowid
    conn.commit()
    conn.close()

    corrected = _definition(
        name="Corrected Marker Name",
        category="lipids",
        unit="corrected-unit",
        standard_low=5.0,
        standard_high=10.0,
        optimal_low=6.0,
        optimal_high=8.0,
        critical_low=3.0,
        critical_high=12.0,
        description="Corrected description",
        clinical_note="Corrected evidence note",
        sort_order=4,
    )
    monkeypatch.setattr(
        biomarker_data, "BIOMARKER_DEFINITIONS", [corrected]
    )

    biomarker_service.seed_biomarker_definitions()

    conn = db_conn()
    stored = dict(
        conn.execute(
            "SELECT * FROM biomarker_definitions WHERE code = ?",
            (corrected["code"],),
        ).fetchone()
    )
    linked_result = conn.execute(
        """SELECT br.id AS result_id, br.biomarker_id, br.value,
                  bd.id AS definition_id, bd.unit
           FROM biomarker_results br
           JOIN biomarker_definitions bd ON bd.id = br.biomarker_id
           WHERE br.id = ?""",
        (result_id,),
    ).fetchone()
    foreign_key_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()

    assert stored["id"] == original_definition_id
    for field in (
        "name",
        "category",
        "unit",
        "standard_low",
        "standard_high",
        "optimal_low",
        "optimal_high",
        "critical_low",
        "critical_high",
        "description",
        "clinical_note",
        "pillar_id",
        "sort_order",
    ):
        assert stored[field] == corrected[field]

    assert linked_result["result_id"] == result_id
    assert linked_result["biomarker_id"] == original_definition_id
    assert linked_result["definition_id"] == original_definition_id
    assert linked_result["value"] == 7.5
    assert linked_result["unit"] == corrected["unit"]
    assert foreign_key_violations == []
