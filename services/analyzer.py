"""Analyzer — orkestrasi analisis saham jadi insight + projeksi + verdict.

Menyatukan:
- services.data_engine.fetch_historical  → OHLCV (cache-aware, yfinance/IHSG)
- services.indicators.compute_all        → SMA/RSI/MACD/Bollinger (pandas vectorized)
- services.forecast.predict_all          → prob up per horizon (logreg walk-fwd)
- services.rankings.recommendation       → sinyal LONG/SHORT/NEUTRAL

Semua perhitungan DETERMINISTIK (pandas/numpy) — tidak ada "math for AI".
Narrative LLM opsional & dipisah (tidak di modul ini) agar testable & transparan.

Public API:
- compute_insight(df)      → dict ringkasan teknikal + trend
- project_price(...)       → dict projeksi harga per horizon
- build_verdict(...)       → dict verdict + confidence + alasan
- analyze_stock(session, ticker, period) → payload lengkap (insight+proj+verdict)
"""

from __future__ import annotations

import logging

import pandas as pd

from services import data_engine, forecast, indicators, rankings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Insight — ringkasan teknikal dari DataFrame indikator
# ---------------------------------------------------------------------------


def compute_insight(df: pd.DataFrame) -> dict:
    """Ekstrak ringkasan teknikal + klasifikasi trend dari DataFrame indikator.

    Args:
        df: Output compute_all (punya sma_20, rsi_14, macd_*, bb_*).

    Returns:
        dict {close, sma_20, rsi_14, macd, macd_histogram, bb_upper, bb_lower,
              trend, dist_to_bb_upper_pct, dist_to_bb_lower_pct}.
    """
    last = df.iloc[-1]
    close = float(last["close"])
    sma20 = float(last["sma_20"])
    rsi = float(last["rsi_14"])
    macd = float(last["macd"])
    macd_hist = float(last["macd_histogram"])
    bb_up = float(last["bb_upper"])
    bb_lo = float(last["bb_lower"])

    # Trend: bandingkan close vs SMA20 + arah MACD histogram (3 bar terakhir)
    sma_slope = float(df["sma_20"].diff().iloc[-1])
    if close > sma20 and sma_slope > 0:
        trend = "uptrend"
    elif close < sma20 and sma_slope < 0:
        trend = "downtrend"
    else:
        trend = "sideways"

    dist_up = (bb_up - close) / close if close else 0.0
    dist_lo = (close - bb_lo) / close if close else 0.0

    return {
        "close": close,
        "sma_20": sma20,
        "rsi_14": rsi,
        "macd": macd,
        "macd_histogram": macd_hist,
        "bb_upper": bb_up,
        "bb_lower": bb_lo,
        "trend": trend,
        "dist_to_bb_upper_pct": dist_up,
        "dist_to_bb_lower_pct": dist_lo,
    }


# ---------------------------------------------------------------------------
# Projection — projeksi harga ke depan (naive drift + probabilitas)
# ---------------------------------------------------------------------------


def project_price(
    close: float,
    prob_up: float | None,
    horizon_days: int,
    vol_10d: float | None = None,
) -> dict:
    """Projeksi harga sederhana & transparan.

    Model: expected_return = (prob_up - 0.5) * 2 * vol_scaled
    vol_scaled = vol_10d (return harian) * sqrt(horizon) sebagai perkiraan
    deviasi. Tanpa vol → asumsi 1.5%/sqrt(horizon) konservatif.

    Args:
        close: Harga terakhir.
        prob_up: P(naik) horizon ini (0..1). None → netral (0 drift).
        horizon_days: Horizon projeksi.
        vol_10d: Volatilitas harian (return std) opsional.

    Returns:
        dict {horizon_days, prob_up, expected_return_pct, projected_close}.
    """
    if prob_up is None:
        drift = 0.0
    else:
        base = (prob_up - 0.5) * 2.0  # -1..1
        if vol_10d is not None and vol_10d > 0:
            vol_factor = vol_10d * (horizon_days ** 0.5)
        else:
            vol_factor = 0.015 * (horizon_days ** 0.5)
        drift = base * vol_factor

    projected = close * (1.0 + drift)
    return {
        "horizon_days": horizon_days,
        "prob_up": prob_up,
        "expected_return_pct": drift,
        "projected_close": projected,
    }


# ---------------------------------------------------------------------------
# Verdict — keputusan akhir deterministik + confidence + alasan
# ---------------------------------------------------------------------------


