"""Database seed script — importable and callable.

Can be called programmatically::

    from multi_tenant_bootstrapper.seed import run_seed
    import asyncio
    asyncio.run(run_seed())

Or run from the command line::

    python -m multi_tenant_bootstrapper.seed
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from multi_tenant_bootstrapper.models.domain import Tenant, User, PlanType, UserRole
from multi_tenant_bootstrapper.core.flags import seed_flags
from multi_tenant_bootstrapper.core.rls import bypass_rls
from multi_tenant_bootstrapper.db.session import get_engine, get_session_factory, init_db
from multi_tenant_bootstrapper.config import get_config


async def run_seed(
    *,
    superadmin_email: str | None = None,
    superadmin_password: str | None = None,
    create_demo: bool = True,
) -> None:
    """Create default superadmin and (optionally) a demo tenant.

    Parameters
    ----------
    superadmin_email:
        Override for the superadmin email (default: ``SUPERADMIN_EMAIL``
        env var or ``admin@saas.com``).
    superadmin_password:
        Override for the superadmin password (default: ``SUPERADMIN_PASSWORD``
        env var or ``superadmin123``).
    create_demo:
        Whether to create the demo tenant with sample users.
    """
    # Ensure DB is initialised
    try:
        get_engine()
    except RuntimeError:
        config = get_config()
        init_db(config.get_async_database_url(), echo=config.SQLALCHEMY_ECHO)

    session_factory = get_session_factory()

    sa_email = superadmin_email or os.environ.get('SUPERADMIN_EMAIL', 'admin@saas.com')
    sa_password = superadmin_password or os.environ.get('SUPERADMIN_PASSWORD', 'superadmin123')

    async with session_factory() as session:
        with bypass_rls():
            # ── Create superadmin user ──
            result = await session.execute(
                select(User).where(User.email == sa_email)
            )
            existing_admin = result.scalar_one_or_none()

            if existing_admin:
                print(f'Superadmin {sa_email} already exists, skipping.')
            else:
                platform_tenant = Tenant(
                    slug='platform',
                    subdomain='platform',
                    display_name='Platform Admin',
                    plan=PlanType.enterprise,
                )
                session.add(platform_tenant)
                await session.flush()

                superadmin = User(
                    tenant_id=platform_tenant.id,
                    email=sa_email,
                    role=UserRole.owner,
                    is_superadmin=True,
                )
                superadmin.set_password(sa_password)
                session.add(superadmin)

                await seed_flags(session, platform_tenant.id, PlanType.enterprise)
                await session.commit()

                print(f'✓ Created superadmin: {sa_email} / {sa_password}')
                print(f'  Tenant: platform (id: {platform_tenant.id})')

            # ── Create demo tenant ──
            if create_demo:
                result = await session.execute(
                    select(Tenant).where(Tenant.subdomain == 'demo')
                )
                demo_tenant = result.scalar_one_or_none()

                if demo_tenant:
                    print('Demo tenant already exists, skipping.')
                else:
                    demo_tenant = Tenant(
                        slug='demo',
                        subdomain='demo',
                        display_name='Demo Company',
                        plan=PlanType.starter,
                    )
                    session.add(demo_tenant)
                    await session.flush()

                    demo_owner = User(
                        tenant_id=demo_tenant.id,
                        email='owner@demo.com',
                        role=UserRole.owner,
                    )
                    demo_owner.set_password('demo12345')
                    session.add(demo_owner)

                    demo_member = User(
                        tenant_id=demo_tenant.id,
                        email='member@demo.com',
                        role=UserRole.member,
                    )
                    demo_member.set_password('demo12345')
                    session.add(demo_member)

                    await seed_flags(session, demo_tenant.id, PlanType.starter)
                    await session.commit()

                    print(f'✓ Created demo tenant: demo (id: {demo_tenant.id})')
                    print(f'  Owner: owner@demo.com / demo12345')

    print('\n✓ Seed complete!')


if __name__ == '__main__':
    asyncio.run(run_seed())
