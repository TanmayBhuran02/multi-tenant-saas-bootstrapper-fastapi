"""Phase 4c — Feature flags tests (plan flags, seed_flags, upgrade_flags)."""

import uuid

import pytest
from sqlalchemy import select

from multi_tenant_bootstrapper.config import BootstrapperConfig, set_config, get_config
from multi_tenant_bootstrapper.models.domain import (
    Tenant, FeatureFlag, PlanType, TenantStatus,
)
from multi_tenant_bootstrapper.core.flags import (
    get_plan_flags,
    get_flag_plan_min,
    seed_flags,
    upgrade_flags,
    DEFAULT_PLAN_FLAGS,
)


class TestGetPlanFlags:

    def test_get_plan_flags_defaults(self):
        flags = get_plan_flags()
        assert PlanType.free in flags
        assert "basic_dashboard" in flags[PlanType.free]

    def test_get_plan_flags_config_override(self):
        original = get_config()
        try:
            cfg = BootstrapperConfig(
                PLAN_FLAGS={"free": ["custom_flag"], "starter": ["custom_flag", "another"]},
                _env_file=None,
            )
            set_config(cfg)
            flags = get_plan_flags()
            # String keys should be converted to PlanType enums
            assert PlanType.free in flags
            assert flags[PlanType.free] == ["custom_flag"]
        finally:
            set_config(original)


class TestGetFlagPlanMin:

    def test_get_flag_plan_min(self):
        flag_min = get_flag_plan_min()
        assert flag_min["basic_dashboard"] == PlanType.free
        assert flag_min["csv_export"] == PlanType.starter
        assert flag_min["advanced_analytics"] == PlanType.pro
        assert flag_min["audit_logs"] == PlanType.enterprise


class TestSeedFlags:

    @pytest.fixture
    async def flag_tenant(self, db_session):
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="flags-seed",
            subdomain="flags-seed",
            display_name="Flags Seed",
            plan=PlanType.free,
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant

    async def test_seed_flags_creates_all(self, db_session, flag_tenant):
        """seed_flags should create all enterprise flags, enabled/disabled by plan."""
        created = await seed_flags(db_session, flag_tenant.id, PlanType.free)
        await db_session.commit()

        # Should have created all enterprise-level flags
        enterprise_flags = DEFAULT_PLAN_FLAGS[PlanType.enterprise]
        assert len(created) == len(enterprise_flags)

        # Only basic_dashboard should be enabled for free plan
        enabled = [f for f in created if f.enabled]
        assert len(enabled) == len(DEFAULT_PLAN_FLAGS[PlanType.free])

    async def test_seed_flags_skips_existing(self, db_session, flag_tenant):
        """Calling seed_flags twice should not duplicate flags."""
        await seed_flags(db_session, flag_tenant.id, PlanType.free)
        await db_session.commit()

        # Second call should create nothing
        created = await seed_flags(db_session, flag_tenant.id, PlanType.free)
        assert len(created) == 0


class TestUpgradeFlags:

    @pytest.fixture
    async def upgrade_tenant(self, db_session):
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="flags-upgrade",
            subdomain="flags-upgrade",
            display_name="Flags Upgrade",
            plan=PlanType.free,
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant

    async def test_upgrade_flags_enables_new(self, db_session, upgrade_tenant):
        """Upgrading from free to pro should enable pro-level flags."""
        # First seed free flags
        await seed_flags(db_session, upgrade_tenant.id, PlanType.free)
        await db_session.commit()

        # Upgrade to pro
        upgraded = await upgrade_flags(db_session, upgrade_tenant.id, PlanType.pro)
        await db_session.commit()

        # Check that pro flags are now enabled
        result = await db_session.execute(
            select(FeatureFlag).where(
                FeatureFlag.tenant_id == upgrade_tenant.id,
                FeatureFlag.flag_name == "advanced_analytics",
            )
        )
        flag = result.scalar_one()
        assert flag.enabled is True

    async def test_upgrade_flags_seeds_missing(self, db_session, upgrade_tenant):
        """upgrade_flags should also seed any missing flags."""
        # Start with no flags at all, then upgrade to starter
        upgraded = await upgrade_flags(db_session, upgrade_tenant.id, PlanType.starter)
        await db_session.commit()

        # All enterprise flags should exist
        result = await db_session.execute(
            select(FeatureFlag).where(FeatureFlag.tenant_id == upgrade_tenant.id)
        )
        flags = result.scalars().all()
        enterprise_flags = DEFAULT_PLAN_FLAGS[PlanType.enterprise]
        assert len(flags) == len(enterprise_flags)
