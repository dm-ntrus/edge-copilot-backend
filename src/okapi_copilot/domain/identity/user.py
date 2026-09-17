"""
User reference entity.

Document 10 Section 5.1: "Copilot ne doit pas créer arbitrairement une
identité métier." This entity is a read-side reference to an identity
that Keycloak (or another IdP) already owns — Copilot never originates
a User on its own initiative from LLM/agent/event input.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class IdentityStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class User:
    user_id: str
    external_identity_id: str
    status: IdentityStatus
    created_at: datetime
    updated_at: datetime

    def is_usable(self) -> bool:
        """Whether this identity may currently be attached to a
        SecurityContext. Suspended/disabled users cannot authenticate,
        regardless of what any token or upstream system claims."""
        return self.status is IdentityStatus.ACTIVE
