"""
Application entrypoint.

This module is intentionally thin: it wires together the interfaces/
application/infrastructure layers. It contains no business logic and
no security decisions of its own — those live in the domain and
application layers, invoked through ports.
"""

from __future__ import annotations

from fastapi import FastAPI

from okapi_copilot.config import get_settings
from okapi_copilot.infrastructure.observability import configure_logging
from okapi_copilot.interfaces.http.error_handlers import register_error_handlers
from okapi_copilot.interfaces.http.middleware import CorrelationMiddleware
from okapi_copilot.interfaces.http.routers import health_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.log_level)

    app = FastAPI(
        title="Okapi Copilot",
        version=settings.contract_version,
        # Full OpenAPI contract (Document 2 Section 6: API Contract = OpenAPI)
        # is served at the default /docs and /openapi.json in non-production
        # environments; production exposure policy is a follow-up decision.
    )

    app.add_middleware(CorrelationMiddleware)

    register_error_handlers(app)

    app.include_router(health_router)

    return app


app = create_app()
