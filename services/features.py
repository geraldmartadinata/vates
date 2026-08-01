"""Feature assembler — harga + indikator + agregat berita.

Pure pandas. build_ml_frame() → DataFrame siap training (features + labels).
"""

import pandas as pd

from services.indicators import compute_all
from services.labels import add_forward_labels

FEATURE_COLS = [
    "sma_20", "rsi_14",
    "macd", "macd_signal", "macd_histogram",
    "bb_upper", "bb_middle", "bb_lower",
    "ret_1d", "volatility_10d",
    "sent_mean", "news_count", "high_impact",
]

LABEL_COLS = ["label_1d", "label_7d", "label_30d"]


def daily_news_features(news_df: pd.DataFrame) -> pd.DataFrame:
    """Agregasi berita per tanggal → sent_mean, news_count, high_impact."""
    if news_df is None or news_df.empty:
        return pd.DataFrame(columns=["date", "sent_mean", "news_count", "high_impact"])

    df = news_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["high_impact"] = (df["impact"] == "high").astype(int)

    g = (
        df.groupby("date")
        .agg(
            sent_mean=("sentiment_score", "mean"),
            news_count=("sentiment_score", "count"),
            high_impact=("high_impact", "sum"),
        )
        .reset_index()
    )
    return g


def build_ml_frame(prices_df: pd.DataFrame, news_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Gabungkan harga → indikator → agregat berita → forward labels.

    Args:
        prices_df: DataFrame dengan kolom 'date' & 'close'.
        news_df: Optional DataFrame dengan kolom 'date', 'sentiment_score', 'impact'.

    Returns:
        DataFrame dengan FEATURE_COLS + LABEL_COLS, baris NaN dibuang.
    """
    df = compute_all(prices_df[["date", "close"]].copy())

    if news_df is not None and not news_df.empty:
        n = daily_news_features(news_df)
        if not n.empty:
            df = df.merge(n, on="date", how="left")
            for col in ("sent_mean", "news_count", "high_impact"):
                df[col] = df[col].fillna(0.0)
        else:
            for col in ("sent_mean", "news_count", "high_impact"):
                df[col] = 0.0
    else:
        for col in ("sent_mean", "news_count", "high_impact"):
            df[col] = 0.0

    df["ret_1d"] = df["close"].pct_change()
    df["volatility_10d"] = df["ret_1d"].rolling(10).std()
    df = add_forward_labels(df)

    return df.dropna(subset=FEATURE_COLS).reset_index(drop=True)


def select_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pisahkan X (features) dan y (labels) dari output build_ml_frame.

    Returns:
        (X, y) — y adalah DataFrame berisi LABEL_COLS.
    """
    X = df[FEATURE_COLS]
    y = df[LABEL_COLS]
    return X, y
