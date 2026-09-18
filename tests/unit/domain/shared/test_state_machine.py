from __future__ import annotations

import pytest

from okapi_copilot.domain.errors import ValidationError
from okapi_copilot.domain.shared.state_machine import ensure_transition_allowed


def test_allowed_transition_passes() -> None:
    ensure_transition_allowed(
        current="a", target="b", allowed_transitions={"a": frozenset({"b"})}, entity_name="Test"
    )


def test_disallowed_transition_raises() -> None:
    with pytest.raises(ValidationError):
        ensure_transition_allowed(
            current="a",
            target="c",
            allowed_transitions={"a": frozenset({"b"})},
            entity_name="Test",
        )


def test_unknown_current_state_has_no_allowed_targets() -> None:
    with pytest.raises(ValidationError):
        ensure_transition_allowed(
            current="z", target="b", allowed_transitions={"a": frozenset({"b"})}, entity_name="Test"
        )
