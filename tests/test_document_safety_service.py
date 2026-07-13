import io

import pytest
from pypdf import PdfWriter

from services.document_safety_service import (
    DocumentValidationError,
    extract_pdf_text_safely,
    redact_direct_identifiers,
    validate_pdf_upload,
    validate_text_upload,
    validate_upload_bytes,
)


def _blank_pdf(page_count: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_validate_upload_rejects_empty_and_oversized_payloads():
    with pytest.raises(DocumentValidationError, match="empty"):
        validate_upload_bytes(b"", label="Report")
    with pytest.raises(DocumentValidationError, match="Maximum allowed size"):
        validate_upload_bytes(b"1234", label="Report", max_bytes=3)


def test_validate_pdf_rejects_excess_pages():
    with pytest.raises(DocumentValidationError, match="3 pages"):
        validate_pdf_upload(_blank_pdf(3), max_pages=2)


def test_extract_pdf_text_rejects_image_only_pdf():
    with pytest.raises(DocumentValidationError, match="no readable text"):
        extract_pdf_text_safely(_blank_pdf(), label="Test PDF")


def test_validate_text_upload_decodes_and_rejects_blank_text():
    assert validate_text_upload(b"  CPET report  ") == "CPET report"
    with pytest.raises(DocumentValidationError, match="no readable text"):
        validate_text_upload(b"   ")


def test_redact_direct_identifiers_preserves_clinical_values():
    source = (
        "Patient Name: Jane Example\n"
        "DOB: 1970-02-03\n"
        "Email: jane@example.com\n"
        "Phone: +1 212 555 0199\n"
        "Collection date: 2026-07-10\n"
        "Hemoglobin 13.4 g/dL"
    )
    redacted = redact_direct_identifiers(source)
    assert "Jane Example" not in redacted
    assert "jane@example.com" not in redacted
    assert "555 0199" not in redacted
    assert "Collection date: 2026-07-10" in redacted
    assert "Hemoglobin 13.4 g/dL" in redacted
