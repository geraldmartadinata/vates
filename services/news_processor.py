"""News ingestion via Google News RSS (no API key) + lexicon sentiment.

Menyediakan: fetch_news, _sentiment_score, ingest_news (save ke DB).
"""

import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

from sqlalchemy import select

from app.models import News

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0"}

_RSS_URL = "https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:en"

_POSITIVE = {
    "naik", "tumbuh", "melesat", "melaju", "pulih", "pemulihan", "rekomendasi",
    "beli", "akuisisi", "ekspansi", "investasi", "dividen", "laba", "untung",
    "profit", "bangkit", "optimistis", "outperform", "kenaikan", "rise", "grow",
    "rally", "upgrade", "buy", "growth", "strong",
}
_NEGATIVE = {
    "turun", "merosot", "anjlok", "ambruk", "rugi", "penurunan", "koreksi",
    "jual", "dijual", "dipangkas", "krisis", "default", "gagal", "tunda",
    "pemecatan", "tuntutan", "investigasi", "turunkan", "waspada", "pressur",
    "sell", "downgrade", "drop", "fall", "weak", "bankrupt", "crash",
}


def _sentiment_score(text: str) -> float:
    """Skor sentimen sederhana berbasis kata kunci → [-1.0, 1.0]."""
    if not text:
        return 0.0
    words = text.lower().split()
    pos = sum(1 for w in words if w in _POSITIVE)
    neg = sum(1 for w in words if w in _NEGATIVE)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def _impact(score: float) -> str:
    """Klasifikasi dampak berdasarkan magnitudo sentimen."""
    if abs(score) > 0.5:
        return "high"
    if abs(score) > 0.2:
        return "medium"
    return "low"


def _parse_rss(xml_bytes: bytes, limit: int = 20) -> list[dict]:
    """Parse RSS Google News → list dict {title, link, published_at}."""
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.error("Gagal parse RSS: %s", exc)
        return items

    for item in root.findall(".//item")[:limit]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        pub_date_raw = item.findtext("pubDate") or ""
        published_at = _parse_pubdate(pub_date_raw)
        items.append({"title": title, "link": link, "published_at": published_at})
    return items


def _parse_pubdate(raw: str) -> datetime:
    """Parse format 'Sat, 01 Aug 2026 07:00:00 GMT' — fallback ke now()."""
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(raw, fmt)
        except (ValueError, TypeError):
            continue
    return datetime.utcnow()


def fetch_news(ticker: str, query: str | None = None, limit: int = 20) -> list[dict]:
    """Ambil berita terbaru untuk ticker via Google News RSS.

    Args:
        ticker: Kode saham (mis. "BBCA" atau "BBCA.JK").
        query: Kata kunci query RSS (default f"{ticker} saham").
        limit: Maks jumlah berita.

    Returns:
        List dict {title, link, published_at, sentiment_score, impact}.

    Raises:
        RuntimeError: Jika network/RSS gagal.
    """
    q = query or f"{ticker.split('.')[0]} saham"
    url = _RSS_URL.format(query=urllib.parse.quote(q))
    req = urllib.request.Request(url, headers=_HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()
    except Exception as exc:
        raise RuntimeError(f"Gagal fetch berita {ticker}: {exc}") from exc

    items = _parse_rss(xml_bytes, limit=limit)
    for it in items:
        score = _sentiment_score(it["title"])
        it["sentiment_score"] = score
        it["impact"] = _impact(score)
    return items


async def ingest_news(session, ticker: str, query: str | None = None, limit: int = 20) -> int:
    """Fetch berita lalu simpan ke tabel news (dedupe by ticker+title).

    Returns:
        Jumlah berita baru yang di-insert.
    """
    items = fetch_news(ticker, query=query, limit=limit)
    inserted = 0
    for it in items:
        exists = (
            await session.execute(
                select(News).where(
                    News.ticker == ticker,
                    News.title == it["title"],
                )
            )
        ).scalar_one_or_none()
        if exists:
            continue
        session.add(
            News(
                ticker=ticker,
                title=it["title"],
                content=it.get("link", ""),
                published_at=it["published_at"],
                sentiment_score=it["sentiment_score"],
                impact=it["impact"],
            )
        )
        inserted += 1
    if inserted:
        await session.commit()
    return inserted
