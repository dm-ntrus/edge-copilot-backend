"""
Identity & Trust domain (Document 10 Section 5-7, Document 3 Section 8).

Copilot references external identity without becoming the IAM owner:
`User` and `ChannelIdentity` are read-side reference entities. Copilot
does not create business identity arbitrarily.
"""

from okapi_copilot.domain.identity.channel_identity import (
    Channel,
    ChannelIdentity,
    VerificationStatus,
)
from okapi_copilot.domain.identity.membership import (
    MembershipReference,
    MembershipStatus,
)
from okapi_copilot.domain.identity.user import IdentityStatus, User

__all__ = [
    "User",
    "IdentityStatus",
    "ChannelIdentity",
    "Channel",
    "VerificationStatus",
    "MembershipReference",
    "MembershipStatus",
]
