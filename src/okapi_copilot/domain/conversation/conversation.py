"""
Conversation entity.

Document 3 Section 17: states CREATED -> ACTIVE -> IDLE -> ARCHIVED, and
the explicit invariant "Une conversation ne constitue jamais une
autorité d'accès" (a conversation is never itself an access authority —
mirrored here as `grants_no_authority()`, matching the pattern already
established for `ChannelIdentity`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from okapi_copilot.domain.shared.state_machine import ensure_transition_allowed


class ConversationState(StrEnum):
    CREATED = "created"
    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVED = "archived"


_ALLOWED_TRANSITIONS: dict[ConversationState, frozenset[ConversationState]] = {
    ConversationState.CREATED: frozenset({ConversationState.ACTIVE}),
    ConversationState.ACTIVE: frozenset({ConversationState.IDLE, ConversationState.ARCHIVED}),
    ConversationState.IDLE: frozenset({ConversationState.ACTIVE, ConversationState.ARCHIVED}),
    ConversationState.ARCHIVED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class Conversation:
    conversation_id: str
    tenant_id: str
    organization_id: str | None
    channel: str
    state: ConversationState
    created_at: datetime
    updated_at: datetime

    def grants_no_authority(self) -> bool:
        """Always True — see module docstring."""
        return True

    def transition_to(self, target: ConversationState, *, now: datetime) -> Conversation:
        ensure_transition_allowed(
            current=self.state,
            target=target,
            allowed_transitions=_ALLOWED_TRANSITIONS,
            entity_name="Conversation",
        )
        return Conversation(
            conversation_id=self.conversation_id,
            tenant_id=self.tenant_id,
            organization_id=self.organization_id,
            channel=self.channel,
            state=target,
            created_at=self.created_at,
            updated_at=now,
        )
