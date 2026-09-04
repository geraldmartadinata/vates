"""Test untuk parser v2 (BingX .P support)."""
import parser as psr


def test_basic_binance():
    """Binance format: BTCUSDT -> BTCUSDT"""
    out = psr.parse("Long BTCUSDT SL 2%")
    assert out["ticker"] == "BTCUSDT"
    assert out["direction"] == "long"
    assert out["sl_pct"] == 2.0
    assert out["kind"] == "signal"


def test_bingx_perpetual_dot_p():
    """BingX perpetual: HBARUSDT.P -> HBARUSDT.P"""
    out = psr.parse("Long HBARUSDT.P entry 0.5 SL 3%")
    assert out["ticker"] == "HBARUSDT.P", f"got {out['ticker']!r}"
    assert out["direction"] == "long"
    assert out["sl_pct"] == 3.0
    assert out["kind"] == "signal"


def test_plain_ticker():
    """Plain: BTC -> BTCUSDT"""
    out = psr.parse("BELI BTC di 60000 SL 2%")
    assert out["ticker"] == "BTCUSDT"
    assert out["direction"] == "beli"
    assert out["kind"] == "signal"


def test_plain_ticker_dot_p():
    """BingX plain with .P: BTC.P -> BTCUSDT.P"""
    out = psr.parse("Short BTC.P entry 65000")
    assert out["ticker"] == "BTCUSDT.P", f"got {out['ticker']!r}"
    assert out["direction"] == "short"


def test_xauusdt():
    """XAU (gold) ticker."""
    out = psr.parse("XAUUSDT long entry 2400")
    assert out["ticker"] == "XAUUSDT"


def test_hypeusdt_dot_p():
    """Hyperliquid BingX: HYPEUSDT.P"""
    out = psr.parse("$HYPEUSDT.P LONG SL 5%")
    assert out["ticker"] == "HYPEUSDT.P", f"got {out['ticker']!r}"
    assert out["direction"] == "long"


def test_no_signal_text():
    """Chat biasa tanpa ticker -> kind=chat"""
    out = psr.parse("halo semua, gimana kabarnya?")
    assert out["kind"] == "chat"
    assert out["ticker"] is None


def test_entry_extraction():
    """Entry + TP multi-level."""
    out = psr.parse("BTCUSDT long entry 65000 TP 66000 67000 68000 SL 2%")
    assert out["entry"] == "65000"
    assert "66000" in out["tp"]
    assert out["kind"] == "signal"


def test_usdt_p_dot_only():
    """Edge case: .P already at end with USDT prefix"""
    out = psr.parse("JUAL ENAUSDT.P di 1.5 SL 3%")
    assert out["ticker"] == "ENAUSDT.P", f"got {out['ticker']!r}"


def test_jasmyusdt_dot_p():
    """JASMY BingX perpetual"""
    out = psr.parse("JASMYUSDT.P buy entry 0.025")
    assert out["ticker"] == "JASMYUSDT.P", f"got {out['ticker']!r}"
    assert out["direction"] == "buy"
