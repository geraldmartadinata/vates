"""REST API endpoints — Vates Core.

Routes:
- GET /            → status
- GET /health      → health check
- GET /api/v1/stocks/{ticker}     → OHLCV historis
- GET /api/v1/indicators/{ticker} → indikator teknikal
"""

import logging
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from services.data_engine import _prepare_df, normalize_ticker
from services.indicators import compute_all

logger = logging.getLogger(__name__)
router = APIRouter()


class ScreenRequest(BaseModel):
    """Request body untuk /api/v1/screen."""
    tickers: list[str]
    horizon: int = 30
    top_n: int = 10

# Frontend build — dist/ di bawah frontend/
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
INDEX_HTML = FRONTEND_DIST / "index.html"


def _serialize(obj):
    """Convert numpy types + NaN ke Python native / None."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        if obj != obj:  # NaN
            return None
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


@router.get("/")
async def root():
    """Root — penanda bahwa server hidup."""
    return {"status": "Vates Core is running"}


@router.get("/dashboard")
async def dashboard():
    """Serve frontend SPA (production build)."""
    if not INDEX_HTML.exists():
        raise HTTPException(
            status_code=503,
            detail="Frontend belum di-build. Jalankan: cd frontend && npm run build",
        )
    return FileResponse(INDEX_HTML)


@router.get("/assets/{filename}")
async def frontend_assets(filename: str):
    """Serve frontend assets (JS/CSS)."""
    asset = FRONTEND_DIST / "assets" / filename
    if not asset.exists():
        raise HTTPException(status_code=404, detail="Asset tidak ditemukan")
    return FileResponse(asset)


@router.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "vates-core", "version": "0.1.0"}


@router.get("/api/v1/stocks/{ticker}")
async def get_stock(ticker: str, period: str = "1mo"):
    """Ambil data OHLCV historis terkini.

    Args:
        ticker: Kode saham (contoh: BBCA, BBCA.JK).
        period: 1mo, 3mo, 6mo, 1y, max.

    Returns:
        JSON: ticker, last_price (object OHLCV), recent (array OHLCV).
    """
    raw = ticker.strip().upper()
    normalized = normalize_ticker(raw)

    try:
        yf_ticker = yf.Ticker(normalized)
        df = yf_ticker.history(period=period)
        df = _prepare_df(df)
        df = df.dropna(subset=["close"]).copy()

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Data saham {normalized} tidak ditemukan.",
            )

        # Baris terakhir
        last = df.iloc[-1]
        last_price = {
            "date": _serialize(last.get("date", last.name)),
            "open": _serialize(last.get("open")),
            "high": _serialize(last.get("high")),
            "low": _serialize(last.get("low")),
            "close": _serialize(last.get("close")),
            "volume": _serialize(int(last.get("volume", 0))),
        }

        # Array historis (maks 100 baris)
        recent = []
        for _, row in df.tail(100).iterrows():
            recent.append({
                "date": _serialize(row.get("date", row.name)),
                "open": _serialize(row.get("open")),
                "high": _serialize(row.get("high")),
                "low": _serialize(row.get("low")),
                "close": _serialize(row.get("close")),
                "volume": _serialize(int(row.get("volume", 0))),
            })

        return {
            "ticker": normalized,
            "last_price": last_price,
            "recent": recent,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching %s", normalized)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/v1/indicators/{ticker}")
async def get_indicators(ticker: str, period: str = "6mo"):
    """Hitung semua indikator teknikal.

    Args:
        ticker: Kode saham.
        period: 6mo, 1y, max — butuh cukup data untuk MACD (26+9 baris).

    Returns:
        JSON: ticker, indicators (object), recent (array indikator per baris).
    """
    raw = ticker.strip().upper()
    normalized = normalize_ticker(raw)

    try:
        yf_ticker = yf.Ticker(normalized)
        df = yf_ticker.history(period=period)
        df = _prepare_df(df)
        df = df.dropna(subset=["close"]).copy()

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Data saham {normalized} tidak ditemukan.",
            )

        try:
            enriched = compute_all(df, dropna=False)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        # Indikator terakhir
        last = enriched.iloc[-1]
        indicators = {
            "sma_20": _serialize(last.get("sma_20")),
            "rsi_14": _serialize(last.get("rsi_14")),
            "macd": _serialize(last.get("macd")),
            "macd_signal": _serialize(last.get("macd_signal")),
            "macd_histogram": _serialize(last.get("macd_histogram")),
            "bb_upper": _serialize(last.get("bb_upper")),
            "bb_middle": _serialize(last.get("bb_middle")),
            "bb_lower": _serialize(last.get("bb_lower")),
        }

        # Array historis indikator (maks 100 baris)
        indicator_keys = [
            "sma_20", "rsi_14", "macd", "macd_signal",
            "macd_histogram", "bb_upper", "bb_middle", "bb_lower",
        ]
        recent = []
        for _, row in enriched.tail(100).iterrows():
            entry = {"date": _serialize(row.get("date", row.name))}
            for k in indicator_keys:
                val = _serialize(row.get(k))
                if val is not None:
                    entry[k] = val
            recent.append(entry)

        return {
            "ticker": normalized,
            "indicators": indicators,
            "recent": recent,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error computing indicators for %s", normalized)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/v1/rankings/{horizon}")
async def get_rankings(
    horizon: int,
    top_n: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """Ranking saham: top & bottom berdasarkan probabilitas naik.

    Args:
        horizon: 1, 7, atau 30 hari.
        top_n: Jumlah entri top/bottom (default 5).

    Returns:
        JSON: horizon, generated_at, top, bottom.
    """
    if horizon not in (1, 7, 30):
        raise HTTPException(status_code=400, detail="horizon harus 1, 7, atau 30")

    from services.rankings import latest_predictions, rank_predictions

    preds = await latest_predictions(db, horizon=horizon)
    ranked = rank_predictions(preds, horizon=horizon, top_n=top_n)
    return {
        "horizon": horizon,
        "generated_at": date.today().isoformat(),
        "top": ranked["top"],
        "bottom": ranked["bottom"],
    }


@router.get("/api/v1/predict/{ticker}")
async def get_prediction(ticker: str, db: AsyncSession = Depends(get_db)):
    """Prediksi terbaru per horizon untuk satu saham.

    Args:
        ticker: Kode saham (contoh: BBCA).

    Returns:
        JSON: ticker, preds (list per horizon), recommendation.
    """
    from services.forecast import predict_all
    from services.rankings import latest_predictions, recommendation

    raw = ticker.strip().upper()
    normalized = normalize_ticker(raw)

    # Cek prediksi tersimpan terbaru dulu
    preds = await latest_predictions(db, horizon=None)
    ticker_preds = [p for p in preds if p["ticker"] == raw.removesuffix(".JK")]

    # Kalau belum ada di DB, hitung live (refit model)
    if not ticker_preds:
        try:
            live = await predict_all(db, raw)
            ticker_preds = [
                {
                    "ticker": raw.removesuffix(".JK"),
                    "horizon_days": p["horizon"],
                    "predicted_prob": p["prob_up"],
                    "predicted_label": p["label"],
                    "model_version": p["model_version"],
                    "created_at": None,
                }
                for p in live
            ]
        except Exception as e:
            logger.exception("Live predict %s gagal", normalized)
            raise HTTPException(status_code=500, detail=str(e)) from e

    if not ticker_preds:
        raise HTTPException(
            status_code=404,
            detail=f"Belum ada prediksi untuk {normalized}.",
        )

    prob_30 = next(
        (p["predicted_prob"] for p in ticker_preds if p["horizon_days"] == 30),
        None,
    )
    rec = recommendation(prob_30, None)
    return {
        "ticker": raw.removesuffix(".JK"),
        "preds": ticker_preds,
        "recommendation": rec,
    }


@router.post("/api/v1/analyze/{ticker}")
async def analyze(ticker: str, db: AsyncSession = Depends(get_db)):
    """Analisis lengkap: insight + proyeksi + verdict (analyzer v2).

    Args:
        ticker: Kode saham (contoh: BBCA).

    Returns:
        JSON: ticker, insight, projection{horizons}, verdict{verdict,confidence,reasons}, raw.
    """
    from services.analyzer import analyze_stock

    raw = ticker.strip().upper()
    normalized = normalize_ticker(raw)

    try:
        result = await analyze_stock(db, normalized, period="2y")
    except Exception as e:
        logger.exception("Analyze %s gagal", normalized)
        raise HTTPException(status_code=500, detail=str(e)) from e

    return result


@router.post("/api/v1/screen")
async def screen_universe(
    req: ScreenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Screen universe of tickers: run analyze_stock on each, return ranked.

    Args:
        req: ScreenRequest body {tickers, horizon, top_n}.
        db: Database session.

    Returns:
        JSON: horizon, screened_count, results (list of analyze_stock output),
              ranked: {top_buys, top_sells, neutrals} based on verdict.
    """
    from services.analyzer import analyze_stock

    if req.horizon not in (1, 7, 30):
        raise HTTPException(status_code=400, detail="horizon harus 1, 7, atau 30")

    results = []
    errors = []

    for t in req.tickers:
        try:
            raw = t.strip().upper()
            normalized = normalize_ticker(raw)
            out = await analyze_stock(db, normalized, period="2y")
            results.append(out)
        except Exception as e:
            errors.append({"ticker": t, "error": str(e)})

    # Rank by verdict strength
    def verdict_score(v):
        order = {
            "STRONG BUY": 3,
            "BUY": 2,
            "HOLD": 1,
            "SELL": -1,
            "STRONG SELL": -2,
        }
        return order.get(v.get("verdict", "HOLD"), 0)

    sorted_results = sorted(results, key=lambda r: verdict_score(r["verdict"]), reverse=True)

    buy_verdicts = ("STRONG BUY", "BUY")
    sell_verdicts = ("STRONG SELL", "SELL")
    top_buys = [r for r in sorted_results if r["verdict"]["verdict"] in buy_verdicts][: req.top_n]
    top_sells = [r for r in sorted_results if r["verdict"]["verdict"] in sell_verdicts][: req.top_n]
    neutrals = [r for r in sorted_results if r["verdict"]["verdict"] == "HOLD"][: req.top_n]

    return {
        "horizon": req.horizon,
        "screened_count": len(results),
        "errors": errors,
        "results": results,
        "ranked": {
            "top_buys": top_buys,
            "top_sells": top_sells,
            "neutrals": neutrals,
        },
    }
