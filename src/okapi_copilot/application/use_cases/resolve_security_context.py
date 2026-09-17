"""
ResolveSecurityContext use case.

This is THE trusted issuance path for a SecurityContext (Document 9
Section 16 / Document 10 Section 8: SERVER GENERATED, SERVER VALIDATED).
No other code in this codebase is permitted to construct a
SecurityContext outside of this use case's output.

Flow, mirroring Document 3 Sections 9/12/13:

    bearer token
      -> IdentityProvider.verify_token          (auth: signature/issuer/
                                                   audience/expiry — done
                                                   inside the adapter)
      -> MembershipRepository.list_by_user      (load candidate contexts)
      -> filter to currently-valid memberships  (Clock, not wall-clock)
      -> resolve tenant/organization
           - zero valid memberships  -> NoValidMembershipError
           - exactly one candidate   -> use it
           - more than one candidate -> AmbiguousTenantContextError
             unless the caller supplied an explicit tenant/organization
             selection that narrows it to exactly one
      -> PolicyEngine.current_policy_version
      -> construct SecurityContext (IdGenerator for context_id, Clock for
         issued_at/expires_at)

"Ne jamais choisir arbitrairement" (Document 3 Section 12) is enforced
by construction: there is no code path here that picks
`candidates[0]` when more than one candidate remains.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from okapi_copilot.application.ports.clock import Clock
from okapi_copilot.application.ports.id_generator import IdGenerator
from okapi_copilot.application.ports.identity_provider import IdentityProvider
from okapi_copilot.application.ports.membership_repository import MembershipRepository
from okapi_copilot.application.ports.policy_engine import PolicyEngine
from okapi_copilot.domain.errors import AmbiguousTenantContextError, NoValidMembershipError
from okapi_copilot.domain.identity.membership import MembershipReference
from okapi_copilot.domain.security.security_context import SecurityContext


@dataclass(frozen=True, slots=True)
class ResolveSecurityContextRequest:
    bearer_token: str
    channel: str
    profile_type: str
    # Explicit selection hints ONLY — never trusted as authorization by
    # themselves. They narrow the candidate set; they cannot add a
    # membership the user does not actually have (Document 9 Section 15
    # warning about X-Tenant-ID / X-Organization-ID).
    requested_tenant_id: str | None = None
    requested_organization_id: str | None = None
    device_id: str | None = None


class ResolveSecurityContext:
    def __init__(
        self,
        *,
        identity_provider: IdentityProvider,
        membership_repository: MembershipRepository,
        policy_engine: PolicyEngine,
        clock: Clock,
        id_generator: IdGenerator,
        context_ttl: timedelta = timedelta(minutes=15),
    ) -> None:
        self._identity_provider = identity_provider
        self._membership_repository = membership_repository
        self._policy_engine = policy_engine
        self._clock = clock
        self._id_generator = id_generator
        self._context_ttl = context_ttl

    async def execute(self, request: ResolveSecurityContextRequest) -> SecurityContext:
        identity = await self._identity_provider.verify_token(request.bearer_token)

        now = self._clock.now()
        memberships = await self._membership_repository.list_by_user(identity.user_id)
        valid = [m for m in memberships if m.is_currently_valid(now=now)]

        if not valid:
            raise NoValidMembershipError(
                "Authenticated identity has no currently valid membership.",
                details={"user_id": identity.user_id},
            )

        candidates = self._narrow(
            valid,
            requested_tenant_id=request.requested_tenant_id,
            requested_organization_id=request.requested_organization_id,
        )

        if len(candidates) == 0:
            raise NoValidMembershipError(
                "Requested tenant/organization does not match any valid "
                "membership for this identity.",
                details={
                    "user_id": identity.user_id,
                    "requested_tenant_id": request.requested_tenant_id,
                    "requested_organization_id": request.requested_organization_id,
                },
            )

        if len(candidates) > 1:
            raise AmbiguousTenantContextError(
                "More than one tenant/organization context is possible for "
                "this identity; explicit selection is required.",
                details={
                    "user_id": identity.user_id,
                    "candidates": [
                        {"tenant_id": m.tenant_id, "organization_id": m.organization_id}
                        for m in candidates
                    ],
                },
            )

        selected = candidates[0]
        policy_version = await self._policy_engine.current_policy_version()

        return SecurityContext(
            context_id=self._id_generator.new_id(),
            user_id=identity.user_id,
            tenant_id=selected.tenant_id,
            organization_id=selected.organization_id,
            membership_id=selected.membership_id,
            roles=selected.role_references,
            # Role -> permission expansion is a PolicyEngine responsibility
            # not yet implemented; left empty rather than fabricated.
            permissions_snapshot=(),
            profile_type=request.profile_type,
            channel=request.channel,
            session_id=identity.session_id,
            device_id=request.device_id,
            authentication_strength=identity.authentication_strength,
            issued_at=now,
            expires_at=now + self._context_ttl,
            policy_version=policy_version,
        )

    @staticmethod
    def _narrow(
        candidates: list[MembershipReference],
        *,
        requested_tenant_id: str | None,
        requested_organization_id: str | None,
    ) -> list[MembershipReference]:
        result = candidates
        if requested_tenant_id is not None:
            result = [m for m in result if m.tenant_id == requested_tenant_id]
        if requested_organization_id is not None:
            result = [m for m in result if m.organization_id == requested_organization_id]
        return result
