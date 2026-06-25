"""PyTorch LSTM forecast of the ONI (Niño-3.4 anomaly).

A compact recurrent baseline to compare against SARIMA on identical terms: same
train/test split, same walk-forward origins, same skill harness. The model maps
a 24-month input window directly to a 12-month forecast (direct multi-horizon,
which avoids recursive error accumulation).

This is intentionally small (single LSTM layer, ~CPU-seconds to train) — the
dataset is short (~900 months) and the goal is an honest, reproducible ML
baseline, not a leaderboard CNN (that's the ERA5/Ham-2019 track, Phase 2b).

Outputs (under data/cache/)
---------------------------
``lstm_backtest.parquet`` : long frame (origin, lead, actual, pred, persistence)
``lstm_forecast.parquet`` : forward forecast (date, mean, lower, upper, model)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = _ROOT / "data" / "cache"
sys.path.insert(0, str(_ROOT / "forecasting" / "verification"))
from skill_metrics import skill_by_lead  # noqa: E402

logger = logging.getLogger(__name__)

WINDOW = 24
HORIZON = 12
SEED = 42


def get_oni_series(path: Path | None = None) -> pd.Series:
    """Load the ONI as a clean monthly (MS) series indexed by date."""
    path = path or CACHE_DIR / "oni.parquet"
    df = pd.read_parquet(path).sort_values("date")
    return pd.Series(
        df["oni"].to_numpy(), index=pd.DatetimeIndex(df["date"]), name="oni"
    ).asfreq("MS")


class LSTMForecaster(nn.Module):
    """Single-layer LSTM with a linear head emitting ``horizon`` steps."""

    def __init__(self, hidden: int = 64, horizon: int = HORIZON) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden, batch_first=True)
        self.head = nn.Linear(hidden, horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # x: (B, WINDOW, 1)
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])  # (B, horizon)


def _make_windows(
    values: np.ndarray, end_inclusive: int
) -> tuple[np.ndarray, np.ndarray]:
    """Build (X, y) sliding windows over ``values[: end_inclusive + 1]``."""
    xs, ys = [], []
    last = end_inclusive - HORIZON
    for t in range(WINDOW - 1, last + 1):
        xs.append(values[t - WINDOW + 1 : t + 1])
        ys.append(values[t + 1 : t + 1 + HORIZON])
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32)


def _train(
    model: nn.Module, X: torch.Tensor, y: torch.Tensor, *, epochs: int, lr: float
) -> None:
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    model.train()
    for epoch in range(epochs):
        opt.zero_grad()
        pred = model(X)
        loss = loss_fn(pred, y)
        loss.backward()
        opt.step()
        if logger.isEnabledFor(logging.INFO) and (epoch + 1) % 100 == 0:
            logger.info("epoch %d/%d  loss=%.5f", epoch + 1, epochs, loss.item())


def run(
    series: pd.Series,
    *,
    test_fraction: float = 0.3,
    hidden: int = 64,
    epochs: int = 400,
    lr: float = 0.01,
    origin_step: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on the first split, backtest on the rest. Return (backtest, forecast)."""
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    raw = series.to_numpy(dtype=np.float32)
    n = len(raw)
    test_start = int(n * (1 - test_fraction))

    # Standardize using TRAIN stats only (no leakage).
    mu, sd = raw[:test_start].mean(), raw[:test_start].std()
    z = (raw - mu) / sd

    X_np, y_np = _make_windows(z, end_inclusive=test_start - 1)
    X = torch.from_numpy(X_np).unsqueeze(-1)  # (B, WINDOW, 1)
    y = torch.from_numpy(y_np)
    model = LSTMForecaster(hidden=hidden)
    logger.info("Training LSTM on %d windows (%d epochs)...", len(X), epochs)
    _train(model, X, y, epochs=epochs, lr=lr)

    # Walk-forward backtest over identical origins to the ARIMA baseline.
    model.eval()
    rows: list[dict] = []
    last_origin = n - HORIZON - 1
    with torch.no_grad():
        for oi in range(test_start, last_origin + 1, origin_step):
            win = z[oi - WINDOW + 1 : oi + 1]
            xb = torch.from_numpy(win).view(1, WINDOW, 1)
            pred_z = model(xb).numpy().ravel()
            pred = pred_z * sd + mu
            origin_value = float(raw[oi])
            for lead in range(1, HORIZON + 1):
                rows.append(
                    {
                        "origin": series.index[oi],
                        "lead": lead,
                        "actual": float(raw[oi + lead]),
                        "pred": float(pred[lead - 1]),
                        "persistence": origin_value,
                    }
                )
    backtest = pd.DataFrame(rows)

    # Forward forecast from the final window; empirical intervals from backtest
    # RMSE per lead (no native LSTM uncertainty — honest residual-based band).
    with torch.no_grad():
        win = z[n - WINDOW : n]
        pred_z = model(torch.from_numpy(win).view(1, WINDOW, 1)).numpy().ravel()
    mean = pred_z * sd + mu
    per_lead_rmse = (
        skill_by_lead(backtest).set_index("lead")["rmse"].reindex(range(1, HORIZON + 1))
    )
    idx = pd.date_range(
        series.index[-1] + pd.offsets.MonthBegin(1), periods=HORIZON, freq="MS"
    )
    forecast = pd.DataFrame(
        {
            "date": idx,
            "mean": mean,
            "lower": mean - 1.645 * per_lead_rmse.to_numpy(),
            "upper": mean + 1.645 * per_lead_rmse.to_numpy(),
            "level": 90,
            "model": "LSTM",
        }
    )
    return backtest, forecast


def main() -> None:
    parser = argparse.ArgumentParser(description="LSTM ONI forecast + backtest.")
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--origin-step", type=int, default=1)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    series = get_oni_series()
    backtest, forecast = run(
        series, hidden=args.hidden, epochs=args.epochs, origin_step=args.origin_step
    )
    backtest.to_parquet(CACHE_DIR / "lstm_backtest.parquet", index=False)
    forecast.to_parquet(CACHE_DIR / "lstm_forecast.parquet", index=False)

    skill = skill_by_lead(backtest)
    print("LSTM skill by lead (vs persistence):")
    print(skill.to_string(index=False, float_format=lambda v: f"{v:6.3f}"))
    beats = (skill["msss_vs_persistence"] > 0).sum()
    print(f"\nBeats persistence at {beats}/{len(skill)} leads (MSSS > 0).")
    print("\nForward forecast (next months):")
    show = forecast.copy()
    show["date"] = show["date"].dt.strftime("%Y-%m")
    print(show[["date", "mean", "lower", "upper"]].to_string(
        index=False, float_format=lambda v: f"{v:+.2f}"))


if __name__ == "__main__":
    main()
