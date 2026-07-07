from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.domain import PlanType, FeatureFlag

PLAN_FLAGS = {
    PlanType.free: [
        'basic_dashboard',
    ],
    PlanType.starter: [
        'basic_dashboard',
        'csv_export',
        'api_access',
    ],
    PlanType.pro: [
        'basic_dashboard',
        'csv_export',
        'api_access',
        'advanced_analytics',
        'webhooks',
        'sso',
    ],
    PlanType.enterprise: [
        'basic_dashboard',
        'csv_export',
        'api_access',
        'advanced_analytics',
        'webhooks',
        'sso',
        'audit_logs',
        'custom_domain',
        'dedicated_support',
    ],
}

FLAG_PLAN_MIN = {}
for plan in [PlanType.free, PlanType.starter, PlanType.pro, PlanType.enterprise]:
    for flag in PLAN_FLAGS[plan]:
        if flag not in FLAG_PLAN_MIN:
            FLAG_PLAN_MIN[flag] = plan


async def seed_flags(db: AsyncSession, tenant_id: str, plan: PlanType):
    if isinstance(plan, str):
        plan = PlanType(plan)

    enabled_flags = set(PLAN_FLAGS.get(plan, []))
    all_flags = set(PLAN_FLAGS[PlanType.enterprise])

    created = []
    for flag_name in all_flags:
        result = await db.execute(
            select(FeatureFlag).where(
                FeatureFlag.tenant_id == tenant_id,
                FeatureFlag.flag_name == flag_name
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            continue

        flag = FeatureFlag(
            tenant_id=tenant_id,
            flag_name=flag_name,
            enabled=flag_name in enabled_flags,
            plan_min=FLAG_PLAN_MIN.get(flag_name),
        )
        db.add(flag)
        created.append(flag)

    return created


async def upgrade_flags(db: AsyncSession, tenant_id: str, new_plan: PlanType):
    if isinstance(new_plan, str):
        new_plan = PlanType(new_plan)

    new_enabled = set(PLAN_FLAGS.get(new_plan, []))
    upgraded = []

    result = await db.execute(select(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id))
    flags = result.scalars().all()

    for flag in flags:
        if flag.flag_name in new_enabled and not flag.enabled:
            flag.enabled = True
            upgraded.append(flag)

    created = await seed_flags(db, tenant_id, new_plan)
    upgraded.extend(created)

    return upgraded
