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


async def predict_all(session, ticker: str, period: str = "2y") -> list[dict]:
    """Prediksi semua horizon untuk ticker.

    Returns:
        List dict {horizon, prob_up, label, model_version}.
    """
    df = await build_ml_dataset(session, ticker, period=period)
    results = []

    for h in HORIZONS:
        label = f"label_{h}d"
        if label not in df.columns:
            continue
        mask = df[label].notna()
        if int(mask.sum()) < 40:
            continue

        X = df.loc[mask, FEATURE_COLS]
        y = df.loc[mask, label]
        clf = LogisticRegression().fit(X, y)

        last_row = df.iloc[-1][FEATURE_COLS].to_frame().T
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
