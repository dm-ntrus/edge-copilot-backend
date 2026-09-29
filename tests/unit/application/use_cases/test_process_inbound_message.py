from __future__ import annotations

from datetime import UTC, datetime

import pytest

from okapi_copilot.application.use_cases.process_inbound_message import (
    ProcessInboundMessage,
    ProcessInboundMessageRequest,
)
from okapi_copilot.domain.conversation.conversation import Conversation, ConversationState
from okapi_copilot.domain.errors import (
    IdempotencyConflictError,
    UnknownChannelIdentityError,
    ValidationError,
)
from okapi_copilot.domain.gateway.webhook_security import WebhookValidationResult
from okapi_copilot.domain.identity.channel_identity import (
    Channel,
    ChannelIdentity,
    VerificationStatus,
)
from okapi_copilot.domain.identity.user import IdentityStatus
from okapi_copilot.domain.messaging.message import MessageState

NOW = datetime(2026, 1, 1, tzinfo=UTC)

KNOWN_IDENTITY = ChannelIdentity(
    channel_identity_id="ci-1",
    user_id="user-1",
    channel=Channel.WHATSAPP,
    provider="whatsapp-business",
    provider_subject_id="+15551234",
    phone_hash="hash",
    encrypted_contact=None,
    verification_status=VerificationStatus.VERIFIED,
    verified_at=NOW,
    status=IdentityStatus.ACTIVE,
    created_at=NOW,
    updated_at=NOW,
)


class _FakeChannelIdentityRepository:
    def __init__(self, identities: tuple[ChannelIdentity, ...]) -> None:
        self._identities = identities

    async def find_by_provider_subject(
        self, *, channel: Channel, provider: str, provider_subject_id: str
    ) -> ChannelIdentity | None:
        for identity in self._identities:
            if (
                identity.channel == channel
                and identity.provider == provider
                and identity.provider_subject_id == provider_subject_id
            ):
                return identity
        return None


class _FakeConversationRepository:
    def __init__(self, existing: Conversation | None = None) -> None:
        self._existing = existing
        self.saved: list[Conversation] = []

    async def find_active_for_channel_identity(
        self, channel_identity_id: str
    ) -> Conversation | None:
        return self._existing

    async def save(self, conversation: Conversation) -> None:
        self.saved.append(conversation)


class _FakeReplayGuard:
    def __init__(self, *, always_first: bool = True) -> None:
        self._always_first = always_first
        self._seen: set[str] = set()

    async def check_and_record(self, key: str, *, ttl_seconds: int) -> bool:
        if self._always_first:
            return True
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


class _FixedClock:
    def now(self) -> datetime:
        return NOW


class _SequentialIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self) -> str:
        self._counter += 1
        return f"id-{self._counter}"


def _request(**overrides: object) -> ProcessInboundMessageRequest:
    defaults: dict[str, object] = dict(
        channel=Channel.WHATSAPP,
        provider="whatsapp-business",
        provider_subject_id="+15551234",
        provider_message_id="wamid.abc",
        content="Hello there",
        received_at=NOW,
        correlation_id="corr-1",
        tenant_id="tenant-a",
    )
    defaults.update(overrides)
    return ProcessInboundMessageRequest(**defaults)  # type: ignore[arg-type]


def _use_case(
    *,
    identities: tuple[ChannelIdentity, ...] = (KNOWN_IDENTITY,),
    existing_conversation: Conversation | None = None,
    replay_guard: object | None = None,
) -> tuple[ProcessInboundMessage, _FakeConversationRepository]:
    conversation_repo = _FakeConversationRepository(existing_conversation)
    use_case = ProcessInboundMessage(
        channel_identity_repository=_FakeChannelIdentityRepository(identities),
        conversation_repository=conversation_repo,
        replay_guard=replay_guard or _FakeReplayGuard(),
        clock=_FixedClock(),
        id_generator=_SequentialIdGenerator(),
    )
    return use_case, conversation_repo


@pytest.mark.asyncio
async def test_full_pipeline_creates_new_conversation() -> None:
    use_case, conversation_repo = _use_case()

    result = await use_case.execute(_request())

    assert result.message.status is MessageState.CONTEXTUALIZED
    assert result.conversation.state is ConversationState.ACTIVE
    assert result.message.conversation_id == result.conversation.conversation_id
    assert len(conversation_repo.saved) == 1


@pytest.mark.asyncio
async def test_reuses_existing_active_conversation() -> None:
    existing = Conversation(
        conversation_id="existing-conv",
        tenant_id="tenant-a",
        organization_id=None,
        channel="whatsapp",
        state=ConversationState.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )
    use_case, conversation_repo = _use_case(existing_conversation=existing)

    result = await use_case.execute(_request())

    assert result.conversation.conversation_id == "existing-conv"
    assert conversation_repo.saved == []  # no new conversation created


@pytest.mark.asyncio
async def test_empty_content_is_rejected() -> None:
    use_case, _ = _use_case()
    with pytest.raises(ValidationError):
        await use_case.execute(_request(content="   "))


@pytest.mark.asyncio
async def test_failed_webhook_authentication_is_rejected() -> None:
    use_case, _ = _use_case()
    with pytest.raises(ValidationError):
        await use_case.execute(
            _request(
                webhook_validation=WebhookValidationResult(False, "invalid_signature")
            )
        )


@pytest.mark.asyncio
async def test_valid_webhook_authentication_passes() -> None:
    use_case, _ = _use_case()
    result = await use_case.execute(
        _request(webhook_validation=WebhookValidationResult(True, "valid"))
    )
    assert result.message.status is MessageState.CONTEXTUALIZED


@pytest.mark.asyncio
async def test_unknown_sender_is_rejected_never_auto_provisioned() -> None:
    use_case, conversation_repo = _use_case(identities=())

    with pytest.raises(UnknownChannelIdentityError):
        await use_case.execute(_request())

    assert conversation_repo.saved == []


@pytest.mark.asyncio
async def test_duplicate_provider_message_is_rejected() -> None:
    replay_guard = _FakeReplayGuard(always_first=False)
    use_case, _ = _use_case(replay_guard=replay_guard)

    first = await use_case.execute(_request())
    assert first.message.status is MessageState.CONTEXTUALIZED

    with pytest.raises(IdempotencyConflictError):
        await use_case.execute(_request())
