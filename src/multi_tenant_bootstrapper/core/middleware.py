"""Tenant resolution middleware for subdomain-based routing.

Resolves the current tenant from the ``Host`` header (subdomain extraction)
or the ``X-Tenant-ID`` header (local development fallback), and sets
``request.state.tenant`` plus the RLS context variable on every request.
"""

import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select

from multi_tenant_bootstrapper.db.session import get_session_factory
from multi_tenant_bootstrapper.models.domain import Tenant
from multi_tenant_bootstrapper.core.rls import set_tenant_id, clear_tenant_id, bypass_rls
from multi_tenant_bootstrapper.config import get_config

_DEFAULT_SKIP_HOSTS = re.compile(
    r'^(localhost|127\.0\.0\.1|0\.0\.0\.0|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
)


def _get_skip_hosts_pattern() -> re.Pattern:
    """Return the compiled skip-hosts regex, honouring config overrides."""
    config = get_config()
    if config.SKIP_HOSTS_PATTERN:
        return re.compile(config.SKIP_HOSTS_PATTERN)
    return _DEFAULT_SKIP_HOSTS


def _extract_subdomain(host: str) -> str | None:
    """Extract the subdomain from a Host header value.

    Returns ``None`` for localhost, raw IPs, or hosts without a subdomain.
    """
    if not host:
        return None
    hostname = host.split(':')[0]
    skip_re = _get_skip_hosts_pattern()
    if skip_re.match(hostname):
        return None
    parts = hostname.split('.')
    if len(parts) >= 2:
        return parts[0]
    return None


class TenantMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that resolves tenant context per-request."""

    async def dispatch(self, request: Request, call_next):
        # Clear context initially
        clear_tenant_id()
        request.state.tenant = None

        host = request.headers.get('host', '')
        subdomain = _extract_subdomain(host)
        tenant_id_header = request.headers.get('X-Tenant-ID')

        tenant = None

        if subdomain or tenant_id_header:
            session_factory = get_session_factory()
            async with session_factory() as session:
                with bypass_rls():
                    if subdomain:
                        result = await session.execute(
                            select(Tenant).where(
                                Tenant.subdomain == subdomain,
                                Tenant.status == 'active',
                            )
                        )
                        tenant = result.scalar_one_or_none()

                    if not tenant and tenant_id_header:
                        try:
                            result = await session.execute(
                                select(Tenant).where(
                                    Tenant.id == tenant_id_header,
                                    Tenant.status == 'active',
                                )
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
