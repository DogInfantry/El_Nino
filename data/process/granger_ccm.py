"""Causal inference between the ONI and sector targets: Granger + CCM.

Correlation (see ``lag_correlator``) cannot establish direction. This module
adds two complementary causal tests:

Granger causality (linear, statsmodels)
    Tests whether past values of a *driver* improve prediction of a *target*
    beyond the target's own past. Requires (weakly) stationary inputs, so series
    are first-differenced. Null hypothesis: driver does NOT Granger-cause target.
    Reported per lag as the SSR F-statistic and its p-value (maxlag up to 24).

Convergent Cross Mapping (nonlinear, self-contained numpy/scipy)
    Better suited to weakly-coupled dynamical systems (climate/ecology) than
    Granger. Implemented here via Sugihara-style simplex projection rather than a
    compiled library, so it is deterministic and free of the multiprocessing
    that makes pyEDM brittle under a dashboard server. To test "A drives B", we
    use B's reconstructed state-space manifold to predict A: if A's signature is
    embedded in B, that cross-map skill (rho) *rises and converges* with library
    size — the causal signature. Results are returned with plain-language
    direction labels ("ONI->target" / "target->ONI").

Always pair these with the surrogate / "correlation != causation" caveats in the
UI; shared seasonality (ENSO phase-locking) can manufacture spurious skill.
"""

from __future__ import annotations

import logging
import warnings

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def make_stationary(
    series: pd.Series, *, log: bool = False, mode: str = "detrend"
) -> pd.Series:
    """Return a (weakly) stationary version of ``series``.

    mode="detrend" : remove a linear trend but KEEP low-frequency variation —
        preferred for ENSO coupling, which lives at multi-month/multi-year
        scales that first-differencing would filter out.
    mode="diff"    : first difference — stricter stationarity, but a high-pass
        filter that suppresses the ENSO-band signal.
    Optionally takes logs first (for prices).
    """
    s = series.astype(float)
    if log:
        s = np.log(s.where(s > 0))
    s = s.dropna()
    if mode == "diff":
        return s.diff().dropna()
    # linear detrend, preserving index
    values = s.to_numpy()
    x = np.arange(len(values), dtype=float)
    slope, intercept = np.polyfit(x, values, 1)
    return pd.Series(values - (slope * x + intercept), index=s.index, name=series.name)


def align(driver: pd.Series, target: pd.Series) -> pd.DataFrame:
    """Inner-join two monthly series into a 2-column frame on shared dates."""
    df = pd.concat(
        [driver.rename("driver"), target.rename("target")], axis=1
    ).dropna()
    return df


def granger_pvalues(
    target: pd.Series, driver: pd.Series, *, maxlag: int = 24
) -> pd.DataFrame:
    """Per-lag Granger test for H0: ``driver`` does not Granger-cause ``target``.

    Inputs should already be stationary. Returns columns [lag, f_stat, p_value].
    """
    from statsmodels.tsa.stattools import grangercausalitytests

    df = align(driver, target)
    # statsmodels expects [target, driver] ordering: 2nd col tests causing 1st.
    data = df[["target", "driver"]].to_numpy()
    rows: list[dict] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = grangercausalitytests(data, maxlag=maxlag, verbose=False)
        except TypeError:  # newer statsmodels dropped the verbose kwarg
            res = grangercausalitytests(data, maxlag=maxlag)
    for lag, (stats, _) in res.items():
        f_stat, p_value = stats["ssr_ftest"][0], stats["ssr_ftest"][1]
        rows.append({"lag": int(lag), "f_stat": float(f_stat), "p_value": float(p_value)})
    return pd.DataFrame(rows)


def _embed(x: np.ndarray, E: int, tau: int) -> tuple[np.ndarray, np.ndarray]:
    """Time-delay embedding. Returns (manifold points (m, E), their time indices)."""
    start = (E - 1) * tau
    n = len(x)
    idx = np.arange(start, n)
    cols = [x[idx - i * tau] for i in range(E)]
    return np.column_stack(cols), idx


