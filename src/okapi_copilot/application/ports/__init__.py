"""
Application ports (SKILL — DDD & Hexagonal Architecture, Section "PORTS").

Every external dependency the application layer needs — identity
resolution, policy decisions, persistence, event publishing, clock,
ID generation — is expressed here as a `typing.Protocol`. Infrastructure
adapters implement these protocols; the domain and application layers
depend only on them, never on a concrete SDK.
"""

from okapi_copilot.application.ports.clock import Clock
from okapi_copilot.application.ports.event_publisher import EventPublisher
from okapi_copilot.application.ports.id_generator import IdGenerator
from okapi_copilot.application.ports.identity_provider import IdentityProvider
from okapi_copilot.application.ports.membership_repository import MembershipRepository
from okapi_copilot.application.ports.policy_engine import PolicyEngine
from okapi_copilot.application.ports.repository import Repository

__all__ = [
    "Clock",
    "EventPublisher",
    "IdGenerator",
    "IdentityProvider",
    "MembershipRepository",
    "PolicyEngine",
    "Repository",
]
