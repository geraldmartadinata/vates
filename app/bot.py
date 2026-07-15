"""Bot Telegram — command handlers.

Commands:
- /start        → sambutan
- /saham TICKER → harga OHLCV terkini
- /indikator TICKER → ringkasan indikator teknikal
"""

import logging

from services.data_engine import fetch_historical, normalize_ticker
from services.indicators import compute_all

logger = logging.getLogger(__name__)

# --- Helpers ---


def _bold(text: str) -> str:
    return f"<b>{text}</b>" if text else ""


def _code(text: str) -> str:
    return f"<code>{text}</code>" if text else ""


def _escape(text: float | int | None) -> str:
    """Format angka dengan pemisah ribuan. NaN → 'N/A'."""
    if text is None:
        return "N/A"
    if isinstance(text, float):
        if text != text:  # NaN check
            return "N/A"
        return f"{text:,.2f}"
    return f"{text:,}"


def _ticker_help() -> str:
    return (
        "Gunakan: <i>/saham kode</i> atau <i>/saham BBCA</i>\n"
        "Kode otomatis ditambahi .JK untuk saham IHSG."
    )


# --- Handlers ---


async def start(update, context):
    """Kirim pesan sambutan."""
    await update.message.reply_text(
        f"{_bold('Vates Bot — Analitik Kuantitatif IHSG')}\n\n"
        f"Perintah tersedia:\n"
        f"  {_code('/saham BBCA')} — Harga terkini\n"
        f"  {_code('/indikator BBCA')} — Indikator teknikal\n\n"
        f"{_bold('Tips')}: cukup nama saham, suffix .JK ditambah otomatis.",
        parse_mode="HTML",
    )


async def saham(update, context):
    """Tampilkan harga OHLCV terkini."""
    if not context.args:
        await update.message.reply_text(
            f"Masukkan kode saham.\n\n{_ticker_help()}",
            parse_mode="HTML",
        )
        return

    raw = context.args[0].strip().upper()
    ticker = normalize_ticker(raw)

    try:
        session = None  # akan di-set oleh context.bot_data nanti
        # Ambil session dari bot_data yang di-inject saat setup
        session_factory = context.bot_data.get("session_factory")
        if session_factory:
            async with session_factory() as db_sesh:
                df = await fetch_historical(db_sesh, raw, period="1mo", force_fetch=False)
        else:
            # Fallback — fetch tanpa cache
            from services.data_engine import _prepare_df
            import yfinance as yf
            yf_ticker = yf.Ticker(ticker)
            df = yf_ticker.history(period="1mo")
            df = _prepare_df(df)

        if df is None or (isinstance(df, list) and len(df) == 0):
            raise RuntimeError("Data kosong")

        # Buang baris tanpa harga (hari ini yg belum tutup → NaN)
        if isinstance(df, list):
            df = [r for r in df if r.close is not None and not (r.close != r.close)]
        else:
            df = df.dropna(subset=["close"]).copy()

        if len(df) == 0:
            raise RuntimeError(f"Tidak ada data harga valid untuk {ticker}.")

        # Ambil baris terakhir
        if isinstance(df, list):
            last = df[-1]
            date_str = last.date.strftime("%d %b %Y") if hasattr(last.date, "strftime") else str(last.date)
            reply = (
                f"{_bold(ticker)} — {date_str}\n"
                f"{_code(f'Open : Rp {_escape(last.open)}')}\n"
                f"{_code(f'High : Rp {_escape(last.high)}')}\n"
                f"{_code(f'Low  : Rp {_escape(last.low)}')}\n"
                f"{_code(f'Close: Rp {_escape(last.close)}')}\n"
                f"{_code(f'Vol  : {_escape(last.volume)}')}"
            )
        else:
            last = df.iloc[-1]
            date_str = last.name.strftime("%d %b %Y") if hasattr(last.name, "strftime") else str(last["date"])
            o = _escape(last.get("open", 0))
            h = _escape(last.get("high", 0))
            l = _escape(last.get("low", 0))
            c = _escape(last.get("close", 0))
            v = _escape(int(last.get("volume", 0)))
            reply = (
                f"{_bold(ticker)} — {date_str}\n"
                f"{_code(f'Open : Rp {o}')}\n"
                f"{_code(f'High : Rp {h}')}\n"
                f"{_code(f'Low  : Rp {l}')}\n"
                f"{_code(f'Close: Rp {c}')}\n"
                f"{_code(f'Vol  : {v}')}"
            )
    except RuntimeError as e:
        reply = f"⛔ {e}"
    except Exception as e:
        logger.exception("Error fetching %s", ticker)
        reply = f"⛔ Gagal memproses {ticker}. Coba lagi nanti."

    await update.message.reply_text(reply, parse_mode="HTML")


