"""Test services/labels.py — forward returns & binary labels."""

import numpy as np
import pandas as pd
import pytest

from services.labels import add_forward_labels


def _frame(closes):
    return pd.DataFrame(
        {"date": pd.date_range("2026-01-01", periods=len(closes), freq="D"), "close": closes}
    )


class TestForwardLabels:
    def test_fwd_ret_1d(self):
        df = add_forward_labels(_frame([100, 110, 99]))
        assert df["fwd_ret_1d"].iloc[0] == pytest.approx(0.10)
        assert np.isnan(df["fwd_ret_1d"].iloc[-1])

    def test_labels_up_down(self):
        df = add_forward_labels(_frame([100, 110, 99]))
        assert df["label_1d"].iloc[0] == 1  # naik → up
        assert df["label_1d"].iloc[1] == 0  # turun → down

    def test_30d_label(self):
        closes = list(range(100, 140))  # naik linear 40 hari
        df = add_forward_labels(_frame(closes))
        assert df["label_30d"].iloc[0] == 1
        assert np.isnan(df["fwd_ret_30d"].iloc[-30:]).all()

    def test_sorted_input(self):
        df = _frame([100, 90, 110])[::-1].reset_index(drop=True)
        out = add_forward_labels(df)
        assert out["date"].is_monotonic_increasing
        assert out["fwd_ret_1d"].iloc[0] == pytest.approx(-0.10)
