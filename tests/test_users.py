"""Fase 0 — test untuk User + UserWatchlist (memori per akun)."""


import pytest
from sqlalchemy import select

from app.models import User, UserWatchlist


@pytest.mark.asyncio
async def test_create_user(db_session):
    """User bisa dibuat dengan telegram_id unik."""
    user = User(telegram_id=123456789, username="testuser")
    db_session.add(user)
    await db_session.commit()

    fetched = (
        await db_session.execute(select(User).where(User.telegram_id == 123456789))
    ).scalar_one()
    assert fetched.username == "testuser"
    assert fetched.id is not None


@pytest.mark.asyncio
async def test_duplicate_telegram_id_rejected(db_session):
    """Dua user dengan telegram_id sama → IntegrityError (unique)."""
    from sqlalchemy.exc import IntegrityError

    db_session.add(User(telegram_id=999))
    await db_session.commit()

    db_session.add(User(telegram_id=999))
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_add_to_watchlist(db_session):
    """Watchlist: user + ticker tersimpan, unique per user+ticker."""
    user = User(telegram_id=555, username="alice")
    db_session.add(user)
    await db_session.commit()

    db_session.add(UserWatchlist(user_id=user.id, ticker="BBCA.JK"))
    db_session.add(UserWatchlist(user_id=user.id, ticker="TLKM.JK"))
    await db_session.commit()

    rows = (
        await db_session.execute(
            select(UserWatchlist).where(UserWatchlist.user_id == user.id)
        )
    ).scalars().all()
    assert len(rows) == 2
    assert {r.ticker for r in rows} == {"BBCA.JK", "TLKM.JK"}


@pytest.mark.asyncio
async def test_watchlist_duplicate_ticker_rejected(db_session):
    """Ticker yang sama 2x untuk user yang sama → IntegrityError."""
    from sqlalchemy.exc import IntegrityError

    user = User(telegram_id=777)
    db_session.add(user)
    await db_session.commit()

    db_session.add(UserWatchlist(user_id=user.id, ticker="BBCA.JK"))
    await db_session.commit()

    db_session.add(UserWatchlist(user_id=user.id, ticker="BBCA.JK"))
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_watchlist_isolated_per_user(db_session):
    """Watchlist user A tidak bocor ke user B."""
    a = User(telegram_id=1, username="a")
    b = User(telegram_id=2, username="b")
    db_session.add_all([a, b])
    await db_session.commit()

    db_session.add(UserWatchlist(user_id=a.id, ticker="BBCA.JK"))
    await db_session.commit()

    b_rows = (
        await db_session.execute(
            select(UserWatchlist).where(UserWatchlist.user_id == b.id)
        )
    ).scalars().all()
    assert b_rows == []


@pytest.mark.asyncio
async def test_remove_from_watchlist(db_session):
    """Hapus ticker dari watchlist."""
    user = User(telegram_id=321)
    db_session.add(user)
    await db_session.commit()

    row = UserWatchlist(user_id=user.id, ticker="ASII.JK")
    db_session.add(row)
    await db_session.commit()

    await db_session.delete(row)
    await db_session.commit()

    remaining = (
        await db_session.execute(
            select(UserWatchlist).where(UserWatchlist.user_id == user.id)
        )
    ).scalars().all()
    assert remaining == []
