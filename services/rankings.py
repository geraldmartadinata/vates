"""Rankings & rekomendasi — pure logic + query helper.

Menyediakan:
- recommendation(prob_30d, macd_hist) → "LONG" / "SHORT" / "NEUTRAL"
- rank_predictions(preds, horizon) → top/bottom
- latest_predictions(session) → prediksi terbaru per (ticker, horizon)
"""

import logging
from typing import Sequence

from sqlalchemy import select

from app.models import Prediction

logger = logging.getLogger(__name__)

# Aturan deterministik rekomendasi (bukan AI — transparan & testable):
# LONG : prob_up(30d) >= 0.6 dan MACD histogram > 0
# SHORT: prob_up(30d) <= 0.4 dan MACD histogram < 0
# selain itu NEUTRAL
LONG_PROB_THRESHOLD = 0.60
SHORT_PROB_THRESHOLD = 0.40


def recommendation(prob_30d: float | None, macd_hist: float | None) -> str:
    """Rekomendasi deterministik berdasarkan probabilitas 30d + momentum MACD.

    Args:
        prob_30d: P(naik) horizon 30 hari dari model. None → NEUTRAL.
        macd_hist: MACD histogram terakhir. None → NEUTRAL.

    Returns:
        "LONG", "SHORT", atau "NEUTRAL".
    """
    if prob_30d is None or macd_hist is None:
        return "NEUTRAL"

    if prob_30d >= LONG_PROB_THRESHOLD and macd_hist > 0:
        return "LONG"
    if prob_30d <= SHORT_PROB_THRESHOLD and macd_hist < 0:
        return "SHORT"
    return "NEUTRAL"


def rank_predictions(
    preds: Sequence[dict],
    horizon: int,
    top_n: int = 5,
) -> dict:
    """Ranking top/bottom berdasarkan predicted_prob untuk horizon tertentu.

    Args:
        preds: List dict dengan keys ticker, horizon_days, predicted_prob,
               predicted_label (dari latest_predictions).
        horizon: Filter horizon (1 / 7 / 30).
        top_n: Jumlah entri di top dan bottom.

    Returns:
        {"top": [...], "bottom": [...]} — tiap entri dict asli.
    """
    filtered = [p for p in preds if p["horizon_days"] == horizon and p["predicted_prob"] is not None]
    if not filtered:
        return {"top": [], "bottom": []}

    ranked = sorted(filtered, key=lambda p: p["predicted_prob"], reverse=True)
    top = ranked[:top_n]
    top_tickers = {p["ticker"] for p in top}
    bottom = [p for p in ranked[::-1] if p["ticker"] not in top_tickers][:top_n]
    return {"top": top, "bottom": bottom}


async def latest_predictions(session, horizon: int | None = None) -> list[dict]:
    """Prediksi TERBARU per (ticker, horizon) — bukan semua history.

    Strategy: ambil semua row id DESC, group di Python dengan dict
    key (ticker, horizon) — row pertama yang ketemu = terbaru.

    Returns:
        List dict {ticker (tanpa .JK), horizon_days, predicted_prob,
                   predicted_label, model_version, created_at}.
    """
    stmt = select(Prediction).order_by(Prediction.id.desc())
    rows = (await session.execute(stmt)).scalars().all()

    seen: dict[tuple[str, int], Prediction] = {}
    for r in rows:
        key = (r.ticker, r.horizon_days)
        if key not in seen:
            seen[key] = r

    result = []
    for r in seen.values():
        if horizon is not None and r.horizon_days != horizon:
            continue
        result.append(
            {
                "ticker": r.ticker.removesuffix(".JK"),
                "horizon_days": r.horizon_days,
                "predicted_prob": r.predicted_prob,
                "predicted_label": r.predicted_label,
                "model_version": r.model_version,
                "created_at": r.created_at,
            }
        )
    return result
