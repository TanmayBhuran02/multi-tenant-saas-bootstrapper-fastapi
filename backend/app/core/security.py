import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import config
from typing import Any
import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

ALGORITHM = "HS256"

def create_access_token(user: Any) -> str:
    """Create an access token with tenant and superadmin claims."""
    expire = datetime.now(timezone.utc) + timedelta(seconds=config.JWT_ACCESS_TOKEN_EXPIRES)
    
    to_encode = {
        "sub": str(user.id),
        "exp": expire,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "is_superadmin": user.is_superadmin,
        "role": user.role.value,
        "email": user.email,
    }
    
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
