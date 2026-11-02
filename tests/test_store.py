import pytest

from app.storage.store import HubStore, InvalidState, RecordNotFound


def pending(store, org="org_acme"):
    return store.create_pending_action(
        organization_id=org,
        requested_by="agent@example.test",
        action_type="support.create_ticket",
        payload={"title": "Login issue", "description": "User cannot sign in", "priority": "high"},
    )


def test_create_pending_action_does_not_create_ticket(store):
    action = pending(store)
    assert action["status"] == "PENDING"
    assert store.list_created_tickets("org_acme") == []


def test_approval_creates_ticket_and_closes_action(store):
    action = pending(store)
    result = store.decide_pending_action(
        organization_id="org_acme", action_id=action["id"],
        decided_by="manager@example.test", decision="approve",
    )
    assert result["status"] == "APPROVED"
    assert result["result_reference"].startswith("TCK-")
    tickets = store.list_created_tickets("org_acme")
    assert len(tickets) == 1
    assert tickets[0]["title"] == "Login issue"


def test_rejection_does_not_create_ticket(store):
    action = pending(store)
    result = store.decide_pending_action(
        organization_id="org_acme", action_id=action["id"],
        decided_by="manager@example.test", decision="reject",
    )
    assert result["status"] == "REJECTED"
    assert store.list_created_tickets("org_acme") == []


def test_action_cannot_be_decided_twice(store):
    action = pending(store)
    store.decide_pending_action(
        organization_id="org_acme", action_id=action["id"],
        decided_by="manager@example.test", decision="approve",
    )
    with pytest.raises(InvalidState):
        store.decide_pending_action(
            organization_id="org_acme", action_id=action["id"],
            decided_by="manager@example.test", decision="reject",
        )


def test_tenant_cannot_approve_another_tenants_action(store):
    action = pending(store, org="org_acme")
    with pytest.raises(RecordNotFound):
        store.decide_pending_action(
            organization_id="org_globex", action_id=action["id"],
            decided_by="attacker@example.test", decision="approve",
        )


def test_pending_action_lists_are_tenant_scoped(store):
    action = pending(store, org="org_acme")
    assert [item["id"] for item in store.list_pending_actions("org_acme")] == [action["id"]]
    assert store.list_pending_actions("org_globex") == []


def test_audit_events_are_tenant_scoped(store):
    store.record_audit(
        organization_id="org_acme", actor="reader", client_id="client-a",
        action="crm_search_customers", outcome="SUCCESS", details={"result_count": 1},
    )
    assert len(store.list_audit_events("org_acme")) == 1
    assert store.list_audit_events("org_globex") == []
