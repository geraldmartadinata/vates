"""Tests for ihsg_tickers.py and universe_fetch.py."""
import pytest
from services.crypto.ihsg_tickers import TICKERS, COMPOSITE


def test_tickers_non_empty():
    assert len(TICKERS) > 0


def test_tickers_max_50():
    """Universe capped at 50 for first version (avoid rate limit)."""
    assert len(TICKERS) <= 50


def test_tickers_unique():
    assert len(TICKERS) == len(set(TICKERS))


def test_ticker_format_4_letter():
    """Each ticker should be 4-letter pure alpha (IHSG convention)."""
    for t in TICKERS:
        assert t.isalpha() and len(t) == 4, f"Invalid: {t}"


def test_composite():
    assert COMPOSITE == "^JKSE"


def test_includes_banks():
    """Most liquid IHSG banks should be included."""
    bank_list = ["BBCA", "BBRI", "BMRI", "BBNI"]
    for b in bank_list:
        assert b in TICKERS, f"{b} missing"


def test_normalize_compat():
    """All tickers should normalize via data_engine.normalize_ticker()."""
    from services.data_engine import normalize_ticker
    for t in TICKERS:
        n = normalize_ticker(t)
        assert n.endswith(".JK"), f"{t} -> {n}"
