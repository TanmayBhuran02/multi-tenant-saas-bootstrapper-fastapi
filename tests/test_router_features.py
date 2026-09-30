"""Phase 6c — Features router integration tests."""

import uuid

import pytest

from multi_tenant_bootstrapper.models.domain import (
    Tenant, FeatureFlag, PlanType, TenantStatus,
)
from multi_tenant_bootstrapper.core.flags import seed_flags


class TestListFlags:

    async def test_list_flags(self, client, db_session, seed_tenant, member_headers):
        # Seed some flags first
        await seed_flags(db_session, seed_tenant.id, PlanType.free)
        await db_session.commit()

        resp = await client.get(
            "/api/features/",
            headers={
                **member_headers,
                "X-Tenant-ID": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "flags" in data
        assert len(data["flags"]) > 0


class TestToggleFlag:

    @pytest.fixture
    async def seeded_flags(self, db_session, seed_tenant):
        await seed_flags(db_session, seed_tenant.id, PlanType.free)
        await db_session.commit()
        return seed_tenant

    async def test_toggle_flag_enable(self, client, seeded_flags, superadmin_headers):
        tenant = seeded_flags
        resp = await client.patch(
            "/api/features/csv_export",
            json={
                "enabled": True,
                "tenant_id": str(tenant.id),
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["flag"]["enabled"] is True

    async def test_toggle_flag_not_found(self, client, seed_tenant, superadmin_headers):
        resp = await client.patch(
            "/api/features/nonexistent_flag",
            json={
                "enabled": True,
                "tenant_id": str(seed_tenant.id),
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 404

    async def test_toggle_flag_no_tenant_id(self, client, superadmin_headers):
        resp = await client.patch(
            "/api/features/basic_dashboard",
            json={
                "enabled": True,
                # no tenant_id
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 400
