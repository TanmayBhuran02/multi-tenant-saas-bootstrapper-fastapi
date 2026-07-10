"""Billing and plan management router."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from multi_tenant_bootstrapper.db.session import get_db
from multi_tenant_bootstrapper.models.domain import Tenant, User, PlanType
from multi_tenant_bootstrapper.schemas.billing import (
    UpgradePlanRequest, PlanResponse, UpgradePlanResponse,
)
from multi_tenant_bootstrapper.api.dependencies import require_tenant, superadmin_only
from multi_tenant_bootstrapper.core.plans import (
    get_plan_limits, get_plan_features, get_all_plan_limits,
)
from multi_tenant_bootstrapper.core.flags import upgrade_flags
from multi_tenant_bootstrapper.core.rls import bypass_rls

router = APIRouter()


@router.get("/plan", response_model=PlanResponse)
async def get_plan(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_tenant),
):
    tenant = getattr(request.state, 'tenant', None)
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant context required")

    plan_name = tenant.plan.value if hasattr(tenant.plan, 'value') else tenant.plan
    limits = get_plan_limits(plan_name)
    features = get_plan_features(plan_name)

    result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant.id)
    )
    user_count = result.scalar_one()

    usage = {
        'users': user_count,
        'api_calls': 0,
    }

    return PlanResponse(
        plan=plan_name,
        limits=limits,
        features=features,
        usage=usage,
        all_plans=get_all_plan_limits(),
    )


@router.post("/upgrade", response_model=UpgradePlanResponse)
async def upgrade_plan(
    data: UpgradePlanRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(superadmin_only),
):
    try:
        new_plan = PlanType(data.new_plan.strip().lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan")

    with bypass_rls():
        result = await db.execute(select(Tenant).where(Tenant.id == data.tenant_id))
        tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    old_plan = tenant.plan
    tenant.plan = new_plan

    try:
        upgraded_flags = await upgrade_flags(db, tenant.id, new_plan)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to upgrade plan")

    return UpgradePlanResponse(
        tenant=tenant.to_dict(),
        old_plan=old_plan.value,
        new_plan=new_plan.value,
        new_flags_enabled=[f.flag_name for f in upgraded_flags],
    )
