from __future__ import annotations

from app.security.identity import Identity


class AuthorizationError(PermissionError):
    """Raised when the authenticated caller lacks a required permission."""


def require_access(
    identity: Identity,
    required_scope: str,
    allowed_roles: set[str] | frozenset[str] | None = None,
) -> None:
    """Enforce scope and optional role checks. No implicit role-to-scope grants."""
    if not identity.organization_id.strip():
        raise AuthorizationError("An organization claim is required.")
    if required_scope not in identity.scopes and "*" not in identity.scopes:
        raise AuthorizationError(f"Missing required scope: {required_scope}.")
    if allowed_roles and identity.role not in allowed_roles:
        raise AuthorizationError("Your role is not allowed to perform this action.")
