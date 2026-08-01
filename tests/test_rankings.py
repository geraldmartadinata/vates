"""Fase 1 — test ranking & rekomendasi (pure functions + DB helper)."""

from datetime import datetime, timedelta

import pytest

from app.models import Prediction


# --- recommendation() ---


def test_recommendation_long():
    from services.rankings import recommendation

    assert recommendation(0.65, 5.0) == "LONG"
    assert recommendation(0.60, 0.1) == "LONG"   # boundary prob
    assert recommendation(0.61, 0.0) == "NEUTRAL"  # macd harus > 0


def test_recommendation_short():
    from services.rankings import recommendation

    assert recommendation(0.35, -3.0) == "SHORT"
    assert recommendation(0.40, -0.5) == "SHORT"  # boundary prob
    assert recommendation(0.39, 0.0) == "NEUTRAL"  # macd harus < 0


def test_recommendation_neutral():
    from services.rankings import recommendation

    assert recommendation(0.50, 0.0) == "NEUTRAL"
    assert recommendation(0.55, -2.0) == "NEUTRAL"  # prob tinggi tapi macd bearish
    assert recommendation(0.30, 2.0) == "NEUTRAL"   # prob rendah tapi macd bullish


def test_recommendation_missing_data():
    from services.rankings import recommendation

    assert recommendation(None, 1.0) == "NEUTRAL"
    assert recommendation(0.7, None) == "NEUTRAL"
    assert recommendation(None, None) == "NEUTRAL"


# --- rank_predictions() ---


def test_rank_predictions_top_bottom():
    from services.rankings import rank_predictions

    preds = [
        {"ticker": "A", "horizon_days": 30, "predicted_prob": 0.9, "predicted_label": 1},
        {"ticker": "B", "horizon_days": 30, "predicted_prob": 0.7, "predicted_label": 1},
        {"ticker": "C", "horizon_days": 30, "predicted_prob": 0.3, "predicted_label": 0},
        {"ticker": "D", "horizon_days": 30, "predicted_prob": 0.1, "predicted_label": 0},
        {"ticker": "E", "horizon_days": 30, "predicted_prob": 0.5, "predicted_label": 1},
    ]
    result = rank_predictions(preds, horizon=30, top_n=2)
    assert [r["ticker"] for r in result["top"]] == ["A", "B"]
    assert [r["ticker"] for r in result["bottom"]] == ["D", "C"]


def test_rank_predictions_filters_horizon():
    from services.rankings import rank_predictions

    preds = [
        {"ticker": "A", "horizon_days": 1, "predicted_prob": 0.9, "predicted_label": 1},
        {"ticker": "B", "horizon_days": 30, "predicted_prob": 0.1, "predicted_label": 0},
    ]
    result = rank_predictions(preds, horizon=1)
    assert [r["ticker"] for r in result["top"]] == ["A"]
    assert result["bottom"] == []


def test_rank_predictions_empty():
    from services.rankings import rank_predictions

    result = rank_predictions([], horizon=30)
    assert result == {"top": [], "bottom": []}


def test_rank_predictions_ignores_none_prob():
    from services.rankings import rank_predictions

    preds = [
        {"ticker": "A", "horizon_days": 30, "predicted_prob": 0.9, "predicted_label": 1},
        {"ticker": "B", "horizon_days": 30, "predicted_prob": None, "predicted_label": None},
    ]
    result = rank_predictions(preds, horizon=30)
    assert [r["ticker"] for r in result["top"]] == ["A"]


# --- latest_predictions() — DB helper ---


@pytest.mark.asyncio
async def test_latest_predictions_returns_newest_per_horizon(db_session):
    from services.rankings import latest_predictions

    now = datetime.utcnow()
    old = Prediction(
        ticker="BBCA", horizon_days=30, predicted_prob=0.4,
        predicted_label=0, created_at=now - timedelta(days=2),
    )
    new = Prediction(
        ticker="BBCA", horizon_days=30, predicted_prob=0.8,
        predicted_label=1, created_at=now,
    )
    other_ticker = Prediction(
        ticker="TLKM", horizon_days=30, predicted_prob=0.2,
        predicted_label=0, created_at=now,
    )
    db_session.add_all([old, new, other_ticker])
    await db_session.commit()

    preds = await latest_predictions(db_session)
    bbca_rows = [p for p in preds if p["ticker"] == "BBCA"]
    assert len(bbca_rows) == 1
    assert bbca_rows[0]["predicted_prob"] == 0.8
    assert bbca_rows[0]["predicted_label"] == 1


@pytest.mark.asyncio
async def test_latest_predictions_horizon_filter(db_session):
    from services.rankings import latest_predictions

    now = datetime.utcnow()
    db_session.add_all([
        Prediction(ticker="BBCA", horizon_days=1, predicted_prob=0.5, predicted_label=1, created_at=now),
        Prediction(ticker="BBCA", horizon_days=30, predicted_prob=0.6, predicted_label=1, created_at=now),
    ])
    await db_session.commit()

    preds = await latest_predictions(db_session, horizon=30)
    assert len(preds) == 1
    assert preds[0]["horizon_days"] == 30


@pytest.mark.asyncio
async def test_latest_predictions_strips_jk_suffix(db_session):
    from services.rankings import latest_predictions

    now = datetime.utcnow()
    db_session.add(
        Prediction(ticker="BBCA.JK", horizon_days=30, predicted_prob=0.7, predicted_label=1, created_at=now)
    )
    await db_session.commit()

    preds = await latest_predictions(db_session)
    assert preds[0]["ticker"] == "BBCA"
