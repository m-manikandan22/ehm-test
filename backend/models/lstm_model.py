"""
lstm_model.py — Lightweight LSTM for demand forecasting.

Architecture:
  Input:  sequence of (load, generation, weather) at 10 timesteps → shape (batch, 10, 3)
  LSTM:   2 layers, hidden_size=32
  Output: predicted next-step demand (scalar)

Training:
  Synthetic dataset is generated once at startup (500 samples).
  No GPU required — runs on CPU in <2 seconds.
"""

import numpy as np  # type: ignore
import torch  # type: ignore
import torch.nn as nn  # type: ignore
from sklearn.preprocessing import MinMaxScaler  # type: ignore
from typing import Optional


# -----------------------------------------------------------------------
# Model Definition
# -----------------------------------------------------------------------

class LSTMForecaster(nn.Module):
    """
    2-layer LSTM followed by a fully-connected head predicting next demand.
    """

    def __init__(self, input_size: int = 3, hidden_size: int = 32,
                 num_layers: int = 2, output_size: int = 1):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.1,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 16),
            nn.ReLU(),
            nn.Linear(16, output_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_size)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out, _ = self.lstm(x, (h0, c0))
        # Take only the last timestep's hidden state
        return self.fc(out[:, -1, :])


# -----------------------------------------------------------------------
# Dataset Generation
# -----------------------------------------------------------------------

def generate_synthetic_data(n_samples: int = 600, seq_len: int = 10):
    """
    Generate synthetic grid time-series data.

    Simulates a day-night load cycle with random noise and occasional spikes.
    Returns (X, y) where:
      X: (n_samples, seq_len, 3)  — [load, generation, weather]
      y: (n_samples,)             — next-step load
    """
    np.random.seed(42)
    t = np.linspace(0, 4 * np.pi, n_samples + seq_len)

    # Day-night load cycle
    base_load = 0.5 + 0.3 * np.sin(t) + 0.1 * np.random.randn(len(t))
    base_load = np.clip(base_load, 0.1, 1.5)

    # Generation follows solar pattern (peaks at midday)
    generation = 0.6 + 0.25 * np.cos(t + np.pi / 4) + 0.05 * np.random.randn(len(t))
    generation = np.clip(generation, 0.05, 1.2)

    # Weather proxy: random storms
    weather = np.zeros(len(t))
    storm_starts = np.random.randint(0, len(t) - 20, 5)
    for s in storm_starts:
        weather[s:s + 20] = np.random.uniform(0.6, 1.0)

    X_list, y_list = [], []
    for i in range(n_samples):
        window = np.stack([
            base_load[i:i + seq_len],
            generation[i:i + seq_len],
            weather[i:i + seq_len],
        ], axis=1)
        X_list.append(window)
        y_list.append(base_load[i + seq_len])

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.float32)
    return X, y


# -----------------------------------------------------------------------
# Training Helper
# -----------------------------------------------------------------------

def _load_csv_data(csv_path: str, seq_len: int):
    """
    Load a CSV with columns [timestamp, load, generation, weather]. Builds
    (X, y) tensors of shape (n, seq_len, 3) and (n,). NaN rows are dropped.
    """
    import csv
    rows: list[tuple[float, float, float]] = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                load_v = float(r["load"])
                gen_v  = float(r["generation"])
                w_v    = float(r.get("weather", 0.0) or 0.0)
            except (KeyError, ValueError, TypeError):
                continue
            rows.append((load_v, gen_v, w_v))
    if len(rows) < seq_len + 1:
        raise ValueError(
            f"CSV at {csv_path} has only {len(rows)} usable rows; "
            f"need at least {seq_len + 1}."
        )
    X_list, y_list = [], []
    for i in range(len(rows) - seq_len):
        win = rows[i:i + seq_len]
        X_list.append(np.array(win, dtype=np.float32))
        y_list.append(rows[i + seq_len][0])
    X = np.stack(X_list, axis=0)
    y = np.array(y_list, dtype=np.float32)
    return X, y


def train_lstm(model: LSTMForecaster, X: np.ndarray, y: np.ndarray,
               epochs: int = 30, lr: float = 1e-3) -> list:
    """
    Train the LSTM on synthetic data. Returns loss history.
    Designed to complete in <5 seconds on CPU.
    """
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    X_t = torch.tensor(X)
    y_t = torch.tensor(y).unsqueeze(1)

    losses = []
    for epoch in range(epochs):
        optimizer.zero_grad()
        pred = model(X_t)  # type: ignore
        loss = criterion(pred, y_t)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    return losses


