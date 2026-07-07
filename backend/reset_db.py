import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models.base import Base
from app.core.config import config

url = config.DATABASE_URL
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(url)

async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        # also drop alembic_version explicitly just in case
        await conn.execute(
            __import__('sqlalchemy').text("DROP TABLE IF EXISTS alembic_version")
        )
    print("Database reset!")

asyncio.run(reset_db())
