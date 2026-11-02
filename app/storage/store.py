from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


class StoreError(Exception):
    """Base persistence error."""


class RecordNotFound(StoreError):
    """A tenant-scoped record was not found."""


class InvalidState(StoreError):
    """A record cannot transition from its current state."""


class HubStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS pending_actions (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('PENDING','APPROVED','REJECTED')),
                    decided_by TEXT,
                    result_reference TEXT,
                    created_at TEXT NOT NULL,
                    decided_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_pending_org_status
                    ON pending_actions(organization_id, status, created_at);

                CREATE TABLE IF NOT EXISTS support_tickets (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tickets_org
                    ON support_tickets(organization_id, created_at);

                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    actor TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_org_created
                    ON audit_events(organization_id, created_at);
                """
            )

    def record_audit(
        self,
        *,
        organization_id: str | None,
        actor: str,
        client_id: str,
        action: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid4()),
            "organization_id": organization_id,
            "actor": actor,
            "client_id": client_id,
            "action": action,
            "outcome": outcome,
            "details": details or {},
            "created_at": self._now(),
        }
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO audit_events
                (id, organization_id, actor, client_id, action, outcome, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event["id"], organization_id, actor, client_id, action,
                    outcome, json.dumps(event["details"]), event["created_at"],
                ),
            )
        return event

    def list_audit_events(self, organization_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM audit_events WHERE organization_id = ?
                ORDER BY created_at DESC LIMIT ?""",
                (organization_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "organization_id": row["organization_id"],
                "actor": row["actor"],
                "client_id": row["client_id"],
                "action": row["action"],
                "outcome": row["outcome"],
                "details": json.loads(row["details_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def create_pending_action(
        self,
        *,
        organization_id: str,
        requested_by: str,
        action_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        action = {
            "id": str(uuid4()),
            "organization_id": organization_id,
            "requested_by": requested_by,
            "action_type": action_type,
            "payload": payload,
            "status": "PENDING",
            "decided_by": None,
            "result_reference": None,
            "created_at": self._now(),
            "decided_at": None,
        }
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO pending_actions
                (id, organization_id, requested_by, action_type, payload_json, status,
                 decided_by, result_reference, created_at, decided_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    action["id"], organization_id, requested_by, action_type,
                    json.dumps(payload), action["status"], None, None,
                    action["created_at"], None,
                ),
            )
        return action

    def list_pending_actions(self, organization_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM pending_actions WHERE organization_id = ? AND status = 'PENDING'
                ORDER BY created_at ASC LIMIT ?""",
                (organization_id, limit),
            ).fetchall()
        return [self._action_from_row(row) for row in rows]

    @staticmethod
    def _action_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "organization_id": row["organization_id"],
            "requested_by": row["requested_by"],
            "action_type": row["action_type"],
            "payload": json.loads(row["payload_json"]),
            "status": row["status"],
            "decided_by": row["decided_by"],
            "result_reference": row["result_reference"],
            "created_at": row["created_at"],
            "decided_at": row["decided_at"],
        }

    def decide_pending_action(
        self,
        *,
        organization_id: str,
        action_id: str,
        decided_by: str,
        decision: str,
    ) -> dict[str, Any]:
        if decision not in {"approve", "reject"}:
            raise ValueError("Decision must be 'approve' or 'reject'.")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM pending_actions WHERE id = ? AND organization_id = ?",
                (action_id, organization_id),
            ).fetchone()
            if row is None:
                raise RecordNotFound("Pending action not found.")
            if row["status"] != "PENDING":
                raise InvalidState(f"Action is already {row['status'].lower()}.")

            now = self._now()
            reference = None
            if decision == "approve":
                payload = json.loads(row["payload_json"])
                if row["action_type"] != "support.create_ticket":
                    raise InvalidState("Unsupported action type.")
                reference = f"TCK-{uuid4().hex[:8].upper()}"
                conn.execute(
                    """INSERT INTO support_tickets
                    (id, organization_id, title, description, priority, status, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        reference, organization_id, payload["title"],
                        payload["description"], payload["priority"],
                        "OPEN", decided_by, now,
                    ),
                )
                status = "APPROVED"
            else:
                status = "REJECTED"

            conn.execute(
                """UPDATE pending_actions SET status = ?, decided_by = ?,
                result_reference = ?, decided_at = ? WHERE id = ? AND organization_id = ?""",
                (status, decided_by, reference, now, action_id, organization_id),
            )
            updated = conn.execute(
                "SELECT * FROM pending_actions WHERE id = ? AND organization_id = ?",
                (action_id, organization_id),
            ).fetchone()
            return self._action_from_row(updated)

    def list_created_tickets(self, organization_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM support_tickets WHERE organization_id = ?
                ORDER BY created_at DESC LIMIT ?""",
                (organization_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]
