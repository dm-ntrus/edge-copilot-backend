from __future__ import annotations

import hashlib
import hmac

from okapi_copilot.domain.gateway.webhook_signature import verify_webhook_signature

SECRET = "shh-its-a-secret"
PAYLOAD = b'{"event": "message"}'


def _sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def test_valid_signature_bare_hex_is_accepted() -> None:
    signature = _sign(PAYLOAD, SECRET)
    assert verify_webhook_signature(
        payload=PAYLOAD, provided_signature=signature, secret=SECRET
    ) is True


def test_valid_signature_with_algorithm_prefix_is_accepted() -> None:
    signature = f"sha256={_sign(PAYLOAD, SECRET)}"
    assert verify_webhook_signature(
        payload=PAYLOAD, provided_signature=signature, secret=SECRET
    ) is True


def test_wrong_secret_is_rejected() -> None:
    signature = _sign(PAYLOAD, SECRET)
    assert (
        verify_webhook_signature(
            payload=PAYLOAD, provided_signature=signature, secret="wrong-secret"
        )
        is False
    )


def test_tampered_payload_is_rejected() -> None:
    signature = _sign(PAYLOAD, SECRET)
    tampered = b'{"event": "message", "amount": 999999}'
    assert (
        verify_webhook_signature(payload=tampered, provided_signature=signature, secret=SECRET)
        is False
    )


def test_sha1_algorithm_supported() -> None:
    signature = hmac.new(SECRET.encode("utf-8"), PAYLOAD, hashlib.sha1).hexdigest()
    assert (
        verify_webhook_signature(
            payload=PAYLOAD, provided_signature=signature, secret=SECRET, algorithm="sha1"
        )
        is True
    )


def test_garbage_signature_is_rejected() -> None:
    assert (
        verify_webhook_signature(
            payload=PAYLOAD, provided_signature="not-a-signature", secret=SECRET
        )
        is False
    )
