"""
Policy decision value objects.

Document 3 Section 40 (POLICY ENGINE) defines exactly five possible
outcomes — not a bare allow/deny. Section 41 (POLICY VERSIONING)
requires every decision to retain policy_id, policy_version, decision,
reason, timestamp, context_reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PolicyDecisionOutcome(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_HUMAN = "require_human"

    @property
    def permits_immediate_execution(self) -> bool:
        """Only ALLOW does. Every other outcome — including the
        REQUIRE_* family — must NOT be treated as permission to proceed
        by any caller; they route to confirmation/approval/human-handoff
        flows instead (none of which exist yet — see README)."""
        return self is PolicyDecisionOutcome.ALLOW


@dataclass(frozen=True, slots=True)
class PolicyDecisionRecord:
    policy_id: str
    policy_version: str
    decision: PolicyDecisionOutcome
    reason: str
    timestamp: datetime
    context_reference: str
