"""
Tests for SurrealDbMembershipRepository.

IMPORTANT: these test query construction and row-mapping logic against
a fake connection object, NOT against a real SurrealDB server — no
SurrealDB instance is reachable from this environment. Wire-protocol
compatibility with a real server is UNVERIFIED (see client.py docstring
and README Known Gaps).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from okapi_copilot.domain.errors import ValidationError
from okapi_copilot.domain.identity.membership import MembershipStatus
from okapi_copilot.infrastructure.persistence.surrealdb.membership_repository import (
    SurrealDbMembershipRepository,
)


@dataclass
class _FakeQueryResponse:
    result: list[dict[str, Any]] = field(default_factory=list)


class _FakeConnection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.last_query: str | None = None
        self.last_variables: dict[str, Any] | None = None

    async def query(self, query: str, variables: dict[str, Any]) -> list[_FakeQueryResponse]:
        self.last_query = query
        self.last_variables = variables
        return [_FakeQueryResponse(result=self._rows)]


class _FakeClient:
    def __init__(self, connection: _FakeConnection) -> None:
        self._connection = connection

    async def connect(self) -> _FakeConnection:
        return self._connection


def _row(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "membership_id": "m1",
        "user_id": "user-1",
        "tenant_id": "tenant-a",
        "organization_id": "org-1",
        "role_references": ["employee"],
        "status": "active",
        "valid_from": "2026-01-01T00:00:00+00:00",
        "valid_until": None,
    }
    defaults.update(overrides)
    return defaults


@pytest.mark.asyncio
async def test_list_by_user_maps_rows_to_domain_entities() -> None:
    connection = _FakeConnection([_row()])
    repo = SurrealDbMembershipRepository(client=_FakeClient(connection))  # type: ignore[arg-type]

    memberships = await repo.list_by_user("user-1")

    assert len(memberships) == 1
    m = memberships[0]
    assert m.membership_id == "m1"
    assert m.tenant_id == "tenant-a"
    assert m.organization_id == "org-1"
    assert m.role_references == ("employee",)
    assert m.status is MembershipStatus.ACTIVE
    assert m.valid_from == datetime(2026, 1, 1, tzinfo=UTC)
    assert m.valid_until is None


@pytest.mark.asyncio
async def test_query_is_parameterized_not_interpolated() -> None:
    """Guards against a future regression that string-interpolates
    user_id into the SurrealQL query (injection risk)."""
    connection = _FakeConnection([])
    repo = SurrealDbMembershipRepository(client=_FakeClient(connection))  # type: ignore[arg-type]

    await repo.list_by_user("user'; DROP TABLE membership; --")

    assert connection.last_variables == {"user_id": "user'; DROP TABLE membership; --"}
    assert "DROP TABLE" not in (connection.last_query or "")
    assert "$user_id" in (connection.last_query or "")


@pytest.mark.asyncio
async def test_multiple_result_sets_are_flattened() -> None:
    connection = _FakeConnection([_row(membership_id="m1"), _row(membership_id="m2")])
    repo = SurrealDbMembershipRepository(client=_FakeClient(connection))  # type: ignore[arg-type]

    memberships = await repo.list_by_user("user-1")

    assert {m.membership_id for m in memberships} == {"m1", "m2"}


@pytest.mark.asyncio
async def test_malformed_row_raises_validation_error_not_crash() -> None:
    connection = _FakeConnection([{"membership_id": "m1"}])  # missing required fields
    repo = SurrealDbMembershipRepository(client=_FakeClient(connection))  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        await repo.list_by_user("user-1")


@pytest.mark.asyncio
async def test_no_organization_id_maps_to_none() -> None:
    connection = _FakeConnection([_row(organization_id=None)])
    repo = SurrealDbMembershipRepository(client=_FakeClient(connection))  # type: ignore[arg-type]

    memberships = await repo.list_by_user("user-1")

    assert memberships[0].organization_id is None
