# Multi-Tenant SaaS Bootstrapper — Integration Guide

A step-by-step guide for injecting the **Multi-Tenant SaaS Bootstrapper** (FastAPI edition) into your own project and integrating every feature it ships with.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Setup (Inject as Dependency)](#quick-setup-inject-as-dependency)
  - [Backend Injection](#1-backend-injection)
  - [Frontend Injection](#2-frontend-injection)
  - [Database & Environment](#3-database--environment)
- [Feature Integration Guide](#feature-integration-guide)
  - [1. Tenant Provisioning & Management](#1-tenant-provisioning--management)
  - [2. Subdomain-Based Routing & Tenant Middleware](#2-subdomain-based-routing--tenant-middleware)
  - [3. Row-Level Security (RLS)](#3-row-level-security-rls)
  - [4. JWT Authentication & RBAC](#4-jwt-authentication--rbac)
  - [5. Feature Flags](#5-feature-flags)
  - [6. Plans & Billing](#6-plans--billing)
  - [7. Superadmin Panel](#7-superadmin-panel)
  - [8. Frontend Hooks & Components](#8-frontend-hooks--components)
  - [9. Docker Deployment](#9-docker-deployment)
- [Adding Your Own Tenant-Scoped Models](#adding-your-own-tenant-scoped-models)
- [Customization Reference](#customization-reference)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.12+ |
| Node.js | 18+ |
| PostgreSQL | 15+ |
| Docker & Docker Compose | Latest (optional, but recommended) |

---

## Quick Setup (Inject as Dependency)

### 1. Backend Injection

#### Option A — Git Submodule (recommended for source access)

```bash
# From your project root
git submodule add https://github.com/your-org/saas-bootstrapper-fastapi.git lib/saas-bootstrapper
git submodule update --init --recursive
```

Then copy the relevant backend modules into your FastAPI app:

```bash
# Copy the core multi-tenant app package into your project
cp -r lib/saas-bootstrapper/backend/app   your_project/backend/app

# Copy migration setup
cp -r lib/saas-bootstrapper/backend/alembic       your_project/backend/alembic
cp    lib/saas-bootstrapper/backend/alembic.ini    your_project/backend/alembic.ini

# Copy the seed script
cp    lib/saas-bootstrapper/backend/seed.py        your_project/backend/seed.py
```

#### Option B — Direct Copy (simpler, no git history)

```bash
# Clone once and copy what you need
git clone https://github.com/your-org/saas-bootstrapper-fastapi.git /tmp/saas-bootstrapper

# Copy backend modules
cp -r /tmp/saas-bootstrapper/backend/app           your_project/backend/app
cp -r /tmp/saas-bootstrapper/backend/alembic       your_project/backend/alembic
cp    /tmp/saas-bootstrapper/backend/alembic.ini    your_project/backend/alembic.ini
cp    /tmp/saas-bootstrapper/backend/seed.py        your_project/backend/seed.py
```

#### Install Python Dependencies

Add these to your `requirements.txt` (or merge with your existing one):

```text
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
alembic
pyjwt
passlib[bcrypt]
pydantic[email]
python-dotenv
pydantic-settings
```

Then install:

```bash
pip install -r requirements.txt
```

---

### 2. Frontend Injection

Copy the relevant frontend modules into your React project:

```bash
# From the cloned bootstrapper (or submodule path)
SRC=lib/saas-bootstrapper/frontend/src

cp    $SRC/api/client.js              your_frontend/src/api/client.js
cp    $SRC/context/TenantContext.jsx   your_frontend/src/context/TenantContext.jsx
cp -r $SRC/hooks                      your_frontend/src/hooks
cp    $SRC/components/FeatureGate.jsx  your_frontend/src/components/FeatureGate.jsx
cp    $SRC/components/FeatureGate.css  your_frontend/src/components/FeatureGate.css
cp    $SRC/components/PlanBadge.jsx    your_frontend/src/components/PlanBadge.jsx
cp    $SRC/components/PrivateRoute.jsx your_frontend/src/components/PrivateRoute.jsx
cp    $SRC/components/SuperadminRoute.jsx your_frontend/src/components/SuperadminRoute.jsx
```

#### Install npm Dependencies

```bash
npm install axios zustand react-router-dom @tanstack/react-query recharts react-hook-form
```

---

### 3. Database & Environment

#### Create your `.env` file (backend)

```bash
# ─── App ─────────────────────────────────────────────────
SECRET_KEY=change-me-to-a-random-string
DEBUG=True

# ─── Database ────────────────────────────────────────────
# Use postgresql:// — the app auto-converts to postgresql+asyncpg://
DATABASE_URL=postgresql://your_user:your_pass@localhost:5432/your_db

# ─── JWT ─────────────────────────────────────────────────
JWT_SECRET_KEY=change-me-to-a-random-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=86400

# ─── Superadmin ──────────────────────────────────────────
SUPERADMIN_SECRET=change-me-to-a-random-superadmin-secret

# ─── CORS ────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173
```

#### Create your `.env.local` file (frontend)

```bash
VITE_API_URL=http://localhost:8000
```

#### Run Migrations & Seed

```bash
cd your_project/backend

# Apply database schema via Alembic
alembic upgrade head

# Seed the default superadmin and demo tenant
python seed.py
```

> **Default credentials after seeding:**
>
> | User | Email | Password |
> |---|---|---|
> | Superadmin | `admin@saas.com` | `superadmin123` |
> | Demo Owner | `owner@demo.com` | `demo12345` |
> | Demo Member | `member@demo.com` | `demo12345` |

#### Start the Backend (Development)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The interactive API docs are available at `http://localhost:8000/docs`.

---

## Feature Integration Guide

### 1. Tenant Provisioning & Management

#### What it provides

- Create (provision) new tenants with an owner user and default feature flags
- Soft-delete tenants (status → `deleted`, preserves audit trail)
- Per-tenant configuration (key-value store with secret masking)
- User management per tenant

#### Backend Integration

Include the tenants router in your FastAPI app:

```python
# app/main.py
from fastapi import FastAPI
from app.api.routers import tenants

app = FastAPI()
app.include_router(tenants.router, prefix="/api/tenants", tags=["Tenants"])
```

#### Key Files

| File | Purpose |
|---|---|
| `app/models/domain.py` | `Tenant`, `TenantConfig`, `User`, `FeatureFlag` SQLAlchemy models |
| `app/api/routers/tenants.py` | `/api/tenants/provision`, `DELETE`, `config` CRUD, `/users` |
| `app/core/middleware.py` | `TenantMiddleware` — request-level tenant resolution |

#### API Endpoints

```bash
# Provision a new tenant (superadmin only)
curl -X POST http://localhost:8000/api/tenants/provision \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Acme Corp",
    "subdomain": "acme",
    "plan": "pro",
    "owner_email": "alice@acme.com",
    "owner_password": "secure-password"
  }'

# Soft-delete a tenant
curl -X DELETE http://localhost:8000/api/tenants/<tenant_id> \
  -H "Authorization: Bearer <superadmin_token>"

# Get tenant config
curl http://localhost:8000/api/tenants/<tenant_id>/config \
  -H "Authorization: Bearer <token>"

# Upsert a config entry
curl -X PATCH http://localhost:8000/api/tenants/<tenant_id>/config \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"key": "theme_color", "value": "#6366f1", "is_secret": false}'

# List tenant users
curl http://localhost:8000/api/tenants/<tenant_id>/users \
  -H "Authorization: Bearer <token>"
```

---

### 2. Subdomain-Based Routing & Tenant Middleware

#### What it provides

- Automatic tenant resolution from the `Host` header (e.g., `acme.yoursaas.com`)
- Fallback to `X-Tenant-ID` header for local development
- Sets `request.state.tenant` on every request
- Automatically activates the RLS context variable for the resolved tenant

#### Backend Integration

Add `TenantMiddleware` in your app factory (it uses Starlette's `BaseHTTPMiddleware`):

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.middleware import TenantMiddleware

app = FastAPI()

# CORS must be added BEFORE TenantMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(TenantMiddleware)
```

#### How Tenant Resolution Works

```
Request arrives
    │
    ├─ Host: acme.yoursaas.com → extract "acme" → lookup Tenant(subdomain="acme", status="active")
    │
    ├─ Host: localhost:8000 + X-Tenant-ID header → lookup Tenant(id=header_value, status="active")
    │
    └─ No match → request.state.tenant = None (unauthenticated / public route)
```

The middleware also calls `clear_tenant_id()` before and after each request to prevent context leakage between requests in the same worker process.

#### Local Development (Without Subdomain DNS)

Pass the `X-Tenant-ID` header in all requests:

```bash
curl http://localhost:8000/api/features/ \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: <tenant_uuid>"
```

Your frontend API client (`api/client.js`) handles this automatically — it reads `tenant_id` from `localStorage` and attaches it as the `X-Tenant-ID` header on every request.

#### Production DNS Setup

For production, configure wildcard DNS:

```
*.yoursaas.com → your server IP
```

The middleware's `_SKIP_HOSTS` regex automatically ignores `localhost`, `127.0.0.1`, and raw IP addresses so local development works without DNS.

---

### 3. Row-Level Security (RLS)

#### What it provides

- Application-level tenant data isolation using SQLAlchemy ORM events
- Automatic `WHERE tenant_id = <current_tenant>` injection on every `SELECT` query
- `bypass_rls()` context manager for superadmin / cross-tenant operations
- Zero manual filtering required in route handlers

#### Backend Integration

Call `register_rls_listener()` once in your app startup (or module import):

```python
# app/main.py  (or wherever you initialize the app)
from app.core.rls import register_rls_listener

register_rls_listener()
```

#### How it Works

1. **ContextVar**: The current `tenant_id` is stored in a `contextvars.ContextVar`, set by `TenantMiddleware` on each request.

2. **SQLAlchemy Event**: A `do_orm_execute` listener intercepts every ORM `SELECT` and appends `.where(Model.tenant_id == current_tenant_id)` for any model that has a `tenant_id` column.

3. **Bypass**: Superadmin routes use `bypass_rls()` to query across tenants:

```python
from app.core.rls import bypass_rls

# Normal query — automatically filtered to current tenant
result = await db.execute(select(User))  # Only returns users for the current tenant

# Superadmin query — bypasses RLS
with bypass_rls():
    result = await db.execute(select(User))  # Returns ALL users across all tenants
```

#### RLS Public API

| Function | Description |
|---|---|
| `set_tenant_id(tid)` | Set the current tenant context |
| `get_tenant_id()` | Get the current tenant context |
| `clear_tenant_id()` | Clear the tenant context |
| `bypass_rls()` | Context manager to skip RLS filtering |
| `register_rls_listener()` | Register the SQLAlchemy event (call once at startup) |

#### Adding RLS to Your Own Models

Any model with a `tenant_id` column is **automatically** filtered by RLS. See [Adding Your Own Tenant-Scoped Models](#adding-your-own-tenant-scoped-models).

---

### 4. JWT Authentication & RBAC

#### What it provides

- JWT-based authentication using `pyjwt` (HS256)
- Token includes `tenant_id`, `role`, `is_superadmin`, and `email` claims
- FastAPI `Depends()` functions: `require_tenant`, `superadmin_only`, `require_role`
- User registration within tenant scope
- Profile endpoint

#### Backend Integration

Include the auth router and wire the dependency injection:

```python
# app/main.py
from app.api.routers import auth

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
```

JWT verification is handled by the dependency functions in `app/api/dependencies.py`. No additional initialization is needed.

#### JWT Token Claims

When a user logs in, the JWT payload contains:

```json
{
  "sub": "<user_id>",
  "exp": "<unix_timestamp>",
  "tenant_id": "<tenant_uuid>",
  "is_superadmin": false,
  "role": "owner | admin | member",
  "email": "user@example.com"
}
```

#### Auth Dependencies

Use these `Depends()` functions to protect your own routes:

```python
from fastapi import APIRouter, Depends
from app.api.dependencies import require_tenant, superadmin_only, require_role, get_current_user
from app.models.domain import User

router = APIRouter()

# Requires a valid JWT with tenant context
@router.get("/my-feature")
async def my_feature(claims: dict = Depends(require_tenant)):
    tenant_id = claims["tenant_id"]
    user_email = claims["email"]
    return {"message": f"Hello {user_email} from tenant {tenant_id}"}


# Requires full User object (fetched from DB)
@router.get("/profile")
async def profile(user: User = Depends(get_current_user)):
    return user.to_dict()


# Requires superadmin — use bypass_rls() inside if querying across tenants
@router.get("/admin/special")
async def admin_special(_: dict = Depends(superadmin_only)):
    ...


# Requires specific role(s) — built on top of require_tenant
@router.patch("/settings")
async def update_settings(claims: dict = Depends(require_role(["owner", "admin"]))):
    ...
```

#### Roles Hierarchy

| Role | Permissions |
|---|---|
| `owner` | Full tenant control, can manage users and config |
| `admin` | Can manage config, limited user management |
| `member` | Read-only access to tenant resources |
| `superadmin` | Cross-tenant access, bypasses RLS |

#### API Endpoints

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@acme.com", "password": "secret"}'

# Get profile (requires tenant context)
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <token>"

# Register a new user within a tenant
curl -X POST http://localhost:8000/api/auth/register \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@acme.com", "password": "secure-pass", "role": "member"}'
```

---

### 5. Feature Flags

#### What it provides

- Per-tenant feature flag management
- Plan-based default flags (auto-seeded on tenant creation)
- Superadmin toggle for individual flags with optional JSON payload
- `upgrade_flags()` logic that enables new flags when a tenant's plan is upgraded

#### Backend Integration

Include the features router:

```python
# app/main.py
from app.api.routers import features

app.include_router(features.router, prefix="/api/features", tags=["Features"])
```

#### Default Flags Per Plan

| Flag | Free | Starter | Pro | Enterprise |
|---|---|---|---|---|
| `basic_dashboard` | ✅ | ✅ | ✅ | ✅ |
| `csv_export` | | ✅ | ✅ | ✅ |
| `api_access` | | ✅ | ✅ | ✅ |
| `advanced_analytics` | | | ✅ | ✅ |
| `webhooks` | | | ✅ | ✅ |
| `sso` | | | ✅ | ✅ |
| `audit_logs` | | | | ✅ |
| `custom_domain` | | | | ✅ |
| `dedicated_support` | | | | ✅ |

#### Adding Custom Flags

Edit `app/core/flags.py` to add your own flags:

```python
# app/core/flags.py

PLAN_FLAGS = {
    PlanType.free: [
        'basic_dashboard',
        'your_custom_flag',       # ← Add here
    ],
    PlanType.starter: [
        'basic_dashboard',
        'csv_export',
        'api_access',
        'your_custom_flag',
        'another_feature',        # ← Add here
    ],
    # ... etc
}
```

#### Checking Flags in Backend Code

```python
from sqlalchemy import select
from app.models.domain import FeatureFlag

async def is_flag_enabled(db, tenant_id: str, flag_name: str) -> bool:
    result = await db.execute(
        select(FeatureFlag).where(
            FeatureFlag.tenant_id == tenant_id,
            FeatureFlag.flag_name == flag_name,
        )
    )
    flag = result.scalar_one_or_none()
    return flag.enabled if flag else False


# Usage in a route
from fastapi import HTTPException, Depends
from app.db.session import get_db

@router.get("/webhooks")
async def webhooks(
    claims: dict = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    enabled = await is_flag_enabled(db, claims["tenant_id"], "webhooks")
    if not enabled:
        raise HTTPException(status_code=403, detail="Feature not available on your plan")
    # ... webhook logic
```

#### API Endpoints

```bash
# List all flags for current tenant (RLS auto-filters to tenant)
curl http://localhost:8000/api/features/ \
  -H "Authorization: Bearer <token>"

# Toggle a flag (superadmin only)
curl -X PATCH http://localhost:8000/api/features/webhooks \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "<uuid>", "enabled": true, "payload": null}'
```

---

### 6. Plans & Billing

#### What it provides

- Four plan tiers: `free`, `starter`, `pro`, `enterprise`
- Configurable resource limits per plan (users, API calls, storage, projects)
- Plan upgrade endpoint with automatic flag re-seeding via `upgrade_flags()`
- Usage tracking (user count, with placeholder for API call tracking)

#### Backend Integration

Include the billing router:

```python
# app/main.py
from app.api.routers import billing

app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
```

#### Plan Limits

| Plan | Users | API Calls/Month | Storage (MB) | Projects | Monthly Price |
|---|---|---|---|---|---|
| `free` | 3 | 1,000 | 100 | 1 | $0 |
| `starter` | 10 | 10,000 | 1,000 | 5 | $29 |
| `pro` | 50 | 100,000 | 10,000 | 25 | $99 |
| `enterprise` | Unlimited | Unlimited | Unlimited | Unlimited | $299 |

#### Customizing Plans

Edit `app/core/plans.py`:

```python
PLAN_LIMITS = {
    'free': {
        'users': 3,
        'api_calls': 1000,
        'storage_mb': 100,
        'projects': 1,
        'price_monthly': 0,
        'your_custom_limit': 10,     # ← Add custom limits
    },
    # ... more plans
}

PLAN_FEATURES = {
    'free': [
        'Basic Dashboard',
        'Community Support',
        'Up to 3 Users',
        'Your Custom Feature Label',  # ← Add display labels
    ],
    # ... more plans
}
```

#### Enforcing Limits in Your Code

```python
from sqlalchemy import select, func
from app.core.plans import get_plan_limits
from app.models.domain import User

async def check_user_limit(db, tenant) -> bool:
    plan_name = tenant.plan.value
    limits = get_plan_limits(plan_name)
    max_users = limits['users']

    if max_users == -1:
        return True  # Unlimited (enterprise)

    result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant.id)
    )
    current_count = result.scalar_one()
    return current_count < max_users
```

#### API Endpoints

```bash
# Get current plan, limits, and usage
curl http://localhost:8000/api/billing/plan \
  -H "Authorization: Bearer <token>"

# Upgrade a tenant (superadmin only)
curl -X POST http://localhost:8000/api/billing/upgrade \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "<uuid>", "new_plan": "enterprise"}'
```

---

### 7. Superadmin Panel

#### What it provides

- Paginated tenant list with user counts, filterable by `status` and `plan`
- Per-tenant metrics (user count, config count, flag breakdown)
- Global aggregate metrics (total tenants, total users, plan/status distribution)

#### Backend Integration

Include the admin router:

```python
# app/main.py
from app.api.routers import admin

app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
```

#### API Endpoints

```bash
# Paginated tenant list
curl "http://localhost:8000/api/admin/tenants?page=1&per_page=20&status=active&plan=pro" \
  -H "Authorization: Bearer <superadmin_token>"

# Per-tenant metrics
curl http://localhost:8000/api/admin/tenants/<tenant_id>/metrics \
  -H "Authorization: Bearer <superadmin_token>"

# Global metrics
curl http://localhost:8000/api/admin/metrics \
  -H "Authorization: Bearer <superadmin_token>"
```

#### Response Examples

**Global Metrics:**
```json
{
  "metrics": {
    "total_tenants": 5,
    "total_users": 23,
    "by_plan": { "free": 2, "starter": 1, "pro": 1, "enterprise": 1 },
    "by_status": { "active": 4, "deleted": 1 }
  }
}
```

**Per-Tenant Metrics:**
```json
{
  "tenant": { "id": "...", "slug": "acme", "plan": "pro", ... },
  "metrics": {
    "user_count": 4,
    "config_count": 3,
    "feature_flags": {
      "total": 9,
      "enabled": 6,
      "disabled": 3,
      "flags": [...]
    }
  }
}
```

---

### 8. Frontend Hooks & Components

#### Wrapping Your App

Your app must be wrapped with `BrowserRouter` and `QueryClientProvider`:

```jsx
// main.jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
```

#### API Client (`api/client.js`)

The Axios client automatically:

- Attaches `Authorization: Bearer <token>` from `localStorage`
- Attaches `X-Tenant-ID` header from `localStorage`
- Redirects to `/login` on 401 responses

```js
import client from './api/client';

// All requests automatically include auth and tenant headers
const { data } = await client.get('/api/features/');
```

#### Zustand Store (`context/TenantContext.jsx`)

The central state store manages tenant, user, plan, and feature flags:

```jsx
import useTenantStore from './context/TenantContext';

function MyComponent() {
  const {
    tenant,          // Current tenant object (with configs, plan, limits, usage)
    user,            // Authenticated user object
    plan,            // Current plan name (string)
    featureFlags,    // Array of { flag_name, enabled, payload, ... }
    isAuthenticated, // Boolean
    isLoading,       // Boolean (true during initial hydration)
    login,           // async (email, password, tenantId?) => data
    logout,          // () => void
    hydrate,         // async () => void (re-fetches everything from API)
    refreshFlags,    // async () => void (re-fetches only feature flags)
    setTenant,       // (tenant) => void
    setUser,         // (user) => void
  } = useTenantStore();
}
```

On app load, call `hydrate()` to restore session state from `localStorage`:

```jsx
// App.jsx
import { useEffect } from 'react';
import useTenantStore from './context/TenantContext';

function App() {
  const { hydrate, isLoading } = useTenantStore();

  useEffect(() => {
    hydrate();
  }, []);

  if (isLoading) return <div>Loading...</div>;

  return <Routes />;
}
```

#### Hook: `useTenant()`

```jsx
import useTenant from './hooks/useTenant';

function DashboardHeader() {
  const { tenant, user, plan } = useTenant();

  return (
    <header>
      <h1>Welcome, {user?.email}</h1>
      <p>Plan: {plan}</p>
    </header>
  );
}
```

#### Hook: `useFeatureFlag(flagName)`

Returns a boolean indicating whether the flag is enabled for the current tenant:

```jsx
import useFeatureFlag from './hooks/useFeatureFlag';

function WebhooksPage() {
  const hasWebhooks = useFeatureFlag('webhooks');

  if (!hasWebhooks) {
    return <p>Upgrade your plan to access webhooks.</p>;
  }

  return <div>Webhook configuration...</div>;
}
```

#### Hook: `useBilling()`

```jsx
import useBilling from './hooks/useBilling';

function BillingPage() {
  const {
    plan,        // Current plan name
    limits,      // { users, api_calls, storage_mb, projects, price_monthly }
    usage,       // { users, api_calls }
    features,    // Array of feature labels for the current plan
    allPlans,    // Object of all plan limits
    isLoading,
    upgrade,     // ({ tenantId, newPlan }) => void
    isUpgrading,
  } = useBilling();

  return (
    <div>
      <h2>Current Plan: {plan}</h2>
      <p>Users: {usage.users} / {limits.users === -1 ? '∞' : limits.users}</p>
      <button
        onClick={() => upgrade({ tenantId: 'xxx', newPlan: 'pro' })}
        disabled={isUpgrading}
      >
        Upgrade to Pro
      </button>
    </div>
  );
}
```

#### Component: `<FeatureGate>`

Conditionally render UI based on feature flag status:

```jsx
import FeatureGate from './components/FeatureGate';

// Basic usage — shows default "🔒 Feature Locked" prompt if disabled
<FeatureGate flagName="advanced_analytics">
  <AdvancedAnalytics />
</FeatureGate>

// With a custom fallback
<FeatureGate flagName="webhooks" fallback={<UpgradePrompt />}>
  <WebhooksConfig />
</FeatureGate>
```

#### Component: `<PlanBadge>`

Renders a colored badge based on the plan name:

```jsx
import PlanBadge from './components/PlanBadge';

<PlanBadge plan="pro" />
// Renders: free=gray, starter=blue, pro=purple, enterprise=gold
```

#### Route Guards

```jsx
import PrivateRoute from './components/PrivateRoute';
import SuperadminRoute from './components/SuperadminRoute';

// Requires authenticated user (redirects to /login)
<PrivateRoute>
  <Dashboard />
</PrivateRoute>

// Requires superadmin (redirects non-superadmins to /dashboard)
<SuperadminRoute>
  <SuperadminPanel />
</SuperadminRoute>
```

---

### 9. Docker Deployment

#### Using Docker Compose

Copy the `docker-compose.yml` to your project and adjust as needed. Key points:

- `db-init` is a one-shot container that runs `alembic upgrade head && python seed.py` before the backend starts.
- `backend` and `frontend` both mount their source directories as volumes in development mode.

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_USER: saas
      POSTGRES_PASSWORD: saas
      POSTGRES_DB: saas_bootstrapper
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U saas -d saas_bootstrapper"]
      interval: 5s
      timeout: 5s
      retries: 5

  db-init:
    build:
      context: ./backend
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://saas:saas@postgres:5432/saas_bootstrapper
      JWT_SECRET_KEY: ${JWT_SECRET_KEY:-change-me-jwt-secret}
      SUPERADMIN_SECRET: ${SUPERADMIN_SECRET:-change-me-superadmin-secret}
    command: >
      sh -c "alembic upgrade head && python seed.py"
    restart: "no"

  backend:
    build:
      context: ./backend
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      db-init:
        condition: service_completed_successfully
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://saas:saas@postgres:5432/saas_bootstrapper
      JWT_SECRET_KEY: ${JWT_SECRET_KEY:-change-me-jwt-secret}
      SUPERADMIN_SECRET: ${SUPERADMIN_SECRET:-change-me-superadmin-secret}
      CORS_ORIGINS: http://localhost:5173,http://localhost:3000

  frontend:
    build:
      context: ./frontend
    restart: unless-stopped
    depends_on:
      - backend
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000

volumes:
  postgres_data:
    driver: local
```

#### Commands

```bash
# Build and start everything
docker-compose up --build

# Run in background
docker-compose up -d

# View backend logs
docker-compose logs -f backend

# Tear down (preserves DB volume)
docker-compose down

# Tear down and wipe the database
docker-compose down -v
```

---

## Adding Your Own Tenant-Scoped Models

Any model you create that includes a `tenant_id` column will **automatically** be filtered by RLS — no extra configuration needed.

### Step 1: Create Your Model

```python
# app/models/domain.py  (add alongside existing models)
from sqlalchemy import Column, String, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, SerializerMixin


class Product(Base, TimestampMixin, SerializerMixin):
    __tablename__ = 'products'

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = Column(String(200), nullable=False)
    description = Column(String(500))
```

### Step 2: Create a Migration

```bash
# From the backend directory
alembic revision --autogenerate -m "add products table"
alembic upgrade head
```

### Step 3: Use It in Routes

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.api.dependencies import require_tenant
from app.models.domain import Product

router = APIRouter(prefix="/api/products", tags=["Products"])

@router.get("/")
async def list_products(
    claims: dict = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    # RLS automatically filters to the current tenant!
    result = await db.execute(select(Product))
    products = result.scalars().all()
    return {"products": [p.to_dict() for p in products]}
```

> **Key point:** You never need to manually add `.where(Product.tenant_id == ...)` — the RLS listener does it for you. This is structurally impossible to forget.

---

## Customization Reference

### Full App Factory Template

Here's a complete `main.py` that wires together all the bootstrapper features:

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import config
from app.core.middleware import TenantMiddleware
from app.core.rls import register_rls_listener
from app.api.routers import auth, tenants, features, admin, billing

app = FastAPI(
    title="My SaaS App",
    description="Built on the Multi-Tenant SaaS Bootstrapper",
    version="1.0.0",
)

# CORS — must be before TenantMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant resolution middleware
app.add_middleware(TenantMiddleware)

# Register RLS query interceptor (call once)
register_rls_listener()

# Core bootstrapper routers
app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(tenants.router,  prefix="/api/tenants",  tags=["Tenants"])
app.include_router(features.router, prefix="/api/features", tags=["Features"])
app.include_router(admin.router,    prefix="/api/admin",    tags=["Admin"])
app.include_router(billing.router,  prefix="/api/billing",  tags=["Billing"])

# Register YOUR custom routers here
# from app.api.routers import products
# app.include_router(products.router, prefix="/api/products", tags=["Products"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "saas-bootstrapper-fastapi"}
```

### Error Response Convention

All API errors follow this shape (FastAPI `HTTPException` detail):

```json
{
  "detail": "Human-readable message"
}
```

Common HTTP status codes used in this project:

| HTTP Status | Meaning |
|---|---|
| `400` | Missing or malformed request body / invalid input |
| `401` | No token provided, invalid credentials, or expired/invalid JWT |
| `403` | Valid token, insufficient access (role, tenant, or superadmin check failed) |
| `404` | Resource not found |
| `409` | Conflict — subdomain or email already taken |
| `500` | Unexpected server error |

### Database Session

All routes receive an `AsyncSession` via `Depends(get_db)`. The session is provided by `async_session_factory` from `app/db/session.py`, which uses `asyncpg` as the PostgreSQL driver. The `DATABASE_URL` in your `.env` can use either `postgresql://` or `postgresql+asyncpg://` format — the session module normalizes it automatically.

---

## Troubleshooting

### Common Issues

| Issue | Cause | Fix |
|---|---|---|
| `403 Tenant context required` on all routes | Tenant middleware can't resolve tenant | Pass `X-Tenant-ID` header in local dev |
| Queries return empty arrays | RLS is filtering — tenant context not set | Ensure middleware is registered and `set_tenant_id()` is called |
| `401 Authorization required` | No `Authorization` header | Include `Bearer <token>` in the request |
| `401 Token has expired` after 24h | Default JWT expiry is 86400 seconds | Increase `JWT_ACCESS_TOKEN_EXPIRES` in `.env` |
| `401 Invalid token` | Wrong `JWT_SECRET_KEY` between frontend and backend | Ensure both use the same secret |
| Migrations fail | Wrong `DATABASE_URL` or PostgreSQL not running | Check `.env` and verify `pg_isready` |
| `409 Subdomain already taken` on provision | Subdomain already exists | Choose a unique subdomain |
| Feature flag not appearing | Flag wasn't seeded | Call `await seed_flags(db, tenant_id, plan)` or re-provision |
| Frontend `401` redirect loop | Token expired and no refresh logic | Clear `localStorage` and re-login |
| Docker `db-init` fails | PostgreSQL not ready | Ensure `healthcheck` is configured on the postgres service |
| `asyncpg` import error | `asyncpg` not installed | Run `pip install asyncpg` or check `requirements.txt` |

### Verifying RLS Is Active

```python
# Quick async test — run with:  python -c "import asyncio; from test_rls import main; asyncio.run(main())"
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.models.domain import User
from app.core.rls import set_tenant_id, bypass_rls, register_rls_listener

register_rls_listener()

async def main():
    engine = create_async_engine("postgresql+asyncpg://saas:saas@localhost/saas_bootstrapper")
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        # Without tenant context — returns no results (RLS blocks unscoped queries)
        result = await db.execute(select(User))
        print("No context:", result.scalars().all())  # []

        # With tenant context — returns only that tenant's users
        set_tenant_id("your-tenant-uuid")
        result = await db.execute(select(User))
        print("With tenant:", result.scalars().all())  # [<User alice@acme.com>]

        # With bypass — returns all users
        with bypass_rls():
            result = await db.execute(select(User))
            print("Bypassed:", result.scalars().all())  # All users
```

### Health Check

The bootstrapper includes a built-in health endpoint:

```bash
curl http://localhost:8000/api/health
# → {"status": "healthy", "service": "saas-bootstrapper-fastapi"}
```

The interactive API docs (Swagger UI) are at:

```
http://localhost:8000/docs
```

The alternative ReDoc docs are at:

```
http://localhost:8000/redoc
```

---

> **Need help?** Open an issue on the repository or refer to the [main README](./README.md) for the full project documentation.
