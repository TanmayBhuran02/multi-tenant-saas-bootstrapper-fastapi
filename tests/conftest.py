"""Shared pytest fixtures for the multi-tenant SaaS bootstrapper test suite.

Provides:
- A test PostgreSQL database (saas_bootstrapper_test)
- Table creation/teardown per session
- Table truncation after each test for isolation
- Seeded tenants, users, and JWT tokens for integration tests
"""

import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Set test env vars BEFORE importing any app modules
os.environ["SAAS_DATABASE_URL"] = "postgresql+asyncpg://postgres:root@localhost:5432/saas_bootstrapper_test"
os.environ["SAAS_SECRET_KEY"] = "test-secret-key"
os.environ["SAAS_JWT_SECRET_KEY"] = "test-jwt-secret"
os.environ["SAAS_SUPERADMIN_SECRET"] = "test-superadmin-secret"
os.environ["SAAS_DEBUG"] = "true"

from multi_tenant_bootstrapper.config import BootstrapperConfig, set_config, get_config
from multi_tenant_bootstrapper.models.base import Base
from multi_tenant_bootstrapper.models.domain import (
    Tenant, User, TenantConfig, FeatureFlag,
    PlanType, TenantStatus, UserRole,
)
from multi_tenant_bootstrapper.core.security import create_access_token, get_password_hash
from multi_tenant_bootstrapper.core.rls import clear_tenant_id
from multi_tenant_bootstrapper.db.session import init_db, get_db
from multi_tenant_bootstrapper.app_factory import create_app


# ── Test Config ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_config() -> BootstrapperConfig:
    """Create a test configuration pointing at the test database."""
    cfg = BootstrapperConfig(
        DATABASE_URL="postgresql+asyncpg://postgres:root@localhost:5432/saas_bootstrapper_test",
        SECRET_KEY="test-secret-key",
        JWT_SECRET_KEY="test-jwt-secret",
        JWT_ACCESS_TOKEN_EXPIRES=86400,
        SUPERADMIN_SECRET="test-superadmin-secret",
        DEBUG=True,
    )
    set_config(cfg)
    return cfg


# ── Database Engine ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine(test_config) -> AsyncEngine:
    """Create a shared async engine for the test session."""
    eng = create_async_engine(
        test_config.DATABASE_URL,
        poolclass=NullPool,
        echo=False,
        future=True,
    )
    return eng


@pytest.fixture(scope="session")
def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to the test engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# ── Table Lifecycle ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def create_tables(engine):
    """Create all tables at session start, drop at session end."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_tables(session_factory):
    """Truncate all tables after each test for a clean slate."""
    yield  # test runs here
    clear_tenant_id()
    async with session_factory() as session:
        table_names = ", ".join(
            f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
        )
        if table_names:
            await session.execute(text(f"TRUNCATE {table_names} CASCADE"))
            await session.commit()


# ── Database Session ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh async session for each test."""
    async with session_factory() as session:
        yield session


# ── FastAPI App ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app(test_config):
    """Create the FastAPI app with test configuration."""
    application = create_app(
        config=test_config,
        include_frontend=False,
    )
    return application


# ── Override get_db dependency ───────────────────────────────────────────────

@pytest.fixture(autouse=True)
def override_get_db(app, session_factory):
    """Override the get_db dependency to use the test session factory."""
    async def _test_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _test_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


# ── HTTP Client ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async HTTP client for integration tests."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as c:
        yield c


# ── Seed Helpers ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def seed_tenant(db_session) -> Tenant:
    """Create and return a test tenant."""
    tenant = Tenant(
        id=uuid.uuid4(),
        slug="test-tenant",
        subdomain="test-tenant",
        display_name="Test Tenant",
        plan=PlanType.free,
        status=TenantStatus.active,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def seed_pro_tenant(db_session) -> Tenant:
    """Create and return a pro-tier test tenant."""
    tenant = Tenant(
        id=uuid.uuid4(),
        slug="pro-tenant",
        subdomain="pro-tenant",
        display_name="Pro Tenant",
        plan=PlanType.pro,
        status=TenantStatus.active,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def seed_user(db_session, seed_tenant) -> User:
    """Create and return a test user (member role) in the test tenant."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=seed_tenant.id,
        email="member@test.com",
        hashed_password=get_password_hash("password123"),
        role=UserRole.member,
        is_superadmin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def seed_owner(db_session, seed_tenant) -> User:
    """Create and return a test owner user in the test tenant."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=seed_tenant.id,
        email="owner@test.com",
        hashed_password=get_password_hash("password123"),
        role=UserRole.owner,
        is_superadmin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def seed_superadmin(db_session, seed_tenant) -> User:
    """Create and return a superadmin user."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=seed_tenant.id,
        email="superadmin@test.com",
        hashed_password=get_password_hash("password123"),
        role=UserRole.admin,
        is_superadmin=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ── JWT Token Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def member_token(seed_user) -> str:
    """Generate a JWT token for the member user."""
    return create_access_token(seed_user)


@pytest.fixture
def owner_token(seed_owner) -> str:
    """Generate a JWT token for the owner user."""
    return create_access_token(seed_owner)


@pytest.fixture
def superadmin_token(seed_superadmin) -> str:
    """Generate a JWT token for the superadmin user."""
    return create_access_token(seed_superadmin)


# ── Auth Header Helpers ──────────────────────────────────────────────────────

@pytest.fixture
def member_headers(member_token) -> dict:
    """Authorization headers for member user."""
    return {"Authorization": f"Bearer {member_token}"}


@pytest.fixture
def owner_headers(owner_token) -> dict:
    """Authorization headers for owner user."""
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture
def superadmin_headers(superadmin_token) -> dict:
    """Authorization headers for superadmin user."""
    return {"Authorization": f"Bearer {superadmin_token}"}
