"""
Redis-backed ReplayGuard.

Implements `application.ports.replay_guard.ReplayGuard` using Redis's
`SET key value NX EX ttl` — a single atomic command, so there is no
check-then-set race window between two separate calls.

NOTE (honesty, same as the SurrealDB adapter): this has not been
exercised against a running Redis server in this codebase's test
suite — no Redis instance is reachable from the environment this code
was written in. The atomicity argument above is a property of the
`SET NX` command itself (documented Redis behavior), not something
this test suite has verified end-to-end. Treat this as UNVERIFIED
until run against `docker compose up redis` or a real deployment.
"""

from __future__ import annotations

from typing import Protocol


class _RedisLike(Protocol):
    async def set(
        self, name: str, value: str, *, nx: bool = False, ex: int | None = None
    ) -> bool | None: ...


class RedisReplayGuard:
    def __init__(self, redis_client: _RedisLike) -> None:
        self._redis = redis_client

    async def check_and_record(self, key: str, *, ttl_seconds: int) -> bool:
        result = await self._redis.set(key, "1", nx=True, ex=ttl_seconds)
        # redis-py returns True on success (key was set, i.e. first time
        # seen) and None when NX prevented the set (key already existed,
        # i.e. a replay).
        return bool(result)
