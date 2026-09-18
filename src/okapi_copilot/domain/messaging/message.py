"""
Message entity.

Document 3 Section 18. Required fields verbatim: message_id,
conversation_id, sender, channel, timestamp, correlation_id, status.
Happy-path states: RECEIVED -> VALIDATED -> IDENTIFIED ->
CONTEXTUALIZED -> UNDERSTOOD -> PROCESSED -> RESPONDED. Error states:
FAILED, RETRYING, DEAD_LETTER.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from okapi_copilot.domain.shared.state_machine import ensure_transition_allowed


class MessageState(StrEnum):
    RECEIVED = "received"
    VALIDATED = "validated"
    IDENTIFIED = "identified"
    CONTEXTUALIZED = "contextualized"
    UNDERSTOOD = "understood"
    PROCESSED = "processed"
    RESPONDED = "responded"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


_HAPPY_PATH_ORDER = [
    MessageState.RECEIVED,
    MessageState.VALIDATED,
    MessageState.IDENTIFIED,
    MessageState.CONTEXTUALIZED,
    MessageState.UNDERSTOOD,
    MessageState.PROCESSED,
    MessageState.RESPONDED,
]

_ALLOWED_TRANSITIONS: dict[MessageState, frozenset[MessageState]] = {
    state: frozenset({_HAPPY_PATH_ORDER[i + 1], MessageState.FAILED})
    for i, state in enumerate(_HAPPY_PATH_ORDER[:-1])
}
_ALLOWED_TRANSITIONS[MessageState.RESPONDED] = frozenset()
_ALLOWED_TRANSITIONS[MessageState.FAILED] = frozenset(
    {MessageState.RETRYING, MessageState.DEAD_LETTER}
)
_ALLOWED_TRANSITIONS[MessageState.RETRYING] = frozenset(
    {MessageState.RECEIVED, MessageState.DEAD_LETTER}
)
_ALLOWED_TRANSITIONS[MessageState.DEAD_LETTER] = frozenset()


@dataclass(frozen=True, slots=True)
class Message:
    message_id: str
    conversation_id: str
    sender: str
    channel: str
    timestamp: datetime
    correlation_id: str
    status: MessageState

    def transition_to(self, target: MessageState) -> Message:
        ensure_transition_allowed(
            current=self.status,
            target=target,
            allowed_transitions=_ALLOWED_TRANSITIONS,
            entity_name="Message",
        )
        return Message(
            message_id=self.message_id,
            conversation_id=self.conversation_id,
            sender=self.sender,
            channel=self.channel,
            timestamp=self.timestamp,
            correlation_id=self.correlation_id,
            status=target,
        )
