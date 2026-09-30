"""Phase 6a — Auth router integration tests."""

import uuid

import pytest

from multi_tenant_bootstrapper.models.domain import (
    Tenant, User, PlanType, TenantStatus, UserRole,
)
from multi_tenant_bootstrapper.core.security import get_password_hash


class TestLogin:

    async def test_login_success(self, client, seed_user, seed_tenant):
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": "member@test.com",
                "password": "password123",
                "tenant_id": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "member@test.com"

    async def test_login_wrong_password(self, client, seed_user, seed_tenant):
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": "member@test.com",
                "password": "wrongpassword",
                "tenant_id": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client, seed_tenant):
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": "nobody@test.com",
                "password": "password123",
                "tenant_id": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 401


class TestRegister:

    async def test_register_success(self, client, seed_tenant, member_headers):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "password123",
            },
            headers={
                **member_headers,
                "X-Tenant-ID": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "member"

    async def test_register_duplicate_email(self, client, seed_user, seed_tenant, member_headers):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "member@test.com",  # already exists
                "password": "password123",
            },
            headers={
                **member_headers,
                "X-Tenant-ID": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 409


class TestProfile:

    async def test_get_profile(self, client, seed_user, seed_tenant, member_headers):
        resp = await client.get(
            "/api/auth/me",
            headers={
                **member_headers,
                "X-Tenant-ID": str(seed_tenant.id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "member@test.com"

    async def test_get_profile_no_auth(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401
