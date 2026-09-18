from __future__ import annotations

from datetime import UTC, datetime

from okapi_copilot.domain.channel.channel_message import ChannelMessage
from okapi_copilot.domain.channel.channel_provider import ChannelProvider
from okapi_copilot.domain.channel.channel_session import ChannelSession, ChannelSessionState
from okapi_copilot.domain.identity.channel_identity import Channel

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_channel_session_grants_no_authority() -> None:
    session = ChannelSession(
        channel_session_id="s1",
        channel=Channel.WHATSAPP,
        channel_identity_id="ci-1",
        state=ChannelSessionState.OPEN,
        started_at=NOW,
        last_activity_at=NOW,
    )
    assert session.grants_no_authority() is True


def test_channel_provider_is_data_not_a_code_branch() -> None:
    provider = ChannelProvider(
        provider_id="p1",
        channel=Channel.WHATSAPP,
        tenant_id="tenant-a",
        display_name="Acme WhatsApp",
        is_active=True,
    )
    assert provider.channel is Channel.WHATSAPP
    assert provider.is_active is True


def test_channel_message_carries_provider_reference() -> None:
    message = ChannelMessage(
        channel_message_id="cm1",
        channel=Channel.WEB,
        channel_session_id="s1",
        provider_message_id="wamid.abc123",
        received_at=NOW,
    )
    assert message.provider_message_id == "wamid.abc123"
