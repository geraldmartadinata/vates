"""Parser v2 - ekstraksi sinyal dari teks pesan Telegram (ID/EN trading slang).
Support: Binance/OKX (USDT), BingX perpetual (.P suffix), standard PERP.

Sengaja konservatif: hanya klasifikasi 'signal' kalau ada bukti kuat (ticker + arah/level).
"""
import re

# Ticker regex: Binance/BingX/Bybit/OKX formats
# - $BTCUSDT, $ETHUSDT.P (BingX perp), $BTCUSDTPERP, $BTC.PERP
TICKER_RE = re.compile(
    r"\$?([A-Z]{2,12})(?:USDT|USDTPERP|USDT\.P|USDC|SUSDTP|\.PERP|PERP)\b",
    re.IGNORECASE,
)
DIRECTION_RE = re.compile(r"\b(long|short|buy|sell|beli|jual)\b", re.IGNORECASE)
SL_PCT_RE = re.compile(r"(?:sl|stop\s?loss)\D{0,24}?(\d+(?:[.,]\d+)?)\s*%", re.IGNORECASE)
ENTRY_RE = re.compile(r"entry\D{0,16}?(\d[\d.,]*)", re.IGNORECASE)
TP_RE = re.compile(r"(?:tp\s?\d*|target)\D{0,16}?(\d[\d.,]*)", re.IGNORECASE)


def _norm_ticker(raw: str) -> str | None:
    """Normalisasi ticker mempertahankan suffix .P (BingX perpetual).
    BTC -> BTCUSDT
    BTC.P -> BTC.P
    BTCUSDT -> BTCUSDT
    BTCUSDT.P -> BTCUSDT.P (BingX perp)
    """
    t = raw.upper()
    # Pertahankan suffix .P (BingX perpetual)
    if t.endswith(".P"):
        # BTC.P -> BTC.P atau BTCUSDT.P tetap
        if t.startswith("USDT") or "USDT" in t:
            return t
        return f"{t.replace('.P', '')}USDT.P"
    if t.endswith("USDT") or t.endswith("USDC") or t.endswith("PERP"):
        return t
    # Plain ticker (BTC, ETH, etc) -> asumsikan USDT spot
    return f"{t}USDT"


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def parse(text: str | None) -> dict:
    """Parse satu pesan. Return dict dengan ticker, direction, sl_pct, entry, tp, kind.
    kind: 'signal' kalau ada ticker + direction/SL/level, else 'chat'.
    """
    out: dict = {"ticker": None, "direction": None, "sl_pct": None,
                 "entry": None, "tp": None, "kind": "chat"}
    if not text:
        return out

    m = TICKER_RE.search(text)
    if m:
        out["ticker"] = _norm_ticker(m.group(0).lstrip("$"))

    d = DIRECTION_RE.search(text)
    if d:
        out["direction"] = d.group(1).lower()

    sl = SL_PCT_RE.search(text)
    if sl:
        try:
            val = _num(sl.group(1))
            if 0 < val <= 50:
                out["sl_pct"] = val
        except ValueError:
            pass

    e = ENTRY_RE.search(text)
    if e:
        out["entry"] = e.group(1)

    tps = TP_RE.findall(text)
    if tps:
        out["tp"] = ",".join(tps[:4])

    # Klasifikasi: signal butuh ticker + (arah ATAU SL%) ATAU ada level entry eksplisit
    strong = out["ticker"] and (out["direction"] or out["sl_pct"] is not None or out["entry"])
    out["kind"] = "signal" if strong else "chat"
    return out