"""Input Gateway / Webhook Security domain logic (Document 3 Sections 15-16)."""

from okapi_copilot.domain.gateway.webhook_security import (
    WebhookSecurityConfig,
    WebhookValidationResult,
    validate_webhook_envelope,
)
from okapi_copilot.domain.gateway.webhook_signature import verify_webhook_signature

__all__ = [
    "verify_webhook_signature",
    "WebhookSecurityConfig",
    "WebhookValidationResult",
    "validate_webhook_envelope",
]
