from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Identity:
    subject: str
    client_id: str
    organization_id: str
    role: str
    scopes: frozenset[str]

    @classmethod
    def from_access_token(cls, token: Any) -> "Identity":
        """Convert an MCP SDK AccessToken into a validated application identity."""
        if token is None:
            raise ValueError("Authentication is required.")
        claims: Mapping[str, Any] = getattr(token, "claims", None) or {}
        organization_id = claims.get("org_id") or claims.get("organization_id")
        subject = getattr(token, "subject", None) or getattr(token, "client_id", None)
        client_id = getattr(token, "client_id", None)
        scopes = getattr(token, "scopes", None) or []
        role = claims.get("role", "viewer")
        if not organization_id or not subject or not client_id:
            raise ValueError("The access token is missing required identity claims.")
        if not isinstance(organization_id, str) or not isinstance(role, str):
            raise ValueError("The access token contains invalid organization or role claims.")
        if not isinstance(scopes, (list, tuple, set)) or not all(
            isinstance(scope, str) for scope in scopes
        ):
            raise ValueError("The access token contains invalid scopes.")
        return cls(
            subject=str(subject),
            client_id=str(client_id),
            organization_id=organization_id,
            role=role,
            scopes=frozenset(scopes),
        )


class AuthenticationError(PermissionError):
    """Raised when a request has no usable identity."""


def identity_from_token(token: Any) -> Identity:
    try:
        return Identity.from_access_token(token)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc
