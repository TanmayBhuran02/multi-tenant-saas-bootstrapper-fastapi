"""Feature flag definitions, seeding, and upgrade logic.

The default ``PLAN_FLAGS`` mapping can be overridden by providing a
custom mapping via ``BootstrapperConfig.PLAN_FLAGS``.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from multi_tenant_bootstrapper.models.domain import PlanType, FeatureFlag
from multi_tenant_bootstrapper.config import get_config

# ── Default Flag Definitions ─────────────────────────────────────────────────

DEFAULT_PLAN_FLAGS: dict[PlanType, list[str]] = {
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


def get_plan_flags() -> dict[PlanType, list[str]]:
    """Return the active PLAN_FLAGS, respecting config overrides."""
    config = get_config()
    if config.PLAN_FLAGS is not None:
        # Convert string keys to PlanType enums
        return {
            PlanType(k) if isinstance(k, str) else k: v
            for k, v in config.PLAN_FLAGS.items()
        }
    return DEFAULT_PLAN_FLAGS


def get_flag_plan_min() -> dict[str, PlanType]:
    """Build a flag→minimum-plan mapping from the active PLAN_FLAGS."""
    plan_flags = get_plan_flags()
    flag_plan_min: dict[str, PlanType] = {}
    for plan in [PlanType.free, PlanType.starter, PlanType.pro, PlanType.enterprise]:
        for flag in plan_flags.get(plan, []):
            if flag not in flag_plan_min:
                flag_plan_min[flag] = plan
    return flag_plan_min


# Pre-compute for the default flags (used when no config override)
FLAG_PLAN_MIN: dict[str, PlanType] = {}
for _plan in [PlanType.free, PlanType.starter, PlanType.pro, PlanType.enterprise]:
    for _flag in DEFAULT_PLAN_FLAGS[_plan]:
        if _flag not in FLAG_PLAN_MIN:
            FLAG_PLAN_MIN[_flag] = _plan


async def seed_flags(db: AsyncSession, tenant_id: str, plan: PlanType) -> list[FeatureFlag]:
    """Seed feature flags for a tenant based on their plan.

    Creates all known flags (enabled or disabled based on plan),
    skipping any that already exist for the tenant.
    """
    if isinstance(plan, str):
        plan = PlanType(plan)

    plan_flags = get_plan_flags()
    flag_plan_min = get_flag_plan_min()

    enabled_flags = set(plan_flags.get(plan, []))
    all_flags = set(plan_flags.get(PlanType.enterprise, []))

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
            plan_min=flag_plan_min.get(flag_name),
        )
        db.add(flag)
        created.append(flag)

    return created


async def upgrade_flags(
    db: AsyncSession, tenant_id: str, new_plan: PlanType
) -> list[FeatureFlag]:
    """Upgrade feature flags when a tenant changes plans.

    Enables flags that the new plan includes and seeds any missing flags.
    """
    if isinstance(new_plan, str):
        new_plan = PlanType(new_plan)

    plan_flags = get_plan_flags()
    new_enabled = set(plan_flags.get(new_plan, []))
    upgraded = []

    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id)
    )
    flags = result.scalars().all()

    for flag in flags:
        if flag.flag_name in new_enabled and not flag.enabled:
            flag.enabled = True
            upgraded.append(flag)

    created = await seed_flags(db, tenant_id, new_plan)
    upgraded.extend(created)

    return upgraded
