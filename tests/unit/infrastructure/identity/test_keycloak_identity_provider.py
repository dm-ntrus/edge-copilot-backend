"""
Tests for KeycloakIdentityProvider.

These use a real RSA keypair and a real signed JWT (via python-jose) so
that signature/issuer/audience/expiry verification is genuinely
exercised, not mocked away. Only the HTTP transport for fetching the
JWKS document is faked (via httpx.MockTransport) — the cryptographic
verification path is real.
"""

from __future__ import annotations

import time

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from jose import jwk, jwt

from okapi_copilot.domain.errors import AuthorizationError
from okapi_copilot.domain.security.security_context import AuthenticationStrength
from okapi_copilot.infrastructure.identity.keycloak_identity_provider import (
    KeycloakIdentityProvider,
)

ISSUER = "https://idp.example.com/realms/okapi"
AUDIENCE = "okapi-copilot"
KID = "test-key-1"


@pytest.fixture(scope="module")
def rsa_keypair() -> dict[str, object]:
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return {"private_key": private_key, "public_key": private_key.public_key()}


def _public_jwk(rsa_keypair: dict[str, object]) -> dict[str, object]:
    public_key = rsa_keypair["public_key"]
    jwk_dict = jwk.construct(public_key, algorithm="RS256").to_dict()
    jwk_dict["kid"] = KID
    jwk_dict["alg"] = "RS256"
    jwk_dict["use"] = "sig"
    return jwk_dict


def _to_pem(private_key: object) -> bytes:
    return private_key.private_bytes(  # type: ignore[attr-defined]
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _sign(rsa_keypair: dict[str, object], claims: dict[str, object]) -> str:
    pem = _to_pem(rsa_keypair["private_key"])
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": KID})


def _make_provider(rsa_keypair: dict[str, object]) -> KeycloakIdentityProvider:
    jwks_document = {"keys": [_public_jwk(rsa_keypair)]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=jwks_document)

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return KeycloakIdentityProvider(
        issuer_url=ISSUER, audience=AUDIENCE, http_client=http_client
    )


def _base_claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-123",
        "sid": "session-abc",
        "iat": now,
        "exp": now + 300,
        "acr": "1",
    }
    claims.update(overrides)
    return claims


@pytest.mark.asyncio
async def test_valid_token_is_accepted(rsa_keypair: dict[str, object]) -> None:
    provider = _make_provider(rsa_keypair)
    token = _sign(rsa_keypair, _base_claims())

    identity = await provider.verify_token(token)

    assert identity.user_id == "user-123"
    assert identity.session_id == "session-abc"
    assert identity.authentication_strength == AuthenticationStrength.PASSWORD


@pytest.mark.asyncio
async def test_mfa_acr_is_detected(rsa_keypair: dict[str, object]) -> None:
    provider = _make_provider(rsa_keypair)
    token = _sign(rsa_keypair, _base_claims(acr="mfa"))

    identity = await provider.verify_token(token)

    assert identity.authentication_strength == AuthenticationStrength.MFA


@pytest.mark.asyncio
async def test_expired_token_is_rejected(rsa_keypair: dict[str, object]) -> None:
    provider = _make_provider(rsa_keypair)
    now = int(time.time())
    token = _sign(rsa_keypair, _base_claims(iat=now - 600, exp=now - 300))

    with pytest.raises(AuthorizationError):
        await provider.verify_token(token)


@pytest.mark.asyncio
async def test_wrong_audience_is_rejected(rsa_keypair: dict[str, object]) -> None:
    provider = _make_provider(rsa_keypair)
    token = _sign(rsa_keypair, _base_claims(aud="some-other-service"))

    with pytest.raises(AuthorizationError):
        await provider.verify_token(token)


@pytest.mark.asyncio
async def test_wrong_issuer_is_rejected(rsa_keypair: dict[str, object]) -> None:
    provider = _make_provider(rsa_keypair)
    token = _sign(rsa_keypair, _base_claims(iss="https://attacker.example.com/realms/evil"))

    with pytest.raises(AuthorizationError):
        await provider.verify_token(token)


@pytest.mark.asyncio
async def test_token_signed_by_untrusted_key_is_rejected(rsa_keypair: dict[str, object]) -> None:
    """A token signed by a DIFFERENT keypair than the one published in the
    JWKS must be rejected even if every claim looks valid."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    provider = _make_provider(rsa_keypair)
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = _to_pem(attacker_key)
    forged_token = jwt.encode(_base_claims(), pem, algorithm="RS256", headers={"kid": KID})

    with pytest.raises(AuthorizationError):
        await provider.verify_token(forged_token)


@pytest.mark.asyncio
async def test_missing_sub_claim_is_rejected(rsa_keypair: dict[str, object]) -> None:
    provider = _make_provider(rsa_keypair)
    claims = _base_claims()
    del claims["sub"]
    token = _sign(rsa_keypair, claims)

    with pytest.raises(AuthorizationError):
        await provider.verify_token(token)


@pytest.mark.asyncio
async def test_malformed_token_is_rejected(rsa_keypair: dict[str, object]) -> None:
    provider = _make_provider(rsa_keypair)

    with pytest.raises(AuthorizationError):
        await provider.verify_token("not-a-jwt-at-all")


@pytest.mark.asyncio
async def test_unknown_kid_is_rejected(rsa_keypair: dict[str, object]) -> None:
    provider = _make_provider(rsa_keypair)
    pem = _to_pem(rsa_keypair["private_key"])
    token = jwt.encode(_base_claims(), pem, algorithm="RS256", headers={"kid": "does-not-exist"})

    with pytest.raises(AuthorizationError):
        await provider.verify_token(token)
