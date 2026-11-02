from types import SimpleNamespace

import pytest

from app.security.identity import AuthenticationError, Identity, identity_from_token
from app.security.policy import AuthorizationError, require_access


def make_identity(scopes=None, role="viewer", org="org_acme"):
    return Identity(
        subject="person@example.test",
        client_id="test-client",
        organization_id=org,
        role=role,
        scopes=frozenset(scopes or []),
    )


def test_identity_created_from_access_token_claims():
    token = SimpleNamespace(
        subject="agent@example.test",
        client_id="support-agent",
        scopes=["hub:access", "tickets:read"],
        claims={"org_id": "org_acme", "role": "agent"},
    )
    identity = identity_from_token(token)
    assert identity.organization_id == "org_acme"
    assert identity.role == "agent"
    assert "tickets:read" in identity.scopes


def test_missing_token_is_rejected():
    with pytest.raises(AuthenticationError):
        identity_from_token(None)


def test_required_scope_is_enforced():
    with pytest.raises(AuthorizationError, match="Missing required scope"):
        require_access(make_identity(["customers:read"]), "tickets:write")


def test_role_is_enforced_even_when_scope_exists():
    with pytest.raises(AuthorizationError, match="role"):
        require_access(make_identity(["tickets:approve"], role="agent"), "tickets:approve", {"approver", "admin"})


def test_wildcard_scope_is_accepted_but_role_still_applies():
    require_access(make_identity(["*"]), "tickets:read")
    with pytest.raises(AuthorizationError):
        require_access(make_identity(["*"], role="viewer"), "tickets:approve", {"admin"})
