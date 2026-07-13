"""AI quality-control review of CPET plot images (threshold-placement sanity check).

Cortex MetaSoft (and every other cart) auto-detects VT1/VT2 from the gas-exchange
curves, and the auto-placement is sometimes visibly wrong even when the numbers
look plausible. This service sends the plot images (V-slope, ventilatory
equivalents, 9-panel, PETCO2/PETO2) to a vision-capable Claude model and asks it
to check whether the marked thresholds line up with the standard visual criteria:

    VT1 / GET  — V-slope (VCO2 vs VO2) breakpoint from slope <1 to >1; the VE/VO2
                 nadir where VE/VO2 starts to rise while VE/VCO2 is still flat;
                 PETO2 begins to rise while PETCO2 is stable.
    VT2 / RCP  — VE/VCO2 starts to rise; PETCO2 begins to fall.

It is decision-support for a coach, not a diagnosis: threshold reading is
reader-dependent, and the supervising clinician makes the final call.
"""

from __future__ import annotations

import base64
import io
import os
from typing import Any

# Model used for the vision review. Overridable via env so the deployment can
# pin a cheaper/faster model without a code change.
DEFAULT_VISION_MODEL = "claude-opus-4-8"
MAX_IMAGE_EDGE_PX = 1600
MAX_IMAGES = 8

_QC_TOOL = {
    "name": "report_threshold_qc",
    "description": "Report the structured quality-control assessment of the CPET threshold placement.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "overall_assessment": {
                "type": "string",
                "enum": [
                    "thresholds_look_consistent",
                    "vt1_possibly_misplaced",
                    "vt2_possibly_misplaced",
                    "both_possibly_misplaced",
                    "insufficient_image_quality",
                ],
            },
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "vt1": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "verdict": {"type": "string", "enum": ["consistent", "possibly_early", "possibly_late", "cannot_assess"]},
                    "criteria_checked": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"},
                },
                "required": ["verdict", "criteria_checked", "rationale"],
            },
            "vt2": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "verdict": {"type": "string", "enum": ["consistent", "possibly_early", "possibly_late", "cannot_assess"]},
                    "criteria_checked": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"},
                },
                "required": ["verdict", "criteria_checked", "rationale"],
            },
            "plots_legible": {"type": "array", "items": {"type": "string"}, "description": "Which panels were clear enough to use (e.g. 'V-slope', 'ventilatory equivalents')."},
            "coach_summary": {"type": "string", "description": "2-4 plain-language sentences for the coach."},
            "clinician_flags": {"type": "array", "items": {"type": "string"}, "description": "Anything to escalate to the supervising clinician."},
        },
        "required": ["overall_assessment", "confidence", "vt1", "vt2", "plots_legible", "coach_summary", "clinician_flags"],
    },
}


class VisionUnavailableError(RuntimeError):
    """Raised when the environment cannot run the vision review."""


def vision_model() -> str:
    return os.getenv("CPET_VISION_MODEL", DEFAULT_VISION_MODEL)


def _anthropic_client():
    """Return an Anthropic client or raise VisionUnavailableError with a reason."""
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider != "anthropic":
        raise VisionUnavailableError(
            f"AI reading currently supports the Anthropic provider only (LLM_PROVIDER={provider})."
        )
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        raise VisionUnavailableError(
            "No Anthropic API key configured (set ANTHROPIC_API_KEY). AI reading is unavailable."
        )
    try:
        import anthropic
    except Exception as exc:  # pragma: no cover
        raise VisionUnavailableError("The anthropic SDK is not installed.") from exc
    return anthropic.Anthropic()


# Numeric CPET fields the extractor may fill; kept in sync with cpet_service specs.
_EXTRACT_NUMERIC_FIELDS = [
    "age_years", "weight_kg", "height_cm", "test_duration_min", "averaging_window_sec",
    "rest_vo2_ml_kg_min", "rest_rer", "rest_ve_l_min",
    "peak_vo2_ml_kg_min", "peak_vo2_l_min", "peak_vo2_pct_pred", "peak_power_w",
    "peak_rer", "rest_hr_bpm", "peak_hr_bpm", "hr_recovery_1min_bpm", "predicted_hr_bpm", "hr_pct_pred",
    "vt1_vo2_ml_kg_min", "vt1_hr_bpm", "vt1_power_w",
    "vt2_vo2_ml_kg_min", "vt2_hr_bpm", "vt2_power_w",
    "ve_vco2_slope", "ve_vco2_nadir", "breathing_reserve_pct", "peak_ve_l_min", "peak_rr_bpm",
    "mvv_l_min", "o2_pulse_ml_beat", "o2_pulse_pct_pred",
    "o2_pulse_50_pct_ml_beat", "o2_pulse_75_pct_ml_beat", "petco2_at_mmhg",
    "spo2_nadir_pct", "peak_lactate_mmol_l", "fatmax_hr_bpm",
]


