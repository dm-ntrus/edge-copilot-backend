"""
IdentityProvider port.

Abstracts Keycloak (Document 9 Section 12 KEYCLOAK CONTRACT). Keycloak
supplies AUTHENTICATION, IDENTITY, SESSION and AUTHENTICATION STRENGTH
only — never business authorization (Document 9 Section 13 DOUBLE
AUTHORIZATION; Instructions Section 9 AUTHENTICATION != AUTHORIZATION).

The application layer uses this port to validate a bearer token and
obtain raw identity facts. Turning those facts into a SecurityContext
(with tenant/organization/membership resolution) is a separate,
explicit application-layer step — never done implicitly inside an
adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from okapi_copilot.domain.security.security_context import AuthenticationStrength


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    """Raw identity facts returned by the IdP, prior to tenant/org resolution."""

    user_id: str
    authentication_strength: AuthenticationStrength
    session_id: str
    raw_claims: dict[str, object]


class IdentityProvider(Protocol):
    async def verify_token(self, bearer_token: str) -> AuthenticatedIdentity:
        """
        Validate a bearer token and return the authenticated identity.

        Must raise a domain-level AuthorizationError (or subclass) on any
        invalid, expired, or malformed token. Never returns a partially
        trusted identity.
        """
        ...
