"""
Shared state-transition guard.

Conversation (Document 3 Section 17), Message (Section 18), and Request
(Section 19) each define an explicit state list and must not allow
silent/illegal jumps between states (e.g. NEW -> COMPLETED skipping
AUTHORIZED/EXECUTING/VERIFYING). This single helper enforces that
consistently instead of three hand-rolled, potentially-diverging copies.
"""

from __future__ import annotations

from typing import TypeVar

from okapi_copilot.domain.errors import ValidationError

StateT = TypeVar("StateT")


def ensure_transition_allowed(
    *,
    current: StateT,
    target: StateT,
    allowed_transitions: dict[StateT, frozenset[StateT]],
    entity_name: str,
) -> None:
    allowed = allowed_transitions.get(current, frozenset())
    if target not in allowed:
        raise ValidationError(
            f"Illegal {entity_name} state transition: {current!r} -> {target!r}",
            details={"current": str(current), "target": str(target)},
        )
