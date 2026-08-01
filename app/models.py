from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, Integer, String, UniqueConstraint
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


class Prediction(Base):
    """Prediksi model per horizon + hasil aktual (feedback loop)."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), index=True, nullable=False)
    horizon_days = Column(Integer, nullable=False)          # 1 / 7 / 30
    predicted_prob = Column(Float, nullable=False)          # P(up)
    predicted_label = Column(Integer, nullable=False)       # 1=up, 0=down
    model_version = Column(String(50), default="v1-logreg")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Feedback — diisi saat horizon berakhir
    resolved_at = Column(DateTime)
    actual_ret = Column(Float)
    actual_label = Column(Integer)
    was_correct = Column(Boolean)
    miss_reason = Column(String(20))                        # model / event