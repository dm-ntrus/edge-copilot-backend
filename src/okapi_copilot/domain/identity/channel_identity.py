"""
ChannelIdentity entity.

Document 10 Section 6, invariant: `ChannelIdentity != User`. A phone
number, WhatsApp handle, or other channel-side identifier is never
itself a business authorization ("Un numero WhatsApp n'est jamais une
autorisation metier").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from okapi_copilot.domain.identity.user import IdentityStatus


class Channel(StrEnum):
    WHATSAPP = "whatsapp"
    WEB = "web"
    MOBILE = "mobile"
    VOICE = "voice"
    API = "api"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"


@dataclass(frozen=True, slots=True)
class ChannelIdentity:
    channel_identity_id: str
    user_id: str
    channel: Channel
    provider: str
    provider_subject_id: str
    phone_hash: str | None
    encrypted_contact: str | None
    verification_status: VerificationStatus
    verified_at: datetime | None
    status: IdentityStatus
    created_at: datetime
    updated_at: datetime

    def grants_no_authority(self) -> bool:
        """
        Always True. Exists as an explicit, testable statement of the
        Document 10 invariant so that no future code path can be written
        to treat a verified channel identity as sufficient for
        authorization — verification proves reachability, not permission.
        """
        return True
