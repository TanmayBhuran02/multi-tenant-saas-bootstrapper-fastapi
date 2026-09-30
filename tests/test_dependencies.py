"""Phase 5 — API dependency tests (JWT decoding, tenant/role guards)."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from multi_tenant_bootstrapper.config import get_config
from multi_tenant_bootstrapper.api.dependencies import (
    get_current_user_claims,
    require_tenant,
    superadmin_only,
    require_role,
)
from multi_tenant_bootstrapper.models.domain import UserRole


def _make_token(claims: dict, secret: str = None, algorithm: str = "HS256") -> str:
    """Helper to create a JWT token with given claims."""
    config = get_config()
    secret = secret or config.JWT_SECRET_KEY
    return jwt.encode(claims, secret, algorithm=algorithm)


def _make_valid_claims(**overrides) -> dict:
    """Create valid JWT claims with defaults."""
    config = get_config()
    base = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "tenant_id": str(uuid.uuid4()),
        "is_superadmin": False,
        "role": "member",
        "email": "test@example.com",
    }
    base.update(overrides)
    return base


class _FakeCredentials:
    """Mock HTTPAuthorizationCredentials."""

    def __init__(self, token: str):
        self.credentials = token


class TestGetCurrentUserClaims:

    async def test_valid_token(self):
        claims = _make_valid_claims()
        token = _make_token(claims)
        result = await get_current_user_claims(credentials=_FakeCredentials(token))
        assert result["email"] == "test@example.com"
        assert result["role"] == "member"

    async def test_expired_token(self):
        claims = _make_valid_claims(
            exp=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        token = _make_token(claims)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_claims(credentials=_FakeCredentials(token))
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    async def test_invalid_token(self):
        token = _make_token(
            _make_valid_claims(), secret="wrong-secret"
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_claims(credentials=_FakeCredentials(token))
        assert exc_info.value.status_code == 401

    async def test_no_credentials(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_claims(credentials=None)
        assert exc_info.value.status_code == 401


class TestRequireTenant:

    async def test_with_tenant_id(self):
        from unittest.mock import MagicMock
        request = MagicMock()
        claims = _make_valid_claims(tenant_id="tid-123")
        result = await require_tenant(request=request, claims=claims)
        assert result["tenant_id"] == "tid-123"

    async def test_no_tenant_no_superadmin(self):
        from unittest.mock import MagicMock
        request = MagicMock()
        claims = _make_valid_claims(tenant_id=None, is_superadmin=False)
        with pytest.raises(HTTPException) as exc_info:
            await require_tenant(request=request, claims=claims)
        assert exc_info.value.status_code == 403

    async def test_superadmin_without_tenant(self):
        """Superadmin should pass even without tenant_id."""
        from unittest.mock import MagicMock
        request = MagicMock()
        claims = _make_valid_claims(tenant_id=None, is_superadmin=True)
        result = await require_tenant(request=request, claims=claims)
        assert result["is_superadmin"] is True


class TestSuperadminOnly:

    async def test_superadmin_pass(self):
        claims = _make_valid_claims(is_superadmin=True)
        result = await superadmin_only(claims=claims)
        assert result["is_superadmin"] is True

    async def test_non_superadmin_fail(self):
        claims = _make_valid_claims(is_superadmin=False)
        with pytest.raises(HTTPException) as exc_info:
            await superadmin_only(claims=claims)
        assert exc_info.value.status_code == 403


class TestRequireRole:

    async def test_require_role_owner_passes(self):
        checker = require_role(["owner", "admin"])
        claims = _make_valid_claims(role="owner", tenant_id="t-1")
        result = await checker(claims=claims)
        assert result["role"] == "owner"

    async def test_require_role_member_rejected(self):
        checker = require_role(["owner", "admin"])
        claims = _make_valid_claims(role="member", tenant_id="t-1")
        with pytest.raises(HTTPException) as exc_info:
            await checker(claims=claims)
        assert exc_info.value.status_code == 403
