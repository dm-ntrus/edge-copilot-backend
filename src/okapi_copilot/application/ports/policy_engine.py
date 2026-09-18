"""
PolicyEngine port.

Per SKILL — Authorization & Policy Engineering:
CAPABILITY != PERMISSION != POLICY != AUTHORIZATION != RISK != AUTONOMY.

Document 3 Section 40 defines the Policy Engine's contract precisely:

    Input:  SecurityContext, Request, Capability, Resource, Risk, Agent, Plan
    Output: ALLOW | DENY | REQUIRE_CONFIRMATION | REQUIRE_APPROVAL | REQUIRE_HUMAN

This is intentionally richer than a bare allow/deny — no other
component (LLM, agent, MCP tool, workflow, scheduler) may substitute
for it, and callers must handle all five outcomes rather than treating
"not DENY" as permission to proceed
(`PolicyDecisionOutcome.permits_immediate_execution` exists precisely
to make that mistake hard to write).
"""

from __future__ import annotations

from typing import Protocol

from okapi_copilot.domain.policy.decision import PolicyDecisionRecord
from okapi_copilot.domain.security.security_context import SecurityContext


class PolicyEngine(Protocol):
    async def current_policy_version(self) -> str:
        """
        Return the policy version currently in force.

        Used to stamp newly-issued SecurityContexts (Document 9/10) so a
        later policy change can be detected and force re-issuance rather
        than silently operating under stale rules.
        """
        ...

    async def authorize(
        self,
        *,
        security_context: SecurityContext,
        action: str,
        resource_type: str,
        resource_id: str | None,
        resource_tenant_id: str,
        resource_organization_id: str | None,
        required_permission: str,
        attributes: dict[str, object] | None = None,
    ) -> PolicyDecisionRecord:
        """
        Return one of ALLOW / DENY / REQUIRE_CONFIRMATION /
        REQUIRE_APPROVAL / REQUIRE_HUMAN.

        Implementations MUST fail closed (Document 3 Section 43: DENY BY
        DEFAULT) — any internal error, timeout, unknown capability, or
        ambiguous state must resolve to DENY, never to a permissive
        outcome.
        """
        ...
