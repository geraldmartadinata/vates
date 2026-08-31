"""Bot Telegram — perintah /analyze dan /screen untuk Vates.

Bekerja langsung dengan service (bukan via HTTP endpoint) untuk latensi rendah.
Modul ini dipasang sebagai plugin atau handler Telegram bot.
"""

import logging

from services.analyzer import analyze_stock

logger = logging.getLogger(__name__)


async def cmd_analyze(session, ticker_raw: str) -> dict:
    """Handle /analyze BBCA. Return payload lengkap + format pesan singkat."""
    try:
        out = await analyze_stock(session, ticker_raw, period="2y")
        v = out["verdict"]["verdict"]
        conf = out["verdict"]["confidence"]
        insight = out["insight"]
        proj_30 = next(
            (h for h in out["projection"]["horizons"] if h["horizon_days"] == 30),
            {},
        )
        msg = (
            f"📊 *{ticker_raw.upper()}* — {v} (confidence: {conf})\n"
            f"• Close: {insight['close']:,.0f} | SMA20: {insight['sma_20']:,.0f}\n"
            f"• RSI14: {insight['rsi_14']:.1f} | MACD hist: {insight['macd_histogram']:+.2f}\n"
            f"• Trend: {insight['trend']} | BB atas: {insight['bb_upper']:,.0f}\n"
            f"• Proj 30d: {proj_30.get('expected_return_pct', 0)*100:+.1f}% "
            f"(close ~ {proj_30.get('projected_close', 0):,.0f})\n"
            f"• Alasan: {'; '.join(out['verdict']['reasons'][:2])}"
        )
        return {"ok": True, "message": msg, "payload": out}
    except Exception as exc:
        logger.exception("cmd_analyze gagal untuk %s", ticker_raw)
        return {"ok": False, "message": f"Analisis {ticker_raw} gagal: {exc}", "payload": None}


async def cmd_screen(session, tickers: list[str], horizon: int = 30) -> dict:
    """Handle /screen BBCA TLKM BBRI. Return ringkasan + top buys/sells."""
    results = []
    errors = []
    for t in tickers:
        try:
            out = await analyze_stock(session, t, period="2y")
            results.append({
                "ticker": t,
                "verdict": out["verdict"]["verdict"],
                "conf": out["verdict"]["confidence"],
                "close": out["insight"]["close"],
                "proj_30": next(
                    (h["expected_return_pct"] for h in out["projection"]["horizons"] if h["horizon_days"] == 30),
                    0,
                ),
            })
        except Exception as exc:
            errors.append({"ticker": t, "error": str(exc)})

    # Sort by verdict score (desc)
    score = {"STRONG BUY": 3, "BUY": 2, "HOLD": 1, "SELL": -1, "STRONG SELL": -2}
    ranked = sorted(results, key=lambda r: score.get(r["verdict"], 0), reverse=True)
    top = ranked[:5]

    lines = [f"📊 *Screen {len(tickers)} ticker* (horizon {horizon}d):"]
    for r in top:
        arrow = "⬆" if r["proj_30"] > 0 else "⬇" if r["proj_30"] < 0 else "➖"
        lines.append(
            f"• {r['ticker']}: {r['verdict']} ({r['conf']}) | "
            f"close {r['close']:,.0f} | proj {arrow}{r['proj_30']*100:+.1f}%"
        )
    if errors:
        lines.append(f"❌ Error: {', '.join(e['ticker'] for e in errors)}")

    return {
        "ok": True,
        "message": "\n".join(lines),
        "results": ranked,
        "errors": errors,
    }
