"""Lagged cross-correlation between the ONI and sector target series.

ENSO impacts on commodities are *lagged* — agricultural price/yield effects
typically trail the ONI peak by 6–24 months (drought → supply shock → price).
This module computes the cross-correlation function (CCF) of a driver (ONI)
against one or many targets (commodity prices) across a range of forward lags.

Methodology (see project causation framework)
---------------------------------------------
1. Both series are linearly *detrended* by default to strip the secular trend
   (warming SSTs, long-run commodity inflation) that would otherwise inflate a
   spurious correlation.
2. For each lag L (0..max_lag months) we correlate driver[t] with target[t+L];
   a positive L therefore means the ONI *leads* the commodity by L months.
3. Pearson r is reported only where the overlapping sample exceeds a minimum
   length, else NaN.

This is correlation, NOT causation — Granger / CCM tests (Phase 2) are required
to argue direction. The dashboard surfaces that caveat explicitly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_OVERLAP = 24  # months required for a correlation to be reported


def detrend(series: pd.Series) -> pd.Series:
    """Linearly detrend a series, preserving its index and NaN positions."""
    s = series.astype(float)
    values = s.to_numpy()
    x = np.arange(len(s), dtype=float)
    mask = ~np.isnan(values)
    if mask.sum() < 3:
        return s - np.nanmean(values)
    slope, intercept = np.polyfit(x[mask], values[mask], 1)
    trend = slope * x + intercept
    return pd.Series(values - trend, index=s.index, name=series.name)


def lagged_cross_correlation(
    driver: pd.Series,
    target: pd.Series,
    *,
    max_lag: int = 24,
    do_detrend: bool = True,
    min_overlap: int = MIN_OVERLAP,
) -> pd.Series:
    """Return Pearson r at each forward lag 0..``max_lag`` (index = lag months).

    Positive lag => ``driver`` leads ``target`` by that many months.
    Both series should be indexed by a monthly :class:`~pandas.DatetimeIndex`.
    """
    joined = pd.concat(
        [driver.rename("driver"), target.rename("target")], axis=1
    ).sort_index()
    if do_detrend:
        joined["driver"] = detrend(joined["driver"])
        joined["target"] = detrend(joined["target"])

    results: dict[int, float] = {}
    for lag in range(0, max_lag + 1):
        shifted = joined["target"].shift(-lag)
        pair = pd.concat([joined["driver"], shifted], axis=1).dropna()
        if len(pair) >= min_overlap:
            results[lag] = float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
        else:
            results[lag] = np.nan
    return pd.Series(results, name="r").rename_axis("lag")


def correlation_matrix(
    driver: pd.Series,
    targets_wide: pd.DataFrame,
    *,
    max_lag: int = 24,
    do_detrend: bool = True,
) -> pd.DataFrame:
    """Cross-correlation for many targets at once.

    Returns a long DataFrame with columns ``[target, lag, r]`` — tidy for Altair.
    """
    rows: list[pd.DataFrame] = []
    for col in targets_wide.columns:
        ccf = lagged_cross_correlation(
            driver, targets_wide[col], max_lag=max_lag, do_detrend=do_detrend
        )
        rows.append(
            pd.DataFrame({"target": col, "lag": ccf.index, "r": ccf.to_numpy()})
        )
    return pd.concat(rows, ignore_index=True)


def peak_lags(matrix_long: pd.DataFrame) -> pd.DataFrame:
    """For each target, the lag with the largest |r| (the dominant lead time)."""
    out = []
    for target, grp in matrix_long.dropna(subset=["r"]).groupby("target"):
        idx = grp["r"].abs().idxmax()
        peak = grp.loc[idx]
        out.append(
            {
                "target": target,
                "peak_lag": int(peak["lag"]),
                "peak_r": round(float(peak["r"]), 3),
            }
        )
    return pd.DataFrame(out).sort_values("peak_r", key=lambda s: s.abs(), ascending=False)
