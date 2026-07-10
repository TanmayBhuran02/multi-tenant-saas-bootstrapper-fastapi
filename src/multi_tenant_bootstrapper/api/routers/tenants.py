"""Tenant provisioning and management router."""

import re
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from multi_tenant_bootstrapper.db.session import get_db
from multi_tenant_bootstrapper.models.domain import Tenant, User, PlanType, TenantConfig
from multi_tenant_bootstrapper.schemas.tenants import (
    ProvisionTenantRequest, TenantConfigUpsert, ProvisionTenantResponse,
)
from multi_tenant_bootstrapper.api.dependencies import (
    require_tenant, superadmin_only, require_role, get_current_user_claims,
)
from multi_tenant_bootstrapper.core.rls import bypass_rls
from multi_tenant_bootstrapper.core.flags import seed_flags

router = APIRouter()
_SUBDOMAIN_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$')


@router.post("/provision", response_model=ProvisionTenantResponse, status_code=status.HTTP_201_CREATED)
async def provision_tenant(
    data: ProvisionTenantRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(superadmin_only),
):
    subdomain = data.subdomain.strip().lower()

    if not _SUBDOMAIN_RE.match(subdomain):
        raise HTTPException(status_code=400, detail="Invalid subdomain format")

    try:
        plan = PlanType(data.plan.strip().lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan")

    if len(data.owner_password) < 8:
        raise HTTPException(status_code=400, detail="Password too weak")

    # Check for existing subdomain
    with bypass_rls():
        result = await db.execute(select(Tenant).where(Tenant.subdomain == subdomain))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Subdomain already taken")

    tenant = Tenant(
        slug=subdomain,
        subdomain=subdomain,
        display_name=data.display_name.strip(),
        plan=plan,
    )
    db.add(tenant)
    await db.flush()  # get tenant id

    owner = User(
        tenant_id=tenant.id,
        email=data.owner_email.strip().lower(),
        role='owner',
    )
    owner.set_password(data.owner_password)
    db.add(owner)

    # Seed feature flags
    await seed_flags(db, tenant.id, plan)

    try:
        await db.commit()
        await db.refresh(tenant)
        await db.refresh(owner)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to provision tenant")

    return {"tenant": tenant, "owner": owner.to_dict()}


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(superadmin_only),
):
    with bypass_rls():
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.status = 'deleted'
    await db.commit()
    return None


@router.get("/{tenant_id}/config")
async def get_config(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(require_tenant),
):
    is_superadmin = claims.get('is_superadmin', False)
    current_tenant_id = claims.get('tenant_id')

    if not is_superadmin and str(current_tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    if is_superadmin:
        with bypass_rls():
            result = await db.execute(
                select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
            )
            configs = result.scalars().all()
    else:
        result = await db.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        configs = result.scalars().all()

    return {"configs": [c.to_dict() for c in configs]}


@router.patch("/{tenant_id}/config")
async def upsert_config(
    tenant_id: str,
    data: TenantConfigUpsert,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(require_tenant),
):
    user_role = claims.get('role')
    is_superadmin = claims.get('is_superadmin', False)

    if not is_superadmin and user_role not in ('owner', 'admin'):
        raise HTTPException(status_code=403, detail="Owner or admin role required")

    if is_superadmin:
        with bypass_rls():
            result = await db.execute(
                select(TenantConfig).where(
                    TenantConfig.tenant_id == tenant_id,
                    TenantConfig.key == data.key,
                )
            )
            config = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(TenantConfig).where(
                TenantConfig.tenant_id == tenant_id,
                TenantConfig.key == data.key,
            )
        )
        config = result.scalar_one_or_none()

    if config:
        config.value = data.value
        config.is_secret = data.is_secret
    else:
        config = TenantConfig(
            tenant_id=tenant_id,
            key=data.key,
            value=data.value,
            is_secret=data.is_secret,
        )
        db.add(config)

    await db.commit()
    return {"config": config.to_dict()}


@router.get("/{tenant_id}/users")
async def get_users(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(require_tenant),
):
    is_superadmin = claims.get('is_superadmin', False)
    current_tenant_id = claims.get('tenant_id')

    if not is_superadmin and str(current_tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    if is_superadmin:
        with bypass_rls():
            result = await db.execute(
                select(User).where(User.tenant_id == tenant_id)
            )
            users = result.scalars().all()
    else:
        result = await db.execute(
            select(User).where(User.tenant_id == tenant_id)
        )
        users = result.scalars().all()

    return {"users": [u.to_dict() for u in users]}
