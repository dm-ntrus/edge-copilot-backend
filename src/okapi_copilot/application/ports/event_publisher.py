"""
EventPublisher port.

Abstracts the event broker (RabbitMQ or compatible, per Document 2
Section 6). The envelope fields mirror the Distributed & Automation
Engineering skill Section 5 (EVENT MODEL) and Document 9 Section 31
(EVENT CONTRACT).

Reminder (Document 9 Section 32, EVENT TRUST MODEL):
an event's payload can never grant authority — publishing an event here
does not authorize anything; it only records/propagates a fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: str
    event_type: str
    schema_version: str
    source: str
    producer: str
    tenant_id: str
    organization_id: str | None
    subject_id: str
    timestamp: datetime
    correlation_id: str
    causation_id: str | None
    trace_id: str | None
    payload: dict[str, Any]
    metadata: dict[str, Any]


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event. Must be safe to call at-least-once;
        consumers are responsible for deduplication (event_id)."""
        ...
