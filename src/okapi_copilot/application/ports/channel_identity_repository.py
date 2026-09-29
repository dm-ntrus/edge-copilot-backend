"""
ChannelIdentityRepository port.

Backed by Copilot's own persistence (SurrealDB per the reference
stack) — no adapter exists yet (see README Known Gaps), same status as
`MembershipRepository` was before its SurrealDB adapter landed.
"""

from __future__ import annotations

from typing import Protocol

from okapi_copilot.domain.identity.channel_identity import Channel, ChannelIdentity


class ChannelIdentityRepository(Protocol):
    async def find_by_provider_subject(
        self, *, channel: Channel, provider: str, provider_subject_id: str
    ) -> ChannelIdentity | None: ...
