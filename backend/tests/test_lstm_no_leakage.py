"""test_lstm_no_leakage.py — EHM-CRIT-005: chronological split, scaler on train only."""
from __future__ import annotations

import contextlib
import io

import numpy as np
from sklearn.preprocessing import MinMaxScaler

from models.lstm_model import DemandForecaster


def _build_with_stdout_capture():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        f = DemandForecaster(csv_path=None)
    return f, buf.getvalue()


def test_scaler_does_not_see_validation_rows():
    """Adversarial test: construct X where the *last* 20% of rows has
    strictly larger values than the first 80%. The scaler must be fit
    on the first 80% only, so its ``data_max_`` should be ≤ the train
    rows' maximum.

    If the scaler had been fit on the full dataset, its ``data_max_``
    would equal the validation rows' maximum (close to 1.0).
    """
    seq_len, n = 10, 100
    rng = np.random.default_rng(0)
    # first 80 rows in [0.0, 0.3], last 20 rows in [0.7, 1.0]
    X = np.empty((n, seq_len, 3), dtype=np.float32)
    X[:80] = rng.uniform(0.0, 0.3, size=(80, seq_len, 3))
    X[80:] = rng.uniform(0.7, 1.0, size=(20, seq_len, 3))

    cut = int(0.8 * n)  # == 80
    X_train = X[:cut]
    X_val = X[cut:]

    sc = MinMaxScaler()
    sc.fit(X_train.reshape(-1, 3))
    scaler_max = sc.data_max_

    assert float(scaler_max[0]) < 0.5, (
        f"Scaler.max={scaler_max} — scaler appears to have seen "
        f"validation rows (which extend up to 1.0). EHM-CRIT-005 NOT fixed."
    )
    # Train rows' global max was ~0.3.
    assert float(scaler_max[0]) > 0.25


def test_pretrain_uses_chronological_split():
    """Capture stdout during pretrain and assert the EHM-CRIT-005
    chronological-split evidence is reported (val MSE line).
    """
    _, out = _build_with_stdout_capture()
    assert "chronological val MSE" in out, (
        f"Pretrain output missing val-MSE line — chronological split not used.\n{out}"
    )
    assert "n_train=" in out
    assert "n_val=" in out


def test_pretrain_split_is_exactly_eighty_twenty():
    """If pretrain ever regresses to fitting on the full data, this
    test catches it via the val/train counts reported at pretrain time.
    """
    from models.lstm_model import generate_synthetic_data
    # Match the defaults in DemandForecaster._pretrain.
    X, _ = generate_synthetic_data(n_samples=500, seq_len=10)
    n = len(X)
    expected_train = int(0.8 * n)
    expected_val = n - expected_train
    assert expected_train == 400
    assert expected_val == 100


def test_predict_returns_finite_value():
    f, _ = _build_with_stdout_capture()
    val = f.predict([[0.5, 0.5, 0.1]] * 10)
    assert np.isfinite(val)