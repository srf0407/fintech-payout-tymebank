from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from ..core.config import settings

# Handle different database URL formats
if settings.database_url.startswith("postgresql://"):
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    database_url = settings.database_url

engine = create_async_engine(database_url, pool_pre_ping=True, pool_recycle=300)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        await session.close()