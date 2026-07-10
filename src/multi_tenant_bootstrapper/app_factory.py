"""App factory — the main entry point for creating a multi-tenant FastAPI app.

Provides two integration patterns:

1. **Standalone** — create a fully configured app::

    from multi_tenant_bootstrapper import create_app
    app = create_app()

2. **Mount into existing app** — add bootstrapper to your own FastAPI app::

    from fastapi import FastAPI
    from multi_tenant_bootstrapper import mount_to_app

    app = FastAPI(title="My App")
    mount_to_app(app)
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from multi_tenant_bootstrapper.config import (
    BootstrapperConfig,
    get_config,
    set_config,
)
from multi_tenant_bootstrapper.core.middleware import TenantMiddleware
from multi_tenant_bootstrapper.core.rls import register_rls_listener
from multi_tenant_bootstrapper.db.session import init_db


def create_app(
    config: BootstrapperConfig | None = None,
    *,
    title: str = "Multi-Tenant SaaS Bootstrapper",
    description: str = "Built with the Multi-Tenant SaaS Bootstrapper for FastAPI",
    version: str = "1.0.0",
    include_auth: bool = True,
    include_tenants: bool = True,
    include_features: bool = True,
    include_admin: bool = True,
    include_billing: bool = True,
    include_frontend: bool = True,
    extra_routers: Sequence[tuple[APIRouter, str, list[str]]] | None = None,
    extra_middleware: Sequence[tuple[type, dict]] | None = None,
    on_startup: Sequence[Callable] | None = None,
    on_shutdown: Sequence[Callable] | None = None,
) -> FastAPI:
    """Create a fully configured multi-tenant FastAPI application.

    Parameters
    ----------
    config:
        Configuration instance. If ``None``, a default
        :class:`BootstrapperConfig` is created (reads from env / ``.env``).
    title:
        FastAPI app title.
    description:
        FastAPI app description.
    version:
        FastAPI app version string.
    include_auth:
        Mount the ``/api/auth`` router (login, register, profile).
    include_tenants:
        Mount the ``/api/tenants`` router (provisioning, config, users).
    include_features:
        Mount the ``/api/features`` router (feature flag CRUD).
    include_admin:
        Mount the ``/api/admin`` router (superadmin panel).
    include_billing:
        Mount the ``/api/billing`` router (plan management).
    include_frontend:
        Serve the bundled React frontend at ``/`` as static files.
        Set to ``False`` to use your own frontend.
    extra_routers:
        Additional routers to mount. Each entry is a tuple of
        ``(router, prefix, tags)``.
    extra_middleware:
        Additional middleware to add. Each entry is a tuple of
        ``(middleware_class, kwargs)``.
    on_startup:
        Async callables to run on app startup.
    on_shutdown:
        Async callables to run on app shutdown.

    Returns
    -------
    FastAPI
        A fully configured FastAPI application instance.
    """
    # Resolve configuration
    cfg = config or BootstrapperConfig()
    set_config(cfg)

    # Initialise database
    init_db(cfg.get_async_database_url(), echo=cfg.SQLALCHEMY_ECHO)

    # Register RLS listener
    register_rls_listener()

    # Create FastAPI instance
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        debug=cfg.DEBUG,
    )

    # ── Lifecycle Events ─────────────────────────────────────────────────
    if on_startup:
        for handler in on_startup:
            app.on_event("startup")(handler)
    if on_shutdown:
        for handler in on_shutdown:
            app.on_event("shutdown")(handler)

    # ── Middleware ────────────────────────────────────────────────────────
    # CORS must be added BEFORE TenantMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Tenant resolution middleware
    app.add_middleware(TenantMiddleware)

    # Extra middleware (added in order)
    if extra_middleware:
        for middleware_class, kwargs in extra_middleware:
            app.add_middleware(middleware_class, **kwargs)

    # ── Routers ──────────────────────────────────────────────────────────
    _mount_routers(
        app,
        include_auth=include_auth,
        include_tenants=include_tenants,
        include_features=include_features,
        include_admin=include_admin,
        include_billing=include_billing,
    )

    # Extra routers
    if extra_routers:
        for router, prefix, tags in extra_routers:
            app.include_router(router, prefix=prefix, tags=tags)

    # ── Health Check ─────────────────────────────────────────────────────
    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "service": "multi-tenant-bootstrapper"}

    # ── Frontend Static Files ────────────────────────────────────────────
    if include_frontend:
        _mount_frontend(app)

    return app


def mount_to_app(
    app: FastAPI,
    config: BootstrapperConfig | None = None,
    *,
    prefix: str = "",
    include_auth: bool = True,
    include_tenants: bool = True,
    include_features: bool = True,
    include_admin: bool = True,
    include_billing: bool = True,
    include_frontend: bool = True,
    extra_routers: Sequence[tuple[APIRouter, str, list[str]]] | None = None,
) -> FastAPI:
    """Mount bootstrapper routers and middleware into an existing FastAPI app.

    This is the recommended integration pattern when you already have
    a FastAPI application and want to add multi-tenant capabilities.

    Parameters
    ----------
    app:
        Your existing FastAPI application instance.
    config:
        Configuration instance. If ``None``, a default is created.
    prefix:
        URL prefix for all bootstrapper routes (e.g. ``"/saas"``
        would mount auth at ``/saas/api/auth``).
    include_auth, include_tenants, include_features, include_admin, include_billing:
        Toggle individual routers on/off.
    include_frontend:
        Serve the bundled React frontend at ``/``.
    extra_routers:
        Additional routers to mount alongside the bootstrapper routes.

    Returns
    -------
    FastAPI
        The same app instance, with bootstrapper mounted.
    """
    # Resolve configuration
    cfg = config or BootstrapperConfig()
    set_config(cfg)

    # Initialise database
    init_db(cfg.get_async_database_url(), echo=cfg.SQLALCHEMY_ECHO)

    # Register RLS listener
    register_rls_listener()

    # ── Middleware ────────────────────────────────────────────────────────
    # Note: CORS should be managed by the host app
    app.add_middleware(TenantMiddleware)

    # ── Routers ──────────────────────────────────────────────────────────
    _mount_routers(
        app,
        prefix=prefix,
        include_auth=include_auth,
        include_tenants=include_tenants,
        include_features=include_features,
        include_admin=include_admin,
        include_billing=include_billing,
    )

    # Extra routers
    if extra_routers:
        for router, rtr_prefix, tags in extra_routers:
            app.include_router(
                router, prefix=f"{prefix}{rtr_prefix}", tags=tags
            )

    # ── Health Check ─────────────────────────────────────────────────────
    @app.get(f"{prefix}/api/health")
    async def health_check():
        return {"status": "healthy", "service": "multi-tenant-bootstrapper"}

    # ── Frontend ─────────────────────────────────────────────────────────
    if include_frontend:
        _mount_frontend(app)

    return app


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mount_routers(
    app: FastAPI,
    *,
    prefix: str = "",
    include_auth: bool = True,
    include_tenants: bool = True,
    include_features: bool = True,
    include_admin: bool = True,
    include_billing: bool = True,
) -> None:
    """Mount the built-in API routers based on toggle flags."""
    # Lazy imports to avoid circular dependencies
    from multi_tenant_bootstrapper.api.routers import (
        auth, tenants, features, admin, billing,
    )

    if include_auth:
        app.include_router(
            auth.router, prefix=f"{prefix}/api/auth", tags=["Auth"]
        )
    if include_tenants:
        app.include_router(
            tenants.router, prefix=f"{prefix}/api/tenants", tags=["Tenants"]
        )
    if include_features:
        app.include_router(
            features.router, prefix=f"{prefix}/api/features", tags=["Features"]
        )
    if include_admin:
        app.include_router(
            admin.router, prefix=f"{prefix}/api/admin", tags=["Admin"]
        )
    if include_billing:
        app.include_router(
            billing.router, prefix=f"{prefix}/api/billing", tags=["Billing"]
        )


def _mount_frontend(app: FastAPI) -> None:
    """Mount the bundled React frontend as static files.

    Looks for a ``frontend/dist`` directory inside the package.
    If not found (e.g. frontend hasn't been built), this is a no-op.
    """
    frontend_dir = Path(__file__).parent / "frontend" / "dist"
    if frontend_dir.exists() and frontend_dir.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_dir), html=True),
            name="frontend",
        )
