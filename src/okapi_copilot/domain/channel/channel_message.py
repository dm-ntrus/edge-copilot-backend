"""
ChannelMessage entity.

The raw, channel-native form of an inbound/outbound message (before it
becomes a domain `Message` via the Input Gateway pipeline, Section 15).
Kept separate from `messaging.Message` so channel-specific transport
fields (provider message ID, raw payload) never leak into the
channel-agnostic Message domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from okapi_copilot.domain.identity.channel_identity import Channel


@dataclass(frozen=True, slots=True)
class ChannelMessage:
    channel_message_id: str
    channel: Channel
    channel_session_id: str
    provider_message_id: str
    received_at: datetime
