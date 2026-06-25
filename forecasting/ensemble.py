"""Combine the SARIMA and LSTM ONI forecasts into an ensemble.

Model averaging is a cheap, robust way to improve forecasts and — more
importantly for this platform — to *quantify disagreement*. We:

1. Merge the two models' walk-forward backtests on (origin, lead), average their
   predictions, and score the ensemble through the shared skill harness.
2. Build a consolidated forward forecast stacking SARIMA, LSTM, and the
   ensemble, where the ensemble interval is the *envelope* of the members
   (min lower / max upper) so it reflects total model + parametric uncertainty.

Consolidated outputs (under data/cache/) feed the forecast dashboard directly:
``skill_all.parquet``     : per-model, per-lead skill (rmse, mae, acc, msss)
``forecasts_all.parquet`` : per-model forward forecast (date, mean, lower, upper)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = _ROOT / "data" / "cache"
sys.path.insert(0, str(_ROOT / "forecasting" / "verification"))
from skill_metrics import skill_by_lead  # noqa: E402

logger = logging.getLogger(__name__)


def build_ensemble_backtest(arima_bt: pd.DataFrame, lstm_bt: pd.DataFrame) -> pd.DataFrame:
    """Average the two backtests on shared (origin, lead) cells."""
    # Key only on (origin, lead): actual/persistence differ in float precision
    # across models (LSTM uses float32), which would break a value-based join.
    merged = arima_bt.merge(
        lstm_bt[["origin", "lead", "pred"]],
        on=["origin", "lead"],
        suffixes=("_arima", "_lstm"),
        how="inner",
    )
    merged["pred"] = merged[["pred_arima", "pred_lstm"]].mean(axis=1)
    logger.info("Ensemble backtest: %d shared (origin, lead) cells.", len(merged))
    return merged[["origin", "lead", "actual", "pred", "persistence"]]


def build_ensemble_forecast(
    arima_fc: pd.DataFrame, lstm_fc: pd.DataFrame
) -> pd.DataFrame:
    """Average member means; widen interval to the member envelope."""
    m = arima_fc.merge(lstm_fc, on="date", suffixes=("_arima", "_lstm"))
    return pd.DataFrame(
        {
            "date": m["date"],
            "mean": m[["mean_arima", "mean_lstm"]].mean(axis=1),
            "lower": m[["lower_arima", "lower_lstm"]].min(axis=1),
            "upper": m[["upper_arima", "upper_lstm"]].max(axis=1),
            "level": 90,
            "model": "Ensemble",
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ARIMA+LSTM ensemble.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    arima_bt = pd.read_parquet(CACHE_DIR / "arima_backtest.parquet")
    lstm_bt = pd.read_parquet(CACHE_DIR / "lstm_backtest.parquet")
    arima_fc = pd.read_parquet(CACHE_DIR / "arima_forecast.parquet")
    lstm_fc = pd.read_parquet(CACHE_DIR / "lstm_forecast.parquet")

    ens_bt = build_ensemble_backtest(arima_bt, lstm_bt)
    ens_fc = build_ensemble_forecast(arima_fc, lstm_fc)

    # Consolidated, per-model skill table.
    skill_frames = []
    for name, bt in (("SARIMA", arima_bt), ("LSTM", lstm_bt), ("Ensemble", ens_bt)):
        sk = skill_by_lead(bt)
        sk.insert(0, "model", name)
        skill_frames.append(sk)
    skill_all = pd.concat(skill_frames, ignore_index=True)
    skill_all.to_parquet(CACHE_DIR / "skill_all.parquet", index=False)

    # Consolidated forward forecasts.
    forecasts_all = pd.concat([arima_fc, lstm_fc, ens_fc], ignore_index=True)
    forecasts_all.to_parquet(CACHE_DIR / "forecasts_all.parquet", index=False)

    # Report: mean ACC and skill-vs-persistence by model.
    summary = (
        skill_all.groupby("model")
        .agg(
            acc_mean=("acc", "mean"),
            msss_mean=("msss_vs_persistence", "mean"),
            leads_beating_persistence=(
                "msss_vs_persistence", lambda s: int((s > 0).sum())
            ),
        )
        .reindex(["SARIMA", "LSTM", "Ensemble"])
    )
    print("Model comparison (mean over leads 1–12):")
    print(summary.to_string(float_format=lambda v: f"{v:6.3f}"))
    print("\nSaved: skill_all.parquet, forecasts_all.parquet")


if __name__ == "__main__":
    main()
