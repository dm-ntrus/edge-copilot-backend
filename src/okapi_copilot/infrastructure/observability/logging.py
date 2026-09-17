"""
Structured logging configuration.

Per SKILL — Okapi Production Audit & Certification, Section 15
(SECRETS IN OBSERVABILITY): passwords, API keys, tokens, credentials,
private keys and unnecessary sensitive payloads must never be logged.

This module wires a structured JSON formatter and a redaction filter.
Full OpenTelemetry trace/span export wiring (Document 2 Section 6) is a
follow-up step once an OTEL collector endpoint is available — the hook
point (`configure_logging`) is established now so call sites do not
need to change later.
"""

from __future__ import annotations

import logging
import re
from typing import Any

_REDACTED = "***REDACTED***"

_SECRET_KEY_PATTERN = re.compile(
    r"(password|token|secret|api[_-]?key|authorization|bearer)",
    re.IGNORECASE,
)


class RedactingFilter(logging.Filter):
    """Redacts likely-sensitive values from structured log extras."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, _value in list(vars(record).items()):
            if _SECRET_KEY_PATTERN.search(key):
                setattr(record, key, _REDACTED)
        return True


def redact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact keys that look sensitive before logging a dict."""
    result: dict[str, Any] = {}
    for key, value in payload.items():
        if _SECRET_KEY_PATTERN.search(key):
            result[key] = _REDACTED
        elif isinstance(value, dict):
            result[key] = redact_dict(value)
        else:
            result[key] = value
    return result


def configure_logging(*, level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format=(
            '{"ts":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","message":"%(message)s"}'
        ),
    )
    root = logging.getLogger()
    root.addFilter(RedactingFilter())
