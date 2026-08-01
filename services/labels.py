"""Target label generator — forward returns untuk 1d/7d/30d.

Pure pandas: terima df dengan kolom 'date' & 'close', return df + kolom label.
"""

import pandas as pd

DEFAULT_HORIZONS = (1, 7, 30)


def add_forward_labels(
    df: pd.DataFrame,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    threshold: float = 0.0,
) -> pd.DataFrame:
    """Tambahkan kolom forward return & label biner up/down.

    Args:
        df: DataFrame dengan kolom 'date' dan 'close' (chronological asc).
        horizons: Tuple horizon hari (default 1, 7, 30).
        threshold: Ambang return untuk label up (default 0.0).

    Returns:
        df + kolom fwd_ret_{h}d (float) & label_{h}d (0/1).
    """
    df = df.sort_values("date").reset_index(drop=True).copy()
    for h in horizons:
        df[f"fwd_ret_{h}d"] = df["close"].shift(-h) / df["close"] - 1.0
        df[f"label_{h}d"] = (df[f"fwd_ret_{h}d"] > threshold).astype(int)
    return df
