import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.domain import Tenant
from app.core.rls import set_tenant_id, clear_tenant_id, bypass_rls

_SKIP_HOSTS = re.compile(
    r'^(localhost|127\.0\.0\.1|0\.0\.0\.0|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
)

def _extract_subdomain(host: str) -> str | None:
    if not host:
        return None
    hostname = host.split(':')[0]
    if _SKIP_HOSTS.match(hostname):
        return None
    parts = hostname.split('.')
    if len(parts) >= 2:
        return parts[0]
    return None

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Clear context initially
        clear_tenant_id()
        request.state.tenant = None
        
        host = request.headers.get('host', '')
        subdomain = _extract_subdomain(host)
        tenant_id_header = request.headers.get('X-Tenant-ID')
        
        tenant = None
        
        if subdomain or tenant_id_header:
            async with async_session_factory() as session:
                with bypass_rls():
                    if subdomain:
                        result = await session.execute(
                            select(Tenant).where(Tenant.subdomain == subdomain, Tenant.status == 'active')
                        )
                        tenant = result.scalar_one_or_none()
                    
                    if not tenant and tenant_id_header:
                        try:
                            result = await session.execute(
                                select(Tenant).where(Tenant.id == tenant_id_header, Tenant.status == 'active')
                            )
                            tenant = result.scalar_one_or_none()
                        except Exception:
                            # Catch invalid UUID errors if tenant_id_header is bad
                            pass

        if tenant:
            request.state.tenant = tenant
            set_tenant_id(str(tenant.id))
        
        try:
            response = await call_next(request)
        finally:
            clear_tenant_id()
            
        return response
