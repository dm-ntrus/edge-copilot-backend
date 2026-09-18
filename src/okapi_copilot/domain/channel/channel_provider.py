"""
ChannelProvider entity.

Represents a configured integration with a channel's transport provider
(e.g. a specific WhatsApp Business API account, a web widget
deployment). Core Copilot logic must never depend on a specific
provider (Instructions Section 12/13: product/domain-agnostic) — this
entity exists precisely so provider identity is data, not a code
branch.
"""

from __future__ import annotations

from dataclasses import dataclass

from okapi_copilot.domain.identity.channel_identity import Channel


@dataclass(frozen=True, slots=True)
class ChannelProvider:
    provider_id: str
    channel: Channel
    tenant_id: str
    display_name: str
    is_active: bool
