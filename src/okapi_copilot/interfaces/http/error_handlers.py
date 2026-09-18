"""
Translates domain errors into the HTTP error contract.

Document 3 Section 73 (ERROR CONTRACT): every error response carries
error_code, message, category, request_id, correlation_id, retryable,
details. Document 3 Section 73 also says explicitly: never expose
internal sensitive details. Concretely: `details` is only ever the
structured, non-sensitive dict the raising code attached (e.g.
candidate tenant IDs for an ambiguity error) — for anything that maps
to 500 (a bug, not a handled domain condition), the client gets a
generic message and no `details`, and nothing about the original
exception's internals leaks into the response body.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from okapi_copilot.domain.errors import (
    AmbiguousTenantContextError,
    AuthorizationError,
    DomainError,
    IdempotencyConflictError,
    NoValidMembershipError,
    OrganizationIsolationError,
    StaleSecurityContextError,
    TenantIsolationError,
    UnknownExecutionStateError,
    ValidationError,
)


@dataclass(frozen=True, slots=True)
class _ErrorMapping:
    status: int
    category: str
    retryable: bool


_MAPPING_BY_ERROR: dict[type[DomainError], _ErrorMapping] = {
    ValidationError: _ErrorMapping(400, "validation", retryable=False),
    TenantIsolationError: _ErrorMapping(403, "authorization", retryable=False),
    OrganizationIsolationError: _ErrorMapping(403, "authorization", retryable=False),
    NoValidMembershipError: _ErrorMapping(403, "authorization", retryable=False),
    AuthorizationError: _ErrorMapping(403, "authorization", retryable=False),
    StaleSecurityContextError: _ErrorMapping(401, "authentication", retryable=True),
    AmbiguousTenantContextError: _ErrorMapping(409, "conflict", retryable=True),
    IdempotencyConflictError: _ErrorMapping(409, "conflict", retryable=False),
    UnknownExecutionStateError: _ErrorMapping(409, "conflict", retryable=True),
}

_DEFAULT_MAPPING = _ErrorMapping(500, "internal", retryable=False)


def _mapping_for(error: DomainError) -> _ErrorMapping:
    for error_type, mapping in _MAPPING_BY_ERROR.items():
        if isinstance(error, error_type):
            return mapping
    return _DEFAULT_MAPPING


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        correlation_id = getattr(request.state, "correlation_id", None)
        mapping = _mapping_for(exc)

        is_internal = mapping is _DEFAULT_MAPPING
        body = {
            "error": {
                "code": "INTERNAL_ERROR" if is_internal else exc.code,
                "message": "An internal error occurred." if is_internal else exc.message,
                "category": mapping.category,
                "request_id": request_id,
                "correlation_id": correlation_id,
                "retryable": mapping.retryable,
                "details": None if is_internal else (exc.details or None),
            }
        }
        return JSONResponse(status_code=mapping.status, content=body)
