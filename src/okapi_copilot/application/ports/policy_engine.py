"""
PolicyEngine port.

Per SKILL — Authorization & Policy Engineering:
CAPABILITY != PERMISSION != POLICY != AUTHORIZATION != RISK != AUTONOMY.

This port represents the single point that turns
(SecurityContext, action, resource, context) into an ALLOW/DENY decision.
No other component — LLM, agent, MCP tool, workflow, scheduler — may
substitute for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from okapi_copilot.domain.security.security_context import SecurityContext


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    policy_version: str
    reason: str | None = None
    risk_score: float | None = None


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
        attributes: dict[str, object] | None = None,
    ) -> AuthorizationDecision:
        """
        Return an explicit ALLOW/DENY decision.

        Implementations MUST fail closed: any internal error, timeout, or
        ambiguous state must resolve to `allowed=False`
        (SKILL — Zero Trust, Section "FAIL CLOSED").
        """
        ...
