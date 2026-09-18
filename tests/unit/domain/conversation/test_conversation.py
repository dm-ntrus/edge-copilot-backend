from __future__ import annotations

from datetime import UTC, datetime

import pytest

from okapi_copilot.domain.conversation.conversation import Conversation, ConversationState
from okapi_copilot.domain.errors import ValidationError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _conversation(state: ConversationState = ConversationState.CREATED) -> Conversation:
    return Conversation(
        conversation_id="c1",
        tenant_id="tenant-a",
        organization_id="org-1",
        channel="web",
        state=state,
        created_at=NOW,
        updated_at=NOW,
    )


def test_grants_no_authority() -> None:
    assert _conversation().grants_no_authority() is True


def test_happy_path_transitions() -> None:
    c = _conversation()
    c = c.transition_to(ConversationState.ACTIVE, now=NOW)
    assert c.state is ConversationState.ACTIVE
    c = c.transition_to(ConversationState.IDLE, now=NOW)
    assert c.state is ConversationState.IDLE
    c = c.transition_to(ConversationState.ACTIVE, now=NOW)
    assert c.state is ConversationState.ACTIVE
    c = c.transition_to(ConversationState.ARCHIVED, now=NOW)
    assert c.state is ConversationState.ARCHIVED


def test_cannot_skip_active_from_created() -> None:
    c = _conversation()
    with pytest.raises(ValidationError):
        c.transition_to(ConversationState.ARCHIVED, now=NOW)


def test_archived_is_terminal() -> None:
    c = _conversation(ConversationState.ARCHIVED)
    with pytest.raises(ValidationError):
        c.transition_to(ConversationState.ACTIVE, now=NOW)
