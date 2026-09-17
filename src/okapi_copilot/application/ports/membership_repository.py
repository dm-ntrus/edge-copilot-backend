"""
MembershipRepository port.

Backed by Copilot's own persistence (SurrealDB per the reference stack),
NOT by a SaaS product's private database (Document 9 Section 29:
DIRECT DATABASE ACCESS FORBIDDEN). This is Copilot's own reference copy
of "which tenant/organization can this user act within", kept in sync
via API/MCP/events per the Global Architecture & Integration Contract —
never queried directly against a product's database.
"""

from __future__ import annotations

from typing import Protocol

from okapi_copilot.domain.identity.membership import MembershipReference


class MembershipRepository(Protocol):
    async def list_by_user(self, user_id: str) -> tuple[MembershipReference, ...]:
        """Return all membership references for a user, active or not —
        validity filtering is the caller's (use case's) responsibility so
        the "as of when" decision stays explicit and testable."""
        ...
