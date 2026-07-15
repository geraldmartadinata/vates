"""Fixtures bersama — SQLite in-memory untuk semua test async."""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base


@pytest_asyncio.fixture
async def db_engine():
    """In-memory SQLite engine — isolated per test session."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """AsyncSession per test — rollback otomatis setelah test."""
    factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
def sample_ticker() -> str:
    return "BBCA.JK"


@pytest_asyncio.fixture
def sample_ohlcv_df() -> pd.DataFrame:
    """DataFrame OHLCV palsu — 5 hari: today-4 sampai today."""
    rows = []
    today = date.today()
    for i in range(5):
        d = today - timedelta(days=4 - i)
        rows.append({
            "date": d,
            "open": 10000.0 + i * 50,
            "high": 10100.0 + i * 50,
            "low": 9900.0 + i * 50,
            "close": 10050.0 + i * 50,
            "volume": int(1000000 + i * 100000),
        })
    return pd.DataFrame(rows)


@pytest_asyncio.fixture
def sample_raw_openbb_response() -> dict:
    """Meniru struktur OBBject yang dikembalikan oleh OpenBB."""
    return {
        "results": [
            {"date": "2025-06-30", "open": 10000.0, "high": 10100.0, "low": 9900.0,
             "close": 10050.0, "volume": 1000000},
            {"date": "2025-07-01", "open": 10050.0, "high": 10150.0, "low": 9950.0,
             "close": 10100.0, "volume": 1100000},
        ]
    }
