"""
ICAO 9303 MRZ check digits (7-3-1 weighting) for TD3 passport second line.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class MrzTd3SecondLine:
    document_number: str
    nationality: str
    dob: date
    sex: str
    expiry: date


def _mrz_char_value(c: str) -> int:
    if c == "<":
        return 0
    if "0" <= c <= "9":
        return int(c)
    if "A" <= c <= "Z":
        return ord(c) - 55
    return 0


def mrz_check_digit(field: str) -> int:
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(field):
        total += _mrz_char_value(ch) * weights[i % 3]
    return total % 10


def build_td3_second_line(
    *,
    doc9: str,
    nationality: str,
    dob_yymmdd: str,
    sex: str,
    expiry_yymmdd: str,
) -> str:
    """Construct a syntactically valid 44-char TD3 MRZ second line (for tests and demos)."""
    doc = doc9.upper().ljust(9, "<")[:9]
    cd0 = str(mrz_check_digit(doc))
    nat = nationality.upper().ljust(3, "<")[:3]
    cd1 = str(mrz_check_digit(dob_yymmdd))
    cd2 = str(mrz_check_digit(expiry_yymmdd))
    optional15 = "<" * 15
    cd3 = str(mrz_check_digit(optional15))
    return f"{doc}{cd0}{nat}{dob_yymmdd}{cd1}{sex}{expiry_yymmdd}{cd2}{optional15}{cd3}"


def _parse_yymmdd(s: str) -> date | None:
    if len(s) != 6 or not s.isdigit():
        return None
    try:
        return datetime.strptime(s, "%y%m%d").date()
    except ValueError:
        return None


def parse_td3_second_line(line: str) -> MrzTd3SecondLine | None:
    line = re.sub(r"\s+", "", line.strip())
    if len(line) < 44:
        return None
    line = line[:44]
    doc_field = line[0:9]
    check_doc = line[9]
    nationality = line[10:13]
    dob_raw = line[13:19]
    check_dob = line[19]
    sex = line[20]
    exp_raw = line[21:27]
    check_exp = line[27]

    try:
        if mrz_check_digit(doc_field) != int(check_doc):
            return None
        if mrz_check_digit(dob_raw) != int(check_dob):
            return None
        if mrz_check_digit(exp_raw) != int(check_exp):
            return None
    except ValueError:
        return None

    dob = _parse_yymmdd(dob_raw)
    expiry = _parse_yymmdd(exp_raw)
    if not dob or not expiry:
        return None
    doc_num = doc_field.replace("<", "").strip()
    return MrzTd3SecondLine(
        document_number=doc_num,
        nationality=nationality,
        dob=dob,
        sex=sex,
        expiry=expiry,
    )


def normalize_passport_number(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _nationality_compatible(mrz_nat: str, extracted: str | None) -> bool:
    if not extracted:
        return True
    e = extracted.strip().upper()
    if len(e) == 3 and e.isalpha():
        return mrz_nat == e
    if "IND" in e or e.startswith("IND") or "INDIAN" in e:
        return mrz_nat == "IND"
    return mrz_nat == e[:3] if len(e) >= 3 else True


def mrz_matches_extracted(
    mrz_line: str,
    *,
    passport_number: str | None,
    dob_iso: str | None,
    expiry_iso: str | None,
    nationality: str | None,
) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    parsed = parse_td3_second_line(mrz_line)
    if not parsed:
        return False, ["mrz_parse_or_checksum_failed"]

    ok = True
    if passport_number:
        ext = normalize_passport_number(passport_number)
        mrz_doc = normalize_passport_number(parsed.document_number)
        if ext and mrz_doc and ext != mrz_doc:
            ok = False
            warnings.append("mrz_passport_number_mismatch")

    if nationality and not _nationality_compatible(parsed.nationality, nationality):
        ok = False
        warnings.append("mrz_nationality_mismatch")

    if dob_iso:
        try:
            y, m, d = (int(x) for x in dob_iso.split("-")[:3])
            if date(y, m, d) != parsed.dob:
                ok = False
                warnings.append("mrz_dob_mismatch")
        except Exception:
            ok = False
            warnings.append("mrz_dob_mismatch")

    if expiry_iso:
        try:
            y, m, d = (int(x) for x in expiry_iso.split("-")[:3])
            if date(y, m, d) != parsed.expiry:
                ok = False
                warnings.append("mrz_expiry_mismatch")
        except Exception:
            ok = False
            warnings.append("mrz_expiry_mismatch")

    return ok, warnings
