from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from okapi_copilot.domain.errors import (
    AmbiguousTenantContextError,
    TenantIsolationError,
    ValidationError,
)
from okapi_copilot.interfaces.http.error_handlers import register_error_handlers
from okapi_copilot.interfaces.http.middleware import CorrelationMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)
    register_error_handlers(app)

    @app.get("/boom/validation")
    async def boom_validation() -> None:
        raise ValidationError("bad input", details={"field": "amount"})

    @app.get("/boom/tenant")
    async def boom_tenant() -> None:
        raise TenantIsolationError("cross-tenant access denied")

    @app.get("/boom/ambiguous")
    async def boom_ambiguous() -> None:
        raise AmbiguousTenantContextError(
            "pick one", details={"candidates": [{"tenant_id": "a"}, {"tenant_id": "b"}]}
        )

    @app.get("/boom/unexpected")
    async def boom_unexpected() -> None:
        raise RuntimeError("some internal secret stack detail")

    return app


def test_validation_error_maps_to_400_with_full_contract() -> None:
    client = TestClient(_make_app())
    response = client.get("/boom/validation")

    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["category"] == "validation"
    assert body["retryable"] is False
    assert body["details"] == {"field": "amount"}
    assert body["request_id"]
    assert body["correlation_id"] == body["request_id"]


def test_tenant_isolation_error_maps_to_403() -> None:
    client = TestClient(_make_app())
    response = client.get("/boom/tenant")

    assert response.status_code == 403
    body = response.json()["error"]
    assert body["code"] == "TENANT_ISOLATION_VIOLATION"
    assert body["category"] == "authorization"
    assert body["retryable"] is False


def test_ambiguous_tenant_error_maps_to_409_and_is_retryable() -> None:
    client = TestClient(_make_app())
    response = client.get("/boom/ambiguous")

    assert response.status_code == 409
    body = response.json()["error"]
    assert body["code"] == "AMBIGUOUS_TENANT_CONTEXT"
    assert body["retryable"] is True
    assert len(body["details"]["candidates"]) == 2


def test_correlation_id_from_request_header_is_propagated_into_error_body() -> None:
    client = TestClient(_make_app())
    response = client.get("/boom/validation", headers={"X-Correlation-ID": "corr-xyz"})

    assert response.json()["error"]["correlation_id"] == "corr-xyz"


def test_unmapped_exception_type_would_bypass_this_handler() -> None:
    """
    RuntimeError is not a DomainError, so FastAPI's default handler (not
    ours) takes over and returns 500. This test documents that boundary:
    register_error_handlers only ever sees DomainError instances -- any
    non-domain exception must be turned into a DomainError before it
    reaches a router, or it will surface FastAPI's default 500 body
    instead of our sanitized contract.
    """
    client = TestClient(_make_app(), raise_server_exceptions=False)
    response = client.get("/boom/unexpected")

    assert response.status_code == 500
