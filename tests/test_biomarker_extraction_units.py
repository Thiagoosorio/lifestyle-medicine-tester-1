import json
from types import SimpleNamespace

import pytest

import anthropic
import services.biomarker_service as biomarker_service
import services.document_safety_service as document_safety_service


class _FakeMessages:
    def __init__(self, payload):
        self._payload = payload

    def create(self, **_kwargs):
        return SimpleNamespace(
            content=[SimpleNamespace(text=json.dumps(self._payload))]
        )


def test_pdf_extraction_converts_units_and_rejects_incompatible_units(monkeypatch):
    payload = {
        "lab_date": "2026-07-01",
        "lab_name": "Example Lab",
        "results": [
            {"name": "Glucose", "value": 5.5, "unit": "mmol/L"},
            {"name": "Creatinine", "value": 88.4, "unit": "\u00b5mol/L"},
            {"name": "HbA1c", "value": 6.5, "unit": "mg/dL"},
            {"name": "LDL", "value": 190, "unit": "unknown"},
        ],
    }
    definitions = [
        {"id": 1, "code": "fasting_glucose", "name": "Fasting Glucose", "unit": "mg/dL"},
        {"id": 2, "code": "creatinine", "name": "Creatinine", "unit": "mg/dL"},
        {"id": 3, "code": "hba1c", "name": "HbA1c", "unit": "%"},
        {"id": 4, "code": "ldl_cholesterol", "name": "LDL Cholesterol", "unit": "mg/dL"},
    ]

    monkeypatch.setattr(
        document_safety_service,
        "extract_pdf_text_safely",
        lambda _pdf_bytes, label: f"{label}: enough report text for extraction",
    )
    monkeypatch.setattr(document_safety_service, "redact_direct_identifiers", lambda text: text)
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda: SimpleNamespace(messages=_FakeMessages(payload)),
    )

    results, skipped = biomarker_service.extract_biomarkers_from_pdf(
        b"mock PDF", definitions
    )

    assert [row["code"] for row in results] == ["fasting_glucose", "creatinine"]

    glucose = results[0]
    assert glucose["value"] == pytest.approx(99.1001)
    assert glucose["unit"] == "mg/dL"
    assert glucose["source_value"] == 5.5
    assert glucose["source_unit"] == "mmol/L"

    creatinine = results[1]
    assert creatinine["value"] == pytest.approx(1.0)
    assert creatinine["unit"] == "mg/dL"
    assert creatinine["source_value"] == 88.4
    assert creatinine["source_unit"] == "\u00b5mol/L"

    assert {row["name"] for row in skipped} == {"HbA1c", "LDL"}
    assert all(row["reason"] == "incompatible_unit" for row in skipped)
    assert {row["expected_unit"] for row in skipped} == {"%", "mg/dL"}
    assert {(row["source_value"], row["source_unit"]) for row in skipped} == {
        (6.5, "mg/dL"),
        (190.0, "unknown"),
    }


@pytest.mark.parametrize("source_unit", [None, "", "bananas", "mmol/mol"])
def test_unknown_or_incompatible_units_are_not_converted(source_unit):
    assert (
        biomarker_service._convert_extracted_value(
            "fasting_glucose", 5.5, source_unit, "mg/dL"
        )
        is None
    )
