# KYC Document Processing Pipeline — Architecture

Visual overview: [Architecture/Architecture.png](Architecture/Architecture.png) (also embedded in the repository [README](README.md)).

## Goals

Deliver a single HTTP API that accepts a scan (PNG, JPEG, or PDF first page), classifies one of five Indian identity document types, extracts structured fields with confidences, validates high-risk fields, enforces Aadhaar masking at the output boundary, and degrades gracefully when the document is not supported.

## High-Level Flow

1. **FastAPI gateway** (`app/main.py`) accepts `multipart/form-data` on `POST /process`, enforces size limits, and never logs raw model output.
2. **Document loader** (`app/pipeline/document_loader.py`) normalizes PDFs to a raster image (first page, 2× zoom for legibility) so the vision model always sees pixels.
3. **Vision LLM** (`app/pipeline/nim_client.py`) calls NVIDIA NIM using the OpenAI-compatible `chat/completions` endpoint with `meta/llama-3.2-90b-vision-instruct`. The user prompt (`app/pipeline/prompts.py`) asks for strict JSON: `document_type`, aggregate and per-field confidence, `fields`, and `extraction_warnings`. The model acts as the **router** (supported vs `unsupported`) and primary **field extractor** in one pass to limit latency and cost; deterministic validators catch format and consistency errors the model might miss.
4. **Post-processing** (`app/pipeline/process.py`) orchestrates:
   - unsupported → `422` with a structured error body;
   - **validators** (`app/pipeline/validate.py`): PAN regex, driving licence expiry vs today, passport MRZ vs extracted biographics;
   - **masking** (`app/pipeline/mask.py`): for Aadhaar, only masked `XXXX XXXX ####` is emitted; optional scrub of embedded 12-digit runs inside address text.
5. **Safe logging** (`app/logging_safe.py`) redacts digit patterns that look like Aadhaar from log lines as a defense-in-depth measure; operational logs intentionally avoid full JSON payloads.

## Why This Split?

- **Vision LLM for extraction and coarse routing** handles skew, blur, Hindi/regional scripts, and layout variance better than classical OCR templates.
- **Code validators** provide auditable rules (PAN pattern, MRZ check digits, licence expiry) independent of model drift.
- **Output-layer masking** guarantees policy even if the model returns an unmasked number internally: the API response builder never forwards the raw 12-digit value.

## MRZ Handling

`app/pipeline/mrz.py` parses the TD3 second line (44 characters), verifies ICAO 7-3-1 check digits for the document number, date of birth, and expiry segments, then compares parsed values to extracted passport fields. Nationality is compared leniently (`IND` vs “Indian”) to reduce false mismatches from free-text extraction.

## Testing Strategy

- **Unit tests** for masking, MRZ construction/checksums, PAN regex, and licence expiry logic.
- **Pipeline tests** monkeypatch the vision client to return representative JSON for Aadhaar, PAN, passport (MRZ-aligned), voter ID, and unsupported flows — no network, deterministic CI.
- **Synthetic fixtures** under `tests/fixtures/` (see `scripts/generate_fixtures.py`): clean PNGs plus a **degraded** voter-style card (downscale/upscale + blur) to document how low-quality scans are represented in `extraction_warnings` when the model signals uncertainty.

## Configuration

Environment variables are documented in `.env.example`. Production requires `NIM_API_KEY`. `USE_MOCK_VISION=true` is reserved for offline demos and should not be enabled in production.
