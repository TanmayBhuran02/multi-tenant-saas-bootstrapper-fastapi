"""Phase 2 — Model tests.

Tests for base mixins (SerializerMixin, TimestampMixin), domain models,
and PostgreSQL-specific behavior (UUID gen, JSONB, constraints, cascades).
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from multi_tenant_bootstrapper.models.base import Base
from multi_tenant_bootstrapper.models.domain import (
    Tenant, TenantConfig, User, FeatureFlag,
    PlanType, TenantStatus, UserRole,
)
from multi_tenant_bootstrapper.core.security import get_password_hash


# ── 2a: Enum Values ─────────────────────────────────────────────────────────

class TestEnums:
    def test_plan_type_enum_values(self):
        assert set(e.value for e in PlanType) == {"free", "starter", "pro", "enterprise"}

    def test_tenant_status_enum_values(self):
        assert set(e.value for e in TenantStatus) == {"active", "suspended", "deleted"}

    def test_user_role_enum_values(self):
        assert set(e.value for e in UserRole) == {"owner", "admin", "member"}


# ── 2b: SerializerMixin ─────────────────────────────────────────────────────

class TestSerializerMixin:

    @pytest.fixture
    async def tenant_in_db(self, db_session):
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="serialize-test",
            subdomain="serialize-test",
            display_name="Serialize Test",
            plan=PlanType.free,
            status=TenantStatus.active,
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant

    async def test_to_dict_basic(self, tenant_in_db):
        d = tenant_in_db.to_dict()
        assert "slug" in d
        assert "display_name" in d
        assert d["slug"] == "serialize-test"

    async def test_to_dict_excludes_fields(self, tenant_in_db):
        d = tenant_in_db.to_dict(exclude={"slug"})
        assert "slug" not in d
        assert "display_name" in d

    async def test_to_dict_uuid_serialization(self, tenant_in_db):
        d = tenant_in_db.to_dict()
        assert isinstance(d["id"], str)
        # Validate it's a valid UUID string
        uuid.UUID(d["id"])

    async def test_to_dict_datetime_serialization(self, tenant_in_db):
        d = tenant_in_db.to_dict()
        assert isinstance(d["created_at"], str)
        # Should be ISO format
        datetime.fromisoformat(d["created_at"])

    async def test_to_dict_enum_serialization(self, tenant_in_db):
        d = tenant_in_db.to_dict()
        assert d["plan"] == "free"
        assert d["status"] == "active"


# ── 2c: Domain Model Behavior ───────────────────────────────────────────────

class TestTenantModel:

    async def test_tenant_repr(self, db_session):
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="repr-test",
            subdomain="repr-test",
            display_name="Repr Test",
            plan=PlanType.starter,
        )
        db_session.add(tenant)
        await db_session.commit()
        assert "repr-test" in repr(tenant)
        assert "starter" in repr(tenant)


class TestTenantConfigModel:

    @pytest.fixture
    async def tenant_for_config(self, db_session):
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="config-test",
            subdomain="config-test",
            display_name="Config Test",
            plan=PlanType.free,
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant

    async def test_tenant_config_to_dict_hides_secrets(self, db_session, tenant_for_config):
        config = TenantConfig(
            id=uuid.uuid4(),
            tenant_id=tenant_for_config.id,
            key="api_key",
            value={"secret": "value123"},
            is_secret=True,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)
        d = config.to_dict()
        assert d["value"] == "********"

    async def test_tenant_config_to_dict_shows_non_secrets(self, db_session, tenant_for_config):
        config = TenantConfig(
            id=uuid.uuid4(),
            tenant_id=tenant_for_config.id,
            key="theme",
            value={"color": "blue"},
            is_secret=False,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)
        d = config.to_dict()
        assert d["value"] == {"color": "blue"}


class TestUserModel:

    @pytest.fixture
    async def tenant_for_user(self, db_session):
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="user-test",
            subdomain="user-test",
            display_name="User Test",
            plan=PlanType.free,
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant

    async def test_user_set_password(self, tenant_for_user):
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_for_user.id,
            email="setpw@test.com",
            hashed_password="placeholder",
            role=UserRole.member,
        )
        user.set_password("mypassword123")
        assert user.hashed_password.startswith("$2b$")

    async def test_user_check_password_correct(self, tenant_for_user):
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_for_user.id,
            email="checkpw@test.com",
            hashed_password="placeholder",
            role=UserRole.member,
        )
        user.set_password("correct_password")
        assert user.check_password("correct_password") is True

    async def test_user_check_password_wrong(self, tenant_for_user):
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_for_user.id,
            email="wrongpw@test.com",
            hashed_password="placeholder",
            role=UserRole.member,
        )
        user.set_password("correct_password")
        assert user.check_password("wrong_password") is False

    async def test_user_to_dict_excludes_hashed_password(self, db_session, tenant_for_user):
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_for_user.id,
            email="exclude@test.com",
            hashed_password=get_password_hash("password123"),
            role=UserRole.member,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        d = user.to_dict()
        assert "hashed_password" not in d
        assert "email" in d


# ── 2d: PostgreSQL-Specific Tests ────────────────────────────────────────────

class TestPostgreSQLSpecific:

    async def test_tenant_uuid_auto_generated(self, db_session):
        """Verify gen_random_uuid() server default generates a UUID."""
        tenant = Tenant(
            slug="uuid-test",
            subdomain="uuid-test",
            display_name="UUID Test",
            plan=PlanType.free,
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        assert tenant.id is not None
        assert isinstance(tenant.id, uuid.UUID)

    async def test_tenant_slug_unique_constraint(self, db_session):
        """Duplicate slugs should raise IntegrityError."""
        t1 = Tenant(
            id=uuid.uuid4(),
            slug="unique-slug",
            subdomain="unique-sub-1",
            display_name="T1",
            plan=PlanType.free,
        )
        db_session.add(t1)
        await db_session.commit()

        t2 = Tenant(
            id=uuid.uuid4(),
            slug="unique-slug",  # duplicate
            subdomain="unique-sub-2",
            display_name="T2",
            plan=PlanType.free,
        )
        db_session.add(t2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_user_tenant_email_unique_constraint(self, db_session):
        """Same email in same tenant should raise IntegrityError."""
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="uc-email",
            subdomain="uc-email",
            display_name="UC Email",
            plan=PlanType.free,
        )
        db_session.add(tenant)
        await db_session.commit()

        u1 = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="dup@test.com",
            hashed_password=get_password_hash("pw123456"),
            role=UserRole.member,
        )
        db_session.add(u1)
        await db_session.commit()

        u2 = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="dup@test.com",  # duplicate in same tenant
            hashed_password=get_password_hash("pw123456"),
            role=UserRole.member,
        )
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_tenant_config_jsonb_round_trip(self, db_session):
        """JSONB values should store and retrieve correctly."""
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="jsonb-test",
            subdomain="jsonb-test",
            display_name="JSONB Test",
            plan=PlanType.free,
        )
        db_session.add(tenant)
        await db_session.commit()

        complex_value = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "bool": True,
            "null_val": None,
        }
        config = TenantConfig(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            key="complex_config",
            value=complex_value,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.value == complex_value
        assert config.value["nested"]["key"] == "value"
        assert config.value["list"] == [1, 2, 3]

    async def test_cascade_delete_tenant_deletes_users(self, db_session):
        """Deleting a tenant should cascade-delete its users."""
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="cascade-test",
            subdomain="cascade-test",
            display_name="Cascade Test",
            plan=PlanType.free,
        )
        db_session.add(tenant)
        await db_session.commit()

        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="cascade@test.com",
            hashed_password=get_password_hash("pw123456"),
            role=UserRole.member,
        )
        db_session.add(user)
        await db_session.commit()

        user_id = user.id
        await db_session.delete(tenant)
        await db_session.commit()

        result = await db_session.execute(select(User).where(User.id == user_id))
        assert result.scalar_one_or_none() is None

    async def test_timestamp_mixin_auto_populates(self, db_session):
        """created_at and updated_at should be auto-populated on insert."""
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="timestamp-test",
            subdomain="timestamp-test",
            display_name="Timestamp Test",
            plan=PlanType.free,
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)

        assert tenant.created_at is not None
        assert tenant.updated_at is not None
        assert isinstance(tenant.created_at, datetime)
        assert isinstance(tenant.updated_at, datetime)
