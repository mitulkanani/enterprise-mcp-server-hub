from __future__ import annotations

from typing import Any

from app.connectors.demo_connectors import (
    DemoBillingConnector,
    DemoCRMConnector,
    DemoSupportConnector,
)
from app.security.identity import Identity
from app.storage.store import HubStore


class HubServices:
    def __init__(self, store: HubStore) -> None:
        self.store = store
        self.crm = DemoCRMConnector()
        self.support = DemoSupportConnector(store)
        self.billing = DemoBillingConnector()

    def search_customers(self, identity: Identity, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return self.crm.search_customers(identity.organization_id, query, limit)

    def search_tickets(self, identity: Identity, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return self.support.search_tickets(identity.organization_id, query, limit)

    def get_invoice(self, identity: Identity, invoice_id: str) -> dict[str, Any] | None:
        return self.billing.get_invoice(identity.organization_id, invoice_id)

    def request_ticket_creation(
        self, identity: Identity, title: str, description: str, priority: str
    ) -> dict[str, Any]:
        return self.store.create_pending_action(
            organization_id=identity.organization_id,
            requested_by=identity.subject,
            action_type="support.create_ticket",
            payload={"title": title, "description": description, "priority": priority},
        )

    def list_pending_actions(self, identity: Identity, limit: int = 20) -> list[dict[str, Any]]:
        return self.store.list_pending_actions(identity.organization_id, limit)

    def decide_action(
        self, identity: Identity, action_id: str, decision: str
    ) -> dict[str, Any]:
        return self.store.decide_pending_action(
            organization_id=identity.organization_id,
            action_id=action_id,
            decided_by=identity.subject,
            decision=decision,
        )
