"""
Webhook envelope validation.

Covers the Document 3 Section 16 checks that are pure computation, no
I/O: timestamp validation (rejects both stale/replayed-looking
timestamps and suspiciously-future ones from clock skew or forgery) and
payload size limit. Signature verification lives in
`webhook_signature.py`; replay protection (needs a store) and rate
limiting (needs a store) are application-layer concerns composed on top
of this in `application/use_cases/verify_webhook.py`. Provider
validation (is this provider configured/active for this tenant) and
schema validation are provider-specific and belong to the calling code
that knows the provider's shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class WebhookSecurityConfig:
    max_clock_skew: timedelta = timedelta(minutes=5)
    max_payload_bytes: int = 1_000_000


@dataclass(frozen=True, slots=True)
class WebhookValidationResult:
    valid: bool
    reason: str


def validate_webhook_envelope(
    *,
    event_timestamp: datetime,
    now: datetime,
    payload_size_bytes: int,
    config: WebhookSecurityConfig,
) -> WebhookValidationResult:
    skew = abs(now - event_timestamp)
    if skew > config.max_clock_skew:
        return WebhookValidationResult(False, "timestamp_out_of_tolerance")

    if payload_size_bytes > config.max_payload_bytes:
        return WebhookValidationResult(False, "payload_too_large")

    return WebhookValidationResult(True, "valid")
