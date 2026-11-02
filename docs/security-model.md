# Security Model

## Request identity

For Streamable HTTP, the official MCP Python SDK validates the bearer token before
processing the MCP request. The development `StaticTokenVerifier` maps opaque demo
tokens to an `AccessToken` with `subject`, `client_id`, scopes, and organization/role
claims. The application reads that verified token from the SDK request context.

Do not treat a client-supplied header, tool argument, or model-generated organization
ID as identity. Tenant context comes only from the verified token claims.

## Scope and role checks

Each tool enforces its own scope. Some actions additionally require a role:

| Action | Required scope | Allowed roles |
|---|---|---|
| Search CRM customers | `customers:read` | Any authenticated role with scope |
| Search support tickets | `tickets:read` | Any authenticated role with scope |
| Read invoice summary | `invoices:read` | Any authenticated role with scope |
| Request ticket creation | `tickets:write` | `agent`, `admin` |
| List pending actions | `tickets:approve` | `approver`, `admin` |
| Approve/reject pending action | `tickets:approve` | `approver`, `admin` |
| Read audit events | `audit:read` | `auditor`, `admin` |

Scopes are never inferred from roles. An administrator still needs the appropriate
scope in the token.

## Approval gate

The ticket-write tool only creates a pending action. It does not create the ticket.
A separate approval tool checks the approver's tenant, role, and scope, then changes
the pending action and creates a demo-local ticket in one SQLite transaction. A
pending action can be decided only once. The sample ticket store is not a live
external support integration.

## Tenant isolation

Every fixture lookup and every persisted pending-action, ticket, and audit query is
filtered by the organization ID from verified token claims. Cross-tenant record IDs
are treated as not found to avoid confirming their existence.

## Audit events

Successful reads, denied tool calls, requests for approval, and approval decisions
are recorded with actor, client ID, organization, action, outcome, and minimal
metadata. Do not place secrets, full access tokens, or unnecessary personal data in
an audit event. The demo SQLite audit store is not tamper-evident; production systems
should export events to a protected append-only logging system.

## Important limitations

- Static tokens in `.env.example` are for local development only.
- Replace the static verifier with JWT signature/issuer/audience validation or an
  authorization-server introspection endpoint before deployment.
- Do not enable local stdio identity fallback for untrusted processes.
- MCP stdio has no HTTP Authorization header. The operating-system process boundary
  is its security boundary.
- Use HTTPS, secret management, rate limits, request-size limits, monitoring,
  retention policies, and security review before public deployment.
- Demo connectors return synthetic fixture data and do not call real business APIs.
