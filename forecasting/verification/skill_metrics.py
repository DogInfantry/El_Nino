"""Forecast skill metrics for ENSO prediction verification.

Deterministic forecast verification, lead-time aware, scored against a
persistence reference (the standard "can you beat naive?" benchmark for ENSO).
Kept dependency-light (numpy/pandas) so it runs anywhere; this mirrors the
core of what ``climpred``/``xskillscore`` provide for the gridded case.

Metrics
-------
RMSE  : root mean squared error (lower better)
MAE   : mean absolute error
ACC   : anomaly correlation coefficient. ONI is already an anomaly (climatology
        ~ 0), so ACC is the Pearson correlation between forecast and observed
        anomalies. Range [-1, 1]; > 0.5 is the usual "useful skill" line.
MSSS  : Mean Squared Skill Score vs a reference forecast,
        MSSS = 1 - MSE(forecast) / MSE(reference). > 0 beats the reference.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clean(obs: np.ndarray, pred: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    obs = np.asarray(obs, dtype=float)
    pred = np.asarray(pred, dtype=float)
    mask = np.isfinite(obs) & np.isfinite(pred)
    return obs[mask], pred[mask]


def rmse(obs, pred) -> float:
    """Root mean squared error."""
    o, p = _clean(obs, pred)
    if o.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean((p - o) ** 2)))


def mae(obs, pred) -> float:
    """Mean absolute error."""
    o, p = _clean(obs, pred)
    if o.size == 0:
        return float("nan")
    return float(np.mean(np.abs(p - o)))


def acc(obs, pred) -> float:
    """Anomaly correlation coefficient (Pearson r for anomaly inputs)."""
    o, p = _clean(obs, pred)
    if o.size < 2 or o.std() == 0 or p.std() == 0:
        return float("nan")
    return float(np.corrcoef(o, p)[0, 1])


def msss(obs, pred, reference) -> float:
    """Mean Squared Skill Score of ``pred`` vs ``reference`` (> 0 beats it)."""
    o, p = _clean(obs, pred)
    o2, r = _clean(obs, reference)
    if o.size == 0 or o2.size == 0:
        return float("nan")
    mse_f = np.mean((p - o) ** 2)
    mse_r = np.mean((r - o2) ** 2)
    if mse_r == 0:
        return float("nan")
    return float(1.0 - mse_f / mse_r)


def persistence_forecast(series: pd.Series, lead: int) -> pd.Series:
    """Persistence reference: value at t+lead predicted by value at t.

    Returns a series indexed like ``series`` holding the persistence prediction
    *for* each timestamp (i.e. shifted forward by ``lead``).
    """
    return series.shift(lead)


def skill_by_lead(
    backtest: pd.DataFrame,
    *,
    obs_col: str = "actual",
    pred_col: str = "pred",
    ref_col: str = "persistence",
    lead_col: str = "lead",
) -> pd.DataFrame:
    """Aggregate a long backtest frame into per-lead skill metrics.

    ``backtest`` must have one row per (origin, lead) with observed, model, and
    reference values. Returns one row per lead with RMSE, MAE, ACC, and MSSS
    (model vs reference) plus the reference RMSE for context.
    """
    rows = []
    for lead, grp in backtest.groupby(lead_col):
        rows.append(
            {
                "lead": int(lead),
                "n": int(grp[pred_col].notna().sum()),
                "rmse": rmse(grp[obs_col], grp[pred_col]),
                "mae": mae(grp[obs_col], grp[pred_col]),
                "acc": acc(grp[obs_col], grp[pred_col]),
                "rmse_persistence": rmse(grp[obs_col], grp[ref_col]),
                "msss_vs_persistence": msss(
                    grp[obs_col], grp[pred_col], grp[ref_col]
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("lead").reset_index(drop=True)
