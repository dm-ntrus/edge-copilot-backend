from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from okapi_copilot.domain.security.security_context import (
    AuthenticationStrength,
    SecurityContext,
)


@pytest.fixture
def valid_security_context() -> SecurityContext:
    now = datetime.now(UTC)
    return SecurityContext(
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
        issued_at=now,
        expires_at=now + timedelta(minutes=15),
        policy_version="1",
    )
