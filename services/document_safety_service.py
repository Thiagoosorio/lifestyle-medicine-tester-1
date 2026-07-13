"""Shared validation for health-document and image uploads."""

from __future__ import annotations

import io
import re


MAX_DOCUMENT_BYTES = 15 * 1024 * 1024
MAX_PDF_PAGES = 40
MAX_EXTRACTED_TEXT_CHARS = 120_000
MAX_TEXT_UPLOAD_BYTES = 1 * 1024 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_BATCH_FILES = 10
MAX_BATCH_BYTES = 50 * 1024 * 1024


class DocumentValidationError(ValueError):
    """Raised when an upload is unsafe or too large to process."""


def validate_upload_bytes(
    payload: bytes,
    *,
    label: str = "File",
    max_bytes: int = MAX_DOCUMENT_BYTES,
) -> bytes:
    if not isinstance(payload, (bytes, bytearray)):
        raise DocumentValidationError(f"{label} could not be read.")
    data = bytes(payload)
    if not data:
        raise DocumentValidationError(f"{label} is empty.")
    if len(data) > max_bytes:
        limit_mb = max_bytes / (1024 * 1024)
        raise DocumentValidationError(
            f"{label} is too large. Maximum allowed size is {limit_mb:g} MB."
        )
    return data


def validate_text_upload(payload: bytes, *, label: str = "Text file") -> str:
    data = validate_upload_bytes(payload, label=label, max_bytes=MAX_TEXT_UPLOAD_BYTES)
    text = data.decode("utf-8", errors="ignore").strip()
    if not text:
        raise DocumentValidationError(f"{label} contains no readable text.")
    if len(text) > MAX_EXTRACTED_TEXT_CHARS:
        raise DocumentValidationError(
            f"{label} contains too much text. Maximum is {MAX_EXTRACTED_TEXT_CHARS:,} characters."
        )
    return text


_IDENTIFIER_LINE = re.compile(
    r"(?im)^\s*(?:patient(?:\s+(?:name|id|no\.?|number))?|name|dob|date\s+of\s+birth|"
    r"birth\s+date|mrn|medical\s+record(?:\s+number)?|national\s+id|passport|address|"
    r"phone|telephone|mobile|email)\s*[:#-].*$"
)
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_CANDIDATE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)")


def redact_direct_identifiers(text: str) -> str:
    """Remove common direct identifiers before report text leaves the app."""
    redacted = _IDENTIFIER_LINE.sub("[DIRECT IDENTIFIER REDACTED]", text)
    redacted = _EMAIL.sub("[EMAIL REDACTED]", redacted)

    def _redact_phone(match: re.Match) -> str:
        candidate = match.group(0)
        return "[PHONE REDACTED]" if sum(ch.isdigit() for ch in candidate) >= 9 else candidate

    return _PHONE_CANDIDATE.sub(_redact_phone, redacted)


def _open_pdf(pdf_bytes: bytes, *, label: str, max_pages: int):
    data = validate_upload_bytes(pdf_bytes, label=label)
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise DocumentValidationError(
                f"{label} is password-protected. Upload an unlocked copy."
            )
        page_count = len(reader.pages)
    except DocumentValidationError:
        raise
    except Exception as exc:
        raise DocumentValidationError(f"Could not read {label.lower()} as a PDF.") from exc

    if page_count == 0:
        raise DocumentValidationError(f"{label} has no pages.")
    if page_count > max_pages:
        raise DocumentValidationError(
            f"{label} has {page_count} pages. Maximum allowed is {max_pages}."
        )
    return reader


def validate_pdf_upload(
    pdf_bytes: bytes,
    *,
    label: str = "PDF",
    max_pages: int = MAX_PDF_PAGES,
) -> int:
    """Validate PDF size, structure, encryption, and page count."""
    return len(_open_pdf(pdf_bytes, label=label, max_pages=max_pages).pages)


def extract_pdf_text_safely(
    pdf_bytes: bytes,
    *,
    label: str = "PDF",
    max_pages: int = MAX_PDF_PAGES,
    max_chars: int = MAX_EXTRACTED_TEXT_CHARS,
    min_chars: int = 20,
) -> str:
    """Extract bounded text from a validated digital PDF."""
    reader = _open_pdf(pdf_bytes, label=label, max_pages=max_pages)
    pages_text: list[str] = []
    total_chars = 0
    try:
        for page in reader.pages:
            page_text = page.extract_text() or ""
            total_chars += len(page_text)
            if total_chars > max_chars:
                raise DocumentValidationError(
                    f"{label} contains too much text. Maximum is {max_chars:,} characters."
                )
            pages_text.append(page_text)
    except DocumentValidationError:
        raise
    except Exception as exc:
        raise DocumentValidationError(f"Could not extract text from {label.lower()}.") from exc

    text = "\n".join(pages_text).strip()
    if len(text) < min_chars:
        raise DocumentValidationError(
            f"{label} has no readable text. It may be a scanned image."
        )
    return text
