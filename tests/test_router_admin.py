"""Phase 6e — Admin router integration tests."""

import uuid

import pytest

from multi_tenant_bootstrapper.models.domain import (
    Tenant, User, TenantConfig, FeatureFlag,
    PlanType, TenantStatus, UserRole,
)
from multi_tenant_bootstrapper.core.security import get_password_hash
from multi_tenant_bootstrapper.core.flags import seed_flags


class TestListTenants:

    async def test_list_tenants(self, client, seed_tenant, superadmin_headers):
        resp = await client.get(
            "/api/admin/tenants",
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tenants" in data
        assert "pagination" in data
        assert data["pagination"]["total"] >= 1

    async def test_list_tenants_filter_by_plan(self, client, db_session, superadmin_headers):
        # Create tenants with different plans
        for plan in [PlanType.free, PlanType.starter]:
            tenant = Tenant(
                id=uuid.uuid4(),
                slug=f"filter-{plan.value}",
                subdomain=f"filter-{plan.value}",
                display_name=f"Filter {plan.value}",
                plan=plan,
                status=TenantStatus.active,
            )
            db_session.add(tenant)
        await db_session.commit()

        resp = await client.get(
            "/api/admin/tenants?plan=starter",
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # All returned tenants should be starter plan
        for t in data["tenants"]:
            assert t["plan"] == "starter"


class TestTenantMetrics:

    async def test_tenant_metrics(self, client, db_session, seed_tenant, seed_user, superadmin_headers):
        # Seed some flags and config
        await seed_flags(db_session, seed_tenant.id, PlanType.free)
        config = TenantConfig(
            id=uuid.uuid4(),
            tenant_id=seed_tenant.id,
            key="test_key",
            value={"x": 1},
        )
        db_session.add(config)
        await db_session.commit()

        resp = await client.get(
            f"/api/admin/tenants/{seed_tenant.id}/metrics",
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tenant" in data
        assert "metrics" in data
        metrics = data["metrics"]
        assert metrics["user_count"] >= 1
        assert metrics["config_count"] >= 1
        assert "feature_flags" in metrics
        assert metrics["feature_flags"]["total"] > 0

    async def test_tenant_metrics_not_found(self, client, superadmin_headers):
        resp = await client.get(
            f"/api/admin/tenants/{uuid.uuid4()}/metrics",
            headers=superadmin_headers,
        )
        assert resp.status_code == 404


class TestGlobalMetrics:

    async def test_global_metrics(self, client, seed_tenant, seed_user, superadmin_headers):
        resp = await client.get(
            "/api/admin/metrics",
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        metrics = data["metrics"]
        assert metrics["total_tenants"] >= 1
        assert metrics["total_users"] >= 1
        assert "by_plan" in metrics
        assert "by_status" in metrics


class TestAdminAuth:

    async def test_admin_requires_superadmin(self, client, member_headers):
        resp = await client.get(
            "/api/admin/tenants",
            headers=member_headers,
        )
        assert resp.status_code == 403

    async def test_admin_no_auth(self, client):
        resp = await client.get("/api/admin/tenants")
        assert resp.status_code == 401
