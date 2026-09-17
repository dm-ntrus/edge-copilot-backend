from __future__ import annotations

from datetime import UTC, datetime, timedelta

from okapi_copilot.domain.identity.channel_identity import (
    Channel,
    ChannelIdentity,
    VerificationStatus,
)
from okapi_copilot.domain.identity.membership import MembershipReference, MembershipStatus
from okapi_copilot.domain.identity.user import IdentityStatus, User


def test_user_is_usable_only_when_active() -> None:
    now = datetime.now(UTC)
    active = User(
        user_id="u1", external_identity_id="ext-1", status=IdentityStatus.ACTIVE,
        created_at=now, updated_at=now,
    )
    suspended = User(
        user_id="u1", external_identity_id="ext-1", status=IdentityStatus.SUSPENDED,
        created_at=now, updated_at=now,
    )
    assert active.is_usable() is True
    assert suspended.is_usable() is False


def test_channel_identity_never_grants_authority() -> None:
    now = datetime.now(UTC)
    identity = ChannelIdentity(
        channel_identity_id="ci-1",
        user_id="u1",
        channel=Channel.WHATSAPP,
        provider="whatsapp-business",
        provider_subject_id="+000000000",
        phone_hash="hash",
        encrypted_contact=None,
        verification_status=VerificationStatus.VERIFIED,
        verified_at=now,
        status=IdentityStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    assert identity.grants_no_authority() is True


def test_membership_valid_window() -> None:
    now = datetime.now(UTC)
    membership = MembershipReference(
        membership_id="m1",
        user_id="u1",
        tenant_id="tenant-a",
        organization_id="org-1",
        role_references=("employee",),
        status=MembershipStatus.ACTIVE,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
    )
    assert membership.is_currently_valid(now=now) is True
    assert membership.is_currently_valid(now=now + timedelta(days=2)) is False
    assert membership.is_currently_valid(now=now - timedelta(days=2)) is False


def test_membership_invalid_when_not_active_status() -> None:
    now = datetime.now(UTC)
    membership = MembershipReference(
        membership_id="m1",
        user_id="u1",
        tenant_id="tenant-a",
        organization_id="org-1",
        role_references=("employee",),
        status=MembershipStatus.REVOKED,
        valid_from=now - timedelta(days=1),
        valid_until=None,
    )
    assert membership.is_currently_valid(now=now) is False


def test_membership_with_no_end_date_stays_valid() -> None:
    now = datetime.now(UTC)
    membership = MembershipReference(
        membership_id="m1",
        user_id="u1",
        tenant_id="tenant-a",
        organization_id=None,
        role_references=(),
        status=MembershipStatus.ACTIVE,
        valid_from=now - timedelta(days=365),
        valid_until=None,
    )
    assert membership.is_currently_valid(now=now + timedelta(days=3650)) is True
