from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import config

from app.core.middleware import TenantMiddleware
from app.api.routers import auth, tenants, features, admin, billing

app = FastAPI(
    title="Multi-Tenant SaaS Bootstrapper",
    description="FastAPI port of the Multi-Tenant SaaS Bootstrapper",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant Middleware
app.add_middleware(TenantMiddleware)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(tenants.router, prefix="/api/tenants", tags=["Tenants"])
app.include_router(features.router, prefix="/api/features", tags=["Features"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "saas-bootstrapper-fastapi"}
