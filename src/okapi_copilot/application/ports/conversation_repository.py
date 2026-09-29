"""
ConversationRepository port.

No adapter exists yet (see README Known Gaps) — same status as
`MembershipRepository` was before its SurrealDB adapter landed.
"""

from __future__ import annotations

from typing import Protocol

from okapi_copilot.domain.conversation.conversation import Conversation


class ConversationRepository(Protocol):
    async def find_active_for_channel_identity(
        self, channel_identity_id: str
    ) -> Conversation | None: ...

    async def save(self, conversation: Conversation) -> None: ...
