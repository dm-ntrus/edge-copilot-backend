from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from okapi_copilot.application.ports.identity_provider import AuthenticatedIdentity
from okapi_copilot.application.use_cases.resolve_security_context import (
    ResolveSecurityContext,
    ResolveSecurityContextRequest,
)
from okapi_copilot.domain.errors import AmbiguousTenantContextError, NoValidMembershipError
from okapi_copilot.domain.identity.membership import MembershipReference, MembershipStatus
from okapi_copilot.domain.security.security_context import AuthenticationStrength


class FakeIdentityProvider:
    def __init__(self, identity: AuthenticatedIdentity) -> None:
        self._identity = identity

    async def verify_token(self, bearer_token: str) -> AuthenticatedIdentity:
        return self._identity


class FakeMembershipRepository:
    def __init__(self, memberships: tuple[MembershipReference, ...]) -> None:
        self._memberships = memberships

    async def list_by_user(self, user_id: str) -> tuple[MembershipReference, ...]:
        return tuple(m for m in self._memberships if m.user_id == user_id)


class FakePolicyEngine:
    async def current_policy_version(self) -> str:
        return "policy-v1"

    async def authorize(self, **kwargs: object) -> None:  # pragma: no cover - unused here
        raise NotImplementedError


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeIdGenerator:
    def new_id(self) -> str:
        return "ctx-fixed-id"


NOW = datetime(2026, 1, 1, tzinfo=UTC)

IDENTITY = AuthenticatedIdentity(
    user_id="user-1",
    authentication_strength=AuthenticationStrength.MFA,
    session_id="session-1",
    raw_claims={},
)


def _membership(**overrides: object) -> MembershipReference:
    defaults: dict[str, object] = dict(
        membership_id="m1",
        user_id="user-1",
        tenant_id="tenant-a",
        organization_id="org-1",
        role_references=("employee",),
        status=MembershipStatus.ACTIVE,
        valid_from=NOW - timedelta(days=1),
        valid_until=None,
    )
    defaults.update(overrides)
    return MembershipReference(**defaults)  # type: ignore[arg-type]


def _use_case(memberships: tuple[MembershipReference, ...]) -> ResolveSecurityContext:
    return ResolveSecurityContext(
        identity_provider=FakeIdentityProvider(IDENTITY),
        membership_repository=FakeMembershipRepository(memberships),
        policy_engine=FakePolicyEngine(),
        clock=FakeClock(NOW),
        id_generator=FakeIdGenerator(),
    )


@pytest.mark.asyncio
async def test_single_valid_membership_resolves_directly() -> None:
    use_case = _use_case((_membership(),))
    request = ResolveSecurityContextRequest(
        bearer_token="tok", channel="web", profile_type="employee"
    )

    context = await use_case.execute(request)

    assert context.tenant_id == "tenant-a"
    assert context.organization_id == "org-1"
    assert context.user_id == "user-1"
    assert context.roles == ("employee",)
    assert context.policy_version == "policy-v1"
    assert context.context_id == "ctx-fixed-id"
    assert context.expires_at > context.issued_at


@pytest.mark.asyncio
async def test_no_valid_membership_raises() -> None:
    expired = _membership(valid_until=NOW - timedelta(days=1))
    use_case = _use_case((expired,))
    request = ResolveSecurityContextRequest(
        bearer_token="tok", channel="web", profile_type="employee"
    )

    with pytest.raises(NoValidMembershipError):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_multiple_memberships_are_ambiguous_by_default() -> None:
    """
    Document 3 Section 12: AMBIGUOUS -> ASK USER. Never choose arbitrarily.
    This is the core regression test for that invariant.
    """
    m1 = _membership(membership_id="m1", tenant_id="tenant-a", organization_id="org-1")
    m2 = _membership(membership_id="m2", tenant_id="tenant-b", organization_id="org-9")
    use_case = _use_case((m1, m2))
    request = ResolveSecurityContextRequest(
        bearer_token="tok", channel="web", profile_type="employee"
    )

    with pytest.raises(AmbiguousTenantContextError) as exc_info:
        await use_case.execute(request)

    candidate_tenants = {c["tenant_id"] for c in exc_info.value.details["candidates"]}
    assert candidate_tenants == {"tenant-a", "tenant-b"}


@pytest.mark.asyncio
async def test_explicit_tenant_selection_narrows_ambiguity() -> None:
    m1 = _membership(membership_id="m1", tenant_id="tenant-a", organization_id="org-1")
    m2 = _membership(membership_id="m2", tenant_id="tenant-b", organization_id="org-9")
    use_case = _use_case((m1, m2))
    request = ResolveSecurityContextRequest(
        bearer_token="tok",
        channel="web",
        profile_type="employee",
        requested_tenant_id="tenant-b",
    )

    context = await use_case.execute(request)

    assert context.tenant_id == "tenant-b"
    assert context.organization_id == "org-9"


@pytest.mark.asyncio
async def test_explicit_selection_matching_nothing_raises_not_ambiguous() -> None:
    """A tenant_id that matches none of the user's valid memberships is a
    straight denial, not an ambiguity — the user never had access, so
    there is nothing to disambiguate."""
    m1 = _membership(membership_id="m1", tenant_id="tenant-a")
    use_case = _use_case((m1,))
    request = ResolveSecurityContextRequest(
        bearer_token="tok",
        channel="web",
        profile_type="employee",
        requested_tenant_id="tenant-does-not-exist",
    )

    with pytest.raises(NoValidMembershipError):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_same_tenant_different_organizations_still_ambiguous_without_org_selection() -> None:
    m1 = _membership(membership_id="m1", tenant_id="tenant-a", organization_id="org-1")
    m2 = _membership(membership_id="m2", tenant_id="tenant-a", organization_id="org-2")
    use_case = _use_case((m1, m2))
    request = ResolveSecurityContextRequest(
        bearer_token="tok",
        channel="web",
        profile_type="employee",
        requested_tenant_id="tenant-a",
    )

    with pytest.raises(AmbiguousTenantContextError):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_explicit_tenant_and_organization_resolves_uniquely() -> None:
    m1 = _membership(membership_id="m1", tenant_id="tenant-a", organization_id="org-1")
    m2 = _membership(membership_id="m2", tenant_id="tenant-a", organization_id="org-2")
    use_case = _use_case((m1, m2))
    request = ResolveSecurityContextRequest(
        bearer_token="tok",
        channel="web",
        profile_type="employee",
        requested_tenant_id="tenant-a",
        requested_organization_id="org-2",
    )

    context = await use_case.execute(request)

    assert context.tenant_id == "tenant-a"
    assert context.organization_id == "org-2"
