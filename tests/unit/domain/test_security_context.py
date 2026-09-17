from __future__ import annotations

import dataclasses
from datetime import timedelta

import pytest

from okapi_copilot.domain.security.security_context import SecurityContext


def test_security_context_is_frozen(valid_security_context: SecurityContext) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        valid_security_context.tenant_id = "tenant-b"  # type: ignore[misc]


def test_belongs_to_tenant(valid_security_context: SecurityContext) -> None:
    assert valid_security_context.belongs_to_tenant("tenant-a") is True
    assert valid_security_context.belongs_to_tenant("tenant-b") is False


def test_belongs_to_organization(valid_security_context: SecurityContext) -> None:
    assert valid_security_context.belongs_to_organization("org-1") is True
    assert valid_security_context.belongs_to_organization("org-2") is False


def test_has_role_and_permission(valid_security_context: SecurityContext) -> None:
    assert valid_security_context.has_role("employee") is True
    assert valid_security_context.has_role("admin") is False
    assert valid_security_context.has_permission("orders:read") is True
    assert valid_security_context.has_permission("orders:delete") is False


def test_is_expired(valid_security_context: SecurityContext) -> None:
    future = valid_security_context.expires_at + timedelta(seconds=1)
    assert valid_security_context.is_expired(now=future) is True

    past = valid_security_context.issued_at - timedelta(seconds=1)
    assert valid_security_context.is_expired(now=past) is False


def test_no_context_has_a_mutation_helper(valid_security_context: SecurityContext) -> None:
    """
    Guard against reintroducing a `with_*` / setter convenience method that
    would let code "modify" a SecurityContext instead of reissuing one
    through the trusted path (Document 9 Section 16).
    """
    forbidden_prefixes = ("with_", "set_", "update_")
    public_methods = [
        name
        for name in dir(valid_security_context)
        if not name.startswith("_") and callable(getattr(valid_security_context, name))
    ]
    offending = [m for m in public_methods if m.startswith(forbidden_prefixes)]
    assert offending == []
