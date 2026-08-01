"""Test services/trainer.py — numpy logistic regression + walk-forward."""

import numpy as np
import pytest

from services.trainer import LogisticRegression, evaluate_walk_forward


def _separable_data(n=200, seed=7):
    """Dua kelas terpisah → model harus akurasi tinggi."""
    rng = np.random.default_rng(seed)
    X1 = rng.normal([-2, -2], 0.4, (n, 2))
    X2 = rng.normal([2, 2], 0.4, (n, 2))
    X = np.vstack([X1, X2])
    y = np.array([0] * n + [1] * n)
    return X, y


class TestLogisticRegression:
    def test_predict_shape(self):
        X, y = _separable_data()
        clf = LogisticRegression(epochs=1000).fit(X, y)
        pred = clf.predict(X)
        assert pred.shape == (len(X),)
        assert set(np.unique(pred)).issubset({0, 1})

    def test_separable_high_accuracy(self):
        X, y = _separable_data()
        clf = LogisticRegression(epochs=2000).fit(X, y)
        acc = np.mean(clf.predict(X) == y)
        assert acc > 0.9


class TestWalkForward:
    def test_returns_accuracy_and_model(self):
        X, y = _separable_data()
        acc, clf = evaluate_walk_forward(X, y, split=0.7)
        assert 0.0 <= acc <= 1.0
        assert hasattr(clf, "w_")

    def test_too_small_raises(self):
        X = np.zeros((5, 2))
        y = np.zeros(5)
        with pytest.raises(ValueError):
            evaluate_walk_forward(X, y, split=0.7)
