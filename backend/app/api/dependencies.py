from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import config
from app.db.session import get_db
from app.models.domain import User
from app.core.rls import bypass_rls, set_tenant_id

security = HTTPBearer(auto_error=False)

async def get_current_user_claims(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required",
        )
    try:
        payload = jwt.decode(credentials.credentials, config.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def require_tenant(
    request: Request,
    claims: dict = Depends(get_current_user_claims)
) -> dict:
    """Dependency: verifies JWT and ensures tenant context from token claims."""
    tenant_id = claims.get('tenant_id')
    is_superadmin = claims.get('is_superadmin')
    
    if not tenant_id and not is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context required"
        )
    
    if tenant_id:
        set_tenant_id(tenant_id)
        
    return claims

async def superadmin_only(
    claims: dict = Depends(get_current_user_claims)
) -> dict:
    """Dependency: checks is_superadmin claim."""
    if not claims.get('is_superadmin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return claims

def require_role(roles: list[str]):
    """Dependency factory: checks that the current user has one of the given roles."""
    async def role_checker(claims: dict = Depends(require_tenant)):
        user_role = claims.get('role')
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(roles)}"
            )
        return claims
    return role_checker

async def get_current_user(
    claims: dict = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db)
) -> User:
    user_id = claims.get('sub')
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token sub")
        
    with bypass_rls():
        result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
        user = result.scalar_one_or_none()
        
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
        
    return user
