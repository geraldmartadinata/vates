"""Live ML pipeline — gabungkan cache harga + berita → dataset → walk-forward.

Menyediakan: build_ml_dataset, evaluate_ticker.
"""

import logging

import pandas as pd

from services.data_engine import fetch_historical
from services.features import FEATURE_COLS, build_ml_frame, select_columns
from services.news_processor import fetch_news
from services.trainer import evaluate_walk_forward

logger = logging.getLogger(__name__)

HORIZONS = (1, 7, 30)


async def build_ml_dataset(session, ticker: str, period: str = "2y") -> pd.DataFrame:
    """Bangun dataset ML: harga (cache→API) + indikator + agregat berita."""
    df = await fetch_historical(session, ticker, period=period, force_fetch=True)
    prices = df[["date", "close"]].copy()

    try:
        news = fetch_news(ticker, limit=50)
    except RuntimeError as exc:
        logger.warning("Gagal ambil berita %s: %s", ticker, exc)
        news = []

    news_df = None
    if news:
        news_df = pd.DataFrame(news)
        news_df = news_df.rename(columns={"published_at": "date"})

    return build_ml_frame(prices, news_df)


async def evaluate_ticker(session, ticker: str, period: str = "2y") -> dict:
    """Latih baseline per horizon → dict {h: {"accuracy": float, "n": int}}."""
    df = await build_ml_dataset(session, ticker, period=period)
    X_full, _ = select_columns(df)
    results = {}

    for h in HORIZONS:
        label = f"label_{h}d"
        if label not in df.columns:
            continue
        mask = df[label].notna()
        n = int(mask.sum())
        if n < 40:
            results[h] = {"accuracy": None, "n": n}
            continue

        X = X_full[mask]
        y = df.loc[mask, label]
        try:
            acc, _ = evaluate_walk_forward(X, y, split=0.7)
        except ValueError as exc:
            logger.warning("%s: %s", ticker, exc)
            acc = None
        results[h] = {"accuracy": acc, "n": n}

    return results
