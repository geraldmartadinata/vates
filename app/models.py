from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class CachedPrice(Base):
    """Cache harga harian saham — mengurangi fetch berulang ke OpenBB."""

    __tablename__ = "cached_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), index=True, nullable=False)
    date = Column(DateTime, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_ticker_date"),
    )

    def __repr__(self) -> str:
        return f"<CachedPrice {self.ticker} {self.date.date()}>"


class News(Base):
    """Berita saham / event yang mempengaruhi harga."""
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), index=True, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(String(500))
    published_at = Column(DateTime, nullable=False, server_default=func.now())
    sentiment_score = Column(Float)
    impact = Column(String(20), default="neutral")