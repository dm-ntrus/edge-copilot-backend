from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import pytest

from okapi_copilot.application.use_cases.verify_webhook import (
    VerifyWebhook,
    VerifyWebhookRequest,
)
from okapi_copilot.domain.gateway.webhook_security import WebhookSecurityConfig

SECRET = "webhook-secret"
PAYLOAD = b'{"event": "inbound_message"}'
NOW = datetime(2026, 1, 1, tzinfo=UTC)


class _FakeReplayGuard:
    def __init__(self, *, always_first: bool = True) -> None:
        self._always_first = always_first
        self._seen: set[str] = set()
        self.calls: list[tuple[str, int]] = []

    async def check_and_record(self, key: str, *, ttl_seconds: int) -> bool:
        self.calls.append((key, ttl_seconds))
        if self._always_first:
            return True
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


def _sign(payload: bytes) -> str:
    return hmac.new(SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _request(**overrides: object) -> VerifyWebhookRequest:
    defaults: dict[str, object] = dict(
        payload=PAYLOAD,
        provided_signature=_sign(PAYLOAD),
        secret=SECRET,
        event_timestamp=NOW,
        replay_key="evt-1",
    )
    defaults.update(overrides)
    return VerifyWebhookRequest(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_valid_webhook_passes_all_checks() -> None:
    use_case = VerifyWebhook(replay_guard=_FakeReplayGuard())
    result = await use_case.execute(_request(), now=NOW)
    assert result.valid is True


@pytest.mark.asyncio
async def test_invalid_signature_short_circuits_before_replay_check() -> None:
    replay_guard = _FakeReplayGuard()
    use_case = VerifyWebhook(replay_guard=replay_guard)

    result = await use_case.execute(_request(provided_signature="forged"), now=NOW)

    assert result.valid is False
    assert result.reason == "invalid_signature"
    assert replay_guard.calls == []  # never reached the replay check


@pytest.mark.asyncio
async def test_stale_timestamp_short_circuits_before_replay_check() -> None:
    replay_guard = _FakeReplayGuard()
    use_case = VerifyWebhook(replay_guard=replay_guard)

    result = await use_case.execute(
        _request(event_timestamp=NOW - timedelta(hours=1)), now=NOW
    )

    assert result.valid is False
    assert result.reason == "timestamp_out_of_tolerance"
    assert replay_guard.calls == []


@pytest.mark.asyncio
async def test_oversized_payload_is_rejected() -> None:
    tight_config = WebhookSecurityConfig(max_payload_bytes=5)
    use_case = VerifyWebhook(replay_guard=_FakeReplayGuard(), config=tight_config)

    result = await use_case.execute(_request(), now=NOW)

    assert result.valid is False
    assert result.reason == "payload_too_large"


@pytest.mark.asyncio
async def test_replayed_webhook_is_rejected_on_second_call() -> None:
    replay_guard = _FakeReplayGuard(always_first=False)
    use_case = VerifyWebhook(replay_guard=replay_guard)

    first = await use_case.execute(_request(), now=NOW)
    second = await use_case.execute(_request(), now=NOW)

    assert first.valid is True
    assert second.valid is False
    assert second.reason == "replay_detected"


@pytest.mark.asyncio
async def test_replay_key_and_ttl_are_passed_through() -> None:
    replay_guard = _FakeReplayGuard()
    use_case = VerifyWebhook(replay_guard=replay_guard, replay_ttl_seconds=900)

    await use_case.execute(_request(replay_key="custom-key"), now=NOW)

    assert replay_guard.calls == [("custom-key", 900)]