def _extract_tool() -> dict[str, Any]:
    props: dict[str, Any] = {
        field: {"type": ["number", "null"]} for field in _EXTRACT_NUMERIC_FIELDS
    }
    props["sex"] = {"type": ["string", "null"], "enum": ["male", "female", None]}
    props["test_date"] = {"type": ["string", "null"], "description": "YYYY-MM-DD if shown."}
    props["test_modality"] = {"type": ["string", "null"], "description": "e.g. cycle ergometer, treadmill, rowing."}
    props["protocol"] = {"type": ["string", "null"]}
    return {
        "name": "extract_cpet_values",
        "description": "Report the CPET values read from the report. Use null for anything not clearly shown; never guess.",
        "input_schema": {"type": "object", "additionalProperties": False, "properties": props},
    }


_EXTRACT_SYSTEM = (
    "You transcribe values from a cardiopulmonary exercise test (CPET) report image into structured "
    "fields. Read only what is printed; if a value is not clearly legible, return null for it — do not "
    "estimate or infer. Report the PEAK / maximum column for peak_* fields, the VT1 (first threshold / "
    "GET / AT) column for vt1_* fields, and the VT2 (second threshold / RCP) column for vt2_* fields. "
    "Cortex reports print oxygen uptake as V'O2 (an apostrophe stands for the dot); V'O2/kg is "
    "peak_vo2_ml_kg_min, V'O2/HR is o2_pulse_ml_beat, V'E is minute ventilation. Report via the "
    "extract_cpet_values tool."
)


def extract_cpet_from_pdf_via_vision(pdf_bytes: bytes, model: str | None = None) -> dict[str, Any]:
    """Extract CPET values from a (possibly image-only) PDF using Claude.

    Sends the PDF as a document so Claude can read image-based reports that have no
    text layer. Returns the same shape as ``extract_cpet_from_text`` with metrics
    passed through ``normalize_cpet_metrics``. Raises VisionUnavailableError when
    the provider/key is missing; other API errors propagate.
    """
    from services.document_safety_service import validate_pdf_upload

    validate_pdf_upload(pdf_bytes, label="CPET report PDF")
    client = _anthropic_client()
    content = [
        {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": base64.standard_b64encode(pdf_bytes).decode("ascii")},
        },
        {"type": "text", "text": "Transcribe this CPET report into the extract_cpet_values tool. Use null for anything not clearly printed."},
    ]
    response = client.messages.create(
        model=model or vision_model(),
        max_tokens=1500,
        system=_EXTRACT_SYSTEM,
        tools=[_extract_tool()],
        tool_choice={"type": "tool", "name": "extract_cpet_values"},
        messages=[{"role": "user", "content": content}],
    )
    raw = None
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "extract_cpet_values":
            raw = dict(block.input)
            break
    if raw is None:
        raise VisionUnavailableError("The model did not return structured CPET values; try again.")

    metrics: dict[str, Any] = {}
    for field in _EXTRACT_NUMERIC_FIELDS:
        value = raw.get(field)
        if isinstance(value, (int, float)):
            metrics[field] = float(value)
    sex = raw.get("sex")
    if sex in ("male", "female"):
        metrics["sex"] = sex

    from services.cpet_service import normalize_cpet_metrics  # lazy: avoids import cycle
    metrics = normalize_cpet_metrics(metrics)

    return {
        "test_date": raw.get("test_date") or None,
        "test_modality": raw.get("test_modality") or None,
        "protocol": raw.get("protocol") or None,
        "source_format": "vision_pdf",
        "metrics": metrics,
        "model": response.model,
        "extraction_warnings": [
            "Values were read from the PDF by AI (the PDF had no text layer). Verify every value below before saving.",
        ] if metrics else [
            "AI could not read CPET values from this PDF. Enter them manually below.",
        ],
    }


def render_pdf_pages_to_images(pdf_bytes: bytes, max_pages: int = 12) -> list[dict[str, Any]]:
    """Render each PDF page to a PNG using PyMuPDF, if it is installed.

    Returns a list of {"page": int (1-based), "png": bytes}. Raises
    VisionUnavailableError when PyMuPDF is not available so the caller can fall
    back to asking the coach to upload plot screenshots.
    """
    from services.document_safety_service import validate_pdf_upload

    validate_pdf_upload(pdf_bytes, label="CPET plot PDF", max_pages=max_pages)
    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # pragma: no cover - environment dependent
        raise VisionUnavailableError(
            "PDF page rendering needs PyMuPDF (pymupdf). Install it, or upload the plot "
            "images (screenshots of the V-slope / ventilatory-equivalents / 9-panel plots) directly."
        ) from exc

    out: list[dict[str, Any]] = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for index, page in enumerate(doc):
            if index >= max_pages:
                break
            pix = page.get_pixmap(dpi=140)
            out.append({"page": index + 1, "png": pix.tobytes("png")})
    finally:
        doc.close()
    return out


