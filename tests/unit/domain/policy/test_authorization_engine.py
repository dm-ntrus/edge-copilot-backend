from __future__ import annotations

from datetime import UTC, datetime, timedelta

from okapi_copilot.domain.policy.authorization_engine import AuthorizationEngine
from okapi_copilot.domain.security.security_context import AuthenticationStrength, SecurityContext

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _context(**overrides: object) -> SecurityContext:
    defaults: dict[str, object] = dict(
        context_id="ctx-1",
        user_id="user-1",
        tenant_id="tenant-a",
        organization_id="org-1",
        membership_id="membership-1",
        roles=("employee",),
        permissions_snapshot=("orders:read",),
        profile_type="employee",
        channel="web",
        session_id="session-1",
        device_id=None,
        authentication_strength=AuthenticationStrength.MFA,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=14),
        policy_version="1",
    )
    defaults.update(overrides)
    return SecurityContext(**defaults)  # type: ignore[arg-type]


def test_allows_when_everything_matches() -> None:
    result = AuthorizationEngine.check(
        security_context=_context(),
        required_permission="orders:read",
        resource_tenant_id="tenant-a",
        resource_organization_id="org-1",
        now=NOW,
    )
    assert result.allowed is True
    assert result.reason == "authorized"


def test_denies_on_expired_context() -> None:
    result = AuthorizationEngine.check(
        security_context=_context(),
        required_permission="orders:read",
        resource_tenant_id="tenant-a",
        resource_organization_id="org-1",
        now=NOW + timedelta(hours=1),
    )
    assert result.allowed is False
    assert result.reason == "security_context_expired"


def test_denies_on_tenant_mismatch() -> None:
    result = AuthorizationEngine.check(
        security_context=_context(),
        required_permission="orders:read",
        resource_tenant_id="tenant-b",
        resource_organization_id=None,
        now=NOW,
    )
    assert result.allowed is False
    assert result.reason == "tenant_mismatch"


def test_denies_on_organization_mismatch() -> None:
    result = AuthorizationEngine.check(
        security_context=_context(),
        required_permission="orders:read",
        resource_tenant_id="tenant-a",
        resource_organization_id="org-2",
        now=NOW,
    )
    assert result.allowed is False
    assert result.reason == "organization_mismatch"


def test_denies_on_missing_permission() -> None:
    result = AuthorizationEngine.check(
        security_context=_context(),
        required_permission="orders:delete",
        resource_tenant_id="tenant-a",
        resource_organization_id="org-1",
        now=NOW,
    )
    assert result.allowed is False
    assert result.reason == "permission_absent"


def test_denies_on_missing_role_when_role_required() -> None:
    result = AuthorizationEngine.check(
        security_context=_context(),
        required_permission="orders:read",
        resource_tenant_id="tenant-a",
        resource_organization_id="org-1",
        now=NOW,
        required_role="admin",
    )
    assert result.allowed is False
    assert result.reason == "role_absent"


def test_no_organization_scoped_resource_skips_org_check() -> None:
    """A resource with no organization scope (resource_organization_id=None)
    must not be denied purely for organization mismatch."""
    result = AuthorizationEngine.check(
        security_context=_context(organization_id=None),
        required_permission="orders:read",
        resource_tenant_id="tenant-a",
        resource_organization_id=None,
        now=NOW,
    )
    assert result.allowed is True
