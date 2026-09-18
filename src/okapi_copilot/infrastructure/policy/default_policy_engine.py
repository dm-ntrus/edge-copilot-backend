"""
DefaultPolicyEngine.

Implements the `PolicyEngine` port (Document 3 Section 40) by composing:

  1. `AuthorizationEngine` (Section 42) — identity/membership/tenant/
     organization/role/permission mechanics.
  2. DENY BY DEFAULT rules (Section 43) that are actually implementable
     today: expired context, tenant mismatch, organization mismatch,
     permission absent.

HONEST SCOPE LIMIT (do not remove this note without replacing the
functionality it describes): this engine can currently only ever
return ALLOW or DENY. Document 3 Section 40 also specifies
REQUIRE_CONFIRMATION, REQUIRE_APPROVAL, and REQUIRE_HUMAN as possible
outcomes, but producing those correctly requires the Risk Engine
(Section 44), Confirmation Engine, Approval Engine, and Human Handoff
policy — none of which exist yet in this codebase. Wiring this engine
into a critical-mutation code path today would therefore only be
correct for operations that are genuinely low-risk enough to never
need confirmation/approval; it must NOT be treated as a complete
Policy Engine for critical operations until those pieces land.

Two DENY BY DEFAULT cases from Section 43 are intentionally NOT
implemented here yet and are also called out explicitly rather than
silently skipped:
  - "capability inconnue" — there is no Capability Registry yet.
  - "policy inconnue" — there is no versioned policy store yet; this
    engine only ever operates under one static, injected policy version.
"""

from __future__ import annotations

from datetime import UTC, datetime

from okapi_copilot.application.ports.clock import Clock
from okapi_copilot.domain.policy.authorization_engine import AuthorizationEngine
from okapi_copilot.domain.policy.decision import PolicyDecisionOutcome, PolicyDecisionRecord
from okapi_copilot.domain.security.security_context import SecurityContext


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class DefaultPolicyEngine:
    def __init__(
        self,
        *,
        policy_id: str = "default",
        policy_version: str = "1",
        clock: Clock | None = None,
    ) -> None:
        self._policy_id = policy_id
        self._policy_version = policy_version
        self._clock = clock or _SystemClock()

    async def current_policy_version(self) -> str:
        return self._policy_version

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
        now = self._clock.now()
        result = AuthorizationEngine.check(
            security_context=security_context,
            required_permission=required_permission,
            resource_tenant_id=resource_tenant_id,
            resource_organization_id=resource_organization_id,
            now=now,
        )

        return PolicyDecisionRecord(
            policy_id=self._policy_id,
            policy_version=self._policy_version,
            decision=(
                PolicyDecisionOutcome.ALLOW if result.allowed else PolicyDecisionOutcome.DENY
            ),
            reason=result.reason,
            timestamp=now,
            context_reference=security_context.context_id,
        )
