"""
Keycloak-backed IdentityProvider adapter.

Implements Document 3 Section 9 steps 1-6 (receive token, validate
signature, validate issuer, validate audience, validate expiration,
resolve identity). Steps 7-8 (load memberships, construct
SecurityContext) are deliberately NOT done here — they belong to
`ResolveSecurityContext`, which composes this adapter with
`MembershipRepository`. Keeping them separate means this adapter can be
fully tested (and is, in
tests/unit/infrastructure/identity/test_keycloak_identity_provider.py)
without any membership store existing yet.

Fail-closed by construction: every failure path raises
`AuthorizationError` (or a subclass). There is no code path that
returns a "partially trusted" identity.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from jose import jwt
from jose.exceptions import JOSEError

from okapi_copilot.application.ports.identity_provider import AuthenticatedIdentity
from okapi_copilot.domain.errors import AuthorizationError
from okapi_copilot.domain.security.security_context import AuthenticationStrength

_MFA_ACR_MARKERS = {"mfa", "urn:mace:incommon:iap:silver"}


@dataclass(frozen=True, slots=True)
class _CachedJwks:
    keys: list[dict[str, object]]
    fetched_at: float


class KeycloakIdentityProvider:
    """
    Validates bearer tokens against a Keycloak realm's JWKS endpoint.

    `issuer_url` must be the realm issuer exactly as Keycloak sets it in
    the `iss` claim, e.g. `https://idp.example.com/realms/okapi`.
    """

    def __init__(
        self,
        *,
        issuer_url: str,
        audience: str,
        http_client: httpx.AsyncClient,
        jwks_cache_ttl_seconds: float = 600.0,
    ) -> None:
        self._issuer_url = issuer_url.rstrip("/")
        self._audience = audience
        self._http_client = http_client
        self._jwks_cache_ttl_seconds = jwks_cache_ttl_seconds
        self._jwks_cache: _CachedJwks | None = None

    @property
    def _jwks_uri(self) -> str:
        return f"{self._issuer_url}/protocol/openid-connect/certs"

    async def verify_token(self, bearer_token: str) -> AuthenticatedIdentity:
        try:
            unverified_header = jwt.get_unverified_header(bearer_token)
        except JOSEError as exc:
            raise AuthorizationError("Malformed bearer token.") from exc

        kid = unverified_header.get("kid")
        if kid is None:
            raise AuthorizationError("Bearer token is missing a key ID (kid).")

        key = await self._resolve_key(kid)
        if key is None:
            raise AuthorizationError("Bearer token key ID does not match any known signing key.")

        try:
            claims = jwt.decode(
                bearer_token,
                key,
                algorithms=[str(key.get("alg", "RS256"))],
                audience=self._audience,
                issuer=self._issuer_url,
                options={"require_exp": True, "require_iat": True},
            )
        except JOSEError as exc:
            # Signature, issuer, audience, and expiration are all
            # enforced by jose.jwt.decode above; any failure among them
            # surfaces here as a single fail-closed AuthorizationError.
            raise AuthorizationError(f"Bearer token failed verification: {exc}") from exc

        user_id = claims.get("sub")
        if not user_id:
            raise AuthorizationError("Bearer token is missing a subject (sub) claim.")

        session_id = claims.get("sid") or claims.get("session_state")
        if not session_id:
            raise AuthorizationError("Bearer token is missing a session identifier.")

        return AuthenticatedIdentity(
            user_id=user_id,
            authentication_strength=self._authentication_strength(claims),
            session_id=session_id,
            raw_claims=claims,
        )

    @staticmethod
    def _authentication_strength(claims: dict[str, object]) -> AuthenticationStrength:
        acr = str(claims.get("acr", ""))
        amr = claims.get("amr") or []
        if acr in _MFA_ACR_MARKERS or (isinstance(amr, list) and "mfa" in amr):
            return AuthenticationStrength.MFA
        if claims.get("client_id") and not claims.get("preferred_username"):
            return AuthenticationStrength.SERVICE_ACCOUNT
        return AuthenticationStrength.PASSWORD

    async def _resolve_key(self, kid: str) -> dict[str, object] | None:
        jwks = await self._get_jwks()
        for key in jwks:
            if key.get("kid") == kid:
                return key
        # Key not found could mean Keycloak rotated its signing keys —
        # force a single refetch before giving up, but never retry more
        # than once per call (no unbounded retry loop against an
        # untrusted/attacker-controlled kid).
        jwks = await self._get_jwks(force_refresh=True)
        for key in jwks:
            if key.get("kid") == kid:
                return key
        return None

    async def _get_jwks(self, *, force_refresh: bool = False) -> list[dict[str, object]]:
        now = time.monotonic()
        cache = self._jwks_cache
        if (
            not force_refresh
            and cache is not None
            and (now - cache.fetched_at) < self._jwks_cache_ttl_seconds
        ):
            return cache.keys

        response = await self._http_client.get(self._jwks_uri, timeout=5.0)
        response.raise_for_status()
        keys = response.json().get("keys", [])
        self._jwks_cache = _CachedJwks(keys=keys, fetched_at=now)
        return keys
