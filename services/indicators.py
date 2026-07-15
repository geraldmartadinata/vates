"""Indikator teknikal — pure DataFrame vectorized ops.

TIDAK ada komunikasi database atau API.
Semua fungsi terima pd.DataFrame dengan kolom `close`, return pd.DataFrame.
Tidak ada for-loops — vektorisasi pandas/numpy murni.
"""

import pandas as pd
import numpy as np


def _sort_chronological(df: pd.DataFrame) -> pd.DataFrame:
    """Sortir ascending by date jika kolom date ada."""
    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)
    return df


def sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Simple Moving Average.

    Args:
        df: DataFrame dengan kolom 'close'.
        period: Window size (default 20).

    Returns:
        DataFrame dengan kolom tambahan 'sma_{period}'.
    """
    df = df.copy()
    df[f"sma_{period}"] = df["close"].rolling(window=period).mean()
    return df


def rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Relative Strength Index — Wilder smoothing.

    RSI = 100 - (100 / (1 + RS))
    RS = average_gain / average_loss

    Args:
        df: DataFrame dengan kolom 'close'.
        period: Lookback period (default 14).

    Returns:
        DataFrame dengan kolom tambahan 'rsi_{period}'.
    """
    df = df.copy()
    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # Wilder smoothing: average gain/loss pertama adalah SMA, selanjutnya EWMA
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi_values = 100.0 - (100.0 / (1.0 + rs))

    # Baris pertama period-1 harus NaN (Wilder smoothing baru valid setelah period)
    rsi_values.iloc[:period] = np.nan

    df[f"rsi_{period}"] = rsi_values

    return df


def macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD (Moving Average Convergence Divergence).

    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal)
    Histogram = MACD - Signal

    Args:
        df: DataFrame dengan kolom 'close'.
        fast: Periode EMA cepat (default 12).
        slow: Periode EMA lambat (default 26).
        signal: Periode EMA signal line (default 9).

    Returns:
        DataFrame dengan kolom tambahan 'macd', 'macd_signal', 'macd_histogram'.
    """
    df = df.copy()
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]

    return df


def bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: int = 2,
) -> pd.DataFrame:
    """Bollinger Bands.

    Middle = SMA(close, period)
    Upper = Middle + std_dev * std(close, period)
    Lower = Middle - std_dev * std(close, period)

    Args:
        df: DataFrame dengan kolom 'close'.
        period: Window size (default 20).
        std_dev: Number of standard deviations (default 2).

    Returns:
        DataFrame dengan kolom tambahan 'bb_upper', 'bb_middle', 'bb_lower'.
    """
    df = df.copy()
    rolling = df["close"].rolling(window=period)

    df["bb_middle"] = rolling.mean()
    bb_std = rolling.std(ddof=0)  # population std — same as pandas-ta / TA-Lib
    df["bb_upper"] = df["bb_middle"] + std_dev * bb_std
    df["bb_lower"] = df["bb_middle"] - std_dev * bb_std

    return df


def clean_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Hapus semua baris yang mengandung NaN."""
    cleaned = df.dropna().reset_index(drop=True)

    # Fallback: jika DataFrame kosong setelah drop, balikin empty (bukan error — di compute_all)
    return cleaned


def compute_all(
    df: pd.DataFrame,
    dropna: bool = True,
) -> pd.DataFrame:
    """Compute semua indikator teknikal dalam satu pass.

    Urutan kronologis dipastikan sebelum komputasi.
    Minimum data threshold: slow (26) + signal (9) = 35 baris bersih setelah dropna.

    Args:
        df: DataFrame dengan kolom 'close' (opsional 'date').
        dropna: Jika True, hapus baris dengan NaN (default True).

    Returns:
        DataFrame dengan kolom indikator lengkap.

    Raises:
        ValueError: Jika data tidak cukup setelah dropna untuk indikator apapun.
    """
    df = _sort_chronological(df)
    df = sma(df, period=20)
    df = rsi(df, period=14)
    df = macd(df, fast=12, slow=26, signal=9)
    df = bollinger_bands(df, period=20, std_dev=2)

    if dropna:
        df = clean_indicators(df)

    # Guard: data kosong setelah dropna
    if len(df) == 0:
        raise ValueError(
            f"Data length insufficient to compute requested indicators. "
            f"Got 0 rows after dropping NaN — need at least "
            f"{26 + 9} rows for MACD with default parameters."
        )

    return df
