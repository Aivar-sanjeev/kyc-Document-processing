"""Application logging that never emits raw identity payloads."""

import logging
import re
from typing import Any

_AADHAAR_LIKE = re.compile(
    r"\b\d{4}\s?\d{4}\s?\d{4}\b|\b\d{12}\b",
    re.IGNORECASE,
)


def install_safe_logging() -> None:
    root = logging.getLogger()
    for h in root.handlers:
        h.addFilter(_RedactAadhaarFilter())


class _RedactAadhaarFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact_string(record.msg)
        if record.args:
            record.args = tuple(
                _redact_string(a) if isinstance(a, str) else a for a in record.args
            )
        return True


def _redact_string(s: str) -> str:
    return _AADHAAR_LIKE.sub("[REDACTED]", s)


def safe_log_dict(logger: logging.Logger, level: int, prefix: str, data: dict[str, Any]) -> None:
    """Log a shallow copy with aadhaar-like digit runs removed."""
    redacted = {k: _redact_value(v) for k, v in data.items()}
    logger.log(level, "%s %s", prefix, redacted)


def _redact_value(v: Any) -> Any:
    if isinstance(v, str):
        return _redact_string(v)
    if isinstance(v, dict):
        return {k: _redact_value(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_redact_value(x) for x in v]
    return v
