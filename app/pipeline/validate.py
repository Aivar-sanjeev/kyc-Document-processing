import re
from datetime import date
from typing import Any

from app.pipeline.mrz import mrz_matches_extracted

_PAN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def normalize_pan(pan: str) -> str:
    return re.sub(r"\s+", "", (pan or "").upper())


def validate_pan(pan: str | None) -> tuple[bool, list[str]]:
    if not pan:
        return False, ["pan_missing"]
    p = normalize_pan(pan)
    if _PAN.match(p):
        return True, []
    return False, ["pan_format_invalid"]


def _parse_date_iso(s: str | None) -> date | None:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()[:10]
    try:
        y, m, d = (int(x) for x in s.split("-"))
        return date(y, m, d)
    except Exception:
        return None


def validate_dl_expiry(fields: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    today = date.today()
    expiry = None
    for key in (
        "dl_expiry",
        "validity_to",
        "valid_to",
        "expiry_date",
        "license_expiry",
        "validity_end",
    ):
        if key in fields:
            expiry = _parse_date_iso(str(fields[key]))
            if expiry:
                break
    if not expiry:
        for key, val in fields.items():
            lk = key.lower()
            if "expir" in lk or ("valid" in lk and "to" in lk):
                expiry = _parse_date_iso(str(val))
                if expiry:
                    break
    if not expiry:
        return True, ["dl_expiry_not_found_skipped_validation"]

    if expiry <= today:
        return False, ["dl_expired"]
    return True, []


def validate_passport_mrz(fields: dict[str, Any]) -> tuple[bool, list[str]]:
    mrz = fields.get("mrz_line") or fields.get("mrz")
    if not mrz or not isinstance(mrz, str):
        return True, ["mrz_missing_skipped_validation"]
    line = mrz.strip().splitlines()
    if len(line) < 2:
        if len(mrz) >= 44:
            second = mrz[-44:]
        else:
            return False, ["mrz_incomplete"]
    else:
        second = line[1].strip()
    return mrz_matches_extracted(
        second,
        passport_number=str(fields.get("passport_number") or ""),
        dob_iso=str(fields.get("dob") or ""),
        expiry_iso=str(fields.get("expiry_date") or fields.get("passport_expiry") or ""),
        nationality=str(fields.get("nationality") or ""),
    )


def run_validators(document_type: str, fields: dict[str, Any]) -> tuple[list[str], list[str]]:
    """
    Returns (validation_warnings, validation_errors_as_warnings).
    For API simplicity we attach hard failures as validation_warnings with clear codes;
    caller may still return 200 with lowered confidence — here we only add warnings.
    """
    warnings: list[str] = []
    if document_type == "pan":
        ok, w = validate_pan(fields.get("pan_number") or fields.get("pan"))
        warnings.extend(w)
        if not ok:
            warnings.append("pan_validation_failed")
    if document_type == "driving_licence":
        ok, w = validate_dl_expiry(fields)
        warnings.extend(w)
        if not ok:
            warnings.append("dl_validation_failed")
    if document_type == "passport":
        ok, w = validate_passport_mrz(fields)
        warnings.extend(w)
        if not ok:
            warnings.append("passport_mrz_validation_failed")
    return warnings, []
