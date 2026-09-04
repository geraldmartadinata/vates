"""Test untuk services/bot_commands.py."""

import pytest

import services.analyzer as az
import services.bot_commands as bc


async def fake_analyze_up(session, ticker, period="2y"):
    return {
        "ticker": ticker,
        "insight": {
            "close": 5000.0, "sma_20": 4900.0, "rsi_14": 55.0,
            "macd_histogram": 2.0, "bb_upper": 5200.0, "bb_lower": 4800.0,
            "trend": "uptrend", "dist_to_bb_upper_pct": 0.04,
            "dist_to_bb_lower_pct": 0.04, "macd": 1.0,
        },
        "projection": {
            "horizons": [
                {"horizon_days": 1, "prob_up": 0.7, "expected_return_pct": 0.01,
                 "projected_close": 5050.0},
                {"horizon_days": 7, "prob_up": 0.7, "expected_return_pct": 0.03,
                 "projected_close": 5150.0},
                {"horizon_days": 30, "prob_up": 0.7, "expected_return_pct": 0.05,
                 "projected_close": 5250.0},
            ],
        },
        "verdict": {"verdict": "BUY", "confidence": "high", "reasons": ["ok"]},
        "raw": {"preds": [], "macd_hist": 2.0},
    }


async def fake_analyze_down(session, ticker, period="2y"):
    return {
        "ticker": ticker,
        "insight": {
            "close": 5000.0, "sma_20": 5100.0, "rsi_14": 40.0,
            "macd_histogram": -2.0, "bb_upper": 5200.0, "bb_lower": 4800.0,
            "trend": "downtrend", "dist_to_bb_upper_pct": 0.04,
            "dist_to_bb_lower_pct": 0.04, "macd": -1.0,
        },
        "projection": {
            "horizons": [
                {"horizon_days": 1, "prob_up": 0.3, "expected_return_pct": -0.01,
                 "projected_close": 4950.0},
                {"horizon_days": 7, "prob_up": 0.3, "expected_return_pct": -0.03,
                 "projected_close": 4850.0},
                {"horizon_days": 30, "prob_up": 0.3, "expected_return_pct": -0.05,
                 "projected_close": 4750.0},
            ],
        },
        "verdict": {"verdict": "SELL", "confidence": "high", "reasons": ["ok"]},
        "raw": {"preds": [], "macd_hist": -2.0},
    }


@pytest.mark.asyncio
async def test_cmd_analyze_returns_message():
    """Test /analyze BBCA return message + payload."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(az, "analyze_stock", fake_analyze_up)
        result = await bc.cmd_analyze(None, "BBCA")

    assert result["ok"] is True
    assert "BBCA" in result["message"]
    assert "BUY" in result["message"]
    assert "high" in result["message"]
    assert result["payload"]["verdict"]["verdict"] == "BUY"


@pytest.mark.asyncio
async def test_cmd_analyze_handles_error():
    """Test /analyze on broken ticker return ok=False."""

    async def broken_analyze(session, ticker, period="2y"):
        raise RuntimeError("network fail")

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(az, "analyze_stock", broken_analyze)
        result = await bc.cmd_analyze(None, "BROKEN")

    assert result["ok"] is False
    assert "gagal" in result["message"].lower() or "fail" in result["message"].lower()
    assert "network fail" in result["message"]


@pytest.mark.asyncio
async def test_cmd_screen_ranks_by_verdict():
    """Test /screen ranks BUY > SELL by score."""
    async def mixed_analyze(session, ticker, period="2y"):
        if ticker == "BBRI":
            return await fake_analyze_up(session, ticker, period)
        if ticker == "TLKM":
            return await fake_analyze_down(session, ticker, period)
        return await fake_analyze_up(session, ticker, period)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(az, "analyze_stock", mixed_analyze)
        result = await bc.cmd_screen(None, ["BBRI", "TLKM", "BBCA"])

    assert result["ok"] is True
    # BBRI/BBCA up, TLKM down — top should be up
    assert result["results"][0]["ticker"] in ("BBRI", "BBCA")
    # Last should be TLKM (SELL)
    assert result["results"][-1]["ticker"] == "TLKM"
    assert "Screen" in result["message"]


@pytest.mark.asyncio
async def test_cmd_screen_collects_errors():
    """Test /screen skip errors and report them."""
    async def selective(session, ticker, period="2y"):
        if ticker == "BAD":
            raise RuntimeError("not found")
        return await fake_analyze_up(session, ticker, period)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(az, "analyze_stock", selective)
        result = await bc.cmd_screen(None, ["BBCA", "BAD"])

    assert result["ok"] is True
    assert len(result["errors"]) == 1
    assert result["errors"][0]["ticker"] == "BAD"
