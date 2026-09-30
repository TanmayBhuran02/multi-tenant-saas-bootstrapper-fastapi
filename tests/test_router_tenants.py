"""Phase 6b — Tenants router integration tests."""

import uuid

import pytest

from multi_tenant_bootstrapper.models.domain import (
    Tenant, User, TenantConfig, PlanType, TenantStatus, UserRole,
)
from multi_tenant_bootstrapper.core.security import get_password_hash


class TestProvisionTenant:

    async def test_provision_tenant_success(self, client, superadmin_headers):
        resp = await client.post(
            "/api/tenants/provision",
            json={
                "display_name": "New Corp",
                "subdomain": "new-corp",
                "plan": "starter",
                "owner_email": "owner@newcorp.com",
                "owner_password": "strongpass123",
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tenant"]["subdomain"] == "new-corp"
        assert data["tenant"]["plan"] == "starter"
        assert data["owner"]["email"] == "owner@newcorp.com"

    async def test_provision_invalid_subdomain(self, client, superadmin_headers):
        resp = await client.post(
            "/api/tenants/provision",
            json={
                "display_name": "Bad Sub",
                "subdomain": "X",  # too short, invalid
                "plan": "free",
                "owner_email": "owner@bad.com",
                "owner_password": "strongpass123",
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 400

    async def test_provision_duplicate_subdomain(self, client, seed_tenant, superadmin_headers):
        resp = await client.post(
            "/api/tenants/provision",
            json={
                "display_name": "Dup Tenant",
                "subdomain": "test-tenant",  # already exists from seed_tenant
                "plan": "free",
                "owner_email": "owner@dup.com",
                "owner_password": "strongpass123",
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 409

    async def test_provision_weak_password(self, client, superadmin_headers):
        resp = await client.post(
            "/api/tenants/provision",
            json={
                "display_name": "Weak PW",
                "subdomain": "weak-pw-test",
                "plan": "free",
                "owner_email": "owner@weak.com",
                "owner_password": "short",  # < 8 chars
            },
            headers=superadmin_headers,
        )
        assert resp.status_code == 400

    async def test_provision_non_superadmin(self, client, member_headers):
        resp = await client.post(
            "/api/tenants/provision",
            json={
                "display_name": "No Auth",
                "subdomain": "no-auth-test",
                "plan": "free",
                "owner_email": "owner@noauth.com",
                "owner_password": "strongpass123",
            },
            headers=member_headers,
        )
        assert resp.status_code == 403


class TestDeleteTenant:

    async def test_delete_tenant(self, client, db_session, superadmin_headers):
        """Delete sets tenant status to 'deleted'."""
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="delete-me",
            subdomain="delete-me",
            display_name="Delete Me",
            plan=PlanType.free,
            status=TenantStatus.active,
        )
        db_session.add(tenant)
        await db_session.commit()

        resp = await client.delete(
            f"/api/tenants/{tenant.id}",
            headers=superadmin_headers,
        )
        assert resp.status_code == 204


class TestTenantConfig:

    async def test_get_tenant_config(self, client, seed_tenant, owner_headers):
        resp = await client.get(
            f"/api/tenants/{seed_tenant.id}/config",
            headers={
                **owner_headers,
                "X-Tenant-ID": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 200
        assert "configs" in resp.json()

    async def test_upsert_tenant_config(self, client, seed_tenant, owner_headers):
        resp = await client.patch(
            f"/api/tenants/{seed_tenant.id}/config",
            json={
                "key": "theme_color",
                "value": "blue",
                "is_secret": False,
            },
            headers={
                **owner_headers,
                "X-Tenant-ID": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 200
        assert resp.json()["config"]["key"] == "theme_color"


class TestTenantUsers:

    async def test_get_tenant_users(self, client, seed_tenant, seed_user, owner_headers):
        resp = await client.get(
            f"/api/tenants/{seed_tenant.id}/users",
            headers={
                **owner_headers,
                "X-Tenant-ID": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert len(data["users"]) >= 1

    async def test_cross_tenant_access_denied(self, client, db_session, member_headers):
        """Accessing another tenant's users should be denied."""
        other_tenant = Tenant(
            id=uuid.uuid4(),
            slug="other-tenant",
            subdomain="other-tenant",
            display_name="Other Tenant",
            plan=PlanType.free,
            status=TenantStatus.active,
        )
        db_session.add(other_tenant)
        await db_session.commit()

        resp = await client.get(
            f"/api/tenants/{other_tenant.id}/users",
            headers=member_headers,
        )
        assert resp.status_code == 403
