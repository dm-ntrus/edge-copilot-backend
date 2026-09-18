"""
SurrealDB-backed MembershipRepository.

Implements `application.ports.membership_repository.MembershipRepository`
against a `membership` table in Copilot's own SurrealDB database (never
a SaaS product's database — Document 9 Section 29).

Query is parameterized ($user_id) to avoid injection; SurrealQL string
interpolation of untrusted input is never used here.

See `client.py` for the honesty note on SurrealDB connectivity being
unverified against a live server in this environment.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from okapi_copilot.domain.errors import ValidationError
from okapi_copilot.domain.identity.membership import MembershipReference, MembershipStatus
from okapi_copilot.infrastructure.persistence.surrealdb.client import SurrealDbClient

_TABLE = "membership"


class _QueryResponseLike(Protocol):
    result: list[dict[str, Any]]


class _SurrealConnectionLike(Protocol):
    async def query(
        self, query: str, variables: dict[str, Any]
    ) -> list[_QueryResponseLike]: ...


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValidationError(f"Unrecognized datetime value from persistence: {value!r}")


def _row_to_membership(row: dict[str, Any]) -> MembershipReference:
    try:
        return MembershipReference(
            membership_id=str(row["membership_id"]),
            user_id=str(row["user_id"]),
            tenant_id=str(row["tenant_id"]),
            organization_id=(
                str(row["organization_id"]) if row.get("organization_id") is not None else None
            ),
            role_references=tuple(row.get("role_references") or ()),
            status=MembershipStatus(row["status"]),
            valid_from=_parse_datetime(row["valid_from"]) or datetime.min,
            valid_until=_parse_datetime(row.get("valid_until")),
        )
    except KeyError as exc:
        raise ValidationError(
            f"Membership row from persistence is missing required field: {exc}",
            details={"row": row},
        ) from exc


class SurrealDbMembershipRepository:
    def __init__(self, client: SurrealDbClient) -> None:
        self._client = client

    async def list_by_user(self, user_id: str) -> tuple[MembershipReference, ...]:
        connection = await self._client.connect()
        responses = await connection.query(
            f"SELECT * FROM {_TABLE} WHERE user_id = $user_id",
            {"user_id": user_id},
        )
        rows: list[dict[str, Any]] = []
        for response in responses:
            rows.extend(response.result)
        return tuple(_row_to_membership(row) for row in rows)
