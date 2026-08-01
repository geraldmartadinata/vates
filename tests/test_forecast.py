"""Test services/forecast.py — predict_all dengan data sintetis (mock fetch)."""

import numpy as np
import pandas as pd
import pytest

from services.features import build_ml_frame
from services.forecast import predict_all
from services.pipeline import HORIZONS


def _synthetic_ml_frame():
    rng = np.random.default_rng(42)
    closes = 100 + np.cumsum(rng.normal(0, 1, 200))
    prices = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=200, freq="B"),
        "close": closes,
    })
    news = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=50, freq="B"),
        "sentiment_score": np.linspace(-0.5, 0.5, 50),
        "impact": ["high" if i % 3 == 0 else "low" for i in range(50)],
    })
    return build_ml_frame(prices, news)


def _patch_build(monkeypatch, frame):
    async def fake_build(*args, **kwargs):
        return frame

    monkeypatch.setattr("services.forecast.build_ml_dataset", fake_build)


@pytest.mark.asyncio
async def test_predict_all_shape(monkeypatch):
    frame = _synthetic_ml_frame()
    _patch_build(monkeypatch, frame)

    # Session tidak dipakai (fetch di-mock) — kirim None.
    results = await predict_all(None, "BBCA")

    assert len(results) == len(HORIZONS)
    for r in results:
        assert r["horizon"] in HORIZONS
        assert 0.0 <= r["prob_up"] <= 1.0
        assert r["label"] in (0, 1)
        assert r["model_version"] == "v1-logreg"


@pytest.mark.asyncio
async def test_predict_all_returns_latest_prob(monkeypatch):
    """Probabilitas harus dari baris TERAKHIR (hari ini)."""
    frame = _synthetic_ml_frame()
    _patch_build(monkeypatch, frame)

    results = await predict_all(None, "BBCA")
    assert all(0.0 <= r["prob_up"] <= 1.0 for r in results)
