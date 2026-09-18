from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from okapi_copilot.domain.policy.decision import PolicyDecisionOutcome
from okapi_copilot.domain.security.security_context import AuthenticationStrength, SecurityContext
from okapi_copilot.infrastructure.policy.default_policy_engine import DefaultPolicyEngine

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class _FixedClock:
    def now(self) -> datetime:
        return NOW


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


@pytest.mark.asyncio
async def test_returns_allow_record_with_versioning_fields() -> None:
    engine = DefaultPolicyEngine(
        policy_id="okapi-default", policy_version="v3", clock=_FixedClock()
    )

    record = await engine.authorize(
        security_context=_context(),
        action="orders.read",
        resource_type="order",
        resource_id="order-1",
        resource_tenant_id="tenant-a",
        resource_organization_id="org-1",
        required_permission="orders:read",
    )

    assert record.decision is PolicyDecisionOutcome.ALLOW
    assert record.decision.permits_immediate_execution is True
    assert record.policy_id == "okapi-default"
    assert record.policy_version == "v3"
    assert record.context_reference == "ctx-1"
    assert record.timestamp == NOW


@pytest.mark.asyncio
async def test_returns_deny_record_on_permission_absent() -> None:
    engine = DefaultPolicyEngine(clock=_FixedClock())

    record = await engine.authorize(
        security_context=_context(),
        action="orders.delete",
        resource_type="order",
        resource_id="order-1",
        resource_tenant_id="tenant-a",
        resource_organization_id="org-1",
        required_permission="orders:delete",
    )

    assert record.decision is PolicyDecisionOutcome.DENY
    assert record.decision.permits_immediate_execution is False
    assert record.reason == "permission_absent"


@pytest.mark.asyncio
async def test_current_policy_version_reflects_construction() -> None:
    engine = DefaultPolicyEngine(policy_version="v7")
    assert await engine.current_policy_version() == "v7"


@pytest.mark.asyncio
async def test_cross_tenant_attempt_is_denied() -> None:
    engine = DefaultPolicyEngine(clock=_FixedClock())

    record = await engine.authorize(
        security_context=_context(),
        action="orders.read",
        resource_type="order",
        resource_id="order-1",
        resource_tenant_id="tenant-attacker",
        resource_organization_id=None,
        required_permission="orders:read",
    )

    assert record.decision is PolicyDecisionOutcome.DENY
    assert record.reason == "tenant_mismatch"
