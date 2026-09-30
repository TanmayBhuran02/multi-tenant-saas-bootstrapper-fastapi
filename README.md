# Multi-Tenant SaaS Bootstrapper (FastAPI)

A production-grade, plug-and-play multi-tenant SaaS bootstrapper built with **FastAPI**, **PostgreSQL** (asyncpg + SQLAlchemy 2.0), and **React (Vite + React Router v6)**.

Packaged as an installable, PEP 621-compliant Python library (`multi-tenant-bootstrapper`) that can run as a **standalone SaaS application** or be **mounted into any existing FastAPI project**.

---

## Table of contents

- [Key features](#key-features)
- [Architecture overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation & Quick start](#installation--quick-start)
  - [1. Standalone application](#1-standalone-application)
  - [2. Mount into an existing FastAPI app](#2-mount-into-an-existing-fastapi-app)
- [Environment variables](#environment-variables)
- [Database setup & migrations](#database-setup--migrations)
- [Running the project](#running-the-project)
- [Project structure](#project-structure)
- [API reference & Docs](#api-reference--docs)
- [Plans & feature flags](#plans--feature-flags)
- [Multi-tenancy & Row-Level Security (RLS)](#multi-tenancy--row-level-security-rls)
- [Frontend](#frontend)
- [Testing](#testing)
- [Conventions](#conventions)
- [Future Scope](#future-scope)

---

## Key features

- **Dual-mode usage**: Run standalone out-of-the-box or mount into an existing FastAPI application with one line of code.
- **Subdomain & header routing**: Automatic tenant resolution from host headers (`subdomain.yourdomain.com`) or fallback `X-Tenant-ID` header.
- **Transparent Row-Level Security (RLS)**: ContextVar-based tenant tracking with automatic SQLAlchemy query interception—no manual `WHERE tenant_id = :id` required.
- **FastAPI auth & RBAC**: JWT tokens with role-based dependencies (`require_tenant`, `superadmin_only`, `require_role`).
- **Feature flag engine**: Tier-based flag provisioning (`free`, `starter`, `pro`, `enterprise`) with per-tenant overrides.
- **Plan & billing management**: Plan limits, tiers, feature gating, and upgrade endpoints.
- **Modern async stack**: Fully asynchronous with FastAPI, SQLAlchemy 2.0 (asyncio + asyncpg), and Pydantic v2.
- **100% test coverage**: 122 pytest unit & integration tests against real PostgreSQL with automatic cascade isolation.

---

## Architecture overview

```
Browser / API Client (acme.yoursaas.com)
        │
        ▼
┌───────────────────────────────────────┐
│  TenantContextMiddleware              │  Reads Host header → extracts subdomain
│  (core/middleware.py)                 │  → sets ContextVar tenant_id
└──────────────────┬────────────────────┘
                   │
┌──────────────────▼────────────────────┐
│  FastAPI Dependencies (JWT / RBAC)    │  Validates token, extracts tenant_id,
│  (api/dependencies.py)                │  role, is_superadmin claims
└──────────────────┬────────────────────┘
                   │
┌──────────────────▼────────────────────┐
│  RLS Query Interceptor                │  SQLAlchemy `before_compile` hook auto-injects
│  (core/rls.py)                        │  `WHERE tenant_id = current_tenant`
└──────────────────┬────────────────────┘
                   │
┌──────────────────▼────────────────────┐
│  PostgreSQL (Shared Schema)           │  Single async DB, all tenants in shared
│  (asyncpg driver)                     │  tables, strictly isolated by tenant_id
└───────────────────────────────────────┘
```

---

## Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Node.js 18+ (for frontend)
- Docker & Docker Compose (optional)

---

## Installation & Quick start

### 1. Standalone application

Clone repository and install dependencies:

```bash
git clone https://github.com/your-org/multi-tenant-saas-bootstrapper-fastapi.git
cd multi-tenant-saas-bootstrapper-fastapi

# Set up virtual environment
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate

# Install package with development dependencies
pip install -e ".[dev]"
```

Run standalone server with Python:

```python
from multi_tenant_bootstrapper import create_app

app = create_app()
```

Or start with Uvicorn:

```bash
uvicorn multi_tenant_bootstrapper.app_factory:create_app --factory --reload --port 8000
```

### 2. Mount into an existing FastAPI app

Install as a dependency in your FastAPI project:

```bash
pip install multi-tenant-bootstrapper
```

Mount into your application:

```python
from fastapi import FastAPI
from multi_tenant_bootstrapper import mount_to_app, BootstrapperConfig

app = FastAPI(title="My Platform")

# Configure bootstrapper
config = BootstrapperConfig(
    DATABASE_URL="postgresql+asyncpg://postgres:secret@localhost:5432/my_saas_db",
    JWT_SECRET_KEY="your-production-jwt-secret-at-least-32-bytes",
)

# Mount bootstrapper routes, middleware, and database hooks
mount_to_app(app, config=config, prefix="/api")
```

---

## Environment variables

Configure using environment variables or a `.env` file (supports `SAAS_` prefix or raw names):

| Variable | Required | Default | Description | Example |
|---|---|---|---|---|
| `SAAS_DATABASE_URL` / `DATABASE_URL` | ✅ | - | PostgreSQL asyncpg URL | `postgresql+asyncpg://user:pass@localhost:5432/saas_db` |
| `SAAS_JWT_SECRET_KEY` / `JWT_SECRET_KEY` | ✅ | - | Secret for signing JWTs (32+ chars) | `your-32-byte-secret-key-goes-here` |
| `SAAS_SECRET_KEY` / `SECRET_KEY` | - | `""` | General application secret key | `super-secret-random-key` |
| `SAAS_SUPERADMIN_SECRET` / `SUPERADMIN_SECRET`| ✅ | - | Secret for bootstrapping superadmins | `admin-bootstrap-secret` |
| `SAAS_CORS_ORIGINS` / `CORS_ORIGINS` | - | `*` | Allowed CORS origins (comma-separated)| `http://localhost:5173,https://app.domain.com` |
| `SAAS_BASE_DOMAIN` / `BASE_DOMAIN` | - | `localhost` | Base domain for subdomain resolution | `yoursaas.com` |
| `SAAS_DEBUG` / `DEBUG` | - | `false` | Enable debug logs & autoreload | `true` |

---

## Database setup & migrations

### Database migrations (Alembic)

Run migrations against your configured database:

```bash
alembic upgrade head
```

Create a new migration revision:

```bash
alembic revision --autogenerate -m "Add new column"
alembic upgrade head
```

### Seeding initial data

Seed default system roles and create initial superadmin:

```bash
python -m multi_tenant_bootstrapper.seed
```

Or seed programmatically:

```python
import asyncio
from multi_tenant_bootstrapper.seed import run_seed

asyncio.run(run_seed(admin_email="admin@yoursaas.com", admin_password="ChangeMe123!"))
```

---

## Running the project

### Development

```bash
# Terminal 1 — Backend API
uvicorn multi_tenant_bootstrapper.app_factory:create_app --factory --reload --port 8000

# Terminal 2 — React Frontend
cd frontend
npm install
npm run dev
```

Interactive Swagger API docs available at: **`http://localhost:8000/docs`**  
ReDoc available at: **`http://localhost:8000/redoc`**

---

## Project structure

```
multi-tenant-saas-bootstrapper-fastapi/
├── src/multi_tenant_bootstrapper/    # Core Python package
│   ├── __init__.py                  # Public exports (create_app, mount_to_app, models, etc.)
│   ├── app_factory.py               # Application factory & router mounter
│   ├── config.py                    # Pydantic Settings configuration (BootstrapperConfig)
│   ├── seed.py                      # Database seeder CLI & functions
│   ├── api/
│   │   ├── dependencies.py          # FastAPI dependencies (auth, tenant, roles)
│   │   └── routers/
│   │       ├── admin.py             # Superadmin metrics & aggregate endpoints
│   │       ├── auth.py              # Login, register, profile
│   │       ├── billing.py           # Plan limits, tiers, upgrades
│   │       ├── features.py          # Feature flag evaluation & toggling
│   │       └── tenants.py           # Tenant provisioning, config, deletion
│   ├── core/
│   │   ├── flags.py                 # Feature flag definitions & seeding logic
│   │   ├── middleware.py            # Subdomain & tenant context middleware
│   │   ├── plans.py                 # Plan definitions, limits, and features
│   │   ├── rls.py                   # ContextVar RLS state & SQLAlchemy compiler hook
│   │   └── security.py              # Password hashing (bcrypt) & JWT handling
│   ├── db/
│   │   └── session.py               # Async engine, sessionmaker, & get_db dependency
│   ├── migrations/                  # Alembic migration scripts
│   ├── models/
│   │   ├── base.py                  # Declarative base & reusable mixins
│   │   └── domain.py                # Tenant, User, TenantConfig, FeatureFlag
│   └── schemas/                     # Pydantic v2 request/response schemas
├── frontend/                        # React SPA (Vite + Tailwind/CSS + React Router v6)
├── tests/                           # Pytest test suite (122 tests)
│   ├── conftest.py                  # Async PostgreSQL session & autouse table cleaner
│   ├── test_config.py               # Configuration tests
│   ├── test_core_*.py               # Middleware, RLS, flags, plans, security tests
│   ├── test_dependencies.py         # Dependency injection tests
│   ├── test_models.py               # Model serialization & constraint tests
│   ├── test_router_*.py             # Integration tests for all routers
│   └── test_schemas.py              # Schema validation tests
├── pyproject.toml                   # PEP 621 package build config
└── README.md
```

---

## API reference & Docs

Full interactive API documentation is generated automatically by FastAPI at `/docs`.

### Auth (`/api/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | Optional | Register a user |
| `POST` | `/api/auth/login` | None | Login with email and password, returns JWT |
| `GET` | `/api/auth/me` | Bearer Token | Get current authenticated user profile |

### Tenants (`/api/tenants`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/tenants/provision` | Superadmin | Provision a new tenant and owner user |
| `DELETE`| `/api/tenants/{tenant_id}` | Superadmin | Delete / deactivate tenant |
| `GET` | `/api/tenants/{tenant_id}/config` | Tenant Member | Get tenant configuration |
| `PUT` | `/api/tenants/{tenant_id}/config` | Tenant Owner | Upsert tenant configuration key |
| `GET` | `/api/tenants/{tenant_id}/users` | Tenant Member | List users belonging to tenant |

### Features (`/api/features`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/features` | Tenant Member | List all feature flags for current tenant |
| `POST` | `/api/features/toggle` | Superadmin | Enable/disable a feature flag for a tenant |

### Billing (`/api/billing`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/billing/plan` | Tenant Member | Get current plan details and limits |
| `POST` | `/api/billing/upgrade` | Superadmin | Upgrade or change tenant plan |

### Admin (`/api/admin`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/admin/tenants` | Superadmin | List all tenants across system |
| `GET` | `/api/admin/metrics` | Superadmin | Global platform metrics |
| `GET` | `/api/admin/tenants/{tenant_id}/metrics` | Superadmin | Metrics for specific tenant |

---

## Plans & feature flags

Four tiers supported out of the box: `free`, `starter`, `pro`, `enterprise`.

Plan limits and flags are defined in `src/multi_tenant_bootstrapper/core/plans.py`:

```python
PLAN_LIMITS = {
    PlanType.free: {"max_users": 3, "max_projects": 1, "storage_mb": 100},
    PlanType.starter: {"max_users": 10, "max_projects": 5, "storage_mb": 1000},
    PlanType.pro: {"max_users": 50, "max_projects": 25, "storage_mb": 10000},
    PlanType.enterprise: {"max_users": -1, "max_projects": -1, "storage_mb": -1},
}
```

---

## Multi-tenancy & Row-Level Security (RLS)

All tenant-scoped models inherit from `Base` and include a `tenant_id` column:

```python
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from multi_tenant_bootstrapper.models.base import Base, TimestampMixin, SerializerMixin

class Project(Base, TimestampMixin, SerializerMixin):
    __tablename__ = "projects"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
```

The bootstrapper automatically registers an ORM query compilation listener (`register_rls_listener`). Every query executed automatically filters `WHERE tenant_id = <current_tenant_id>`.

To execute operations across tenants (e.g., admin tasks or system jobs), use the context manager:

```python
from multi_tenant_bootstrapper.core.rls import bypass_rls

with bypass_rls():
    # RLS filter suppressed in this block
    all_projects = await db.execute(select(Project))
```

---

## Frontend

The React frontend (in `frontend/`) connects seamlessly:

```bash
cd frontend
npm install
npm run dev
```

Provides:
- Tenant onboarding wizard (`/onboarding`)
- Tenant login & dashboard (`/login`, `/dashboard`)
- Superadmin management panel (`/superadmin`)
- Reusable hooks & context (`TenantContext`, `useFeatureFlag`, `useTenant`)

---

## Testing

The test suite runs against PostgreSQL using `asyncpg` with automatic cascade table cleanup after every test:

```bash
# Run all tests
pytest

# Run tests with short summary
pytest -q

# Run specific test suite
pytest tests/test_router_tenants.py
```

Configuration in `pyproject.toml` automatically manages async test lifecycle:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
testpaths = ["tests"]
```

---

## Conventions

- **FastAPI dependency injection**: Authenticated claims and tenant IDs accessed via standard FastAPI `Depends()`.
- **Async everywhere**: All DB operations use SQLAlchemy async sessions and asyncpg.
- **Pydantic v2 schemas**: Strict validation with automatic OpenAPI serialization.
- **Tenant isolation**: Zero cross-tenant data leaks guaranteed via ContextVar RLS hooks.
- [JSON responses](file:///c:/Users/tanma/.gemini/antigravity-ide/scratch/multi-tenant-saas-bootstrapper-fastapi/README.md): Unified REST responses with standard HTTP error codes.

---

## Future Scope

- **Tenant-Based Partitioning (`tenant_id`) on Every Table**:
  - Implement PostgreSQL declarative table partitioning across all tenant-scoped tables (`users`, `tenant_configs`, `feature_flags`, and custom domain tables).
  - Eliminates noisy-neighbor performance degradation by pruning index scans to individual tenant partitions.
  - Allows zero-downtime, instantaneous tenant offboarding via partition dropping (`DROP TABLE ...`) instead of cascading row deletions.
  - Enables per-tenant storage tiering (hot NVMe for enterprise vs cold storage for inactive/archived tenants).

