from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _connect_args() -> dict:
    """SQLite: WAL mode + busy timeout untuk concurrent read/write."""
    return {"timeout": 30}


engine = create_async_engine(
    get_settings().database_url,
    echo=get_settings().debug,
    connect_args=_connect_args(),
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    """Aktifkan WAL mode — scheduler (write) + API (read) bisa barengan."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=30000")
    cur.close()


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
