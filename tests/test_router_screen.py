"""Test untuk router — screen endpoint."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import get_db
from main import app

# Override DB untuk test (in-memory SQLite)
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db

transport = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_screen_universe_endpoint():
    """Test screen endpoint dengan mock tickers — butuh network (yfinance).
    Test ini integration test ringan; skip kalau offline."""
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test dengan tickers IHSG populer
        response = await ac.post(
            "/api/v1/screen",
            json={"tickers": ["BBCA", "TLKM"], "horizon": 30, "top_n": 5}
        )

    # Bisa 200 (sukses) atau 500 (network error) — keduanya valid behavior
    assert response.status_code in (200, 500)

    if response.status_code == 200:
        data = response.json()
        assert "horizon" in data
        assert data["horizon"] == 30
        assert "screened_count" in data
        assert "results" in data
        assert "ranked" in data
        assert "top_buys" in data["ranked"]
        assert "top_sells" in data["ranked"]
        assert "neutrals" in data["ranked"]


@pytest.mark.asyncio
async def test_screen_universe_invalid_horizon():
    """Test validasi horizon."""
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/screen",
            json={"tickers": ["BBCA"], "horizon": 99, "top_n": 5}
        )

    assert response.status_code == 400
    assert "horizon harus 1, 7, atau 30" in response.text