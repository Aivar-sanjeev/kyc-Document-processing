import json

from app.schemas import SUPPORTED_TYPES

_USER_TEMPLATE = """Analyze this image. Return a single JSON object with this shape:
{{
  "document_type": one of {supported} OR \"unsupported\",
  "confidence": number 0-1 for document_type,
  "field_confidence": {{ "<field_name>": 0-1, ... }},
  "fields": {{ ... }},
  "extraction_warnings": [ "snake_case_reason", ... ]
}}

Per document_type, populate `fields` as follows:
- aadhaar: name, dob (ISO yyyy-mm-dd), gender, address, aadhaar_number (digits with or without spaces)
- pan: name, father_name, dob (ISO), pan_number
- voter_id: name, father_or_husband_name, dob (ISO), voter_id_number, address, constituency
- driving_licence: name, dob (ISO), dl_number, validity_from, validity_to (ISO), vehicle_classes, address
- passport: name, dob (ISO), passport_number, nationality, expiry_date (ISO), mrz_line (full MRZ block text if visible, else \"\")

Rules:
- Use Latin transliteration for names if mixed scripts; prefer English printed labels.
- If a field is unreadable, omit it and add an extraction_warning like low_confidence_<field>.
- If scan quality is globally poor, add low_scan_quality.

Supported types only: {supported_list}.
"""


def vision_user_prompt() -> str:
    supported = ", ".join(f'"{t}"' for t in sorted(SUPPORTED_TYPES))
    return _USER_TEMPLATE.format(
        supported=supported,
        supported_list=supported,
    )


def mock_json_response() -> str:
    """Deterministic stub for tests when USE_MOCK_VISION=1."""
    return json.dumps(
        {
            "document_type": "pan",
            "confidence": 0.91,
            "field_confidence": {"name": 0.9, "father_name": 0.88, "dob": 0.92, "pan_number": 0.95},
            "fields": {
                "name": "MOCK USER",
                "father_name": "MOCK FATHER",
                "dob": "1991-06-15",
                "pan_number": "ABCDE1234F",
            },
            "extraction_warnings": [],
        }
    )
