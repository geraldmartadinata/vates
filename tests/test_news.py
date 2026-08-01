"""Test services/news_processor.py — sentiment, impact, RSS parsing."""

from datetime import datetime

import pytest
from sqlalchemy import select

from services.news_processor import _impact, _parse_rss, _sentiment_score

RSS_SAMPLE = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>News</title>
<item>
<title>BBCA laba tumbuh, rekomendasi beli</title>
<link>https://example.com/1</link>
<pubDate>Sat, 01 Aug 2026 07:00:00 GMT</pubDate>
</item>
<item>
<title>Saham merosot, investor jual</title>
<link>https://example.com/2</link>
<pubDate>Sun, 02 Aug 2026 07:00:00 GMT</pubDate>
</item>
<item>
<title>Pasar datar hari ini</title>
<link>https://example.com/3</link>
<pubDate>Mon, 03 Aug 2026 07:00:00 GMT</pubDate>
</item>
</channel></rss>"""


class TestSentiment:
    def test_positive(self):
        assert _sentiment_score("Laba tumbuh, rekomendasi beli") > 0

    def test_negative(self):
        assert _sentiment_score("Saham merosot, investor jual") < 0

    def test_neutral(self):
        assert _sentiment_score("Pasar datar hari ini") == 0.0

    def test_empty(self):
        assert _sentiment_score("") == 0.0

    def test_bounded(self):
        s = _sentiment_score("laba tumbuh pulih naik melesat beli")
        assert -1.0 <= s <= 1.0


class TestImpact:
    def test_high(self):
        assert _impact(0.8) == "high"

    def test_medium(self):
        assert _impact(0.3) == "medium"

    def test_low(self):
        assert _impact(0.1) == "low"

    def test_neutral_low(self):
        assert _impact(0.0) == "low"


class TestRssParsing:
    def test_parse_three_items(self):
        items = _parse_rss(RSS_SAMPLE)
        assert len(items) == 3

    def test_parse_limits(self):
        items = _parse_rss(RSS_SAMPLE, limit=2)
        assert len(items) == 2

    def test_parse_fields(self):
        items = _parse_rss(RSS_SAMPLE)
        assert items[0]["title"].startswith("BBCA")
        assert items[0]["link"] == "https://example.com/1"
        assert items[0]["published_at"].year == 2026

    def test_parse_invalid(self):
        assert _parse_rss(b"<not xml") == []


@pytest.mark.asyncio
async def test_ingest_news_saves_rows(db_session, sample_ticker, monkeypatch):
    from app.models import News
    from services.news_processor import ingest_news

    fake_items = [
        {
            "title": "BBCA laba tumbuh",
            "link": "https://example.com/x",
            "published_at": datetime(2026, 8, 1),
            "sentiment_score": 0.5,
            "impact": "high",
        }
    ]

    def fake_fetch(ticker, query=None, limit=20):
        return fake_items

    monkeypatch.setattr("services.news_processor.fetch_news", fake_fetch)

    inserted = await ingest_news(db_session, sample_ticker, limit=5)
    assert inserted == 1

    rows = (await db_session.execute(
        select(News).where(News.ticker == sample_ticker)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].sentiment_score == 0.5
