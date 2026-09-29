"""
VerifyWebhook use case.

Composes the Document 3 Section 16 checks in order, short-circuiting on
the first failure — cheapest and most security-critical first:

    1. Signature verification (rejects forged payloads outright)
    2. Timestamp validation (rejects stale/future-skewed envelopes)
    3. Payload size limit
    4. Replay protection (only reached once the above pass, since it's
       the one check that costs a store round-trip)

NOT implemented here (see README Known Gaps): Provider validation
(needs a ChannelProvider repository backed by real persistence) and
Rate limiting (needs its own counter store, distinct from replay
dedup). Schema validation is provider-specific and is the caller's
responsibility once this use case has confirmed the envelope is
authentic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from okapi_copilot.application.ports.replay_guard import ReplayGuard
from okapi_copilot.domain.gateway.webhook_security import (
    WebhookSecurityConfig,
    WebhookValidationResult,
    validate_webhook_envelope,
)
from okapi_copilot.domain.gateway.webhook_signature import Algorithm, verify_webhook_signature


@dataclass(frozen=True, slots=True)
class VerifyWebhookRequest:
    payload: bytes
    provided_signature: str
    secret: str
    event_timestamp: datetime
    replay_key: str
    algorithm: Algorithm = "sha256"


class VerifyWebhook:
    def __init__(
        self,
        *,
        replay_guard: ReplayGuard,
        config: WebhookSecurityConfig | None = None,
        replay_ttl_seconds: int = 300,
    ) -> None:
        self._replay_guard = replay_guard
        self._config = config or WebhookSecurityConfig()
        self._replay_ttl_seconds = replay_ttl_seconds

    async def execute(
        self, request: VerifyWebhookRequest, *, now: datetime
    ) -> WebhookValidationResult:
        if not verify_webhook_signature(
            payload=request.payload,
            provided_signature=request.provided_signature,
            secret=request.secret,
            algorithm=request.algorithm,
        ):
            return WebhookValidationResult(False, "invalid_signature")

        envelope_result = validate_webhook_envelope(
            event_timestamp=request.event_timestamp,
            now=now,
            payload_size_bytes=len(request.payload),
            config=self._config,
        )
        if not envelope_result.valid:
            return envelope_result

        is_first_occurrence = await self._replay_guard.check_and_record(
            request.replay_key, ttl_seconds=self._replay_ttl_seconds
        )
        if not is_first_occurrence:
            return WebhookValidationResult(False, "replay_detected")

        return WebhookValidationResult(True, "valid")
