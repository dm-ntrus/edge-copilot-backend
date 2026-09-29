"""
Tests for RedisReplayGuard.

Against a fake client, not a real Redis server — see the adapter's
docstring for the honesty note on why (no Redis reachable from this
environment). These tests verify the adapter calls SET with the right
NX/EX semantics and interprets the return value correctly; they do not
prove Redis itself behaves atomically (that is documented Redis
behavior, not something this suite can observe).
"""

from __future__ import annotations

import pytest

from okapi_copilot.infrastructure.persistence.redis.replay_guard import RedisReplayGuard


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self.last_call: dict[str, object] | None = None

    async def set(
        self, name: str, value: str, *, nx: bool = False, ex: int | None = None
    ) -> bool | None:
        self.last_call = {"name": name, "value": value, "nx": nx, "ex": ex}
        if nx and name in self._store:
            return None
        self._store[name] = value
        return True


@pytest.mark.asyncio
async def test_first_occurrence_returns_true() -> None:
    guard = RedisReplayGuard(_FakeRedis())
    result = await guard.check_and_record("webhook:evt-1", ttl_seconds=300)
    assert result is True


@pytest.mark.asyncio
async def test_second_occurrence_of_same_key_returns_false() -> None:
    redis = _FakeRedis()
    guard = RedisReplayGuard(redis)

    first = await guard.check_and_record("webhook:evt-1", ttl_seconds=300)
    second = await guard.check_and_record("webhook:evt-1", ttl_seconds=300)

    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_different_keys_are_independent() -> None:
    guard = RedisReplayGuard(_FakeRedis())
    a = await guard.check_and_record("webhook:evt-a", ttl_seconds=300)
    b = await guard.check_and_record("webhook:evt-b", ttl_seconds=300)
    assert a is True
    assert b is True


@pytest.mark.asyncio
async def test_uses_nx_and_ttl() -> None:
    redis = _FakeRedis()
    guard = RedisReplayGuard(redis)

    await guard.check_and_record("webhook:evt-1", ttl_seconds=42)

    assert redis.last_call == {"name": "webhook:evt-1", "value": "1", "nx": True, "ex": 42}
