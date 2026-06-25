"""SARIMA baseline forecast of the ONI (Niño-3.4 anomaly).

A statistical baseline every ML model must beat. We fit a SARIMAX model on the
monthly ONI series and evaluate it pseudo-out-of-sample with a walk-forward
backtest across forecast leads 1–12 months, scored against persistence.

Why SARIMAX
-----------
ONI is near-stationary (it is already an anomaly) and strongly autocorrelated
with mild seasonal phase-locking (events tend to peak in NH winter). A low-order
SARIMA captures that persistence cheaply and provides calibrated prediction
intervals for the forecast fan chart (dashboard page 03).

Efficiency
----------
Parameters are estimated once on the training span; each backtest origin then
reuses those parameters via ``SARIMAXResults.apply`` (Kalman filter on the
history up to that origin, no re-estimation) — fast and leak-free.

Outputs (under data/cache/)
---------------------------
``arima_backtest.parquet`` : long frame (origin, lead, actual, pred, persistence)
``arima_forecast.parquet`` : forward forecast (date, mean, lower, upper, level)
"""

from __future__ import annotations

import argparse
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = _ROOT / "data" / "cache"
sys.path.insert(0, str(_ROOT / "forecasting" / "verification"))
from skill_metrics import skill_by_lead  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_ORDER = (2, 0, 1)
DEFAULT_SEASONAL = (1, 0, 0, 12)
MAX_LEAD = 12


def get_oni_series(path: Path | None = None) -> pd.Series:
    """Load the ONI as a clean monthly (MS) series indexed by date."""
    path = path or CACHE_DIR / "oni.parquet"
    df = pd.read_parquet(path).sort_values("date")
    s = pd.Series(df["oni"].to_numpy(), index=pd.DatetimeIndex(df["date"]), name="oni")
    return s.asfreq("MS")


def fit_sarimax(
    series: pd.Series,
    *,
    order: tuple[int, int, int] = DEFAULT_ORDER,
    seasonal_order: tuple[int, int, int, int] = DEFAULT_SEASONAL,
):
    """Fit a SARIMAX model and return the fitted results object."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = SARIMAX(
            series,
            order=order,
            seasonal_order=seasonal_order,
            trend="n",
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        return model.fit(disp=False)


def backtest(
    series: pd.Series,
    *,
    order=DEFAULT_ORDER,
    seasonal_order=DEFAULT_SEASONAL,
    max_lead: int = MAX_LEAD,
    test_fraction: float = 0.3,
    origin_step: int = 1,
) -> pd.DataFrame:
    """Walk-forward backtest. Returns long frame (origin, lead, actual, pred, persistence)."""
    n = len(series)
    test_start = int(n * (1 - test_fraction))
    train = series.iloc[:test_start]
    fitted = fit_sarimax(train, order=order, seasonal_order=seasonal_order)
    logger.info(
        "Fitted SARIMAX%s x %s on %d train obs; backtesting %d test origins.",
        order, seasonal_order, len(train), (n - test_start - max_lead),
    )

    rows: list[dict] = []
    last_origin = n - max_lead - 1
    for oi in range(test_start, last_origin + 1, origin_step):
        history = series.iloc[: oi + 1]
        origin_date = series.index[oi]
        origin_value = float(series.iloc[oi])  # persistence baseline
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = fitted.apply(history, refit=False)
            fc = res.forecast(steps=max_lead)
        for lead in range(1, max_lead + 1):
            actual = float(series.iloc[oi + lead])
            rows.append(
                {
                    "origin": origin_date,
                    "lead": lead,
                    "actual": actual,
                    "pred": float(fc.iloc[lead - 1]),
                    "persistence": origin_value,
                }
            )
    return pd.DataFrame(rows)


def forecast_future(
    series: pd.Series,
    *,
    steps: int = MAX_LEAD,
    order=DEFAULT_ORDER,
    seasonal_order=DEFAULT_SEASONAL,
    alpha: float = 0.1,
) -> pd.DataFrame:
    """Forecast ``steps`` months ahead with (1-alpha) prediction intervals."""
    fitted = fit_sarimax(series, order=order, seasonal_order=seasonal_order)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pred = fitted.get_forecast(steps=steps)
    ci = pred.conf_int(alpha=alpha)
    idx = pd.date_range(
        series.index[-1] + pd.offsets.MonthBegin(1), periods=steps, freq="MS"
    )
    return pd.DataFrame(
        {
            "date": idx,
            "mean": pred.predicted_mean.to_numpy(),
            "lower": ci.iloc[:, 0].to_numpy(),
            "upper": ci.iloc[:, 1].to_numpy(),
            "level": int((1 - alpha) * 100),
            "model": "SARIMA",
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="SARIMA ONI baseline + backtest.")
    parser.add_argument("--max-lead", type=int, default=MAX_LEAD)
    parser.add_argument("--test-fraction", type=float, default=0.3)
    parser.add_argument("--origin-step", type=int, default=1)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    series = get_oni_series()
    bt = backtest(
        series,
        max_lead=args.max_lead,
        test_fraction=args.test_fraction,
        origin_step=args.origin_step,
    )
    bt.to_parquet(CACHE_DIR / "arima_backtest.parquet", index=False)

    fc = forecast_future(series, steps=args.max_lead)
    fc.to_parquet(CACHE_DIR / "arima_forecast.parquet", index=False)

    skill = skill_by_lead(bt)
    print("SARIMA skill by lead (vs persistence):")
    print(skill.to_string(index=False, float_format=lambda v: f"{v:6.3f}"))
    beats = (skill["msss_vs_persistence"] > 0).sum()
    print(f"\nBeats persistence at {beats}/{len(skill)} leads (MSSS > 0).")
    print("\nForward forecast (next months):")
    show = fc.copy()
    show["date"] = show["date"].dt.strftime("%Y-%m")
    print(show[["date", "mean", "lower", "upper"]].to_string(
        index=False, float_format=lambda v: f"{v:+.2f}"))


if __name__ == "__main__":
    main()
