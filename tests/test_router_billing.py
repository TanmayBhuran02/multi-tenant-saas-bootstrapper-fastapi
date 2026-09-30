"""Phase 6d — Billing router integration tests."""

import uuid

import pytest

from multi_tenant_bootstrapper.models.domain import (
    Tenant, User, PlanType, TenantStatus, UserRole,
)
from multi_tenant_bootstrapper.core.security import get_password_hash
from multi_tenant_bootstrapper.core.flags import seed_flags


class TestGetPlan:

    async def test_get_plan(self, client, seed_tenant, seed_user, member_headers):
        resp = await client.get(
            "/api/billing/plan",
            headers={
                **member_headers,
                "X-Tenant-ID": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "free"
        assert "limits" in data
        assert "features" in data
        assert "usage" in data
        assert "all_plans" in data


class TestUpgradePlan:

    async def test_upgrade_plan_success(self, client, db_session, superadmin_headers):
        # Create a dedicated tenant for upgrade
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="upgrade-test",
            subdomain="upgrade-test",
            display_name="Upgrade Test",
            plan=PlanType.free,
            status=TenantStatus.active,
        )
        db_session.add(tenant)
        await db_session.commit()

        # Seed initial flags
        await seed_flags(db_session, tenant.id, PlanType.free)
        await db_session.commit()

        resp = await client.post(
            "/api/billing/upgrade",
            json={
                "tenant_id": str(tenant.id),
                "new_plan": "pro",
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["old_plan"] == "free"
        assert data["new_plan"] == "pro"
        assert isinstance(data["new_flags_enabled"], list)

    async def test_upgrade_plan_invalid(self, client, seed_tenant, superadmin_headers):
        resp = await client.post(
            "/api/billing/upgrade",
            json={
                "tenant_id": str(seed_tenant.id),
                "new_plan": "nonexistent_plan",
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 400

    async def test_upgrade_plan_tenant_not_found(self, client, superadmin_headers):
        resp = await client.post(
            "/api/billing/upgrade",
            json={
                "tenant_id": str(uuid.uuid4()),
                "new_plan": "pro",
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 404

    async def test_upgrade_plan_non_superadmin(self, client, seed_tenant, member_headers):
        resp = await client.post(
            "/api/billing/upgrade",
            json={
                "tenant_id": str(seed_tenant.id),
                "new_plan": "pro",
            },
            headers=member_headers,
        )
        assert resp.status_code == 403
