"""FastAPI dependencies for RBAC.

Extracts the user role from the X-User-Role header. In v2, this will
validate a JWT token and extract the role from the token claims.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

# Valid personas/roles
VALID_ROLES = {"hr", "engineering", "admin"}


async def get_user_role(x_user_role: str = Header(...)) -> str:
    """Extract and validate the user role from the X-User-Role header.

    Returns the validated role string.
    Raises 403 if the role is invalid.
    """
    role = x_user_role.strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid role: {x_user_role!r}. Valid roles: {', '.join(sorted(VALID_ROLES))}",
        )
    return role


async def get_optional_role(
    x_user_role: str | None = Header(default=None),
) -> str | None:
    """Optionally extract user role (some endpoints don't require it)."""
    if x_user_role is None:
        return None
    role = x_user_role.strip().lower()
    return role if role in VALID_ROLES else None