async def indikator(update, context):
    """Tampilkan ringkasan indikator teknikal."""
    if not context.args:
        await update.message.reply_text(
            f"Masukkan kode saham.\n\n{_ticker_help()}",
            parse_mode="HTML",
        )
        return

    raw = context.args[0].strip().upper()
    ticker = normalize_ticker(raw)

    try:
        session_factory = context.bot_data.get("session_factory")
        if session_factory:
            async with session_factory() as db_sesh:
                df = await fetch_historical(db_sesh, raw, period="6mo", force_fetch=False)
        else:
            import yfinance as yf
            from services.data_engine import _prepare_df
            yf_ticker = yf.Ticker(ticker)
            df = yf_ticker.history(period="6mo")
            df = _prepare_df(df)

        if df is None or (isinstance(df, list) and len(df) == 0):
            raise RuntimeError("Data kosong — coba kode saham lain.")

        # Buang baris tanpa close (hari ini yg belum tutup → NaN)
        if isinstance(df, list):
            import pandas as pd
            df = [r for r in df if r.close is not None and not (r.close != r.close)]
            df = pd.DataFrame([{"close": r.close, "date": r.date} for r in df])
        else:
            df = df.dropna(subset=["close"]).copy()

        if len(df) == 0:
            raise RuntimeError(f"Tidak ada data harga valid untuk {ticker}.")

        enriched = compute_all(df, dropna=True)

        last = enriched.iloc[-1]

        c_close = _escape(last.get("close", 0))
        c_sma = _escape(last.get("sma_20", 0))
        c_rsi = last.get("rsi_14", 50)
        c_macd = last.get("macd", 0)
        c_signal = last.get("macd_signal", 0)
        c_hist = last.get("macd_histogram", 0)
        c_bb_u = _escape(last.get("bb_upper", 0))
        c_bb_m = _escape(last.get("bb_middle", 0))
        c_bb_l = _escape(last.get("bb_lower", 0))

        # Helper signal
        def rsi_signal(val):
            if val > 70:
                return "Overbought ⬆"
            if val < 30:
                return "Oversold ⬇"
            return "Neutral ➖"

        def macd_signal(hist):
            if hist > 0:
                return "Bullish 🟢"
            return "Bearish 🔴"

        ohlcv_row = (
            f"{_bold(ticker)} — Data 6 bulan terakhir\n\n"
            f"Harga Terakhir\n"
            f"{_code(f'Close: Rp {c_close}')}\n\n"
            f"{_bold('Indikator Teknikal')}\n"
            f"{_code(f'SMA 20  : {c_sma}')}\n"
            f"{_code(f'RSI 14  : {c_rsi:.2f}')} — "
            f"{rsi_signal(c_rsi)}\n"
            f"{_code(f'MACD    : {c_macd:.2f}')}\n"
            f"{_code(f'Signal  : {c_signal:.2f}')}\n"
            f"{_code(f'Hist    : {c_hist:.2f}')} — "
            f"{macd_signal(c_hist)}\n"
            f"{_bold('Bollinger Bands')} (20,2)\n"
            f"{_code(f'Upper: Rp {c_bb_u}')}\n"
            f"{_code(f'Mid  : Rp {c_bb_m}')}\n"
            f"{_code(f'Lower: Rp {c_bb_l}')}"
        )

    except ValueError as e:
        # Data insufficient
        ohlcv_row = f"⛔ {e}"
    except RuntimeError as e:
        ohlcv_row = f"⛔ {e}"
    except Exception as e:
        logger.exception("Error computing indicators for %s", ticker)
        ohlcv_row = f"⛔ Gagal memproses indikator {ticker}. Coba lagi nanti."

    await update.message.reply_text(ohlcv_row, parse_mode="HTML")


async def error(update, context):
    """Global error handler — log, kirim pesan ramah ke user."""
    logger.error("Update %s caused error %s", update, context.error)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⛔ Terjadi kesalahan internal. Silakan coba lagi."
            )
    except Exception:
        pass
