"""Fase RED — test untuk services/indicators.py.

Skenario:
1. sma_basic           → SMA(3) dari [1,2,3,4,5] → [NaN, NaN, 2, 3, 4]
2. sma_period_longer   → SMA(10) cuma 5 baris → all NaN
3. rsi_basic           → RSI(3) dari sequence naik terus → mendekati 100
4. rsi_oversold        → RSI(3) dari turun terus → mendekati 0
5. macd_basic          → MACD(3,6,2) — verifikasi MACD = EMA_fast - EMA_slow
6. macd_cross          → harga berubah drastis → histogram flip sign
7. bollinger_basic     → BB(3,2) — middle = SMA, upper > middle > lower
8. clean_indicators    → dropna hanya pada baris non-NaN
9. compute_all         → semua kolom indikator ada
"""

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_almost_equal


@pytest.fixture
def five_series() -> pd.DataFrame:
    """5 baris close: 1,2,3,4,5 — naik linear."""
    return pd.DataFrame({"close": [1.0, 2.0, 3.0, 4.0, 5.0]})


@pytest.fixture
def twenty_series() -> pd.DataFrame:
    """50 baris sinusoidal — cukup untuk MACD default (slow=26)."""
    np.random.seed(42)
    vals = 100 + np.cumsum(np.random.randn(50) * 2)
    return pd.DataFrame({"close": vals})


class TestSMA:
    def test_sma_basic(self, five_series):
        from services.indicators import sma

        result = sma(five_series.copy(), period=3)
        assert "sma_3" in result.columns
        assert np.isnan(result["sma_3"].iloc[0])
        assert np.isnan(result["sma_3"].iloc[1])
        assert result["sma_3"].iloc[2] == pytest.approx(2.0)   # (1+2+3)/3
        assert result["sma_3"].iloc[3] == pytest.approx(3.0)   # (2+3+4)/3
        assert result["sma_3"].iloc[4] == pytest.approx(4.0)   # (3+4+5)/3

    def test_sma_period_longer(self, five_series):
        from services.indicators import sma

        result = sma(five_series.copy(), period=10)
        assert result["sma_10"].isna().all()

    def test_sma_keeps_original_columns(self, five_series):
        from services.indicators import sma
        orig = five_series.copy()
        result = sma(orig, period=3)
        assert "close" in result.columns


class TestRSI:
    def test_rsi_uptrend(self):
        """Harga naik 10 hari berturut-turut → RSI mendekati 100."""
        from services.indicators import rsi

        df = pd.DataFrame({"close": list(range(100, 120))})  # 20 baris
        result = rsi(df.copy(), period=14)
        assert "rsi_14" in result.columns
        # RSI harus > 99 untuk uptrend sempurna
        assert result["rsi_14"].iloc[-1] > 99.0

    def test_rsi_downtrend(self):
        """Harga turun 10 hari berturut-turut → RSI mendekati 0."""
        from services.indicators import rsi

        df = pd.DataFrame({"close": list(range(120, 100, -1))})
        result = rsi(df.copy(), period=14)
        assert "rsi_14" in result.columns
        assert result["rsi_14"].iloc[-1] < 1.0

    def test_rsi_first_n_periods_are_nan(self, twenty_series):
        from services.indicators import rsi

        result = rsi(twenty_series.copy(), period=14)
        assert result["rsi_14"].iloc[:13].isna().all()
        assert not np.isnan(result["rsi_14"].iloc[14])

    def test_rsi_boundaries(self, twenty_series):
        """RSI selalu antara 0-100."""
        from services.indicators import rsi

        result = rsi(twenty_series.copy(), period=5)
        vals = result["rsi_5"].dropna()
        assert (vals >= 0).all()
        assert (vals <= 100).all()


