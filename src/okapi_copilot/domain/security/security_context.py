"""
SecurityContext value object.

Source of truth: DOCUMENT 9 - GLOBAL ARCHITECTURE & INTEGRATION CONTRACT,
Section 16 (SECURITY CONTEXT CONTRACT).

Invariants enforced here (see also SKILL — Okapi Zero Trust & AI Security,
Section 3):

  - The SecurityContext MUST be server-generated. Nothing in this module
    parses untrusted input (headers, LLM output, agent output, event
    payloads) directly into a SecurityContext. Construction is the
    responsibility of a trusted application-layer service backed by the
    IdentityProvider port (application/ports/identity_provider.py) plus
    tenant/organization/membership resolution.
  - The object is immutable (frozen dataclass). There is no setter, no
    mutation method, no "with_role" / "with_tenant" convenience — any code
    that appears to "modify" a SecurityContext must instead construct a new
    one through the trusted issuance path, never by copying an existing one
    with elevated fields.
  - Nothing here decides authorization. This is a carrier of already-
    resolved identity/tenant/organization/session facts, not a decision
    engine. Authorization (ALLOW/DENY) belongs to the Policy Engine port.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class AuthenticationStrength(StrEnum):
    """Coarse authentication strength levels surfaced by Keycloak / IdP."""

    PASSWORD = "password"
    MFA = "mfa"
    DEVICE_BOUND = "device_bound"
    SERVICE_ACCOUNT = "service_account"


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """
    Immutable, server-issued security context.

    Fields mirror Document 9 Section 16 verbatim:
      context_id, user_id, tenant_id, organization_id, membership_id,
      roles, permissions_snapshot, profile_type, channel, session_id,
      device_id, authentication_strength, issued_at, expires_at,
      policy_version, context_version.
    """

    context_id: str
    user_id: str
    tenant_id: str
    organization_id: str | None
    membership_id: str | None
    roles: tuple[str, ...]
    permissions_snapshot: tuple[str, ...]
    profile_type: str
    channel: str
    session_id: str
    device_id: str | None
    authentication_strength: AuthenticationStrength
    issued_at: datetime
    expires_at: datetime
    policy_version: str
    context_version: str = field(default="1")

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """Pure check — callers are responsible for fail-closed handling."""
        reference = now or datetime.now(UTC)
        return reference >= self.expires_at

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions_snapshot

    def belongs_to_tenant(self, tenant_id: str) -> bool:
        return self.tenant_id == tenant_id

    def belongs_to_organization(self, organization_id: str) -> bool:
        return self.organization_id is not None and self.organization_id == organization_id
