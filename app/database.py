from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    get_settings().database_url,
    echo=get_settings().debug,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """Dependency injection untuk FastAPI — yield session, auto close."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
