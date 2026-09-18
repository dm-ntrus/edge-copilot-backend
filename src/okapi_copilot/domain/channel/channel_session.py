"""
ChannelSession entity.

A channel-level session (e.g. a WhatsApp conversation window, a web
socket connection) is distinct from both `SecurityContext` and
`Conversation`: it tracks channel-transport lifecycle only, and — like
`ChannelIdentity` — grants no authority by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from okapi_copilot.domain.identity.channel_identity import Channel


class ChannelSessionState(StrEnum):
    OPEN = "open"
    IDLE = "idle"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class ChannelSession:
    channel_session_id: str
    channel: Channel
    channel_identity_id: str
    state: ChannelSessionState
    started_at: datetime
    last_activity_at: datetime

    def grants_no_authority(self) -> bool:
        return True
