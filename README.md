# Multi-Tenant SaaS Bootstrapper

A production-grade multi-tenant SaaS starter kit built with **Python Flask**, **PostgreSQL**, and **React (Vite + React Router v6)**. Ships with tenant provisioning, subdomain-based routing, row-level security, feature flags, plan/billing management, and a superadmin panel — all wired together and ready to extend.

---

## Table of contents

- [Architecture overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [Database setup](#database-setup)
- [Running the project](#running-the-project)
- [Project structure](#project-structure)
- [API reference](#api-reference)
- [Plans & feature flags](#plans--feature-flags)
- [Multi-tenancy & RLS](#multi-tenancy--rls)
- [Frontend](#frontend)
- [Docker](#docker)
- [Testing](#testing)
- [Conventions](#conventions)

---

## Architecture overview

```
Browser (acme.yoursaas.com)
        │
        ▼
┌───────────────────────────────┐
│  Tenant context middleware    │  Reads Host header → looks up subdomain
│  (app/tenants/middleware.py)  │  → sets g.tenant + ContextVar
└──────────────┬────────────────┘
               │
┌──────────────▼────────────────┐
│  JWT auth layer               │  Verifies token, extracts tenant_id,
│  (app/auth/)                  │  role, is_superadmin
└──────────────┬────────────────┘
               │
┌──────────────▼────────────────┐
│  RLS query interceptor        │  Auto-injects WHERE tenant_id = X
│  (app/rls/events.py)          │  on every SQLAlchemy query
└──────────────┬────────────────┘
               │
┌──────────────▼────────────────┐
│  PostgreSQL (shared schema)   │  Single DB, all tenants in the same
│                               │  tables, isolated by tenant_id column
└───────────────────────────────┘
```

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+
- Docker & Docker Compose (optional but recommended)

---

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/your-org/saas-bootstrapper.git
cd saas-bootstrapper
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in your values
```

### 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env.local      # then fill in your values
```

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Required | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/saas_db` |
| `JWT_SECRET_KEY` | ✅ | Secret used to sign JWT tokens | `a-long-random-string` |
| `SUPERADMIN_SECRET` | ✅ | Token/password for bootstrapping the first superadmin | `super-secret-value` |
| `FLASK_ENV` | ✅ | `development`, `production`, or `testing` | `development` |
| `FLASK_APP` | ✅ | Entry point for Flask CLI | `run.py` |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description | Example |
|---|---|---|---|
| `VITE_API_URL` | ✅ | Base URL of the Flask backend | `http://localhost:5000` |

---

## Database setup

```bash
cd backend

# Run migrations
flask db upgrade

# (First time only) seed a superadmin user
flask seed-superadmin --email admin@yoursaas.com --password changeme
```

To create a new migration after changing models:

```bash
flask db migrate -m "describe your change"
flask db upgrade
```

---

## Running the project

### Development (without Docker)

```bash
# Terminal 1 — backend
cd backend
source venv/bin/activate
flask run --port 5000

# Terminal 2 — frontend
cd frontend
npm run dev
```

### With Docker Compose

```bash
docker-compose up --build
```

Services started:

| Service | URL |
|---|---|
| Backend API | `http://localhost:5000` |
| Frontend | `http://localhost:5173` |
| PostgreSQL | `localhost:5432` |

The `db-init` service runs `flask db upgrade` automatically on first start.

---

## Project structure

```
saas-bootstrapper/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App factory: create_app()
│   │   ├── admin/
│   │   │   └── routes.py        # Superadmin-only aggregate endpoints
│   │   ├── auth/
│   │   │   ├── jwt.py           # JWT setup and claims
│   │   │   └── decorators.py    # @require_tenant, @superadmin_only
│   │   ├── billing/
│   │   │   ├── plans.py         # PLAN_LIMITS dict
│   │   │   └── routes.py        # /api/billing endpoints
│   │   ├── features/
│   │   │   ├── flags.py         # PLAN_FLAGS dict + seed_flags()
│   │   │   └── routes.py        # /api/features endpoints
│   │   ├── rls/
│   │   │   └── events.py        # SQLAlchemy RLS query interceptor
│   │   └── tenants/
│   │       ├── middleware.py    # Tenant context middleware
│   │       ├── models.py        # Tenant, TenantConfig, User, FeatureFlag
│   │       └── routes.py        # /api/tenants endpoints
│   ├── migrations/              # Alembic migration files
│   ├── config.py                # Dev / Prod / Testing config classes
│   ├── requirements.txt
│   └── run.py
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js        # Axios instance with interceptors
│   │   ├── context/
│   │   │   └── TenantContext.jsx
│   │   ├── hooks/
│   │   │   ├── useTenant.js
│   │   │   ├── useFeatureFlag.js
│   │   │   └── useBilling.js
│   │   ├── pages/
│   │   │   ├── Dashboard/
│   │   │   ├── Onboarding/
│   │   │   └── Superadmin/
│   │   ├── components/
│   │   │   ├── FeatureGate.jsx
│   │   │   └── PlanBadge.jsx
│   │   └── App.jsx              # Routes + guards
│   ├── index.html
│   └── vite.config.js
│
├── docker-compose.yml
└── README.md
```

---

## API reference

All endpoints return JSON. Errors follow the shape:

```json
{ "error": "Human-readable message", "code": "MACHINE_CODE" }
```

All UUIDs are returned as strings.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | None | Returns a JWT token |
| `POST` | `/api/auth/refresh` | Bearer token | Refreshes an expiring token |

**Login example:**
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@acme.com", "password": "secret"}'
```

Response:
```json
{ "access_token": "<jwt>", "tenant_id": "uuid-...", "role": "owner" }
```

---

### Tenants

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/tenants/provision` | Superadmin | Create a new tenant + owner user |
| `DELETE` | `/api/tenants/:tenant_id` | Superadmin | Soft-delete a tenant |
| `GET` | `/api/tenants/:tenant_id/config` | Tenant member | Get non-secret config entries |
| `PATCH` | `/api/tenants/:tenant_id/config` | Owner / Admin | Upsert a config entry |

**Provision a tenant:**
```bash
curl -X POST http://localhost:5000/api/tenants/provision \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Acme Corp",
    "subdomain": "acme",
    "plan": "pro",
    "owner_email": "alice@acme.com",
    "owner_password": "secure-password"
  }'
```

**Soft-delete a tenant:**
```bash
curl -X DELETE http://localhost:5000/api/tenants/<tenant_id> \
  -H "Authorization: Bearer <superadmin_token>"
```
Returns `204 No Content`. The tenant row is not removed — `status` is set to `deleted`.

**Upsert a config entry:**
```bash
curl -X PATCH http://localhost:5000/api/tenants/<tenant_id>/config \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"key": "theme_color", "value": "#6366f1", "is_secret": false}'
```

---

### Feature flags

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/features` | Tenant member | List all flags for the current tenant |
| `PATCH` | `/api/features/:flag_name` | Superadmin | Toggle a flag for a specific tenant |

**List flags:**
```bash
curl http://localhost:5000/api/features \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: <tenant_id>"    # local dev only
```

**Toggle a flag:**
```bash
curl -X PATCH http://localhost:5000/api/features/webhooks \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "<uuid>", "enabled": true}'
```

---

### Billing

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/billing/plan` | Tenant member | Current plan, limits, and usage |
| `POST` | `/api/billing/upgrade` | Superadmin | Upgrade a tenant to a higher plan |

**Upgrade a tenant:**
```bash
curl -X POST http://localhost:5000/api/billing/upgrade \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "<uuid>", "new_plan": "enterprise"}'
```

---

### Admin

All routes require a superadmin token.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/admin/tenants` | Paginated tenant list with user counts |
| `GET` | `/api/admin/tenants/:id/metrics` | Per-tenant metrics |
| `GET` | `/api/admin/metrics` | Aggregated metrics across all tenants |

**Paginated tenant list:**
```bash
curl "http://localhost:5000/api/admin/tenants?page=1&per_page=20" \
  -H "Authorization: Bearer <superadmin_token>"
```

---

## Plans & feature flags

### Plan tiers

| Plan | Max users | API calls/month |
|---|---|---|
| `free` | 3 | 1,000 |
| `starter` | 10 | 10,000 |
| `pro` | 50 | 100,000 |
| `enterprise` | Unlimited | Unlimited |

### Default flags per plan

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

Upgrading a plan re-seeds new flags automatically. Manually toggled flags are never removed during an upgrade.

---

## Multi-tenancy & RLS

This project uses **shared schema** multi-tenancy. Every tenant-scoped table has a `tenant_id` UUID column. Data isolation is enforced at the ORM layer — not in individual route handlers — so it's structurally impossible to forget a filter.

**How it works:**

1. `app/tenants/middleware.py` reads the `Host` header on every request, looks up the subdomain, and stores the `tenant_id` in a `ContextVar`.
2. `app/rls/events.py` listens on the SQLAlchemy `do_orm_execute` event and automatically appends `.where(Model.tenant_id == get_tenant_id())` to every query on tenant-scoped models.
3. Superadmin routes activate `bypass_rls()` (a context manager) to query across all tenants.

**Local development** — pass `X-Tenant-ID: <uuid>` as a request header instead of relying on subdomain DNS:

```bash
curl http://localhost:5000/api/features \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: <tenant_uuid>"
```

---

## Frontend

### Key hooks

```jsx
const { tenant, user, plan } = useTenant();

const hasWebhooks = useFeatureFlag('webhooks');  // → boolean

const { plan, limits, upgrade } = useBilling();
```

### Feature gating in components

```jsx
import FeatureGate from '@/components/FeatureGate';

<FeatureGate flagName="advanced_analytics">
  <AdvancedAnalytics />
</FeatureGate>

// With a fallback:
<FeatureGate flagName="webhooks" fallback={<UpgradePrompt />}>
  <WebhooksConfig />
</FeatureGate>
```

### Plan badge

```jsx
import PlanBadge from '@/components/PlanBadge';

<PlanBadge plan="pro" />
// Renders a colored badge: free=gray, starter=blue, pro=purple, enterprise=gold
```

### Routes

| Path | Component | Guard |
|---|---|---|
| `/` | Redirect | Redirects to `/onboarding` or `/dashboard` |
| `/onboarding` | `OnboardingWizard` | None |
| `/login` | `LoginPage` | None |
| `/dashboard` | `Dashboard` | `PrivateRoute` (valid JWT) |
| `/superadmin` | `SuperadminPanel` | `SuperadminRoute` (is_superadmin claim) |

---

## Docker

```yaml
# docker-compose.yml services
postgres:   postgres:15, persistent volume
backend:    python:3.12-slim, runs Flask
db-init:    runs `flask db upgrade` on first start
frontend:   node:18-alpine, runs Vite dev server
```

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

## Testing

```bash
cd backend
pytest                          # run all tests
pytest -k "test_tenant"         # filter by name
pytest --cov=app                # with coverage report
```

Set `FLASK_ENV=testing` to use `TestingConfig`, which points to a separate test database and disables JWT expiry checks.

---

## Conventions

- All Flask routes return JSON. No HTML responses.
- Every model exposes a `to_dict()` method. No raw SQLAlchemy objects in responses.
- No raw SQL anywhere — SQLAlchemy ORM only (migrations use Alembic SQL where needed).
- UUIDs are always returned as strings, never bytes.
- No hardcoded tenant IDs anywhere — always sourced from JWT claims or `flask.g.tenant`.
- React components: functional components and hooks only, no class components.
- Error shape is always `{ "error": "...", "code": "..." }` with an appropriate HTTP status code.