class TestMACD:
    def test_macd_columns_exist(self, twenty_series):
        from services.indicators import macd

        result = macd(twenty_series.copy(), fast=5, slow=13, signal=4)
        for col in ["macd", "macd_signal", "macd_histogram"]:
            assert col in result.columns

    def test_macd_formula(self):
        """MACD = EMA(fast) - EMA(slow). Verifikasi manual."""
        from services.indicators import macd

        df = pd.DataFrame({"close": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]})
        result = macd(df.copy(), fast=3, slow=6, signal=2)
        # MACD non-NaN mulai index 5 (slow=6 butuh 6 nilai)
        # Verifikasi: MACD[5] = EMA3[5] - EMA6[5]
        ema3 = df["close"].ewm(span=3, adjust=False).mean()
        ema6 = df["close"].ewm(span=6, adjust=False).mean()
        expected_macd = ema3 - ema6
        assert_almost_equal(result["macd"].values, expected_macd.values, decimal=5)

    def test_macd_histogram_sign(self, twenty_series):
        """Histogram = MACD - Signal."""
        from services.indicators import macd

        result = macd(twenty_series.copy(), fast=5, slow=13, signal=4)
        expected_hist = result["macd"] - result["macd_signal"]
        assert_almost_equal(result["macd_histogram"].values, expected_hist.values, decimal=5)


class TestBollingerBands:
    def test_bb_columns_exist(self, twenty_series):
        from services.indicators import bollinger_bands

        result = bollinger_bands(twenty_series.copy(), period=10, std_dev=2)
        for col in ["bb_upper", "bb_middle", "bb_lower"]:
            assert col in result.columns

    def test_bb_middle_is_sma(self, twenty_series):
        from services.indicators import bollinger_bands

        result = bollinger_bands(twenty_series.copy(), period=10, std_dev=2)
        sma10 = twenty_series["close"].rolling(10).mean()
        assert_almost_equal(result["bb_middle"].values, sma10.values, decimal=5)

    def test_bb_upper_greater_than_middle(self, twenty_series):
        from services.indicators import bollinger_bands

        result = bollinger_bands(twenty_series.copy(), period=10, std_dev=2)
        valid = result.dropna()
        assert (valid["bb_upper"] > valid["bb_middle"]).all()

    def test_bb_lower_less_than_middle(self, twenty_series):
        from services.indicators import bollinger_bands

        result = bollinger_bands(twenty_series.copy(), period=10, std_dev=2)
        valid = result.dropna()
        assert (valid["bb_lower"] < valid["bb_middle"]).all()

    def test_bb_width_increases_with_volatility(self):
        """Bollinger melebar saat volatilitas tinggi."""
        from services.indicators import bollinger_bands

        prices = (
            [100] * 15          # flat
            + [100, 120, 100, 120, 100]  # volatile
        )
        df = pd.DataFrame({"close": prices})
        result = bollinger_bands(df.copy(), period=5, std_dev=2)
        bb_width = result["bb_upper"] - result["bb_lower"]
        # Bandwidth harus lebih lebar di periode volatile
        assert bb_width.iloc[-1] > bb_width.iloc[15]


class TestCleanIndicators:
    def test_clean_removes_nan(self, twenty_series):
        from services.indicators import sma, clean_indicators

        df = sma(twenty_series.copy(), period=10)
        n_before = len(df)
        cleaned = clean_indicators(df)
        assert len(cleaned) < n_before
        assert not cleaned.isna().any(axis=None)

    def test_clean_no_nan_unchanged(self, five_series):
        from services.indicators import clean_indicators

        cleaned = clean_indicators(five_series.copy())
        assert len(cleaned) == len(five_series)


class TestComputeAll:
    def test_compute_all_columns(self, twenty_series):
        from services.indicators import compute_all

        result = compute_all(twenty_series.copy())
        expected_columns = {
            "sma_20", "rsi_14",
            "macd", "macd_signal", "macd_histogram",
            "bb_upper", "bb_middle", "bb_lower",
        }
        assert expected_columns.issubset(set(result.columns))

    def test_compute_all_no_nan(self, twenty_series):
        from services.indicators import compute_all

        result = compute_all(twenty_series.copy(), dropna=True)
        assert not result.isna().any(axis=None)

    def test_compute_all_preserves_close(self, twenty_series):
        from services.indicators import compute_all

        result = compute_all(twenty_series.copy())
        assert "close" in result.columns
