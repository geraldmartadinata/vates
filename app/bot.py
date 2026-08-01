"""Bot Telegram — command handlers.

Commands:
- /start        → sambutan
- /saham TICKER → harga OHLCV terkini
- /indikator TICKER → ringkasan indikator teknikal
"""

import logging

from sqlalchemy import select

from app.models import User, UserWatchlist
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


def _get_user_id(update) -> int:
    """Ambil telegram_id dari update."""
    if update.effective_user:
        return update.effective_user.id
    if update.effective_message and update.effective_message.from_user:
        return update.effective_message.from_user.id
    raise RuntimeError("User tidak teridentifikasi")


async def _ensure_user(session, update) -> User:
    """Auto-register user pertama kali. Return User row (ada di session)."""
    telegram_id = _get_user_id(update)
    user = (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()

    if user is None:
        u = update.effective_user
        user = User(
            telegram_id=telegram_id,
            username=u.username if u else None,
            first_name=u.first_name if u else None,
        )
        session.add(user)
        await session.commit()
        logger.info("User baru terdaftar: %s (%s)", telegram_id, u.username if u else "?")
    else:
        # Update last_active
        from datetime import datetime
        user.last_active_at = datetime.utcnow()
        await session.commit()
    return user


# --- Handlers ---


async def start(update, context):
    """Kirim pesan sambutan."""
    # Auto-register user
    session_factory = context.bot_data.get("session_factory")
    if session_factory:
        async with session_factory() as db_sesh:
            await _ensure_user(db_sesh, update)

    await update.message.reply_text(
        f"{_bold('Vates Bot — Analitik Kuantitatif IHSG')}\n\n"
        f"Perintah tersedia:\n"
        f"  {_code('/saham BBCA')} — Harga terkini\n"
        f"  {_code('/indikator BBCA')} — Indikator teknikal\n"
        f"  {_code('/prediksi BBCA')} — Probabilitas arah 1d/7d/30d\n"
        f"  {_code('/watch add BBCA')} — Tambah ke watchlist\n"
        f"  {_code('/watch remove BBCA')} — Hapus dari watchlist\n"
        f"  {_code('/watch list')} — Lihat watchlist\n\n"
        f"{_bold('Tips')}: cukup nama saham, suffix .JK ditambah otomatis.\n"
        f"Watchlist-mu ikut diproses pipeline prediksi harian.",
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


async def prediksi(update, context):
    """Tampilkan probabilitas arah (up/down) per horizon."""
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
        if not session_factory:
            await update.message.reply_text("Prediksi belum siap. Coba lagi nanti.")
            return

        from services.forecast import predict_all

        async with session_factory() as db_sesh:
            preds = await predict_all(db_sesh, raw)

        if not preds:
            await update.message.reply_text(
                f"Data untuk {ticker} belum cukup untuk prediksi."
            )
            return

        def arrow(prob):
            if prob > 0.6:
                return "Naik ▲"
            if prob < 0.4:
                return "Turun ▼"
            return "Ragu ➖"

        lines = [
            f"{_bold(f'{ticker} — Prediksi')}",
            "",
        ]
        for p in preds:
            prob = p["prob_up"]
            h = p["horizon"]
            lines.append(f"{_code(f'{h:>3d} hari  : {prob:.1%} {arrow(prob)}')}")
        lines.append("")
        lines.append("<i>Prob = peluang harga naik. Model v1-logreg, "
                     "otomatis belajar dari hasil harian.</i>")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.exception("Error predicting %s", ticker)
        await update.message.reply_text(
            f"⛔ Gagal memprediksi {ticker}. Coba lagi nanti."
        )


async def watch(update, context):
    """Kelola watchlist per user: add / remove / list."""
    session_factory = context.bot_data.get("session_factory")
    if not session_factory:
        await update.message.reply_text("Layanan belum siap. Coba lagi nanti.")
        return

    if not context.args:
        await update.message.reply_text(
            f"Gunakan: {_code('/watch add BBCA')} | "
            f"{_code('/watch remove BBCA')} | {_code('/watch list')}",
            parse_mode="HTML",
        )
        return

    action = context.args[0].lower()

    async with session_factory() as db_sesh:
        try:
            user = await _ensure_user(db_sesh, update)
        except Exception:
            await update.message.reply_text("Gagal identifikasi user.")
            return

        # --- LIST ---
        if action == "list":
            rows = (
                await db_sesh.execute(
                    select(UserWatchlist)
                    .where(UserWatchlist.user_id == user.id)
                    .order_by(UserWatchlist.created_at.asc())
                )
            ).scalars().all()
            if not rows:
                await update.message.reply_text(
                    "Watchlist kosong. Tambah dengan "
                    f"{_code('/watch add BBCA')}",
                    parse_mode="HTML",
                )
                return
            tickers = [r.ticker.removesuffix(".JK") for r in rows]
            await update.message.reply_text(
                f"{_bold('Watchlist-mu')} ({len(tickers)})\n"
                + "\n".join(f"  {_code(t)}" for t in tickers),
                parse_mode="HTML",
            )
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                f"Gunakan: {_code('/watch add BBCA')} atau "
                f"{_code('/watch remove BBCA')}",
                parse_mode="HTML",
            )
            return

        raw = context.args[1].strip().upper()
        ticker = normalize_ticker(raw)

        # --- ADD ---
        if action == "add":
            existing = (
                await db_sesh.execute(
                    select(UserWatchlist).where(
                        UserWatchlist.user_id == user.id,
                        UserWatchlist.ticker == ticker,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                await update.message.reply_text(
                    f"{ticker} sudah ada di watchlist-mu.",
                    parse_mode="HTML",
                )
                return
            db_sesh.add(UserWatchlist(user_id=user.id, ticker=ticker))
            await db_sesh.commit()
            await update.message.reply_text(
                f"{_bold(ticker)} ditambahkan ke watchlist-mu. "
                f"Ikut diproses prediksi harian.",
                parse_mode="HTML",
            )
            return

        # --- REMOVE ---
        if action == "remove":
            row = (
                await db_sesh.execute(
                    select(UserWatchlist).where(
                        UserWatchlist.user_id == user.id,
                        UserWatchlist.ticker == ticker,
                    )
                )
            ).scalar_one_or_none()
            if not row:
                await update.message.reply_text(
                    f"{ticker} tidak ada di watchlist-mu.",
                    parse_mode="HTML",
                )
                return
            await db_sesh.delete(row)
            await db_sesh.commit()
            await update.message.reply_text(
                f"{ticker} dihapus dari watchlist-mu.",
                parse_mode="HTML",
            )
            return

        await update.message.reply_text(
            f"Perintah tidak dikenal: {_code(action)}. "
            f"Pakai add/remove/list.",
            parse_mode="HTML",
        )


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
