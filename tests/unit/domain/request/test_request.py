from __future__ import annotations

from datetime import UTC, datetime

import pytest

from okapi_copilot.domain.errors import ValidationError
from okapi_copilot.domain.request.intent import Intent
from okapi_copilot.domain.request.request import Request, RequestState
from okapi_copilot.domain.request.request_constraint import RequestConstraint

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _request(state: RequestState = RequestState.NEW) -> Request:
    return Request(
        request_id="r1",
        conversation_id="c1",
        tenant_id="tenant-a",
        organization_id="org-1",
        state=state,
        created_at=NOW,
        updated_at=NOW,
    )


def test_full_happy_path_through_confirmation() -> None:
    r = _request()
    for target in [
        RequestState.UNDERSTANDING,
        RequestState.PLANNING,
        RequestState.WAITING_CONFIRMATION,
        RequestState.AUTHORIZED,
        RequestState.EXECUTING,
        RequestState.VERIFYING,
        RequestState.COMPLETED,
    ]:
        r = r.transition_to(target, now=NOW)
    assert r.state is RequestState.COMPLETED
    assert r.is_terminal() is True


def test_low_risk_path_skips_confirmation_and_approval() -> None:
    """Planning may go straight to AUTHORIZED when the Policy Engine
    decision was a plain ALLOW (no confirmation/approval required)."""
    r = _request(RequestState.PLANNING)
    r = r.transition_to(RequestState.AUTHORIZED, now=NOW)
    assert r.state is RequestState.AUTHORIZED


def test_cannot_skip_planning_straight_to_executing() -> None:
    r = _request(RequestState.NEW)
    with pytest.raises(ValidationError):
        r.transition_to(RequestState.EXECUTING, now=NOW)


def test_cannot_leave_a_terminal_state() -> None:
    r = _request(RequestState.COMPLETED)
    with pytest.raises(ValidationError):
        r.transition_to(RequestState.EXECUTING, now=NOW)
    assert r.is_terminal() is True


def test_requires_human_can_resolve_to_authorized_or_denied() -> None:
    r = _request(RequestState.REQUIRES_HUMAN)
    authorized = r.transition_to(RequestState.AUTHORIZED, now=NOW)
    assert authorized.state is RequestState.AUTHORIZED

    r2 = _request(RequestState.REQUIRES_HUMAN)
    denied = r2.transition_to(RequestState.DENIED, now=NOW)
    assert denied.is_terminal() is True


def test_execution_failure_paths() -> None:
    r = _request(RequestState.EXECUTING)
    failed = r.transition_to(RequestState.FAILED, now=NOW)
    assert failed.is_terminal() is True

    r2 = _request(RequestState.EXECUTING)
    partial = r2.transition_to(RequestState.PARTIALLY_COMPLETED, now=NOW)
    assert partial.is_terminal() is True


def test_intent_confidence_threshold() -> None:
    confident = Intent(intent_type="place_order", confidence=0.9)
    unsure = Intent(intent_type="place_order", confidence=0.3)
    assert confident.is_confident() is True
    assert unsure.is_confident() is False


def test_request_constraint_is_plain_value_object() -> None:
    c = RequestConstraint(constraint_type="max_amount", value="1000")
    assert c.constraint_type == "max_amount"
    assert c.value == "1000"
