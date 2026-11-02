# Enterprise MCP Server Hub

A security-focused reference implementation of a multi-tenant **Model Context
Protocol (MCP) server hub**. It exposes demo CRM, support, and billing connectors as
MCP tools, resources, and prompts, with token-derived tenant identity, scope and role
checks, approval-gated writes, and audit events.

> **Current scope:** a runnable demo using synthetic connector fixtures and local
> SQLite persistence. It does not connect to a real CRM, helpdesk, or billing
> provider. The included static bearer-token verifier is for local development only.

## Why this project

AI assistants need a consistent way to discover and invoke business capabilities.
MCP standardizes the interface; this project demonstrates the governance layer that
an enterprise hub needs around it: identity, scopes, organization boundaries,
controlled writes, and auditability.

## Features

- Official MCP Python SDK v2, exposing tools, a resource, and a prompt.
- Streamable HTTP endpoint at `/mcp` and local stdio transport.
- Token-derived organization identity; client-supplied tenant IDs are never trusted.
- Fine-grained scopes plus role checks for write/approval/audit tools.
- Demo CRM customer search, support ticket search, and billing invoice lookup.
- Ticket creation starts as a pending action; only an authorized approver can
  approve it and create a demo-local ticket.
- Tenant-scoped SQLite persistence for pending actions, tickets, and audit events.
- Atomic approval decisions; a request cannot be approved/rejected twice.
- Health endpoint, Docker Compose, tests, and GitHub Actions CI.

## Architecture

```text
MCP Host / Agent
      |
      | Streamable HTTP + Authorization: Bearer <token>
      v
Official MCP Python SDK v2
      |
      +--> TokenVerifier --> verified subject/client/scopes/org/role
      |
      +--> MCP tool registry
              |
              +--> Policy enforcement (scope + role)
              |
              +--> Connector adapters
              |      +--> Demo CRM
              |      +--> Demo Support
              |      +--> Demo Billing
              |
              +--> SQLite store
                     +--> Pending actions
                     +--> Demo tickets
                     +--> Audit events
```

## Tool catalog

| Tool | Required scope | Additional role | Behavior |
|---|---|---|---|
| `crm_search_customers` | `customers:read` | — | Search tenant-scoped demo customers |
| `support_search_tickets` | `tickets:read` | — | Search tenant-scoped demo tickets |
| `billing_get_invoice` | `invoices:read` | — | Read tenant-scoped invoice summary |
| `support_request_ticket_creation` | `tickets:write` | `agent` or `admin` | Creates a pending approval request only |
| `hub_list_pending_actions` | `tickets:approve` | `approver` or `admin` | List pending requests for own tenant |
| `hub_decide_pending_action` | `tickets:approve` | `approver` or `admin` | Approve/reject request; approved request creates demo-local ticket |
| `hub_get_audit_events` | `audit:read` | `auditor` or `admin` | Read own tenant's audit events |

Also included:

- Resource: `hub://catalog`
- Prompt: `investigate_customer(customer_name)`
- Health endpoint: `GET /health`

## Quick start

Python 3.11+ is required.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1

python -m pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env` and keep the sample token configuration only for local development.
Then start the HTTP MCP server:

```bash
uvicorn app.mcp_server:app --reload --host 127.0.0.1 --port 8000
```

MCP endpoint: `http://127.0.0.1:8000/mcp`

Health check: `http://127.0.0.1:8000/health`

The SDK's protected-resource metadata endpoint is also available under
`/.well-known/oauth-protected-resource/mcp`.

## Try it with the MCP Inspector

Run:

```bash
npx -y @modelcontextprotocol/inspector
```

Connect to the Streamable HTTP endpoint. Set the HTTP Authorization header to
`Bearer agent-demo-token` to use read and ticket-request tools. Use
`approver-demo-token` for approval and audit tools.

For a trusted local stdio integration, see [docs/mcp-client-config.md](docs/mcp-client-config.md).

## Example end-to-end flow

1. Call `support_request_ticket_creation` using `agent-demo-token`.
2. The result contains `approval_required: true` and a pending action ID. No ticket
   has been created yet.
3. Call `hub_list_pending_actions` using `approver-demo-token`.
4. Call `hub_decide_pending_action` with the action ID and `decision="approve"`.
5. The approved action is persisted and a demo-local ticket reference is returned.
6. Read `hub_get_audit_events` with the approver token.

## Demo identities and scopes

The `.env.example` file includes four local identities:

| Token | Org | Role | Example permissions |
|---|---|---|---|
| `reader-demo-token` | `org_acme` | viewer | customer/ticket/invoice reads |
| `agent-demo-token` | `org_acme` | agent | reads + request ticket creation |
| `approver-demo-token` | `org_acme` | admin | approve/reject + audit read |
| `globex-reader-token` | `org_globex` | viewer | read only, isolated tenant |

All tokens also have `hub:access`, which the MCP HTTP authorization layer requires.
The sample tokens are public demo credentials and must never be used outside a local
sandbox.

## Run tests

```bash
pytest
pytest --cov=app --cov-report=term-missing
```

The unit tests cover token claim mapping, scope and role enforcement, tenant
isolation, approval state transitions, duplicate decisions, and audit separation.
They test the policy and service layer without requiring an external MCP host or a
live business system.

## Run with Docker

```bash
cp .env.example .env
# Edit .env before exposing the service. The included tokens are demo-only.
docker compose up --build
```

The container stores SQLite data in a named volume. The sample compose setup binds
the service to the host's published port; keep it behind a trusted network until
real authentication and host allowlists are configured.

## Project layout

```text
app/
  connectors/demo_connectors.py  # synthetic CRM, support, and billing adapters
  security/identity.py           # token-to-identity mapping
  security/policy.py             # scope and role enforcement
  security/tokens.py             # development static token verifier
  storage/store.py               # SQLite approvals, tickets, and audit log
  services.py                     # service orchestration
  mcp_server.py                   # MCP tools, resources, prompt, HTTP app
  config.py

tests/
docs/
.github/workflows/ci.yml
```

## Security boundaries and production checklist

- The official MCP SDK performs bearer-token verification for Streamable HTTP. This
  project's static verifier is a development-only example. Replace it with a real
  OAuth/OIDC JWT verifier or token-introspection integration.
- Validate issuer, signature, expiry, audience/resource binding, and scopes. Do not
  forward inbound bearer tokens to downstream providers.
- `stdio` does not carry HTTP auth headers. Its security boundary is the local
  process. The optional local identity bypass is off by default and must not be
  enabled for remote/untrusted processes.
- The HTTP transport has a localhost Host allowlist for this sample. Configure a
  precise allowed-host/origin policy and HTTPS before deployment.
- Demo connectors use synthetic data. Add provider-specific credentials, least-
  privilege API scopes, timeouts, retries, idempotency keys, and secret storage when
  implementing real integrations.
- The SQLite audit log is useful for a demo but is not tamper-evident. Export events
  to a protected append-only logging platform for production.
- Add rate limiting, request-size limits, monitoring, retention controls, backup,
  and security testing before public or multi-customer deployment.

## References

- [Official MCP Python SDK v2](https://py.sdk.modelcontextprotocol.io/)
- [MCP Python SDK authorization guide](https://py.sdk.modelcontextprotocol.io/run/authorization/)
- [MCP tool security considerations](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)

## License

MIT. See [LICENSE](LICENSE).