def _prepare_image(image_bytes: bytes) -> str:
    """Downscale/normalise an image and return base64 PNG for the API."""
    from services.document_safety_service import MAX_IMAGE_BYTES, validate_upload_bytes

    image_bytes = validate_upload_bytes(
        image_bytes,
        label="CPET plot image",
        max_bytes=MAX_IMAGE_BYTES,
    )
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise VisionUnavailableError("Image handling needs Pillow (PIL).") from exc

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    longest = max(img.size)
    if longest > MAX_IMAGE_EDGE_PX:
        scale = MAX_IMAGE_EDGE_PX / longest
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.standard_b64encode(buffer.getvalue()).decode("ascii")


def _context_text(context: dict[str, Any] | None) -> str:
    context = context or {}
    def fmt(key: str, label: str, unit: str = "") -> str | None:
        value = context.get(key)
        if value is None or value == "":
            return None
        return f"{label}: {value}{unit}"

    lines = [
        fmt("vt1_vo2_ml_kg_min", "Software VT1 VO2", " mL/kg/min"),
        fmt("vt1_hr_bpm", "Software VT1 HR", " bpm"),
        fmt("vt1_power_w", "Software VT1 power", " W"),
        fmt("vt1_pct_peak_vo2", "Software VT1 as % of peak VO2", "%"),
        fmt("vt2_vo2_ml_kg_min", "Software VT2 VO2", " mL/kg/min"),
        fmt("vt2_hr_bpm", "Software VT2 HR", " bpm"),
        fmt("vt2_power_w", "Software VT2 power", " W"),
        fmt("vt2_pct_peak_vo2", "Software VT2 as % of peak VO2", "%"),
        fmt("peak_vo2_ml_kg_min", "Peak VO2", " mL/kg/min"),
        fmt("ve_vco2_slope", "VE/VCO2 slope", ""),
        fmt("peak_rer", "Peak RER", ""),
    ]
    known = "\n".join(f"- {line}" for line in lines if line)
    return known or "- (no numeric threshold values were provided)"


_SYSTEM_PROMPT = (
    "You are assisting a lifestyle-medicine coach with a QUALITY-CONTROL check of a "
    "cardiopulmonary exercise test (CPET). CPET carts (e.g. Cortex MetaSoft) auto-detect "
    "the ventilatory thresholds VT1 (GET/aerobic threshold) and VT2 (RCP/second threshold) "
    "from the gas-exchange curves, and the auto-placement is sometimes visibly wrong.\n\n"
    "You are given plot images and the software's reported threshold values. Judge ONLY from "
    "what is clearly legible in the images. For each threshold, check the standard visual criteria "
    "and say whether the marked line (usually a vertical line) sits where those criteria put it:\n"
    "- VT1/GET: the V-slope (VCO2 vs VO2) breakpoint where the slope changes from <1 to >1; the "
    "VE/VO2 nadir where VE/VO2 starts to rise while VE/VCO2 is still flat or falling; PETO2 starts "
    "to rise while PETCO2 stays stable.\n"
    "- VT2/RCP: VE/VCO2 starts to rise (its nadir); PETCO2 starts to fall; the second V-slope break.\n\n"
    "If the marked line looks earlier than the criteria suggest, that is 'possibly_early'; later is "
    "'possibly_late'. If a panel is unreadable or the marker is not visible, use 'cannot_assess' and "
    "say so — never guess. This is coach decision-support, not a diagnosis: threshold reading is "
    "reader-dependent and the supervising clinician makes the final call. Report via the "
    "report_threshold_qc tool."
)


def analyze_cpet_plots(
    images: list[bytes],
    context: dict[str, Any] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Run the vision QC review over the supplied plot images.

    Raises VisionUnavailableError when no API key / provider is configured, and
    lets anthropic API errors propagate for the caller to surface.
    """
    if not images:
        raise VisionUnavailableError("No plot images were provided.")
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider != "anthropic":
        raise VisionUnavailableError(
            f"CPET plot QC currently supports the Anthropic provider only (LLM_PROVIDER={provider})."
        )
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        raise VisionUnavailableError(
            "No Anthropic API key configured (set ANTHROPIC_API_KEY). Plot QC is unavailable."
        )

    try:
        import anthropic
    except Exception as exc:  # pragma: no cover
        raise VisionUnavailableError("The anthropic SDK is not installed.") from exc

    content: list[dict[str, Any]] = []
    for image_bytes in images[:MAX_IMAGES]:
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": _prepare_image(image_bytes)},
            }
        )
    content.append(
        {
            "type": "text",
            "text": (
                "Software-reported values for this test:\n"
                + _context_text(context)
                + "\n\nReview the images above and report the threshold-placement QC via the tool."
            ),
        }
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model or vision_model(),
        max_tokens=1500,
        system=_SYSTEM_PROMPT,
        tools=[_QC_TOOL],
        tool_choice={"type": "tool", "name": "report_threshold_qc"},
        messages=[{"role": "user", "content": content}],
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "report_threshold_qc":
            result = dict(block.input)
            result["model"] = response.model
            result["image_count"] = len(content) - 1
            return result
    raise VisionUnavailableError("The model did not return a structured QC result; try again.")
