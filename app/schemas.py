from typing import Any

from pydantic import BaseModel, Field


SUPPORTED_TYPES = frozenset({"aadhaar", "pan", "voter_id", "driving_licence", "passport"})


class ProcessErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    supported_types: list[str] = Field(
        default_factory=lambda: sorted(SUPPORTED_TYPES),
    )


class FieldConfidence(BaseModel):
    """Per-field confidence 0..1 from the vision model."""

    values: dict[str, float] = Field(default_factory=dict)


class ProcessSuccessResponse(BaseModel):
    document_type: str
    confidence: float
    fields: dict[str, Any]
    field_confidence: dict[str, float] = Field(default_factory=dict)
    masked: bool
    extraction_warnings: list[str] = Field(default_factory=list)
