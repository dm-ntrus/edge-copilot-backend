"""
ReplayGuard port.

Document 3 Section 16: "Replay protection". Backed by Redis (reference
stack, Section 59), used both for webhook replay protection and
message-level deduplication in the Input Gateway pipeline (Section 15).
"""

from __future__ import annotations

from typing import Protocol


class ReplayGuard(Protocol):
    async def check_and_record(self, key: str, *, ttl_seconds: int) -> bool:
        """
        Atomically check whether `key` has been seen before and record
        it if not.

        Returns True if this is the FIRST time `key` is seen (caller
        should proceed) and False if it is a replay/duplicate (caller
        must reject/skip). Implementations must make the check-and-set
        atomic — a check-then-set done as two separate operations would
        reopen exactly the race this port exists to close.
        """
        ...
