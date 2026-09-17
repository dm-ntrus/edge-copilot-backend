"""
Domain error hierarchy.

Per SKILL — Architecture Guardian / DDD & Hexagonal Architecture:
the domain must remain framework-independent. These exceptions carry
no dependency on FastAPI, HTTP status codes, or any transport concern.
Translation to HTTP (Document 9 §18 ERROR CONTRACT) happens exclusively
in interfaces/http.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level errors."""

    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(DomainError):
    """Raised when a domain invariant or value object constraint is violated."""

    code = "VALIDATION_ERROR"


class AuthorizationError(DomainError):
    """
    Raised when an operation is denied by a security/authorization decision.

    NOTE: this represents a DENY outcome surfaced to the domain/application
    layer. It is not itself the authorization mechanism — per Document 9 and
    the Zero-Trust skill, actual authorization decisions are made by the
    Policy Engine / Authorization port, never inferred here.
    """

    code = "AUTHORIZATION_DENIED"


class TenantIsolationError(AuthorizationError):
    """Raised when an operation would cross tenant boundaries."""

    code = "TENANT_ISOLATION_VIOLATION"


class OrganizationIsolationError(AuthorizationError):
    """Raised when an operation would cross organization boundaries."""

    code = "ORGANIZATION_ISOLATION_VIOLATION"


class StaleSecurityContextError(DomainError):
    """Raised when a SecurityContext has expired or its version is stale."""

    code = "STALE_SECURITY_CONTEXT"


class IdempotencyConflictError(DomainError):
    """Raised when a duplicate mutation is detected outside the allowed
    idempotency window/semantics (Document 9 Section 21)."""

    code = "IDEMPOTENCY_CONFLICT"


class UnknownExecutionStateError(DomainError):
    """
    Raised to force explicit reconciliation when an operation's outcome
    could not be determined (timeout, partial failure).

    Per the Distributed & Automation Engineering skill, this must NEVER be
    caught and silently retried it must trigger the
    query-state -> reconcile -> retry-if-safe sequence.
    """

    code = "UNKNOWN_EXECUTION_STATE"
