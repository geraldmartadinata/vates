"""Demo: evaluasi baseline winrate (1d/7d/30d) untuk beberapa ticker IHSG.

Usage: .\.venv\Scripts\python.exe scripts\evaluate_demo.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, async_session_factory, engine
from services.pipeline import evaluate_ticker

TICKERS = ["BBCA", "ASII", "TLKM", "BBRI", "UNVR"]


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        for t in TICKERS:
            try:
                res = await evaluate_ticker(session, t, period="2y")
            except Exception as exc:
                print(f"{t:6s} ERROR {exc}")
                continue
            cells = []
            for h in (1, 7, 30):
                v = res.get(h, {})
                acc = v.get("accuracy")
                cells.append(
                    f"{h}d={acc:.1%}" if acc is not None else f"{h}d=-"
                )
            print(f"{t:6s} " + " ".join(cells))


if __name__ == "__main__":
    asyncio.run(main())
