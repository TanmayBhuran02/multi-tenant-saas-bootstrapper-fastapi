from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.domain import FeatureFlag
from app.schemas.features import ToggleFlagRequest
from app.api.dependencies import require_tenant, superadmin_only
from app.core.rls import bypass_rls

router = APIRouter()

@router.get("/")
async def list_flags(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_tenant)
):
    result = await db.execute(select(FeatureFlag))
    flags = result.scalars().all()
    return {"flags": [f.to_dict() for f in flags]}

@router.patch("/{flag_name}")
async def toggle_flag(
    flag_name: str,
    data: ToggleFlagRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(superadmin_only)
):
    tenant_id = data.tenant_id or request.query_params.get('tenant_id')
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id required")

    with bypass_rls():
        result = await db.execute(
            select(FeatureFlag).where(
                FeatureFlag.tenant_id == tenant_id,
                FeatureFlag.flag_name == flag_name
            )
        )
        flag = result.scalar_one_or_none()

    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    flag.enabled = data.enabled
    if data.payload is not None:
        flag.payload = data.payload

    await db.commit()
    return {"flag": flag.to_dict()}
