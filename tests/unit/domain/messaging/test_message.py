from __future__ import annotations

from datetime import UTC, datetime

import pytest

from okapi_copilot.domain.errors import ValidationError
from okapi_copilot.domain.messaging.message import Message, MessageState

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _message(state: MessageState = MessageState.RECEIVED) -> Message:
    return Message(
        message_id="m1",
        conversation_id="c1",
        sender="user-1",
        channel="web",
        timestamp=NOW,
        correlation_id="corr-1",
        status=state,
    )


def test_happy_path() -> None:
    m = _message()
    for target in [
        MessageState.VALIDATED,
        MessageState.IDENTIFIED,
        MessageState.CONTEXTUALIZED,
        MessageState.UNDERSTOOD,
        MessageState.PROCESSED,
        MessageState.RESPONDED,
    ]:
        m = m.transition_to(target)
    assert m.status is MessageState.RESPONDED


def test_can_fail_from_any_non_terminal_step() -> None:
    m = _message(MessageState.CONTEXTUALIZED)
    m = m.transition_to(MessageState.FAILED)
    assert m.status is MessageState.FAILED


def test_failed_can_retry_or_dead_letter() -> None:
    m = _message(MessageState.FAILED)
    retried = m.transition_to(MessageState.RETRYING)
    assert retried.status is MessageState.RETRYING
    dead = m.transition_to(MessageState.DEAD_LETTER)
    assert dead.status is MessageState.DEAD_LETTER


def test_retrying_goes_back_to_received() -> None:
    m = _message(MessageState.RETRYING)
    m = m.transition_to(MessageState.RECEIVED)
    assert m.status is MessageState.RECEIVED


def test_responded_is_terminal() -> None:
    m = _message(MessageState.RESPONDED)
    with pytest.raises(ValidationError):
        m.transition_to(MessageState.PROCESSED)


def test_cannot_skip_steps() -> None:
    m = _message(MessageState.RECEIVED)
    with pytest.raises(ValidationError):
        m.transition_to(MessageState.RESPONDED)
