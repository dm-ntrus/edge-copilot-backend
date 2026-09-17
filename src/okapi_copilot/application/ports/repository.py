"""
Generic repository port.

Kept intentionally minimal/generic here; concrete aggregates will define
their own repository protocols (e.g. `WorkflowRunRepository`) as those
aggregates are introduced in later phases. This module exists so the
directory contract (application/ports/repository.py) is established from
day one, per SKILL — DDD & Hexagonal Architecture.

Per Document 9 Section 29/30: repositories talk to Copilot's OWN
persistence (SurrealDB by reference stack). They never provide a path to
a SaaS product's private database — that access goes through API / MCP /
events / contracted integration only.
"""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

T = TypeVar("T")
ID = TypeVar("ID", contravariant=True)


class Repository(Protocol, Generic[T, ID]):
    async def get_by_id(self, entity_id: ID, *, tenant_id: str) -> T | None:
        """Every lookup is tenant-scoped by construction — there is no
        variant of get_by_id that omits tenant_id."""
        ...

    async def save(self, entity: T, *, tenant_id: str) -> None:
        ...
