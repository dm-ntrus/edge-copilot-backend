"""
Webhook signature verification.

Document 3 Section 16, first line item: "Signature verification". This
is pure computation over bytes using the standard library's `hmac`/
`hashlib` (not a third-party SDK or network client, so it stays inside
the domain purity rule — the forbidden imports are frameworks,
databases, and provider SDKs, not the standard library's own crypto
primitives, which `security_context.py`'s use of `datetime` already
establishes as fine).

Uses `hmac.compare_digest` throughout — never `==` on signatures — to
avoid timing-attack side channels.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Literal

Algorithm = Literal["sha256", "sha1"]


def verify_webhook_signature(
    *,
    payload: bytes,
    provided_signature: str,
    secret: str,
    algorithm: Algorithm = "sha256",
) -> bool:
    """
    Verify an HMAC webhook signature.

    `provided_signature` may be a bare hex digest or carry a
    "sha256=<hex>" / "sha1=<hex>" style prefix (the common convention
    used by e.g. Meta/WhatsApp webhooks) — the prefix, if present, is
    stripped before comparison.
    """
    prefix = f"{algorithm}="
    candidate = (
        provided_signature[len(prefix) :]
        if provided_signature.startswith(prefix)
        else provided_signature
    )

    hash_func = getattr(hashlib, algorithm)
    expected = hmac.new(secret.encode("utf-8"), payload, hash_func).hexdigest()

    return hmac.compare_digest(expected, candidate)
