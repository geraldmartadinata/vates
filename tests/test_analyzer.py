"""Fase RED — test untuk services/analyzer.py.

analyzer.py menyatukan data_engine + indicators + forecast + rankings
menjadi satu payload analisis saham: insight, projeksi, dan verdict detail.

Aturan vates-core: NO MATH FOR AI — semua hitung di pandas/numpy, deterministic,
testable. LLM/narrative opsional (diurus terpisah), bukan di sin.
"""

import pandas as pd
import pytest

from services.analyzer import (
    build_verdict,
    compute_insight,
    project_price,
)
from services.indicators import compute_all


def _sample_prices(n: int = 260) -> pd.DataFrame:
    """Harga acak tapi deterministic untuk test (naik bertahap + noise kecil)."""
    import numpy as np
    rng = np.random.default_rng(42)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    _ = 1000.0 + rng.normal(0, 5, n).cumsum() / 5.0  # unused, kept for reference
    closes = 1000.0 + (idx.dayofyear * 0.5)  # tren naik halus
    df = pd.DataFrame({
        "date": idx,
        "open": closes,
        "high": [c + 5 for c in closes],
        "low": [c - 5 for c in closes],
        "close": closes,
        "volume": [1_000_000] * n,
    })
    return df


# --- compute_insight() : ringkasan teknikal dari indikator ---


def test_compute_insight_basic():
    from services.indicators import compute_all
    df = compute_all(_sample_prices()[["date", "close"]].copy(), dropna=True)
    insight = compute_insight(df)
    # harus ada key penting
    for k in ("close", "rsi_14", "macd_histogram", "sma_20", "bb_upper", "trend"):
        assert k in insight
    assert insight["trend"] in ("uptrend", "downtrend", "sideways")


def test_compute_insight_uptrend_detected():
    df = compute_all(_sample_prices(260)[["date", "close"]].copy(), dropna=True)
    insight = compute_insight(df)
    # data kita tren naik → uptrend atau sideways (bukan dowtrend)
    assert insight["trend"] != "downtrend"


# --- project_price() : projeksi ke depan (naive + berdasar prob) ---


def test_project_price_returns_horizons():
    proj = project_price(close=1000.0, prob_up=0.65, horizon_days=30)
    assert "projected_close" in proj
    assert "expected_return_pct" in proj
    # kalau prob_up tinggi, projeksi harus > close
    assert proj["projected_close"] > 1000.0


def test_project_price_low_prob_bearish():
    proj = project_price(close=1000.0, prob_up=0.35, horizon_days=30)
    assert proj["projected_close"] < 1000.0


# --- build_verdict() : verdict akhir deterministik ---


def test_build_verdict_long():
    v = build_verdict(prob_30d=0.7, macd_hist=3.0, trend="uptrend",
                      rsi_14=55.0, project_ret=0.08)
    assert v["verdict"] == "STRONG BUY"
    assert v["confidence"] in ("high", "medium", "low")


def test_build_verdict_short():
    v = build_verdict(prob_30d=0.3, macd_hist=-3.0, trend="downtrend",
                      rsi_14=70.0, project_ret=-0.08)
    assert v["verdict"] in ("SELL", "STRONG SELL")


def test_build_verdict_neutral_on_weak_signal():
    v = build_verdict(prob_30d=0.52, macd_hist=0.2, trend="sideways",
                      rsi_14=50.0, project_ret=0.01)
    assert v["verdict"] == "HOLD"


def test_build_verdict_overbought_caps_upside():
    # RSI overbought harus nurunin confidence meski sinyal bullish
    v = build_verdict(prob_30d=0.8, macd_hist=5.0, trend="uptrend",
                      rsi_14=82.0, project_ret=0.10)
    assert v["confidence"] != "high"  # RSI>80 → gak high confidence


# --- analyze_stock() : orkestrasi end-to-end (dengan mock tidak perlu network) ---


def test_analyze_stock_shape():
    """Mock fetch + forecast biar gak network, cek struktur payload lengkap."""
    import asyncio

    import services.analyzer as az

    prices = _sample_prices(260)

    with pytest.MonkeyPatch().context() as mp:
        async def fake_fetch(*a, **k):
            return prices
        mp.setattr(az.data_engine, "fetch_historical", fake_fetch)

        async def fake_predict(session, ticker, period="2y"):
            return [
                {"horizon": 1, "prob_up": 0.55, "label": 1, "model_version": "t"},
                {"horizon": 7, "prob_up": 0.6, "label": 1, "model_version": "t"},
                {"horizon": 30, "prob_up": 0.65, "label": 1, "model_version": "t"},
            ]
        mp.setattr(az.forecast, "predict_all", fake_predict)

        out = asyncio.run(az.analyze_stock(None, "BBCA", period="1y"))
    assert out["ticker"] == "BBCA"
    for sec in ("insight", "projection", "verdict", "raw"):
        assert sec in out
    assert "verdict" in out["verdict"]
    # projection punya 3 horizon
    assert len(out["projection"]["horizons"]) == 3
