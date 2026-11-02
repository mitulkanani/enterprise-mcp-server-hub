import pytest

from app.security.identity import Identity
from app.services import HubServices
from app.storage.store import InvalidState, RecordNotFound


def ident(org="org_acme", role="agent", scopes=None):
    return Identity("agent@example.test", "test-client", org, role, frozenset(scopes or []))


def test_service_creates_pending_request_and_requires_decision(store):
    services = HubServices(store)
    action = services.request_ticket_creation(
        ident(), "New issue", "Repro steps", "normal"
    )
    assert action["status"] == "PENDING"
    assert store.list_created_tickets("org_acme") == []


def test_service_approval_completes_request(store):
    services = HubServices(store)
    action = services.request_ticket_creation(
        ident(), "New issue", "Repro steps", "normal"
    )
    approver = ident(role="admin")
    result = services.decide_action(approver, action["id"], "approve")
    assert result["status"] == "APPROVED"
    assert len(store.list_created_tickets("org_acme")) == 1


def test_service_cannot_approve_cross_tenant_request(store):
    services = HubServices(store)
    action = services.request_ticket_creation(
        ident("org_acme"), "New issue", "Repro steps", "normal"
    )
    with pytest.raises(RecordNotFound):
        services.decide_action(ident("org_globex", "admin"), action["id"], "approve")
