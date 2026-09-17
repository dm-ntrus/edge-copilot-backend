"""
Translates domain errors into the HTTP error contract.

Domain exceptions (okapi_copilot.domain.errors) never leak stack traces
or internal details to the client (Instructions Section 17: NEVER
retourner des stack traces). This is the ONLY place that maps a domain
error code to an HTTP status code — the mapping itself lives here, not
scattered across routers.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from okapi_copilot.domain.errors import (
    AuthorizationError,
    DomainError,
    IdempotencyConflictError,
    OrganizationIsolationError,
    TenantIsolationError,
    UnknownExecutionStateError,
    ValidationError,
)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    ValidationError: 400,
    AuthorizationError: 403,
    TenantIsolationError: 403,
    OrganizationIsolationError: 403,
    IdempotencyConflictError: 409,
    UnknownExecutionStateError: 409,
}


def _status_for(error: DomainError) -> int:
    for error_type, status in _STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return status
    return 500


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=_status_for(exc),
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                }
            },
        )
