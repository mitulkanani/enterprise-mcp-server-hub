from __future__ import annotations

from typing import Any

from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.config import settings


class StaticTokenVerifier(TokenVerifier):
    """Development verifier backed by static tokens from MCP_STATIC_TOKENS.

    Replace this with your identity provider's JWT signature validation or token
    introspection before exposing the service to real users. Never use static
    demo tokens as production credentials.
    """

    def __init__(self, token_config: dict[str, dict[str, Any]] | None = None) -> None:
        self._token_config = token_config if token_config is not None else settings.static_tokens

    async def verify_token(self, token: str) -> AccessToken | None:
        config = self._token_config.get(token)
        if not config:
            return None
        scopes = config.get("scopes", [])
        claims = config.get("claims", {})
        if not isinstance(scopes, list) or not isinstance(claims, dict):
            return None
        subject = config.get("subject")
        client_id = config.get("client_id")
        if not isinstance(subject, str) or not isinstance(client_id, str):
            return None
        return AccessToken(
            token=token,
            client_id=client_id,
            subject=subject,
            scopes=scopes,
            claims=claims,
        )
