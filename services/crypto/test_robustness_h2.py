"""Sanity test untuk robustness_h2.py."""
import robustness_h2 as rh2


def test_neighbor_grid_returns_list():
    res = rh2.neighbor_grid("LTC-USD", {"N": [12], "K": [3], "RR": [3.0]})
    assert isinstance(res, list)
    assert len(res) > 0
    assert "N" in res[0]


def test_rolling_walk_forward():
    res = rh2.rolling_walk_forward("LTC-USD", 3)
    assert isinstance(res, list)
    assert len(res) == 3


def test_regime_split():
    res = rh2.regime_split("LTC-USD")
    assert "up" in res or "down" in res
