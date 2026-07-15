"""Data engine — yfinance wrapper + cache-aware fetching.

Menyediakan: normalize_ticker, fetch_historical.
Isolasi provider di satu file — swap provider tinggal ganti dalam sini.
"""

import logging
import re
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession

from services.cache import get_cached_prices, is_cache_fresh, save_prices

logger = logging.getLogger(__name__)

# Ticker IHSG = 4 huruf alfabet murni (A-Z, a-z)
_PATTERN_IHSG_TICKER = re.compile(r"^[A-Za-z]{4}$")


def normalize_ticker(raw: str) -> str:
    """Normalisasi ticker IHSG — tambah suffix .JK jika 4 huruf murni.

    Args:
        raw: Input ticker (contoh: "BBCA", "BBCA.JK", "AAPL", "bbca").

    Returns:
        Ticker ternormalisasi dengan suffix .JK untuk saham IHSG.
    """
    ticker = raw.strip().upper()

    # Jika sudah punya suffix .JK, balikin apa adanya
    if ticker.endswith(".JK"):
        return ticker

    # Jika tepat 4 huruf alfabet murni — ini saham IHSG
    if _PATTERN_IHSG_TICKER.match(ticker):
        return f"{ticker}.JK"

    # Selain itu — biarkan asli (saham luar, ETF asing, indeks)
    return ticker


async def fetch_historical(
    session: AsyncSession,
    ticker_raw: str,
    period: str = "1mo",
    interval: str = "1d",
    force_fetch: bool = False,
    cache_max_age_days: int = 1,
) -> list | pd.DataFrame:
    """Ambil data historis saham, cache-aware.

    Flow:
    1. Normalisasi ticker (tambah .JK jika IHSG).
    2. Jika force_fetch=False, cek cache lokal.
    3. Cache hit → return data dari DB.
    4. Cache miss → fetch via OpenBB, simpan ke cache, return DataFrame.

    Args:
        session: SQLAlchemy async session.
        ticker_raw: Input ticker (bisa "BBCA", "BBCA.JK", dll).
        period: Periode data ("1mo", "3mo", "6mo", "1y", "max").
        interval: Interval ("1d", "1wk", "1mo").
        force_fetch: Jika True, skip cache dan fetch dari API.
        cache_max_age_days: Maks umur cache dianggap fresh.

    Returns:
        list[CachedPrice] jika cache hit, pd.DataFrame jika fetch API.

    Raises:
        RuntimeError: Jika API gagal atau ticker tidak ditemukan.
    """
    ticker = normalize_ticker(ticker_raw)
    logger.info("fetch_historical: %s (raw=%s)", ticker, ticker_raw)

    # --- Cek cache ---
    if not force_fetch:
        try:
            fresh = await is_cache_fresh(session, ticker, cache_max_age_days)
        except Exception:
            fresh = False

        if fresh:
            logger.info("Cache FRESH untuk %s — skip API fetch", ticker)
            # Return dari DB — range dari period
            start, end = _period_to_date_range(period)
            cached = await get_cached_prices(session, ticker, start, end)
            if cached:
                return cached
            # fall-through: cache stale atau kosong, fetch API

    # --- Fetch dari yfinance ---
    logger.info("Cache MISS — fetch yfinance untuk %s", ticker)
    try:
        yf_ticker = yf.Ticker(ticker)
        df = yf_ticker.history(period=period, interval=interval)
    except Exception as exc:
        raise RuntimeError(
            f"Gagal mengambil data {ticker}: {exc}"
        )

    if df is None or df.empty:
        raise RuntimeError(
            f"Data saham {ticker} tidak ditemukan. Periksa kembali kode saham."
        )

    # --- Simpan ke cache ---
    df = _prepare_df(df)
    try:
        await save_prices(session, ticker, df)
    except Exception as exc:
        logger.warning("Gagal simpan cache untuk %s: %s", ticker, exc)

    return df


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Siapkan DataFrame: lowercase kolom, reset index, tanggal UTC → naive."""
    df = df.reset_index()

    # Kolom yfinance: Date (index), Open, High, Low, Close, Volume
    # Standarisasi ke lowercase
    col_map = {
        "Date": "date", "Datetime": "date",
        "Open": "open", "High": "high",
        "Low": "low", "Close": "close",
        "Volume": "volume",
    }
    df.rename(columns=col_map, inplace=True)

    # Konversi tanggal ke datetime naive (SQLite compatible)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        if hasattr(df["date"].dtype, "tz") and df["date"].dtype.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)

    return df


def _period_to_date_range(period: str) -> tuple[date, date]:
    """Konversi string period ke (start_date, end_date).

    Args:
        period: "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"

    Returns:
        Tuple (start_date, end_date).
    """
    end = date.today()
    mapping = {
        "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
        "1y": 365, "2y": 730, "5y": 1825, "max": 3650,
    }
    days = mapping.get(period, 30)
    start = end - timedelta(days=days)
    return start, end
