"""
Health endpoints.

Intentionally unauthenticated and free of any business/tenant logic —
these exist purely for orchestrator liveness/readiness probes
(Docker/Kubernetes, per Document 2 Section 6). Readiness will be
extended to check downstream dependencies (SurrealDB, Redis, broker)
once those adapters exist; until then it reports "not_wired" rather
than fabricating a healthy status the system cannot back up
(SKILL — Production Audit, Section 23: NO FALSE CERTIFICATION).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict[str, object]:
    return {
        "status": "not_wired",
        "dependencies": {
            "surrealdb": "not_wired",
            "redis": "not_wired",
            "broker": "not_wired",
            "keycloak": "not_wired",
        },
    }
