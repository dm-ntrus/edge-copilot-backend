"""ID generation port — decouples the choice of ID scheme (UUIDv7, ULID,
snowflake, ...) from domain/application code."""

from __future__ import annotations

from typing import Protocol


class IdGenerator(Protocol):
    def new_id(self) -> str:
        """Generate a new globally-unique identifier."""
        ...
