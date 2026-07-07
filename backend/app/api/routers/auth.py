from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.domain import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, LoginResponse, UserResponse
from app.core.security import create_access_token
from app.api.dependencies import get_current_user, require_tenant
from app.core.rls import bypass_rls

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    with bypass_rls():
        tenant_id = data.tenant_id or (str(request.state.tenant.id) if getattr(request.state, 'tenant', None) else None)
        
        query = select(User).where(User.email == data.email, User.is_active == True)
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
            
        result = await db.execute(query)
        user = result.scalar_one_or_none()

    if not user or not user.check_password(data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    token = create_access_token(user)
    return LoginResponse(
        access_token=token,
        user=user.to_dict()
    )


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    _: dict = Depends(require_tenant)
):
    return current_user.to_dict()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_tenant)
):
    tenant = getattr(request.state, 'tenant', None)
    tenant_id = str(tenant.id) if tenant else None
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required"
        )

    # Check for existing user
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    user = User(
        tenant_id=tenant_id,
        email=data.email,
        role=UserRole(data.role) if data.role else UserRole.member,
    )
    user.set_password(data.password)

    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

    return user.to_dict()
