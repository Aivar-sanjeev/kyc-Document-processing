import logging
import statistics
from typing import Any

from app.logging_safe import safe_log_dict
from app.pipeline.mask import finalize_aadhaar_output_fields
from app.pipeline.nim_client import call_vision_llm
from app.pipeline.validate import run_validators
from app.schemas import SUPPORTED_TYPES, ProcessSuccessResponse
from app.settings import Settings

logger = logging.getLogger(__name__)


class UnsupportedDocumentError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _aggregate_confidence(raw: dict[str, Any]) -> float:
    doc_c = float(raw.get("confidence") or 0.0)
    fc = raw.get("field_confidence") or {}
    if isinstance(fc, dict) and fc:
        vals = [float(v) for v in fc.values() if isinstance(v, (int, float))]
        if vals:
            return max(0.0, min(1.0, statistics.mean([doc_c, statistics.fmean(vals)])))
    return max(0.0, min(1.0, doc_c))


def _normalize_field_confidence(raw: dict[str, Any]) -> dict[str, float]:
    fc = raw.get("field_confidence") or {}
    if not isinstance(fc, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in fc.items():
        try:
            out[str(k)] = max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            continue
    return out


def _normalize_warnings(raw: dict[str, Any]) -> list[str]:
    w = raw.get("extraction_warnings") or []
    if isinstance(w, list):
        return [str(x) for x in w]
    return []


async def process_document_bytes(
    settings: Settings,
    *,
    file_bytes: bytes,
    filename: str | None,
) -> ProcessSuccessResponse:
    from app.pipeline.document_loader import bytes_to_png_and_media_type

    image_bytes, media_type = bytes_to_png_and_media_type(file_bytes, filename)

    raw = await call_vision_llm(settings, image_png_or_jpeg=image_bytes, media_type=media_type)

    doc_type = str(raw.get("document_type") or "").strip().lower().replace(" ", "_")
    if doc_type in {"driving_license", "dl"}:
        doc_type = "driving_licence"
    if doc_type == "voterid":
        doc_type = "voter_id"

    if doc_type == "unsupported" or doc_type not in SUPPORTED_TYPES:
        raise UnsupportedDocumentError(
            "Document type not supported or could not be classified confidently.",
        )

    fields = raw.get("fields") or {}
    if not isinstance(fields, dict):
        fields = {}

    safe_log_dict(
        logger,
        logging.INFO,
        "vision_extracted",
        {
            "document_type": doc_type,
            "field_keys": list(fields.keys()),
            "warnings_count": len(_normalize_warnings(raw)),
        },
    )

    fc = _normalize_field_confidence(raw)
    extraction_warnings = _normalize_warnings(raw)
    confidence = _aggregate_confidence(raw)

    fields_out: dict[str, Any] = dict(fields)
    masked_flag = False

    if doc_type == "aadhaar":
        fields_out, masked_flag = finalize_aadhaar_output_fields(fields_out)

    val_warnings, _ = run_validators(doc_type, fields_out)
    all_warnings = list(dict.fromkeys(extraction_warnings + val_warnings))

    if val_warnings:
        confidence = max(0.0, confidence - 0.05 * len(val_warnings))

    return ProcessSuccessResponse(
        document_type=doc_type,
        confidence=round(confidence, 4),
        fields=fields_out,
        field_confidence=fc,
        masked=masked_flag,
        extraction_warnings=all_warnings,
    )
