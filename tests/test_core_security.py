"""Phase 4a — Security tests (password hashing, JWT tokens)."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest

from multi_tenant_bootstrapper.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)
from multi_tenant_bootstrapper.config import get_config
from multi_tenant_bootstrapper.models.domain import UserRole


class TestPasswordHashing:

    def test_get_password_hash_returns_bcrypt(self):
        hashed = get_password_hash("mypassword")
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        hashed = get_password_hash("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_password_wrong(self):
        hashed = get_password_hash("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_different_hashes(self):
        h1 = get_password_hash("password1")
        h2 = get_password_hash("password2")
        assert h1 != h2


class TestCreateAccessToken:

    def _make_mock_user(self, **overrides):
        user = MagicMock()
        user.id = overrides.get("id", uuid.uuid4())
        user.tenant_id = overrides.get("tenant_id", uuid.uuid4())
        user.is_superadmin = overrides.get("is_superadmin", False)
        user.role = overrides.get("role", UserRole.member)
        user.email = overrides.get("email", "test@example.com")
        return user

    def test_create_access_token_contains_claims(self):
        user = self._make_mock_user(email="claims@test.com")
        token = create_access_token(user)
        config = get_config()
        payload = jwt.decode(
            token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
        )
        assert payload["sub"] == str(user.id)
        assert payload["tenant_id"] == str(user.tenant_id)
        assert payload["email"] == "claims@test.com"
        assert payload["is_superadmin"] is False
        assert payload["role"] == "member"

    def test_create_access_token_has_expiry(self):
        user = self._make_mock_user()
        token = create_access_token(user)
        config = get_config()
        payload = jwt.decode(
            token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
        )
        assert "exp" in payload
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)

    def test_create_access_token_superadmin(self):
        user = self._make_mock_user(is_superadmin=True, role=UserRole.admin)
        token = create_access_token(user)
        config = get_config()
        payload = jwt.decode(
            token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
        )
        assert payload["is_superadmin"] is True
        assert payload["role"] == "admin"

    def test_create_access_token_no_tenant(self):
        user = self._make_mock_user(tenant_id=None)
        token = create_access_token(user)
        config = get_config()
        payload = jwt.decode(
            token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
        )
        assert payload["tenant_id"] is None
