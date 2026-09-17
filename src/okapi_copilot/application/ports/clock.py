"""Clock port — the domain/application layer never calls datetime.now()
directly so that time is deterministic and testable."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current UTC time."""
        ...
