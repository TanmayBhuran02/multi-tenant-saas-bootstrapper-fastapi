import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.models.domain import Tenant, User, PlanType, UserRole
from app.core.flags import seed_flags
from app.core.rls import bypass_rls
from app.core.config import config

url = config.DATABASE_URL
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(url)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def seed():
    """Create default superadmin and demo tenant."""
    async with async_session() as session:
        with bypass_rls():
            # ── Create superadmin user ──
            superadmin_email = os.environ.get('SUPERADMIN_EMAIL', 'admin@saas.com')
            superadmin_password = os.environ.get('SUPERADMIN_PASSWORD', 'superadmin123')

            result = await session.execute(select(User).where(User.email == superadmin_email))
            existing_admin = result.scalar_one_or_none()
            if existing_admin:
                print(f'Superadmin {superadmin_email} already exists, skipping.')
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
                    email=superadmin_email,
                    role=UserRole.owner,
                    is_superadmin=True,
                )
                superadmin.set_password(superadmin_password)
                session.add(superadmin)

                await seed_flags(session, platform_tenant.id, PlanType.enterprise)
                await session.commit()

                print(f'✓ Created superadmin: {superadmin_email} / {superadmin_password}')
                print(f'  Tenant: platform (id: {platform_tenant.id})')

            # ── Create demo tenant ──
            result = await session.execute(select(Tenant).where(Tenant.subdomain == 'demo'))
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
    asyncio.run(seed())
