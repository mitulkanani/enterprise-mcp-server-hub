from __future__ import annotations

from typing import Any

from app.storage.store import HubStore


# Static, clearly synthetic records used to demonstrate tenant-aware read tools.
_CUSTOMERS = [
    {"id": "CUS-AC-100", "organization_id": "org_acme", "name": "Acme Components", "email": "ops@acme.example", "tier": "enterprise", "status": "active"},
    {"id": "CUS-AC-101", "organization_id": "org_acme", "name": "Acme Retail West", "email": "west@acme.example", "tier": "growth", "status": "active"},
    {"id": "CUS-GL-200", "organization_id": "org_globex", "name": "Globex Manufacturing", "email": "procurement@globex.example", "tier": "enterprise", "status": "active"},
]
_TICKETS = [
    {"id": "TCK-AC-001", "organization_id": "org_acme", "title": "Cannot access reporting workspace", "description": "The monthly reporting workspace returns an access error.", "priority": "high", "status": "open"},
    {"id": "TCK-AC-002", "organization_id": "org_acme", "title": "Invoice export question", "description": "Customer needs help exporting an invoice PDF.", "priority": "normal", "status": "pending"},
    {"id": "TCK-GL-009", "organization_id": "org_globex", "title": "Production API timeout", "description": "Periodic timeout from the order API.", "priority": "urgent", "status": "open"},
]
_INVOICES = [
    {"id": "INV-AC-300", "organization_id": "org_acme", "customer_id": "CUS-AC-100", "amount": 1240.50, "currency": "USD", "status": "paid", "due_date": "2026-11-15"},
    {"id": "INV-AC-301", "organization_id": "org_acme", "customer_id": "CUS-AC-101", "amount": 875.00, "currency": "USD", "status": "open", "due_date": "2026-11-20"},
    {"id": "INV-GL-700", "organization_id": "org_globex", "customer_id": "CUS-GL-200", "amount": 9300.00, "currency": "USD", "status": "overdue", "due_date": "2026-10-15"},
]


class DemoCRMConnector:
    def search_customers(self, organization_id: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
        needle = query.casefold().strip()
        rows = [
            row for row in _CUSTOMERS
            if row["organization_id"] == organization_id
            and needle in f"{row['id']} {row['name']} {row['email']}".casefold()
        ]
        return [{k: v for k, v in row.items() if k != "organization_id"} for row in rows[:limit]]


class DemoSupportConnector:
    def __init__(self, store: HubStore) -> None:
        self.store = store

    def search_tickets(self, organization_id: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
        needle = query.casefold().strip()
        fixtures = [
            row for row in _TICKETS
            if row["organization_id"] == organization_id
            and needle in f"{row['id']} {row['title']} {row['description']} {row['status']}".casefold()
        ]
        created = [
            {"id": row["id"], "title": row["title"], "description": row["description"], "priority": row["priority"], "status": row["status"]}
            for row in self.store.list_created_tickets(organization_id, limit=limit)
            if needle in f"{row['id']} {row['title']} {row['description']} {row['status']}".casefold()
        ]
        return [
            {k: v for k, v in row.items() if k != "organization_id"}
            for row in (fixtures + created)[:limit]
        ]


class DemoBillingConnector:
    def get_invoice(self, organization_id: str, invoice_id: str) -> dict[str, Any] | None:
        for row in _INVOICES:
            if row["organization_id"] == organization_id and row["id"].casefold() == invoice_id.casefold():
                return {k: v for k, v in row.items() if k != "organization_id"}
        return None
