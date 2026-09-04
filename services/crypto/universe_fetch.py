"""Batch fetch for IHSG universe tickers.

Uses yfinance per-ticker with exponential backoff (reuses data_engine retry logic).
Saves to SQLite cache (cached_prices table via data_engine.save_prices).
Runs in batches to avoid rate limits (Yahoo Finance rate-limits ~2000/hr).
"""
import asyncio
import logging

from services.crypto.ihsg_tickers import TICKERS, COMPOSITE
from services.data_engine import fetch_historical, normalize_ticker

logger = logging.getLogger(__name__)
BATCH_SIZE = 10  # tickers per batch to respect rate limits
SLEEP_BETWEEN_BATCHES = 5  # seconds


async def fetch_universe(session, tickers: list[str] | None = None, batch_size: int = BATCH_SIZE) -> dict:
    """Fetch OHLCV for all tickers in universe.

    Args:
        session: Async DB session (for cache).
        tickers: List of ticker codes. Default = TICKERS (50 IHSG stocks).
        batch_size: Number of tickers fetched concurrently per batch.

    Returns:
        dict {ticker: success/failed, data: {ticker: list}, errors: [str]}
    """
    tickers = tickers or TICKERS[:]
    results = {}
    errors = []

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        logger.info("Batch %d/%d: fetching %d tickers", (i // batch_size) + 1, (len(tickers) - 1) // batch_size + 1, len(batch))
        for ticker_raw in batch:
            try:
                result = await fetch_historical(session, ticker_raw, period="2y", force_fetch=False)
                results[ticker_raw] = {"ok": True, "data": result, "normalized": normalize_ticker(ticker_raw)}
            except Exception as exc:
                errors.append(f"{ticker_raw}: {exc}")
                results[ticker_raw] = {"ok": False, "error": str(exc)}
        # Rate limit guard between batches
        if i + batch_size < len(tickers):
            await asyncio.sleep(SLEEP_BETWEEN_BATCHES)

    # Composite index separately
    try:
        comp_result = await fetch_historical(session, COMPOSITE, period="2y", force_fetch=False)
        results["^JKSE"] = {"ok": True, "data": comp_result, "normalized": COMPOSITE}
    except Exception as exc:
        errors.append(f"{COMPOSITE}: {exc}")
        results[COMPOSITE] = {"ok": False, "error": str(exc)}

    logger.info("Fetch universe done: %d tickers fetched, %d errors", len([r for r in results.values() if r.get("ok")]), len(errors))
    return {"results": results, "errors": errors, "fetched_count": len([r for r in results.values() if r.get("ok")]), "total": len(tickers) + 1}


if __name__ == "__main__":
    # Quick smoke: fetch 3 tickers + composite (manual, no DB session needed for quick check)
    print("Quick smoke: fetching BBCA.JK + TLKM.JK + ^JKSE")
