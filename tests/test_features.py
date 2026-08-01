"""Test services/features.py — feature assembler."""

import numpy as np
import pandas as pd

from services.features import FEATURE_COLS, LABEL_COLS, build_ml_frame, daily_news_features


def _prices(n=120):
    rng = np.random.default_rng(42)
    closes = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame(
        {"date": pd.date_range("2026-01-01", periods=n, freq="B"), "close": closes}
    )


def _news(n=10):
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=n, freq="B"),
            "sentiment_score": np.linspace(-0.8, 0.8, n),
            "impact": ["high" if i % 3 == 0 else "low" for i in range(n)],
        }
    )


class TestDailyNewsFeatures:
    def test_agg_columns(self):
        n = daily_news_features(_news())
        assert list(n.columns) == ["date", "sent_mean", "news_count", "high_impact"]

    def test_high_impact_count(self):
        n = daily_news_features(_news())
        assert int(n["high_impact"].sum()) == 4  # every 3rd index of 10

    def test_empty(self):
        assert daily_news_features(None).empty
        assert daily_news_features(pd.DataFrame()).empty


class TestBuildMlFrame:
    def test_columns_present(self):
        df = build_ml_frame(_prices(), _news())
        assert set(FEATURE_COLS).issubset(set(df.columns))
        assert set(LABEL_COLS).issubset(set(df.columns))

    def test_no_nan_in_features(self):
        df = build_ml_frame(_prices(), _news())
        assert not df[FEATURE_COLS].isna().any().any()

    def test_no_news_zeros(self):
        df = build_ml_frame(_prices())
        assert (df["sent_mean"] == 0).all()
        assert (df["news_count"] == 0).all()
