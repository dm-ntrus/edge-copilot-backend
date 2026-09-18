"""
End-to-end test of the SecurityContext HTTP dependency: a real signed
JWT (real RSA crypto, real KeycloakIdentityProvider) goes in via the
Authorization header, a resolved SecurityContext comes out — using fake
MembershipRepository/PolicyEngine/Clock/IdGenerator so no real
SurrealDB/broker is needed to prove the wiring itself is correct.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwk, jwt

from okapi_copilot.application.use_cases.resolve_security_context import ResolveSecurityContext
from okapi_copilot.domain.identity.membership import MembershipReference, MembershipStatus
from okapi_copilot.infrastructure.identity.keycloak_identity_provider import (
    KeycloakIdentityProvider,
)
from okapi_copilot.interfaces.http.dependencies.security_context import (
    build_security_context_dependency,
)
from okapi_copilot.interfaces.http.error_handlers import register_error_handlers
from okapi_copilot.interfaces.http.middleware import CorrelationMiddleware

ISSUER = "https://idp.example.com/realms/okapi"
AUDIENCE = "okapi-copilot"
KID = "test-key-1"


class _FakeMembershipRepository:
    def __init__(self, memberships: tuple[MembershipReference, ...]) -> None:
        self._memberships = memberships

    async def list_by_user(self, user_id: str) -> tuple[MembershipReference, ...]:
        return tuple(m for m in self._memberships if m.user_id == user_id)


class _FakePolicyEngine:
    async def current_policy_version(self) -> str:
        return "policy-v1"

    async def authorize(self, **kwargs: object) -> None:  # pragma: no cover - unused
        raise NotImplementedError


class _FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _FixedIdGenerator:
    def new_id(self) -> str:
        return "ctx-fixed-id"


@pytest.fixture
def rsa_keypair() -> dict[str, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return {"private_key": private_key, "public_key": private_key.public_key()}


def _sign(rsa_keypair: dict[str, object], claims: dict[str, object]) -> str:
    private_key = rsa_keypair["private_key"]
    pem = private_key.private_bytes(  # type: ignore[attr-defined]
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": KID})


def _make_app(
    rsa_keypair: dict[str, object], memberships: tuple[MembershipReference, ...]
) -> FastAPI:
    public_jwk = jwk.construct(rsa_keypair["public_key"], algorithm="RS256").to_dict()
    public_jwk["kid"] = KID
    public_jwk["alg"] = "RS256"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"keys": [public_jwk]})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    identity_provider = KeycloakIdentityProvider(
        issuer_url=ISSUER, audience=AUDIENCE, http_client=http_client
    )

    now = datetime(2026, 1, 1, tzinfo=UTC)
    resolve_security_context = ResolveSecurityContext(
        identity_provider=identity_provider,
        membership_repository=_FakeMembershipRepository(memberships),
        policy_engine=_FakePolicyEngine(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(),
    )

    dependency = build_security_context_dependency(resolve_security_context)

    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)
    register_error_handlers(app)

    @app.get("/whoami")
    async def whoami(security_context=Depends(dependency)) -> dict[str, object]:  # noqa: B008
        return {
            "user_id": security_context.user_id,
            "tenant_id": security_context.tenant_id,
            "organization_id": security_context.organization_id,
        }

    return app


def _membership(**overrides: object) -> MembershipReference:
    defaults: dict[str, object] = dict(
        membership_id="m1",
        user_id="user-123",
        tenant_id="tenant-a",
        organization_id="org-1",
        role_references=("employee",),
        status=MembershipStatus.ACTIVE,
        valid_from=datetime(2025, 1, 1, tzinfo=UTC),
        valid_until=None,
    )
    defaults.update(overrides)
    return MembershipReference(**defaults)  # type: ignore[arg-type]


def _token_claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-123",
        "sid": "session-abc",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return claims


def test_valid_token_and_single_membership_resolves_security_context(
    rsa_keypair: dict[str, object],
) -> None:
    app = _make_app(rsa_keypair, (_membership(),))
    token = _sign(rsa_keypair, _token_claims())
    client = TestClient(app)

    response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-123",
        "tenant_id": "tenant-a",
        "organization_id": "org-1",
    }


def test_missing_authorization_header_is_rejected(rsa_keypair: dict[str, object]) -> None:
    app = _make_app(rsa_keypair, (_membership(),))
    client = TestClient(app)

    response = client.get("/whoami")

    assert response.status_code == 403
    assert response.json()["error"]["category"] == "authorization"


def test_malformed_authorization_header_is_rejected(rsa_keypair: dict[str, object]) -> None:
    app = _make_app(rsa_keypair, (_membership(),))
    client = TestClient(app)

    response = client.get("/whoami", headers={"Authorization": "Basic abc123"})

    assert response.status_code == 403


def test_invalid_token_is_rejected(rsa_keypair: dict[str, object]) -> None:
    app = _make_app(rsa_keypair, (_membership(),))
    client = TestClient(app)

    response = client.get("/whoami", headers={"Authorization": "Bearer not-a-real-jwt"})

    assert response.status_code == 403


def test_ambiguous_membership_surfaces_as_409_with_candidates(
    rsa_keypair: dict[str, object],
) -> None:
    memberships = (
        _membership(membership_id="m1", tenant_id="tenant-a", organization_id="org-1"),
        _membership(membership_id="m2", tenant_id="tenant-b", organization_id="org-9"),
    )
    app = _make_app(rsa_keypair, memberships)
    token = _sign(rsa_keypair, _token_claims())
    client = TestClient(app)

    response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 409
    body = response.json()["error"]
    assert body["code"] == "AMBIGUOUS_TENANT_CONTEXT"
    assert len(body["details"]["candidates"]) == 2


def test_explicit_tenant_header_narrows_ambiguity(rsa_keypair: dict[str, object]) -> None:
    """X-Tenant-ID is a narrowing hint only -- it must not by itself grant
    access to a tenant the identity has no membership in (covered by
    test_tenant_header_cannot_grant_unowned_tenant below); here it just
    resolves an otherwise-ambiguous set down to one."""
    memberships = (
        _membership(membership_id="m1", tenant_id="tenant-a", organization_id="org-1"),
        _membership(membership_id="m2", tenant_id="tenant-b", organization_id="org-9"),
    )
    app = _make_app(rsa_keypair, memberships)
    token = _sign(rsa_keypair, _token_claims())
    client = TestClient(app)

    response = client.get(
        "/whoami",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-b"},
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-b"


def test_tenant_header_cannot_grant_unowned_tenant(rsa_keypair: dict[str, object]) -> None:
    """The core security guarantee: an attacker-controlled X-Tenant-ID
    header cannot grant access to a tenant the authenticated identity has
    no real membership in (Document 9 Section 15)."""
    app = _make_app(rsa_keypair, (_membership(tenant_id="tenant-a"),))
    token = _sign(rsa_keypair, _token_claims())
    client = TestClient(app)

    response = client.get(
        "/whoami",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-victim"},
    )

    assert response.status_code == 403


def test_no_valid_membership_is_rejected(rsa_keypair: dict[str, object]) -> None:
    expired = _membership(valid_until=datetime(2025, 6, 1, tzinfo=UTC))
    app = _make_app(rsa_keypair, (expired,))
    token = _sign(rsa_keypair, _token_claims())
    client = TestClient(app)

    response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