def _cross_map_skill(
    source: np.ndarray,
    target_vals: np.ndarray,
    *,
    E: int,
    tau: int,
    lib_size: int,
    n_pred: int = 200,
    rng: np.random.Generator | None = None,
) -> float:
    """Simplex cross-map: predict ``target_vals`` from ``source``'s manifold.

    High skill means the source's state space encodes the target — i.e. the
    target *drives* the source. Returns Pearson rho of predicted vs actual.
    """
    from scipy.spatial import cKDTree

    rng = rng or np.random.default_rng(0)
    manifold, idx = _embed(source, E, tau)
    m = len(manifold)
    if lib_size > m:
        lib_size = m
    lib_rows = rng.choice(m, size=lib_size, replace=False)
    lib_pts, lib_idx = manifold[lib_rows], idx[lib_rows]

    pred_rows = rng.choice(m, size=min(n_pred, m), replace=False)
    tree = cKDTree(lib_pts)
    k = E + 1
    # +1 neighbor in case the point itself is in the library (excluded below).
    dist, nn = tree.query(manifold[pred_rows], k=min(k + 1, lib_size))
    dist = np.atleast_2d(dist)
    nn = np.atleast_2d(nn)

    preds, actuals = [], []
    for r, prow in enumerate(pred_rows):
        d, neigh = dist[r], nn[r]
        keep = lib_idx[neigh] != idx[prow]  # exclude self-match
        d, neigh = d[keep][:k], neigh[keep][:k]
        if len(d) < 2:
            continue
        d0 = d[0] if d[0] > 0 else 1e-9
        w = np.exp(-d / d0)
        w /= w.sum()
        pred = float(np.dot(w, target_vals[lib_idx[neigh]]))
        preds.append(pred)
        actuals.append(target_vals[idx[prow]])
    if len(preds) < 3:
        return float("nan")
    preds, actuals = np.asarray(preds), np.asarray(actuals)
    if preds.std() == 0 or actuals.std() == 0:
        return float("nan")
    return float(np.corrcoef(preds, actuals)[0, 1])


def ccm_convergence(
    driver: pd.Series,
    target: pd.Series,
    *,
    E: int = 3,
    tau: int = 1,
    lib_steps: int = 10,
    seed: int = 0,
) -> pd.DataFrame:
    """Cross-map skill vs library size for both causal directions.

    Returns long frame [lib_size, rho, direction] with direction labels
    "ONI->target" (evidence ONI drives the commodity) and "target->ONI".
    """
    df = align(driver, target)
    d = df["driver"].to_numpy(dtype=float)
    t = df["target"].to_numpy(dtype=float)
    n = len(d)
    lib_max = n - (E - 1) * tau
    if lib_max < 25:
        raise ValueError("Series too short for CCM after embedding.")
    libs = np.unique(np.linspace(20, lib_max, lib_steps, dtype=int))
    rng = np.random.default_rng(seed)

    rows: list[dict] = []
    for L in libs:
        # target's manifold predicts ONI  -> evidence ONI drives target
        rho_oni_drives = _cross_map_skill(t, d, E=E, tau=tau, lib_size=int(L), rng=rng)
        # ONI's manifold predicts target  -> evidence target drives ONI
        rho_tgt_drives = _cross_map_skill(d, t, E=E, tau=tau, lib_size=int(L), rng=rng)
        rows.append({"lib_size": int(L), "rho": rho_oni_drives, "direction": "ONI->target"})
        rows.append({"lib_size": int(L), "rho": rho_tgt_drives, "direction": "target->ONI"})
    return pd.DataFrame(rows)


def analyze(
    oni: pd.Series,
    commodity: pd.Series,
    *,
    maxlag: int = 24,
    log_price: bool = True,
    mode: str = "detrend",
) -> dict[str, pd.DataFrame]:
    """Full causal panel for one commodity. Returns dict of result frames."""
    oni_s = make_stationary(oni, log=False, mode=mode)
    com_s = make_stationary(commodity, log=log_price, mode=mode)

    granger_oni_to_com = granger_pvalues(com_s, oni_s, maxlag=maxlag)
    granger_com_to_oni = granger_pvalues(oni_s, com_s, maxlag=maxlag)

    result = {
        "granger_oni_to_target": granger_oni_to_com,
        "granger_target_to_oni": granger_com_to_oni,
    }
    try:
        result["ccm"] = ccm_convergence(oni_s, com_s)
    except Exception as exc:  # noqa: BLE001 - CCM is best-effort
        logger.warning("CCM failed: %s", exc)
        result["ccm"] = pd.DataFrame(columns=["lib_size", "rho", "direction"])
    return result
