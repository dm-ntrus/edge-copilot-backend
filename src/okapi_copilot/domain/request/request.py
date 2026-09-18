"""
Request entity.

Document 3 Section 19. States mirror the Architectural Golden Chain
(Document 1/9): a Request moves through understanding, planning,
confirmation/approval gates, authorization, execution, and verification
— never skipping the gates (e.g. PLANNING cannot jump straight to
EXECUTING; it must pass through AUTHORIZED, which itself requires
having gone through WAITING_CONFIRMATION/WAITING_APPROVAL when the
Policy Engine required them).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from okapi_copilot.domain.shared.state_machine import ensure_transition_allowed


class RequestState(StrEnum):
    NEW = "new"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    WAITING_CONFIRMATION = "waiting_confirmation"
    WAITING_APPROVAL = "waiting_approval"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    DENIED = "denied"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    REQUIRES_HUMAN = "requires_human"


_TERMINAL: frozenset[RequestState] = frozenset(
    {
        RequestState.COMPLETED,
        RequestState.DENIED,
        RequestState.CANCELLED,
        RequestState.EXPIRED,
        RequestState.FAILED,
        RequestState.PARTIALLY_COMPLETED,
    }
)

_ALLOWED_TRANSITIONS: dict[RequestState, frozenset[RequestState]] = {
    RequestState.NEW: frozenset({RequestState.UNDERSTANDING, RequestState.CANCELLED}),
    RequestState.UNDERSTANDING: frozenset(
        {
            RequestState.PLANNING,
            RequestState.REQUIRES_HUMAN,
            RequestState.CANCELLED,
            RequestState.EXPIRED,
        }
    ),
    RequestState.PLANNING: frozenset(
        {
            RequestState.WAITING_CONFIRMATION,
            RequestState.WAITING_APPROVAL,
            RequestState.AUTHORIZED,
            RequestState.DENIED,
            RequestState.CANCELLED,
            RequestState.EXPIRED,
            RequestState.REQUIRES_HUMAN,
        }
    ),
    RequestState.WAITING_CONFIRMATION: frozenset(
        {
            RequestState.AUTHORIZED,
            RequestState.DENIED,
            RequestState.CANCELLED,
            RequestState.EXPIRED,
        }
    ),
    RequestState.WAITING_APPROVAL: frozenset(
        {
            RequestState.AUTHORIZED,
            RequestState.DENIED,
            RequestState.CANCELLED,
            RequestState.EXPIRED,
            RequestState.REQUIRES_HUMAN,
        }
    ),
    RequestState.AUTHORIZED: frozenset(
        {RequestState.EXECUTING, RequestState.CANCELLED, RequestState.EXPIRED}
    ),
    RequestState.EXECUTING: frozenset(
        {RequestState.VERIFYING, RequestState.FAILED, RequestState.PARTIALLY_COMPLETED}
    ),
    RequestState.VERIFYING: frozenset(
        {
            RequestState.COMPLETED,
            RequestState.FAILED,
            RequestState.PARTIALLY_COMPLETED,
            RequestState.REQUIRES_HUMAN,
        }
    ),
    RequestState.REQUIRES_HUMAN: frozenset(
        {RequestState.AUTHORIZED, RequestState.DENIED, RequestState.CANCELLED}
    ),
    **{state: frozenset() for state in _TERMINAL},
}


@dataclass(frozen=True, slots=True)
class Request:
    request_id: str
    conversation_id: str
    tenant_id: str
    organization_id: str | None
    state: RequestState
    created_at: datetime
    updated_at: datetime

    def is_terminal(self) -> bool:
        return self.state in _TERMINAL

    def transition_to(self, target: RequestState, *, now: datetime) -> Request:
        ensure_transition_allowed(
            current=self.state,
            target=target,
            allowed_transitions=_ALLOWED_TRANSITIONS,
            entity_name="Request",
        )
        return Request(
            request_id=self.request_id,
            conversation_id=self.conversation_id,
            tenant_id=self.tenant_id,
            organization_id=self.organization_id,
            state=target,
            created_at=self.created_at,
            updated_at=now,
        )
