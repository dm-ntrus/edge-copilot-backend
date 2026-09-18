"""
ConversationContext value object.

Carries conversational working memory (last intent, pending
clarification, etc.) — never security-sensitive fields. Per the Zero
Trust skill ("Memory != Permission"), nothing in here can be read as
authorization; `SecurityContext` is the only trusted authority carrier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ConversationContext:
    conversation_id: str
    last_message_at: datetime | None
    pending_clarification: str | None = None
    variables: dict[str, str] = field(default_factory=dict)
