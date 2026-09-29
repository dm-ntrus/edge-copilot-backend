from __future__ import annotations

from datetime import UTC, datetime, timedelta

from okapi_copilot.domain.gateway.webhook_security import (
    WebhookSecurityConfig,
    validate_webhook_envelope,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CONFIG = WebhookSecurityConfig()


def test_fresh_timestamp_and_normal_size_is_valid() -> None:
    result = validate_webhook_envelope(
        event_timestamp=NOW - timedelta(seconds=10),
        now=NOW,
        payload_size_bytes=1000,
        config=CONFIG,
    )
    assert result.valid is True


def test_stale_timestamp_is_rejected() -> None:
    result = validate_webhook_envelope(
        event_timestamp=NOW - timedelta(hours=1),
        now=NOW,
        payload_size_bytes=1000,
        config=CONFIG,
    )
    assert result.valid is False
    assert result.reason == "timestamp_out_of_tolerance"


def test_future_timestamp_beyond_skew_is_rejected() -> None:
    """Guards against forged/replayed events claiming a future timestamp,
    not just old ones."""
    result = validate_webhook_envelope(
        event_timestamp=NOW + timedelta(hours=1),
        now=NOW,
        payload_size_bytes=1000,
        config=CONFIG,
    )
    assert result.valid is False
    assert result.reason == "timestamp_out_of_tolerance"


def test_oversized_payload_is_rejected() -> None:
    result = validate_webhook_envelope(
        event_timestamp=NOW,
        now=NOW,
        payload_size_bytes=CONFIG.max_payload_bytes + 1,
        config=CONFIG,
    )
    assert result.valid is False
    assert result.reason == "payload_too_large"


def test_config_is_overridable() -> None:
    tight_config = WebhookSecurityConfig(
        max_clock_skew=timedelta(seconds=30), max_payload_bytes=100
    )
    result = validate_webhook_envelope(
        event_timestamp=NOW - timedelta(minutes=1),
        now=NOW,
        payload_size_bytes=50,
        config=tight_config,
    )
    assert result.valid is False
    assert result.reason == "timestamp_out_of_tolerance"