def build_verdict(
    prob_30d: float | None,
    macd_hist: float | None,
    trend: str,
    rsi_14: float | None,
    project_ret: float | None,
) -> dict:
    """Susun verdict + confidence + alasan dari sinyal kuantitatif.

    Logika (transparan, testable):
    - Base dari rankings.recommendation (prob 30d + MACD hist).
    - RSI > 78 (overbought) / < 22 (oversold) → cap confidence, tweak arah.
    - Trend & project_ret memperkuat/melawan base signal.

    Returns:
        dict {verdict, confidence, reasons: [str]}.
    """
    reasons: list[str] = []
    base = rankings.recommendation(prob_30d, macd_hist)

    if base == "LONG":
        verdict = "STRONG BUY" if (prob_30d or 0) >= 0.65 else "BUY"
    elif base == "SHORT":
        verdict = "STRONG SELL" if (prob_30d or 1) <= 0.35 else "SELL"
    else:
        verdict = "HOLD"

    # Confidence awal
    confidence = "high" if abs((prob_30d or 0.5) - 0.5) >= 0.15 else "medium"
    if base == "NEUTRAL":
        confidence = "low"

    # RSI overbought/oversold → cap & adjust
    if rsi_14 is not None:
        if rsi_14 > 78:
            reasons.append(f"RSI {rsi_14:.0f} overbought — risiko koreksi.")
            if verdict in ("STRONG BUY", "BUY"):
                confidence = "medium"
        elif rsi_14 < 22:
            reasons.append(f"RSI {rsi_14:.0f} oversold — potensi rebound.")
            if verdict in ("STRONG SELL", "SELL"):
                confidence = "medium"

    # Trend confirmation
    if trend == "uptrend" and base == "LONG":
        reasons.append("Harga di atas SMA20 dengan slope positif (uptrend).")
    elif trend == "downtrend" and base == "SHORT":
        reasons.append("Harga di bawah SMA20 dengan slope negatif (downtrend).")
    elif trend == "sideways":
        reasons.append("Pergerakan sideways — sinyal lemah.")

    # Projection alignment
    if project_ret is not None:
        if project_ret > 0 and base == "LONG":
            reasons.append(f"Projeksi +{project_ret*100:.1f}% mendukung posisi long.")
        elif project_ret < 0 and base == "SHORT":
            reasons.append(f"Projeksi {project_ret*100:.1f}% mendukung posisi short.")
        elif project_ret is not None and ((project_ret > 0) != (base == "LONG")):
            reasons.append("Projeksi berlawanan dengan sinyal dasar — hati-hati.")

    if not reasons:
        reasons.append("Sinyal netral — tidak ada konfirmasi kuat.")

    return {"verdict": verdict, "confidence": confidence, "reasons": reasons}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def analyze_stock(session, ticker: str, period: str = "2y") -> dict:
    """Analisis saham lengkap: insight + projeksi + verdict.

    Pipeline:
    1. fetch_historical → OHLCV (cache-aware).
    2. compute_all → indikator.
    3. predict_all → prob up per horizon (1/7/30).
    4. compute_insight + project_price(per horizon) + build_verdict.

    Returns:
        dict {
            ticker, insight, projection{horizons:[...]},
            verdict{verdict,confidence,reasons}, raw{preds, macd_hist}
        }
    """
    prices = await data_engine.fetch_historical(session, ticker, period=period)
    df_prices = prices if isinstance(prices, pd.DataFrame) else pd.DataFrame(prices)

    ind = indicators.compute_all(df_prices[["date", "close"]].copy(), dropna=True)
    ins = compute_insight(ind)

    preds = await forecast.predict_all(session, ticker, period=period)
    pred_by_h = {p["horizon"]: p for p in preds}

    # vol 10d dari indikator (ret_1d bukan di compute_all; hitung manual)
    ret_1d = ind["close"].pct_change()
    vol_10d = float(ret_1d.tail(10).std()) if len(ret_1d) >= 10 else None

    horizons = []
    for h in (1, 7, 30):
        p = pred_by_h.get(h)
        prob = p["prob_up"] if p else None
        proj = project_price(ins["close"], prob, h, vol_10d)
        horizons.append(proj)

    proj_ret_30 = next(
        (p["expected_return_pct"] for p in horizons if p["horizon_days"] == 30),
        None,
    )
    prob_30 = pred_by_h.get(30, {}).get("prob_up")
    macd_hist = ins["macd_histogram"]

    verdict = build_verdict(
        prob_30d=prob_30,
        macd_hist=macd_hist,
        trend=ins["trend"],
        rsi_14=ins["rsi_14"],
        project_ret=proj_ret_30,
    )

    return {
        "ticker": ticker,
        "insight": ins,
        "projection": {"horizons": horizons},
        "verdict": verdict,
        "raw": {"preds": preds, "macd_hist": macd_hist},
    }
