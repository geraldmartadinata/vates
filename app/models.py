from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

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
    volume = Column(Integer)

    def __repr__(self) -> str:
        return f"<CachedPrice {self.ticker} {self.date.date()}>"
