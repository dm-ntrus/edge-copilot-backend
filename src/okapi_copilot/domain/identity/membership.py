"""
MembershipReference entity.

Document 10 Section 7: "La membership indique la relation entre
l'identite et un contexte metier. Elle ne remplace pas la source
d'autorite du SaaS." This is Copilot's own reference record of which
tenant/organization a user may act within — it informs tenant/
organization resolution (Document 3 Section 12-13) but is never itself
the authorization decision (that belongs to the Policy Engine).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class MembershipReference:
    membership_id: str
    user_id: str
    tenant_id: str
    organization_id: str | None
    role_references: tuple[str, ...]
    status: MembershipStatus
    valid_from: datetime
    valid_until: datetime | None

    def is_currently_valid(self, *, now: datetime) -> bool:
        if self.status is not MembershipStatus.ACTIVE:
            return False
        if now < self.valid_from:
            return False
        return not (self.valid_until is not None and now >= self.valid_until)
