"""Multi-Tenant SaaS Bootstrapper for FastAPI.

A plug-and-play, pip-installable package that adds multi-tenancy,
JWT authentication, RBAC, feature flags, plan management, and an
optional bundled frontend to any FastAPI application.

Quick Start::

    # Standalone app
    from multi_tenant_bootstrapper import create_app
    app = create_app()

    # Mount into existing FastAPI app
    from fastapi import FastAPI
    from multi_tenant_bootstrapper import mount_to_app
    app = FastAPI(title="My App")
    mount_to_app(app)

    # Full customization
    from multi_tenant_bootstrapper import create_app, BootstrapperConfig
    config = BootstrapperConfig(
        DATABASE_URL="postgresql+asyncpg://...",
        JWT_SECRET_KEY="my-secret",
    )
    app = create_app(config=config, include_admin=False)
"""

__version__ = "1.0.0"

# ── App Factory ──────────────────────────────────────────────────────────────
from multi_tenant_bootstrapper.app_factory import create_app, mount_to_app

# ── Configuration ────────────────────────────────────────────────────────────
from multi_tenant_bootstrapper.config import BootstrapperConfig

# ── Database ─────────────────────────────────────────────────────────────────
from multi_tenant_bootstrapper.db.session import get_db

# ── Models ───────────────────────────────────────────────────────────────────
from multi_tenant_bootstrapper.models.base import Base, TimestampMixin, SerializerMixin
from multi_tenant_bootstrapper.models.domain import (
    Tenant,
    TenantConfig,
    User,
    FeatureFlag,
    PlanType,
    TenantStatus,
    UserRole,
)

# ── RLS ──────────────────────────────────────────────────────────────────────
from multi_tenant_bootstrapper.core.rls import (
    set_tenant_id,
    get_tenant_id,
    clear_tenant_id,
    bypass_rls,
    register_rls_listener,
)

# ── Auth Dependencies ────────────────────────────────────────────────────────
from multi_tenant_bootstrapper.api.dependencies import (
    require_tenant,
    superadmin_only,
    require_role,
    get_current_user,
    get_current_user_claims,
)

# ── Seed ─────────────────────────────────────────────────────────────────────
from multi_tenant_bootstrapper.seed import run_seed

__all__ = [
    # Factory
    "create_app",
    "mount_to_app",
    # Config
    "BootstrapperConfig",
    # Database
    "get_db",
    # Models
    "Base",
    "TimestampMixin",
    "SerializerMixin",
    "Tenant",
    "TenantConfig",
    "User",
    "FeatureFlag",
    "PlanType",
    "TenantStatus",
    "UserRole",
    # RLS
    "set_tenant_id",
    "get_tenant_id",
    "clear_tenant_id",
    "bypass_rls",
    "register_rls_listener",
    # Auth Dependencies
    "require_tenant",
    "superadmin_only",
    "require_role",
    "get_current_user",
    "get_current_user_claims",
    # Seed
    "run_seed",
]
