"""Robustness grid untuk H2 spring strategy — dipinjam dari signal-ingest.

run_strategy berasal dari signal-ingest/h2_spring.py; di vates-core
dipakai via import eksplisit. Jika h2_spring belum tersedia di repo ini,
modul ini hanya untuk referensi dan tidak bisa dijalankan.
"""
from services.crypto.h2_spring import run_strategy  # noqa: F401


def run_grid(df, params):
    results = []
    for N in params.get("N", [12, 24, 48]):
        for K in params.get("K", [3, 5]):
            for RR in params.get("RR", [2.0, 3.0]):
                train_n = int(len(df) * 0.7)
                trades = run_strategy(
                    df, N, K, RR, train_cut=0.7, train_start=train_n
                )
                # Filter OOS trades (entry_time >= train_n)
                test_trades = [
                    t
                    for t in trades
                    if df.index.get_loc(t["entry_time"], method="nearest")
                    >= train_n
                ]
                total_r = sum(t["r"] for t in test_trades)
                n_tr = len(test_trades)
                results.append({
                    "N": N, "K": K, "RR": RR,
                    "trades": n_tr,
                    "total_r": total_r,
                    "pf": total_r / n_tr if test_trades else 0.0
                })
    return results