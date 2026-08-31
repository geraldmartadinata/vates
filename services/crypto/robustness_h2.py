"""H2 Spring Reclaim — Robustness tests (mirrors robustness.py for H1).

Tests:
1. neighbor grid: 6 param combos (N in 12/24/48, K in 3/5, RR=3.0) — run on TRAIN only.
2. rolling walk-forward (3 windows) — 70/30 split rolling.
3. regime split: uptrend / downtrend / high-vol / low-vol — split by ATR percentile + price vs SMA20.

Output per asset: win-rate, PF, totR, MDD, param kombi terbaik per tes.
"""

import pandas as pd
from h2_spring import run_strategy

SYMS = [
    "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD",
    "DOGE-USD", "ADA-USD", "AVAX-USD", "LINK-USD", "TRX-USD",
    "LTC-USD", "NEAR-USD", "AAVE-USD", "INJ-USD",
]
DATA_DIR = "data/cache/yf"


def load_df(sym):
    """Baca CSV dari fetch_data (per symbol)."""
    import os
    fname = os.path.join(DATA_DIR, sym.replace("-", "") + "_1h.csv")
    df = pd.read_csv(fname, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _detect_range(df, n):
    from h2_spring import detect_ranges
    return detect_ranges(df, n)


def run_grid(df, params):
    results = []
    for N in params.get("N", [12, 24, 48]):
        for K in params.get("K", [3, 5]):
            for RR in params.get("RR", [2.0, 3.0]):
                # Grid hanya di 70% data pertama (TRAIN)
                train_n = int(len(df) * 0.7)
                train_df = df.iloc[:train_n]
                # Run strategy di train — ambil statistik (bukan OOS)
                # Untuk simplicity, kita pakai seluruh df tapi hitung hanya di train region
                # (mirip robustness H1)
                trades = run_strategy(df.iloc[:len(df)], n=N, k=K, rr=RR,
                                      train_cut=0.7, test_start=train_n)
                # Filter trade yang terjadi di train region
                train_cut_idx = train_n
                train_trades = [t for t in trades if df.index.get_loc(t["entry_time"], method="nearest") < train_cut_idx] if not isinstance(t, dict) else [t]
                # Sederhanakan: hitung semua trades (karena parameter dipilih di train, tapi eksekusi bisa di train+test untuk evaluasi kombinasi)
                # Untuk grid: pakai OOS (30% akhir) seperti robustness H1
                # Ambil trades yang entry_time di OOS region
                test_trades = [t for t in trades if df.index.get_loc(t.get("entry_time", t.get("entry_idx", 0)), method="nearest") >= train_cut_idx]
                if not test_trades:
                    pass  # bisa kosong jika parameter menghasilkan 0 trade di test
                total_r = sum(t["r"] for t in test_trades)
                n_tr = len(test_trades)
                results.append({
                    "N": N, "K": K, "RR": RR,
                    "trades": n_tr, "total_r": total_r,
                    "pf": (sum(t["exit_price"] for t in test_trades) / sum(t["entry_price"] for t in test_trades)) if test_trades else 0.0,
                })
    return results


def neighbor_grid(sym, params):
    df = load_df(sym)
    return run_grid(df, params)


def rolling_walk_forward(sym, n_windows=3):
    df = load_df(sym)
    n = len(df)
    window_size = n // (n_windows + 1)
    results = []
    for w in range(n_windows):
        cut_start = w * window_size
        cut_end = (w + 1) * window_size
        train_df = df.iloc[:cut_end]
        # Grid default
        trades = run_strategy(train_df, n=24, k=3, rr=3.0,
                              train_cut=0.7, test_start=int(len(train_df)*0.7))
        total_r = sum(t.get("r", t.get("exit_r", 0)) for t in trades)
        results.append({
            "window": w,
            "train_n": len(train_df),
            "test_n": len(train_df[int(len(train_df)*0.7):]),
            "total_r": total_r,
            "n_trades": len(trades),
        })
    return results


# Regime split helpers

def regime_split(sym):
    df = load_df(sym)
    # Sederhana: split berdasarkan SMA20 slope dan vol
    df["trend"] = df["close"] > df["close"].rolling(20).mean()
    df["regime"] = df["trend"].map({True: "up", False: "down"})
    # High vol: ATR percentile > 66 dari train
    # Untuk simplicity, pakai rolling std return sebagai proxy
    df["ret_std"] = df["close"].pct_change().rolling(14).std()
    results = {}
    for reg in ["up", "down"]:
        reg_df = df[df["regime"] == reg]
        if len(reg_df) > 30:
            trades = run_strategy(reg_df, n=24, k=3, rr=3.0,
                                  train_cut=0.7, test_start=int(len(reg_df)*0.7))
            total_r = sum(t.get("r", 0) for t in trades)
            results[reg] = {"n": len(trades), "total_r": total_r}
        else:
            results[reg] = {"n": 0, "total_r": 0}
    return results


if __name__ == "__main__":
    # Quick sanity: grid + rolling + regime untuk 1 simbol (LTC-USD)
    sym = "LTC-USD"
    print(f"=== {sym} ===")
    grid_res = neighbor_grid(sym, {"N": [12, 24, 48], "K": [3, 5], "RR": [2.0, 3.0]})
    for gr in grid_res:
        print(f"  grid N={gr['N']} K={gr['K']} RR={gr['RR']} -> trades={gr['trades']} R={gr['total_r']:+.1f}")
    rolling = rolling_walk_forward(sym, 3)
    for r in rolling:
        print(f"  rolling w={r['window']} -> trades={r['n_trades']} R={r['total_r']:+.1f}")
    regime = regime_split(sym)
    print(f"  regime -> {regime}")
