"""
Correlation middleware.

Implements the request metadata contract from Document 9 Section 15
(REQUEST HEADERS / METADATA) and Section 69 (CORRELATION CONTRACT):
every request must carry / be assigned a request_id and correlation_id,
propagated to logs, traces, and downstream calls.

This middleware does NOT touch X-Tenant-ID / X-Organization-ID —
those are handled by the (not-yet-implemented) security-context
resolution middleware, which must validate them against the trusted
SecurityContext rather than trust them at face value (Document 9
Section 15, explicit warning).
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
CAUSATION_ID_HEADER = "X-Causation-ID"


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id
        causation_id = request.headers.get(CAUSATION_ID_HEADER)

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.causation_id = causation_id

        response = await call_next(request)

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
