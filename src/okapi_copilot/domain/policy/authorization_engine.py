"""
AuthorizationEngine domain service.

Document 3 Section 42: "Créer une couche d'autorisation distincte de la
policy. Elle doit vérifier: identity, membership, tenant, organization,
role, permission, resource, operation. La Policy Engine ajoute ensuite
les contraintes contextuelles."

This is deliberately a pure domain service: it only needs a
`SecurityContext` (already-resolved identity/membership/tenant/
organization) plus the resource/operation being requested, and computes
a mechanical allow/deny from role & permission membership and tenant/
organization match. No I/O, no risk scoring, no confirmation/approval
logic — those are the Policy Engine's job (Section 40), layered on top
of this in `infrastructure/policy/default_policy_engine.py`.

Fail-closed per Document 3 Section 43 (DENY BY DEFAULT): every check
below defaults to denial; there is no fallthrough "allow" path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from okapi_copilot.domain.security.security_context import SecurityContext


@dataclass(frozen=True, slots=True)
class AuthorizationCheckResult:
    allowed: bool
    reason: str


class AuthorizationEngine:
    @staticmethod
    def check(
        *,
        security_context: SecurityContext,
        required_permission: str,
        resource_tenant_id: str,
        resource_organization_id: str | None,
        now: datetime,
        required_role: str | None = None,
    ) -> AuthorizationCheckResult:
        if security_context.is_expired(now=now):
            return AuthorizationCheckResult(False, "security_context_expired")

        if not security_context.belongs_to_tenant(resource_tenant_id):
            return AuthorizationCheckResult(False, "tenant_mismatch")

        if (
            resource_organization_id is not None
            and not security_context.belongs_to_organization(resource_organization_id)
        ):
            return AuthorizationCheckResult(False, "organization_mismatch")

        if required_role is not None and not security_context.has_role(required_role):
            return AuthorizationCheckResult(False, "role_absent")

        if not security_context.has_permission(required_permission):
            return AuthorizationCheckResult(False, "permission_absent")

        return AuthorizationCheckResult(True, "authorized")
