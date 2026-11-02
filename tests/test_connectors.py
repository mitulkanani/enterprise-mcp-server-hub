from app.connectors.demo_connectors import DemoBillingConnector, DemoCRMConnector, DemoSupportConnector


def test_crm_search_only_returns_current_tenant():
    results = DemoCRMConnector().search_customers("org_acme", "Acme")
    assert results
    assert all("Globex" not in row["name"] for row in results)
    assert all("organization_id" not in row for row in results)


def test_crm_search_does_not_leak_other_tenant_records():
    assert DemoCRMConnector().search_customers("org_acme", "Globex") == []


def test_billing_lookup_is_tenant_scoped():
    billing = DemoBillingConnector()
    assert billing.get_invoice("org_acme", "INV-GL-700") is None
    assert billing.get_invoice("org_globex", "INV-GL-700")["status"] == "overdue"


def test_support_connector_includes_created_demo_tickets(store):
    action = store.create_pending_action(
        organization_id="org_acme", requested_by="agent",
        action_type="support.create_ticket",
        payload={"title": "Network access", "description": "VPN issue", "priority": "normal"},
    )
    store.decide_pending_action(
        organization_id="org_acme", action_id=action["id"],
        decided_by="manager", decision="approve",
    )
    rows = DemoSupportConnector(store).search_tickets("org_acme", "VPN")
    assert len(rows) == 1
    assert rows[0]["title"] == "Network access"
