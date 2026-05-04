import re
from typing import Any

_AADHAAR_DIGITS = re.compile(r"(\d{12}|\d{4}\s*\d{4}\s*\d{4})")


def normalize_aadhaar_digits(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) != 12:
        return None
    return digits


def mask_aadhaar_number_from_digits(digits: str) -> str:
    """digits must be exactly 12 digits."""
    return f"XXXX XXXX {digits[-4:]}"


def mask_aadhaar_number(raw: str) -> str | None:
    digits = normalize_aadhaar_digits(raw)
    if not digits:
        return None
    return mask_aadhaar_number_from_digits(digits)


def mask_aadhaar_in_text(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        d = normalize_aadhaar_digits(m.group(0))
        if not d:
            return m.group(0)
        return mask_aadhaar_number_from_digits(d)

    return _AADHAAR_DIGITS.sub(repl, text)


def finalize_aadhaar_output_fields(fields: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """
    Build public fields for Aadhaar: single masked aadhaar_number; scrub embedded numbers in strings.
    Raw 12-digit value is used only transiently inside this function.
    """
    out: dict[str, Any] = {}
    masked = False
    raw_digits: str | None = None

    for key, val in fields.items():
        lk = str(key).lower()
        if lk in {"aadhaar_number", "aadhaar", "uid", "uidai_number", "enrolment_id"}:
            if isinstance(val, str):
                raw_digits = normalize_aadhaar_digits(val) or raw_digits
            continue
        out[key] = val

    if raw_digits:
        out["aadhaar_number"] = mask_aadhaar_number_from_digits(raw_digits)
        masked = True
        raw_digits = None
    else:
        for key in ("aadhaar_number", "aadhaar", "uid"):
            v = fields.get(key)
            if not isinstance(v, str):
                continue
            condensed = re.sub(r"\s+", "", v).upper()
            if re.fullmatch(r"X{8}\d{4}", condensed):
                last4 = condensed[-4:]
                out["aadhaar_number"] = f"XXXX XXXX {last4}"
                masked = True
                break

    for key in ("address", "full_address", "correspondence_address"):
        if key in out and isinstance(out[key], str):
            if _AADHAAR_DIGITS.search(out[key]):
                out[key] = mask_aadhaar_in_text(out[key])
                masked = True

    if "aadhaar_number" not in out:
        for key, val in list(out.items()):
            if isinstance(val, str):
                d = normalize_aadhaar_digits(val)
                if d:
                    out["aadhaar_number"] = mask_aadhaar_number_from_digits(d)
                    out.pop(key, None)
                    masked = True
                    break

    return out, masked
