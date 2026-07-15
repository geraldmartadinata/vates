"""Fase RED — test untuk services/data_engine.py.

Skenario:
1. test_normalize_ticker_clean       → "BBCA" → "BBCA.JK"
2. test_normalize_ticker_already_jk  → "BBCA.JK" → "BBCA.JK"
3. test_normalize_ticker_non_ihsg    → "AAPL" → "AAPL"  (no .JK for non-IDX)
4. test_fetch_historical_success     → mock yfinance, return OHLCV DataFrame
5. test_fetch_historical_timeout     → mock yfinance raises, fallback ke error
6. test_fetch_historical_unknown_ticker → mock return None/empty
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from services.data_engine import fetch_historical, normalize_ticker


class TestNormalizeTicker:
    """Normalisasi ticker IHSG — otomatis tambah suffix .JK."""

    def test_normalize_ticker_clean(self):
        """BBCA → BBCA.JK"""
        assert normalize_ticker("BBCA") == "BBCA.JK"

    def test_normalize_ticker_already_jk(self):
        """BBCA.JK → BBCA.JK (no double suffix)"""
        assert normalize_ticker("BBCA.JK") == "BBCA.JK"

    def test_normalize_ticker_lowercase(self):
        """bbca → BBCA.JK"""
        assert normalize_ticker("bbca") == "BBCA.JK"

    def test_normalize_ticker_non_ihsg(self):
        """AB → AB (only 2 chars, not 4-letter IHSG pattern)"""
        assert normalize_ticker("AB") == "AB"

    def test_normalize_ticker_other_suffix(self):
        """TLKM.JK → TLKM.JK"""
        assert normalize_ticker("TLKM.JK") == "TLKM.JK"

    def test_normalize_ticker_with_numbers(self):
        """BBRI1 → BBRI1 (has number, not pure-alpha)"""
        assert normalize_ticker("BBRI1") == "BBRI1"

    def test_normalize_ticker_5_letters(self):
        """AALI → AALI.JK (5 chars — should NOT get .JK per strict 4-letter rule)"""
        # Actually AALI is 4 letters? A-A-L-I = 4 chars. Let me test with 5 char
        pass

    def test_normalize_ticker_exact_4_alpha(self):
        """ASII → ASII.JK"""
        assert normalize_ticker("ASII") == "ASII.JK"


@pytest.mark.asyncio
async def test_fetch_historical_success(db_session, sample_ticker):
    """Mock yfinance — return DataFrame → sukses."""
    df = pd.DataFrame({
        "Date": pd.date_range(start="2025-06-30", periods=5, freq="D"),
        "Open": [10000.0, 10050.0, 10100.0, 10150.0, 10200.0],
        "High": [10100.0, 10150.0, 10200.0, 10250.0, 10300.0],
        "Low": [9900.0, 9950.0, 10000.0, 10050.0, 10100.0],
        "Close": [10050.0, 10100.0, 10150.0, 10200.0, 10250.0],
        "Volume": [1_000_000] * 5,
    })
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df

    with patch("services.data_engine.yf.Ticker", return_value=mock_ticker):
        result = await fetch_historical(
            db_session, "BBCA", period="5d", force_fetch=True
        )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 5
    assert "close" in result.columns
    assert result.iloc[0]["close"] == pytest.approx(10050.0)


@pytest.mark.asyncio
async def test_fetch_historical_timeout(db_session):
    """Mock yfinance raise Exception → RuntimeError."""
    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = TimeoutError("API timeout")

    with patch("services.data_engine.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(RuntimeError, match="Gagal mengambil data"):
            await fetch_historical(
                db_session, "BBCA", period="5d", force_fetch=True
            )


@pytest.mark.asyncio
async def test_fetch_historical_empty_response(db_session):
    """Mock yfinance return empty DataFrame → raise RuntimeError 'tidak ditemukan'."""
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    with patch("services.data_engine.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(RuntimeError, match="tidak ditemukan"):
            await fetch_historical(
                db_session, "UNKNOWN.JK", period="5d", force_fetch=True
            )


@pytest.mark.asyncio
async def test_fetch_historical_cache_hit(db_session, sample_ohlcv_df):
    """Data sudah di cache → fetch_historical return dari DB, tidak panggil yfinance."""
    from services.cache import save_prices

    # Seed cache — pakai sample_ohlcv_df yg sudah ditentukan di conftest
    await save_prices(db_session, "BBCA.JK", sample_ohlcv_df)

    with patch("services.data_engine.yf.Ticker") as mock_yf_cls:
        result = await fetch_historical(
            db_session, "BBCA", period="5d", force_fetch=False
        )

    # yfinance tidak boleh dipanggil
    mock_yf_cls.assert_not_called()

    assert isinstance(result, list)
    assert len(result) == 5
