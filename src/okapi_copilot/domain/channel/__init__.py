"""
Channel domain (Document 3 Section 14).

`Channel` and `ChannelIdentity` already live in `domain.identity` (they
were needed there first, per Document 10 Section 6). This package adds
the remaining Section 14 entities — ChannelSession, ChannelProvider,
ChannelMessage — and re-exports Channel/ChannelIdentity so callers can
import the whole Channel domain from one place without a second
Channel enum being (re)defined.
"""

from okapi_copilot.domain.channel.channel_message import ChannelMessage
from okapi_copilot.domain.channel.channel_provider import ChannelProvider
from okapi_copilot.domain.channel.channel_session import ChannelSession, ChannelSessionState
from okapi_copilot.domain.identity.channel_identity import Channel, ChannelIdentity

__all__ = [
    "Channel",
    "ChannelIdentity",
    "ChannelSession",
    "ChannelSessionState",
    "ChannelProvider",
    "ChannelMessage",
]