# -----------------------------------------------------------------------
# Top-Level Manager
# -----------------------------------------------------------------------

class DemandForecaster:
    """
    High-level wrapper used by the API.
    - Generates synthetic training data at startup (or loads from CSV if provided)
    - Pre-trains the LSTM (fast, CPU-only)
    - Provides predict() for the /predict endpoint
    """

    SEQ_LEN = 10

    def __init__(self, csv_path: Optional[str] = None):  # type: ignore
        self.model = LSTMForecaster()
        self.scaler = MinMaxScaler()
        self.csv_path = csv_path
        self._pretrain(csv_path=csv_path)

    def _pretrain(self, csv_path: Optional[str] = None):  # type: ignore
        """Train the LSTM on synthetic data (or real CSV if provided) at startup.

        EHM-CRIT-005 fix: the scaler is now fit on the *training* split only
        (chronological 80/20 default) — never on the validation portion —
        so reported validation metrics reflect honest, leak-free scaling.
        """
        if csv_path:
            try:
                print(f"[LSTM] Loading real dataset from {csv_path}...")
                X, y = _load_csv_data(csv_path, seq_len=self.SEQ_LEN)
                print(f"[LSTM] Loaded {len(X)} windows from CSV.")
            except (FileNotFoundError, ValueError) as e:
                print(f"[LSTM] CSV load failed ({e}); falling back to synthetic.")
                X, y = generate_synthetic_data(n_samples=500, seq_len=self.SEQ_LEN)
        else:
            print("[LSTM] Generating synthetic dataset...")
            X, y = generate_synthetic_data(n_samples=500, seq_len=self.SEQ_LEN)

        # Chronological 80/20 split — train on the earlier portion of the
        # series, validate on the later portion. Scaler is fit on training
        # only and applied to both — no leakage (EHM-CRIT-005).
        n = len(X)
        if n < 2:
            raise ValueError(
                f"Need at least 2 samples for a chronological split; got {n}."
            )
        cut = max(1, int(0.8 * n))
        X_train, X_val = X[:cut], X[cut:]
        y_train, y_val = y[:cut], y[cut:]

        # Fit scaler on the training split only
        flat_train = X_train.reshape(-1, 3)
        self.scaler.fit(flat_train)

        X_train_norm = np.array([
            self.scaler.transform(x) for x in X_train
        ], dtype=np.float32)
        X_val_norm = np.array([
            self.scaler.transform(x) for x in X_val
        ], dtype=np.float32) if len(X_val) > 0 else X_train_norm[:0]

        print("[LSTM] Training on CPU (30 epochs)...")
        losses = train_lstm(self.model, X_train_norm, y_train, epochs=30)
        if len(X_val) > 0:
            from sklearn.metrics import mean_squared_error  # type: ignore
            with torch.no_grad():
                preds = self.model(torch.tensor(X_val_norm)).squeeze(-1).numpy()
            val_mse = float(mean_squared_error(y_val, preds))
            print(f"[LSTM] Training complete. Final loss: {losses[-1]:.6f}"
                  f" | chronological val MSE: {val_mse:.6f}"
                  f" (n_train={len(X_train)}, n_val={len(X_val)})")
        else:
            print(f"[LSTM] Training complete. Final loss: {losses[-1]:.6f}")
        self.model.eval()

    def predict(self, sequence: list) -> float:
        """
        Predict the next demand given a list of 10 [load, gen, weather] triples.

        Args:
            sequence: list of 10 lists, each [load, generation, weather]
        Returns:
            Predicted next load (float, unnormalised)
        """
        if len(sequence) < self.SEQ_LEN:
            sequence = [[0.5, 0.5, 0.0]] * (self.SEQ_LEN - len(sequence)) + sequence

        seq_arr = np.array(sequence[-self.SEQ_LEN:], dtype=np.float32)  # type: ignore
        seq_norm = self.scaler.transform(seq_arr)
        x_t = torch.tensor(seq_norm).unsqueeze(0)  # (1, 10, 3)

        with torch.no_grad():
            pred = self.model(x_t).item()  # type: ignore

        # Clamp to reasonable demand range
        return float(np.clip(pred, 0.05, 2.0))
