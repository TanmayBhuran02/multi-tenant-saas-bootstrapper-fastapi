from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.domain import Tenant, User, TenantConfig, FeatureFlag, TenantStatus, PlanType
from app.schemas.admin import TenantListResponse, GlobalMetricsResponse, TenantMetricsResponse
from app.api.dependencies import superadmin_only
from app.core.rls import bypass_rls

router = APIRouter()

@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str = None,
    plan: str = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(superadmin_only)
):
    with bypass_rls():
        user_count_sq = (
            select(User.tenant_id, func.count(User.id).label('user_count'))
            .group_by(User.tenant_id)
            .subquery()
        )

        query = (
            select(Tenant, user_count_sq.c.user_count)
            .outerjoin(user_count_sq, Tenant.id == user_count_sq.c.tenant_id)
        )

        if status:
            try:
                query = query.where(Tenant.status == TenantStatus(status))
            except ValueError:
                pass

        if plan:
            try:
                query = query.where(Tenant.plan == PlanType(plan))
            except ValueError:
                pass

        query = query.order_by(Tenant.created_at.desc())

        # Note: in async SQLAlchemy counting is slightly different
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        query = query.offset((page - 1) * per_page).limit(per_page)
        results = await db.execute(query)
        
        tenants = []
        for tenant, user_count in results.all():
            data = tenant.to_dict()
            data['user_count'] = user_count or 0
            tenants.append(data)

    return {
        "tenants": tenants,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }
    }


@router.get("/tenants/{tenant_id}/metrics", response_model=TenantMetricsResponse)
async def tenant_metrics(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(superadmin_only)
):
    with bypass_rls():
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Tenant not found")

        u_count = await db.execute(select(func.count(User.id)).where(User.tenant_id == tenant_id))
        user_count = u_count.scalar_one()

        c_count = await db.execute(select(func.count(TenantConfig.id)).where(TenantConfig.tenant_id == tenant_id))
        config_count = c_count.scalar_one()

        f_res = await db.execute(select(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id))
        flags = f_res.scalars().all()
        flags_enabled = sum(1 for f in flags if f.enabled)
        flags_disabled = len(flags) - flags_enabled

    return {
        "tenant": tenant.to_dict(),
        "metrics": {
            "user_count": user_count,
            "config_count": config_count,
            "feature_flags": {
                "total": len(flags),
                "enabled": flags_enabled,
                "disabled": flags_disabled,
                "flags": [f.to_dict() for f in flags],
            }
        }
    }


@router.get("/metrics", response_model=GlobalMetricsResponse)
async def global_metrics(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(superadmin_only)
):
    with bypass_rls():
        t_count = await db.execute(select(func.count(Tenant.id)))
        total_tenants = t_count.scalar_one()

        u_count = await db.execute(select(func.count(User.id)))
        total_users = u_count.scalar_one()

        p_breakdown = await db.execute(
            select(Tenant.plan, func.count(Tenant.id)).group_by(Tenant.plan)
        )
        plan_breakdown = p_breakdown.all()

        s_breakdown = await db.execute(
            select(Tenant.status, func.count(Tenant.id)).group_by(Tenant.status)
        )
        status_breakdown = s_breakdown.all()

    return {
        "metrics": {
            "total_tenants": total_tenants,
            "total_users": total_users,
            "by_plan": {
                plan.value: count for plan, count in plan_breakdown
            },
            "by_status": {
                status.value: count for status, count in status_breakdown
            }
        }
    }
