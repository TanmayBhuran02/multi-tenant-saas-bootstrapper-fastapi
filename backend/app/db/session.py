import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv()

# We need an async dialect for postgres. Convert postgresql:// to postgresql+asyncpg://
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://saas:saas@localhost:5432/saas_bootstrapper'
).replace("postgresql://", "postgresql+asyncpg://")

# If it's sqlite, we can use sqlite+aiosqlite://
if DATABASE_URL.startswith("sqlite://"):
    DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")

engine = create_async_engine(
    DATABASE_URL,
    echo=os.environ.get('SQLALCHEMY_ECHO', 'False').lower() == 'true',
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db():
    """Dependency for getting async database session."""
    async with async_session_factory() as session:
        yield session
