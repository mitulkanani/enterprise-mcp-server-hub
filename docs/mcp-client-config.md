# MCP Client Configuration

## Local stdio (trusted local process only)

Install the project in a virtual environment, set `MCP_ALLOW_LOCAL_STDIO_IDENTITY=true`
for local development only, and configure a compatible MCP host to start:

```json
{
  "mcpServers": {
    "enterprise-mcp-hub": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/absolute/path/to/enterprise-mcp-server-hub",
      "env": {
        "ENVIRONMENT": "development",
        "MCP_ALLOW_LOCAL_STDIO_IDENTITY": "true"
      }
    }
  }
}
```

The local stdio fallback represents a fully privileged local developer identity. It
must never be enabled for an MCP server exposed to untrusted users or processes.

## Streamable HTTP

Start the server with `uvicorn app.mcp_server:app --host 127.0.0.1 --port 8000`.
Configure a client to connect to `http://127.0.0.1:8000/mcp` and send one of the
local demo bearer tokens from `.env.example`, for example `agent-demo-token`.

The server publishes protected-resource metadata using the official MCP SDK. The
example issuer URL is a placeholder; the static token verifier is only a local
integration example. A production deployment must configure a real authorization
server and a verifier that validates token signature/introspection, issuer,
audience/resource binding, expiry, and scopes.
