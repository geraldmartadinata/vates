"""News ingestion – placeholder for real headline fetch."""
import asyncio
from datetime import datetime

from app.models import News

async def insert_dummy_news(session, ticker):
    """Insert a single dummy news row (used while prototyping)."""
    news_item = News(
        ticker=ticker,
        title="Sample market sentiment",
        content="No real news yet.",
        published_at=datetime.utcnow(),
        sentiment_score=0.0,
        impact="neutral",
    )
    session.add(news_item)
    await session.commit()