"""Forecast — probabilitas arah (up/down) per horizon dari model terbaru.

Model di-fit ulang dari seluruh history setiap kali dipanggil, jadi data
label yang baru ter-resolve otomatis ikut dipelajari (self-learning loop).
"""

import logging

from services.features import FEATURE_COLS
from services.pipeline import HORIZONS, build_ml_dataset
from services.trainer import LogisticRegression

logger = logging.getLogger(__name__)

MODEL_VERSION = "v1-logreg"


def _predict_horizons(df, features) -> list[dict]:
    """Prediksi semua horizon dari satu DataFrame ML. Shared oleh semua caller.

    Args:
        df: DataFrame dari build_ml_dataset (punya FEATURE_COLS + label_*d).
        features: List kolom fitur.

    Returns:
        List dict {horizon, prob_up, label, model_version}.
    """
    results = []
    for h in HORIZONS:
        label = f"label_{h}d"
        if label not in df.columns:
            continue
        mask = df[label].notna()
        if int(mask.sum()) < 40:
            continue

        X = df.loc[mask, features]
        y = df.loc[mask, label]
        clf = LogisticRegression().fit(X, y)

        last_row = df.iloc[-1][features].to_frame().T
        prob_up = float(clf.predict_proba(last_row)[0])
        results.append(
            {
                "horizon": h,
                "prob_up": prob_up,
                "label": int(prob_up > 0.5),
                "model_version": MODEL_VERSION,
            }
        )
    return results


async def predict_all(session, ticker: str, period: str = "2y") -> list[dict]:
    """Prediksi semua horizon untuk ticker.

    Returns:
        List dict {horizon, prob_up, label, model_version}.
    """
    df = await build_ml_dataset(session, ticker, period=period)
    return _predict_horizons(df, FEATURE_COLS)


async def analyze_ticker(session, ticker: str, period: str = "2y") -> dict:
    """Prediksi + data harga + rekomendasi untuk satu ticker.

    Returns:
        dict {
            ticker, close, macd_hist, preds: [...], recommendation
        }
    """
    from services.indicators import compute_all
    from services.rankings import recommendation

    df = await build_ml_dataset(session, ticker, period=period)

    # Ambil close + macd_histogram dari baris terakhir indikator
    ind = compute_all(df[["date", "close"]].copy(), dropna=True)
    last = ind.iloc[-1]
    close = float(last.get("close", 0))
    macd_hist = float(last.get("macd_histogram", 0))

    preds = _predict_horizons(df, FEATURE_COLS)
    rec = recommendation(
        next((p["prob_up"] for p in preds if p["horizon"] == 30), None),
        macd_hist,
    )
    return {
        "ticker": ticker,
        "close": close,
        "macd_hist": macd_hist,
        "preds": preds,
        "recommendation": rec,
    }
