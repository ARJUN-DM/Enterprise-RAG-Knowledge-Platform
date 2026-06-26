"""Tests for RBAC authentication dependencies."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.auth.dependencies import VALID_ROLES, get_user_role


class TestAuthDependencies:
    """Verify RBAC dependency functions."""

    def test_valid_roles_defined(self):
        """Should have at least HR, Engineering, and Admin roles."""
        assert "hr" in VALID_ROLES
        assert "engineering" in VALID_ROLES
        assert "admin" in VALID_ROLES

    @pytest.mark.asyncio
    async def test_valid_role_accepted(self):
        """Valid roles should pass through."""
        for role in VALID_ROLES:
            result = await get_user_role(x_user_role=role)
            assert result == role

    @pytest.mark.asyncio
    async def test_case_insensitive(self):
        """Roles should be case-insensitive."""
        result = await get_user_role(x_user_role="HR")
        assert result == "hr"

        result = await get_user_role(x_user_role="Engineering")
        assert result == "engineering"

    @pytest.mark.asyncio
    async def test_invalid_role_raises(self):
        """Invalid roles should raise HTTPException (403)."""
        with pytest.raises(HTTPException) as excinfo:
            await get_user_role(x_user_role="guest")
        assert excinfo.value.status_code == 403
