"""
ProcessInboundMessage use case — the Input Gateway pipeline.

Document 3 Section 15:

    Receive -> Authenticate source where applicable -> Validate ->
    Normalize -> Deduplicate -> Identify -> Contextualize

"Aucune requête ne doit atteindre le LLM directement" — this use case's
entire purpose is to be the mandatory checkpoint between raw inbound
input and anything LLM/agent-facing. Nothing downstream of this use
case should ever accept a raw webhook/channel payload directly.

Step-by-step mapping:
  - Receive: the caller already did this (raw payload arrives as
    `ProcessInboundMessageRequest`).
  - Authenticate source: `webhook_validation`, when the channel is
    webhook-based, must be the result of `VerifyWebhook` run by the
    caller beforehand. `None` means "not applicable" (e.g. an
    internally-authenticated channel) — it does NOT mean "skip
    authentication silently"; callers on a webhook channel MUST pass a
    real result.
  - Validate: structural check that message content is non-empty.
  - Normalize: construct the domain `Message` entity, RECEIVED ->
    VALIDATED.
  - Deduplicate: `ReplayGuard` keyed on the provider's own message ID
    (a duplicate delivery of the same provider message must not be
    processed twice).
  - Identify: `ChannelIdentityRepository` lookup. No match ->
    `UnknownChannelIdentityError` (see that error's docstring for why
    this never auto-provisions).
  - Contextualize: find the sender's active `Conversation` via
    `ConversationRepository`, or start a new one (CREATED -> ACTIVE) if
    none is active. Saved through the same repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from okapi_copilot.application.ports.channel_identity_repository import (
    ChannelIdentityRepository,
)
from okapi_copilot.application.ports.clock import Clock
from okapi_copilot.application.ports.conversation_repository import ConversationRepository
from okapi_copilot.application.ports.id_generator import IdGenerator
from okapi_copilot.application.ports.replay_guard import ReplayGuard
from okapi_copilot.domain.conversation.conversation import Conversation, ConversationState
from okapi_copilot.domain.errors import (
    IdempotencyConflictError,
    UnknownChannelIdentityError,
    ValidationError,
)
from okapi_copilot.domain.gateway.webhook_security import WebhookValidationResult
from okapi_copilot.domain.identity.channel_identity import Channel
from okapi_copilot.domain.messaging.message import Message, MessageState


@dataclass(frozen=True, slots=True)
class ProcessInboundMessageRequest:
    channel: Channel
    provider: str
    provider_subject_id: str
    provider_message_id: str
    content: str
    received_at: datetime
    correlation_id: str
    tenant_id: str
    organization_id: str | None = None
    webhook_validation: WebhookValidationResult | None = None


@dataclass(frozen=True, slots=True)
class ProcessInboundMessageResult:
    message: Message
    conversation: Conversation


class ProcessInboundMessage:
    def __init__(
        self,
        *,
        channel_identity_repository: ChannelIdentityRepository,
        conversation_repository: ConversationRepository,
        replay_guard: ReplayGuard,
        clock: Clock,
        id_generator: IdGenerator,
        dedup_ttl_seconds: int = 86_400,
    ) -> None:
        self._channel_identity_repository = channel_identity_repository
        self._conversation_repository = conversation_repository
        self._replay_guard = replay_guard
        self._clock = clock
        self._id_generator = id_generator
        self._dedup_ttl_seconds = dedup_ttl_seconds

    async def execute(
        self, request: ProcessInboundMessageRequest
    ) -> ProcessInboundMessageResult:
        # Authenticate source (where applicable).
        if request.webhook_validation is not None and not request.webhook_validation.valid:
            raise ValidationError(
                "Inbound message failed source authentication.",
                details={"reason": request.webhook_validation.reason},
            )

        # Validate.
        if not request.content.strip():
            raise ValidationError("Inbound message content is empty.")

        now = self._clock.now()
        message = Message(
            message_id=self._id_generator.new_id(),
            conversation_id="",  # filled in once Contextualize resolves one
            sender=request.provider_subject_id,
            channel=request.channel.value,
            timestamp=request.received_at,
            correlation_id=request.correlation_id,
            status=MessageState.RECEIVED,
        )
        message = message.transition_to(MessageState.VALIDATED)

        # Deduplicate.
        dedup_key = (
            f"message:{request.channel.value}:{request.provider}:"
            f"{request.provider_message_id}"
        )
        is_first_occurrence = await self._replay_guard.check_and_record(
            dedup_key, ttl_seconds=self._dedup_ttl_seconds
        )
        if not is_first_occurrence:
            raise IdempotencyConflictError(
                "Duplicate inbound message from provider.",
                details={"provider_message_id": request.provider_message_id},
            )

        # Identify.
        channel_identity = await self._channel_identity_repository.find_by_provider_subject(
            channel=request.channel,
            provider=request.provider,
            provider_subject_id=request.provider_subject_id,
        )
        if channel_identity is None:
            raise UnknownChannelIdentityError(
                "Could not identify the sender of this inbound message.",
                details={
                    "channel": request.channel.value,
                    "provider": request.provider,
                    "provider_subject_id": request.provider_subject_id,
                },
            )
        message = message.transition_to(MessageState.IDENTIFIED)

        # Contextualize.
        conversation = await self._conversation_repository.find_active_for_channel_identity(
            channel_identity.channel_identity_id
        )
        if conversation is None:
            conversation = Conversation(
                conversation_id=self._id_generator.new_id(),
                tenant_id=request.tenant_id,
                organization_id=request.organization_id,
                channel=request.channel.value,
                state=ConversationState.CREATED,
                created_at=now,
                updated_at=now,
            ).transition_to(ConversationState.ACTIVE, now=now)
            await self._conversation_repository.save(conversation)

        message = Message(
            message_id=message.message_id,
            conversation_id=conversation.conversation_id,
            sender=message.sender,
            channel=message.channel,
            timestamp=message.timestamp,
            correlation_id=message.correlation_id,
            status=message.status,
        ).transition_to(MessageState.CONTEXTUALIZED)

        return ProcessInboundMessageResult(message=message, conversation=conversation)
