"""Baseline classifier — logistic regression (numpy, no sklearn) + walk-forward.

LogisticRegression.fit menerima (X, y) mentah; standardisasi dilakukan internal.
"""

import numpy as np


class LogisticRegression:
    def __init__(self, lr: float = 0.1, epochs: int = 2000):
        self.lr = lr
        self.epochs = epochs

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1, 1)

        self.mu_ = X.mean(axis=0)
        self.sd_ = X.std(axis=0) + 1e-9
        Xn = (X - self.mu_) / self.sd_
        Xn = np.hstack([np.ones((len(Xn), 1)), Xn])

        w = np.zeros((Xn.shape[1], 1))
        for _ in range(self.epochs):
            p = 1.0 / (1.0 + np.exp(-(Xn @ w)))
            grad = Xn.T @ (p - y) / len(Xn)
            w -= self.lr * grad
        self.w_ = w
        return self

    def predict_proba(self, X) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        Xn = (X - self.mu_) / self.sd_
        Xn = np.hstack([np.ones((len(Xn), 1)), Xn])
        return (1.0 / (1.0 + np.exp(-(Xn @ self.w_)))).ravel()

    def predict(self, X) -> np.ndarray:
        return (self.predict_proba(X) > 0.5).astype(int)


def evaluate_walk_forward(
    X,
    y,
    split: float = 0.7,
    lr: float = 0.1,
    epochs: int = 2000,
) -> tuple[float, LogisticRegression]:
    """Train pada 70% data awal, evaluasi akurasi pada 30% terakhir.

    Returns:
        (accuracy, fitted_model).
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    n = int(len(X) * split)
    if n < 10:
        raise ValueError("Terlalu sedikit data untuk walk-forward split")

    clf = LogisticRegression(lr=lr, epochs=epochs).fit(X[:n], y[:n])
    pred = clf.predict(X[n:])
    accuracy = float(np.mean(pred == y[n:]))
    return accuracy, clf
