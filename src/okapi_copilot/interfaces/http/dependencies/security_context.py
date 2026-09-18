"""
SecurityContext HTTP dependency.

This is the ONLY place in `interfaces/http` allowed to construct a
`SecurityContext` from a request — it does so exclusively by calling
`ResolveSecurityContext.execute`, never by reading headers directly
into a context.

Deliberately implemented as a FastAPI dependency (not a middleware)
so it can be applied per-route rather than globally: not every route
needs a resolved SecurityContext (health checks, for instance, must
not require one), and Document 9 Section 15's warning about
X-Tenant-ID/X-Organization-ID only matters for routes that actually
resolve one.

`X-Tenant-ID` / `X-Organization-ID` request headers, if present, are
passed through to `ResolveSecurityContext` as *explicit selection
hints* only (`requested_tenant_id` / `requested_organization_id`) --
exactly the narrowing input the use case already treats as
non-authoritative. They can only ever narrow an ambiguous set of
memberships the identity actually has; they cannot grant one it
doesn't.

NOT WIRED into `main.py`'s routes by default (see README Known Gaps):
`MembershipRepository` (SurrealDB) has not been verified against a
live server, and `KeycloakIdentityProvider` needs a real issuer/JWKS
endpoint. Wiring this in front of a route today would require both.
This module is ready to be composed once those are confirmed live —
see `build_security_context_dependency` for how.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Header, Request

from okapi_copilot.application.use_cases.resolve_security_context import (
    ResolveSecurityContext,
    ResolveSecurityContextRequest,
)
from okapi_copilot.domain.errors import AuthorizationError
from okapi_copilot.domain.security.security_context import SecurityContext

_BEARER_PREFIX = "Bearer "


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None or not authorization.startswith(_BEARER_PREFIX):
        raise AuthorizationError("Missing or malformed Authorization header.")
    token = authorization[len(_BEARER_PREFIX) :].strip()
    if not token:
        raise AuthorizationError("Missing or malformed Authorization header.")
    return token


def build_security_context_dependency(
    resolve_security_context: ResolveSecurityContext,
    *,
    profile_type: str = "employee",
) -> Callable[..., Awaitable[SecurityContext]]:
    """
    Returns a FastAPI dependency callable that resolves a
    `SecurityContext` for the current request.

    `resolve_security_context` must be constructed with real adapters
    (KeycloakIdentityProvider, SurrealDbMembershipRepository,
    DefaultPolicyEngine) by the caller — this function only wires the
    HTTP-shaped inputs (headers) into the use case's request shape.
    """

    async def dependency(
        request: Request,
        authorization: str | None = Header(default=None),
        x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
        x_organization_id: str | None = Header(default=None, alias="X-Organization-ID"),
        x_device_id: str | None = Header(default=None, alias="X-Device-ID"),
    ) -> SecurityContext:
        token = _extract_bearer_token(authorization)
        channel = getattr(request.state, "channel", "web")

        context = await resolve_security_context.execute(
            ResolveSecurityContextRequest(
                bearer_token=token,
                channel=channel,
                profile_type=profile_type,
                requested_tenant_id=x_tenant_id,
                requested_organization_id=x_organization_id,
                device_id=x_device_id,
            )
        )
        request.state.security_context = context
        return context

    return dependency
