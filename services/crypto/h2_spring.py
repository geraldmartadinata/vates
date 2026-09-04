# H2 spring reclaim (SMC-style): sweep range low -> reclaim -> long.
# Range = N-bar lookback high/low. Sweep = close < range_low. Reclaim = close
# back above range_low within K bars -> entry long at reclaim close.
# SL = below sweep wick (low of sweep bar). TP = range_high (or mid as alt).
# Pure, no lookahead: range computed on bars BEFORE entry bar.
import pandas as pd

FEE = 0.001  # round-trip taker ~0.1% per leg accounted per trade
GRID_N = [12, 24, 48]      # range lookback (bars)
GRID_K = [3, 5, 8]        # reclaim window (bars)
GRID_RR = [1.5, 2.0, 3.0] # take-profit as multiple of risk (SL distance)


def detect_ranges(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Return df with range_high/range_low using N-bar lookback EXCLUDING the
    current bar. rolling(n) at i covers [i-n+1, i]; .shift(1) makes value at i
    the range of bars [i-n, i-1] — strictly before bar i (no lookahead)."""
    hh = df["high"].rolling(n).max().shift(1)
    ll = df["low"].rolling(n).min().shift(1)
    return pd.DataFrame({"range_high": hh, "range_low": ll})


def run_strategy(df: pd.DataFrame, n: int, k: int, rr: float,
                 cap_hold: int = 96) -> list[dict]:
    rng = detect_ranges(df, n)
    rh, rl = rng["range_high"], rng["range_low"]
    h, low, c = df["high"].values, df["low"].values, df["close"].values
    n_bars = len(df)
    trades: list[dict] = []
    i = n + 2
    while i < n_bars - 1:
        if pd.isna(rl.iloc[i]) or pd.isna(rh.iloc[i]):
            i += 1
            continue
        # sweep: this bar closed below range low
        if c[i] < rl.iloc[i]:
            sweep_low = low[i]
            # look for reclaim within K bars
            reclaimed = -1
            for j in range(i + 1, min(i + 1 + k, n_bars - 1)):
                if c[j] > rl.iloc[i]:
                    reclaimed = j
                    break
            if reclaimed == -1:
                i = i + 1
                continue
            entry = c[reclaimed]
            risk = max(entry - sweep_low, 1e-9)
            sl = sweep_low - risk * 0.15
            tp = entry + risk * rr
            exit_i = reclaimed
            r_mult = 0.0
            while exit_i < min(reclaimed + cap_hold, n_bars - 1):
                exit_i += 1
                if low[exit_i] <= sl:
                    r_mult = -1.0
                    break
                if h[exit_i] >= tp:
                    r_mult = rr
                    break
            else:
                # closed at last bar
                close_p = c[min(exit_i, n_bars - 1)]
                r_mult = (close_p - entry) / risk
            r_net = r_mult - (FEE * 2 if r_mult != 0 else 0)
            trades.append({"entry_time": df.index[reclaimed], "n": n, "k": k, "rr": rr,
                           "r": r_net, "side": "long"})
            i = reclaimed + 1
            continue
        i += 1
    return trades


def summarize(trades: list[dict], label: str) -> dict:
    if not trades:
        return {"label": label, "n": 0, "win_rate": None, "profit_factor": None,
                "total_r": 0.0, "avg_r": 0.0, "max_dd_pct": 0.0}
    rs = [t["r"] for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [-r for r in rs if r < 0]
    gross_w = sum(wins)
    gross_l = sum(losses) if losses else 0.0
    pf = (gross_w / gross_l) if gross_l > 0 else (float("inf") if gross_w > 0 else 0.0)
    cum = 0.0
    peak = 0.0
    mdd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        mdd = min(mdd, cum - peak)
    return {"label": label, "n": len(rs),
            "win_rate": round(100 * len(wins) / len(rs), 1),
            "profit_factor": round(pf, 2) if pf != float("inf") else None,
            "total_r": round(sum(rs), 1), "avg_r": round(sum(rs) / len(rs), 3),
            "max_dd_pct": round(-mdd, 1)}
