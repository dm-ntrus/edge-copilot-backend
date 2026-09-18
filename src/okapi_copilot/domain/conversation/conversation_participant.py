from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ConversationParticipant:
    participant_id: str
    conversation_id: str
    user_id: str | None
    channel_identity_id: str | None
    joined_at: datetime
