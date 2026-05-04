"""
End-to-end pipeline checks with a stub vision model (no external API).
Demonstrates multiple document types and masking rules.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.pipeline.process import UnsupportedDocumentError, process_document_bytes
from app.pipeline.mrz import build_td3_second_line
from app.settings import Settings


def _mrz_line2() -> str:
    return build_td3_second_line(
        doc9="Z1234567",
        nationality="IND",
        dob_yymmdd="900412",
        sex="F",
        expiry_yymmdd="350401",
    )


@pytest.mark.asyncio
async def test_pipeline_aadhaar_masks(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_vision(*_a, **_k):
        return {
            "document_type": "aadhaar",
            "confidence": 0.95,
            "field_confidence": {"name": 0.94, "aadhaar_number": 0.9},
            "fields": {
                "name": "Priya Sharma",
                "dob": "1990-04-12",
                "gender": "F",
                "address": "Demo address",
                "aadhaar_number": "1234 5678 9012",
            },
            "extraction_warnings": [],
        }

    monkeypatch.setattr("app.pipeline.process.call_vision_llm", fake_vision)
    settings = Settings(use_mock_vision=True)
    res = await process_document_bytes(settings, file_bytes=b"\x89PNG\r\n\x1a\n", filename="x.png")
    assert res.document_type == "aadhaar"
    assert res.masked is True
    assert res.fields.get("aadhaar_number") == "XXXX XXXX 9012"
    assert "123456789012" not in str(res.model_dump())


@pytest.mark.asyncio
async def test_pipeline_pan_validation_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_vision(*_a, **_k):
        return {
            "document_type": "pan",
            "confidence": 0.9,
            "field_confidence": {"pan_number": 0.6},
            "fields": {"name": "X", "pan_number": "BADPAN"},
            "extraction_warnings": ["low_scan_quality"],
        }

    monkeypatch.setattr("app.pipeline.process.call_vision_llm", fake_vision)
    settings = Settings(use_mock_vision=True)
    res = await process_document_bytes(settings, file_bytes=b"x", filename="pan.png")
    assert "pan_format_invalid" in res.extraction_warnings or "pan_validation_failed" in res.extraction_warnings


@pytest.mark.asyncio
async def test_pipeline_passport_mrz(monkeypatch: pytest.MonkeyPatch) -> None:
    line2 = _mrz_line2()
    mrz_block = f"P<INDDEMO<<VOTER<<<<<<<<<<<<<<<<<<<<<<<<<<<\n{line2}"

    async def fake_vision(*_a, **_k):
        return {
            "document_type": "passport",
            "confidence": 0.93,
            "field_confidence": {"passport_number": 0.92},
            "fields": {
                "name": "Demo",
                "dob": "1990-04-12",
                "passport_number": "Z1234567",
                "nationality": "IND",
                "expiry_date": "2035-04-01",
                "mrz_line": mrz_block,
            },
            "extraction_warnings": [],
        }

    monkeypatch.setattr("app.pipeline.process.call_vision_llm", fake_vision)
    settings = Settings(use_mock_vision=True)
    res = await process_document_bytes(settings, file_bytes=b"x", filename="passport.png")
    assert res.document_type == "passport"
    assert not any("mrz_" in w for w in res.extraction_warnings)


@pytest.mark.asyncio
async def test_pipeline_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_vision(*_a, **_k):
        return {
            "document_type": "unsupported",
            "confidence": 0.2,
            "field_confidence": {},
            "fields": {},
            "extraction_warnings": [],
        }

    monkeypatch.setattr("app.pipeline.process.call_vision_llm", fake_vision)
    settings = Settings(use_mock_vision=True)
    with pytest.raises(UnsupportedDocumentError):
        await process_document_bytes(settings, file_bytes=b"x", filename="x.png")


@pytest.mark.asyncio
async def test_fixture_bytes_load_voter_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = Path(__file__).parent / "fixtures" / "synthetic_voter_degraded.png"
    if not path.exists():
        pytest.skip("Run scripts/generate_fixtures.py to create synthetic fixtures")

    async def fake_vision(*_a, **_k):
        return {
            "document_type": "voter_id",
            "confidence": 0.72,
            "field_confidence": {"voter_id_number": 0.55},
            "fields": {
                "name": "Demo Voter",
                "father_or_husband_name": "Demo Guardian",
                "dob": "1990-01-01",
                "voter_id_number": "ABC1234567",
                "address": "Demo",
                "constituency": "DEMO-01",
            },
            "extraction_warnings": ["low_scan_quality", "low_confidence_voter_id_number"],
        }

    monkeypatch.setattr("app.pipeline.process.call_vision_llm", fake_vision)
    settings = Settings(use_mock_vision=True)
    data = path.read_bytes()
    res = await process_document_bytes(settings, file_bytes=data, filename=path.name)
    assert res.document_type == "voter_id"
    assert "low_scan_quality" in res.extraction_warnings
