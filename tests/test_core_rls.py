"""Phase 4d — RLS (Row-Level Security) tests."""

import uuid

import pytest
from sqlalchemy import select

from multi_tenant_bootstrapper.models.domain import (
    Tenant, User, PlanType, TenantStatus, UserRole,
)
from multi_tenant_bootstrapper.core.rls import (
    set_tenant_id,
    get_tenant_id,
    clear_tenant_id,
    bypass_rls,
    _has_tenant_id_column,
)
from multi_tenant_bootstrapper.core.security import get_password_hash


class TestContextVars:

    def test_set_get_clear_tenant_id(self):
        clear_tenant_id()
        assert get_tenant_id() is None

        set_tenant_id("tenant-123")
        assert get_tenant_id() == "tenant-123"

        clear_tenant_id()
        assert get_tenant_id() is None

    def test_bypass_rls_context_manager(self):
        """bypass_rls() should set and reset the bypass flag."""
        from multi_tenant_bootstrapper.core.rls import _bypass_rls

        assert _bypass_rls.get() is False
        with bypass_rls():
            assert _bypass_rls.get() is True
        assert _bypass_rls.get() is False


class TestHasTenantIdColumn:

    def test_has_tenant_id_column_true(self):
        """User model has tenant_id column."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        assert _has_tenant_id_column(mapper) is True

    def test_has_tenant_id_column_false(self):
        """Tenant model does NOT have tenant_id column."""
        from sqlalchemy import inspect
        mapper = inspect(Tenant)
        assert _has_tenant_id_column(mapper) is False


class TestRLSFiltering:
    """Test that the RLS event listener actually filters queries by tenant."""

    @pytest.fixture
    async def two_tenants_with_users(self, db_session):
        """Create two tenants, each with a user."""
        t1 = Tenant(
            id=uuid.uuid4(),
            slug="rls-t1",
            subdomain="rls-t1",
            display_name="RLS T1",
            plan=PlanType.free,
            status=TenantStatus.active,
        )
        t2 = Tenant(
            id=uuid.uuid4(),
            slug="rls-t2",
            subdomain="rls-t2",
            display_name="RLS T2",
            plan=PlanType.free,
            status=TenantStatus.active,
        )
        db_session.add_all([t1, t2])
        await db_session.commit()

        u1 = User(
            id=uuid.uuid4(),
            tenant_id=t1.id,
            email="user1@rls.com",
            hashed_password=get_password_hash("pw123456"),
            role=UserRole.member,
        )
        u2 = User(
            id=uuid.uuid4(),
            tenant_id=t2.id,
            email="user2@rls.com",
            hashed_password=get_password_hash("pw123456"),
            role=UserRole.member,
        )
        db_session.add_all([u1, u2])
        await db_session.commit()

        return t1, t2, u1, u2

    async def test_rls_filters_queries_by_tenant(self, db_session, two_tenants_with_users):
        """With tenant set, select(User) only returns that tenant's users."""
        t1, t2, u1, u2 = two_tenants_with_users

        set_tenant_id(str(t1.id))
        try:
            result = await db_session.execute(select(User))
            users = result.scalars().all()
            assert len(users) == 1
            assert users[0].email == "user1@rls.com"
        finally:
            clear_tenant_id()

    async def test_rls_bypass_returns_all(self, db_session, two_tenants_with_users):
        """Inside bypass_rls(), all users returned regardless of tenant."""
        t1, t2, u1, u2 = two_tenants_with_users

        set_tenant_id(str(t1.id))
        try:
            with bypass_rls():
                result = await db_session.execute(select(User))
                users = result.scalars().all()
                assert len(users) == 2
        finally:
            clear_tenant_id()
