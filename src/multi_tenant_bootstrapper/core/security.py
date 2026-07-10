"""JWT token creation and password hashing utilities."""

import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any

from multi_tenant_bootstrapper.config import get_config


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8'),
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(user: Any) -> str:
    """Create a JWT access token with tenant and superadmin claims.

    The token payload includes:
    - ``sub``: User ID
    - ``exp``: Expiry timestamp
    - ``tenant_id``: Tenant UUID (or None for platform-level users)
    - ``is_superadmin``: Boolean
    - ``role``: User role value
    - ``email``: User email
    """
    config = get_config()
    expire = datetime.now(timezone.utc) + timedelta(
        seconds=config.JWT_ACCESS_TOKEN_EXPIRES
    )

    to_encode = {
        "sub": str(user.id),
        "exp": expire,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "is_superadmin": user.is_superadmin,
        "role": user.role.value,
        "email": user.email,
    }

    encoded_jwt = jwt.encode(
        to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM
    )
    return encoded_jwt
