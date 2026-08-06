"""Unit tests for the pure (network-free) core logic.

Run either way::

    python tests/test_core.py        # no extra deps
    pytest tests/test_core.py        # if pytest installed
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "data" / "process"))
sys.path.insert(0, str(_ROOT / "data" / "ingest"))
sys.path.insert(0, str(_ROOT / "forecasting" / "verification"))

from enso_phase_labeler import (  # noqa: E402
    classify_intensity,
    event_summary,
    label_phases,
    simple_phase,
)
from lag_correlator import (  # noqa: E402
    detrend,
    lagged_cross_correlation,
)
from granger_ccm import ccm_convergence  # noqa: E402
from weekly_nino34 import parse_weekly  # noqa: E402
from source_registry import Source, _status  # noqa: E402
from positioning import (  # noqa: E402
    DIVERGENCE_TOL,
    IMPACT_FLOOR,
    conviction,
    regime_label,
    stance,
)
from skill_metrics import acc, msss, rmse, skill_by_lead  # noqa: E402


def _seasons(values: list[float]) -> pd.DataFrame:
    """Build a minimal monthly ONI-like frame from a list of values."""
    dates = pd.date_range("2000-01-01", periods=len(values), freq="MS")
    return pd.DataFrame(
        {
            "date": dates,
            "season": [f"S{i}" for i in range(len(values))],
            "year": dates.year,
            "oni": values,
        }
    )


def test_simple_phase_thresholds() -> None:
    assert simple_phase(0.6) == "El Nino"
    assert simple_phase(-0.6) == "La Nina"
    assert simple_phase(0.3) == "Neutral"
    assert simple_phase(float("nan")) == "Neutral"


def test_classify_intensity_tiers() -> None:
    assert classify_intensity(0.7) == "Weak"
    assert classify_intensity(1.2) == "Moderate"
    assert classify_intensity(1.7) == "Strong"
    assert classify_intensity(2.3) == "Very Strong"


def test_event_requires_five_consecutive_seasons() -> None:
    # A 4-season warm run is NOT an event; a 5-season run IS.
    four = _seasons([0.6, 0.7, 0.8, 0.7, 0.1, 0.0])
    labeled4 = label_phases(four)
    assert (labeled4["phase_event"] == "El Nino").sum() == 0

    five = _seasons([0.6, 0.7, 0.8, 0.9, 0.7, 0.1])
    labeled5 = label_phases(five)
    assert (labeled5["phase_event"] == "El Nino").sum() == 5
    summary = event_summary(labeled5)
    assert len(summary) == 1
    assert summary.iloc[0]["phase"] == "El Nino"
    assert summary.iloc[0]["intensity"] == "Weak"  # peak 0.9


def test_detrend_removes_linear_trend() -> None:
    x = pd.Series(np.arange(100, dtype=float) * 2.0 + 5.0)
    d = detrend(x)
    assert abs(d.mean()) < 1e-9
    assert d.std() < 1e-6  # a pure line detrends to ~zero


def test_lagged_correlation_recovers_known_lag() -> None:
    rng = np.random.default_rng(0)
    idx = pd.date_range("1990-01-01", periods=240, freq="MS")
    driver = pd.Series(rng.standard_normal(240), index=idx)
    # target = driver delayed by 6 months -> peak |r| should be at lag 6.
    target = driver.shift(6) + rng.standard_normal(240) * 0.05
    ccf = lagged_cross_correlation(
        driver, target, max_lag=24, do_detrend=False
    )
    assert int(ccf.abs().idxmax()) == 6
    assert ccf.loc[6] > 0.9


def test_skill_metrics_basic() -> None:
    obs = [0.0, 1.0, 2.0, 3.0]
    perfect = [0.0, 1.0, 2.0, 3.0]
    assert rmse(obs, perfect) == 0.0
    assert acc(obs, perfect) == 1.0
    # A forecast equal to obs has MSSS = 1 vs a worse reference.
    worse = [1.0, 1.0, 1.0, 1.0]
    assert msss(obs, perfect, worse) == 1.0


def test_skill_by_lead_shape() -> None:
    bt = pd.DataFrame(
        {
            "lead": [1, 1, 2, 2],
            "actual": [0.5, 0.6, 0.7, 0.8],
            "pred": [0.5, 0.6, 0.65, 0.85],
            "persistence": [0.0, 0.0, 0.0, 0.0],
        }
    )
    sk = skill_by_lead(bt)
    assert list(sk["lead"]) == [1, 2]
    assert (sk["rmse"] >= 0).all()


def test_ccm_recovers_coupling_direction() -> None:
    # Build x -> y coupling: y depends on lagged x, x is independent.
    rng = np.random.default_rng(1)
    n = 400
    x = np.zeros(n)
    y = np.zeros(n)
    for t in range(1, n):
        x[t] = 0.7 * x[t - 1] + rng.standard_normal() * 0.3
        y[t] = 0.3 * y[t - 1] + 0.6 * x[t - 1] + rng.standard_normal() * 0.1
    idx = pd.date_range("1980-01-01", periods=n, freq="MS")
    driver, target = pd.Series(x, index=idx), pd.Series(y, index=idx)
    ccm = ccm_convergence(driver, target, E=3, tau=1, lib_steps=6)
    fwd = ccm[ccm["direction"] == "ONI->target"].sort_values("lib_size")["rho"]
    # x drives y, so y's manifold encodes x: forward cross-map (recovering the
    # driver from the target manifold) must achieve clear positive skill. (The
    # fwd>rev asymmetry only holds for *weak* coupling, so we don't assert it.)
    assert fwd.notna().all()
    assert fwd.iloc[-1] > 0.3


def test_weekly_nino34_parses_runtogether_negative() -> None:
    """A negative anomaly is glued to the SST ("26.8-0.1") in the CPC weekly file.

    That is the one case a naive ``str.split()`` gets wrong — it yields 7 fields
    instead of 8 and silently shifts every column. Header lines must be ignored.
    """
    text = (
        "Weekly SST data starts week centered on 2Sept1981\n"
        "                Nino1+2      Nino3        Nino34        Nino4\n"
        " Week          SST SSTA     SST SSTA     SST SSTA     SST SSTA\n"
        " 04MAR2026     27.6 1.0     27.0 0.2     26.8-0.1     28.2 0.1\n"
        " 22JUL2026     25.4 3.8     28.1 2.5     29.3 2.2     29.8 1.0\n"
    )
    df = parse_weekly(text)
    assert len(df) == 2, "header lines must not be parsed as data"
    assert df.iloc[0]["week_date"] == pd.Timestamp("2026-03-04")
    assert df.iloc[0]["nino34_anom"] == -0.1   # the run-together case
    assert df.iloc[0]["nino34_sst"] == 26.8
    assert df.iloc[1]["nino34_anom"] == 2.2


def test_stance_causal_gate_outranks_magnitude() -> None:
    """A WEAK or untested causal verdict is capped at WATCH however big the impact.

    This is the misattribution guard applied to the *prescription*. If it ever regresses,
    the desk starts issuing directional views on links CCM could not confirm.
    """
    assert stance(2.0, "weak") == ("● WATCH", "watch")
    assert stance(-2.0, "weak") == ("● WATCH", "watch")
    assert stance(2.0, "untested") == ("● WATCH", "watch")
    # A confirmed link still has to clear the noise floor.
    assert stance(IMPACT_FLOOR / 2, "mod") == ("● WATCH", "watch")
    # ...and only then does the sign of r_peak * state pick the direction.
    assert stance(0.9, "mod")[0] == "▲ CONSTRUCTIVE"
    assert stance(-0.9, "mod")[0] == "▼ CAUTIOUS"
    assert stance(float("nan"), "mod") == ("● WATCH", "watch")


def test_conviction_haircut_on_model_observation_split() -> None:
    """Models disagreeing with the observation costs a notch; bounds stay 1..4."""
    base = conviction(0.3, "mod", None)
    assert conviction(0.3, "mod", DIVERGENCE_TOL + 0.5) == base - 1
    assert conviction(0.3, "mod", DIVERGENCE_TOL - 0.5) == base   # inside tolerance
    assert conviction(5.0, "strong", None) == 4                   # capped
    assert conviction(0.0, "untested", 9.0) == 1                  # floored


def test_regime_label_flags_trajectory_from_weekly() -> None:
    """The ONI lags ~2.5 months; the live weekly says whether it is still moving."""
    when = pd.Timestamp("2026-05-01")
    assert regime_label(0.98, when) == "WEAK EL NIÑO · 2026"
    assert regime_label(0.98, when, weekly=2.15).endswith("STRENGTHENING")
    assert regime_label(0.98, when, weekly=1.0) == "WEAK EL NIÑO · 2026"  # gap < tol
    assert regime_label(-1.2, when, weekly=-2.4).startswith("MODERATE LA NIÑA")
    assert regime_label(0.1, when, weekly=0.2).startswith("NEUTRAL")


def test_freshness_subtracts_structural_label_lag() -> None:
    """A perfectly current ONI must NOT read stale just because of its centre-month label.

    The ONI is a 3-month mean stored under its centre month, so an on-schedule value is
    ~75 days old *by its own label*. Judging raw age against a 31-day cadence flags it
    stale forever — which is exactly the false alarm this registry exists to prevent.
    """
    oni = Source("ONI", "feed", "u", 31, "oni.parquet", expected_lag_days=75)
    assert _status(oni, 98 - 75) == "FRESH"     # on schedule
    assert _status(oni, 98) == "STALE"          # what the naive raw-age check would say
    assert _status(oni, 55) == "AGING"          # genuinely a publication late
    # Deliberate cutoffs are decisions, not neglect — never STALE however old.
    pink = Source("Pink Sheet", "snapshot", "u", None, "commodities.parquet")
    assert _status(pink, 5_000) == "SNAPSHOT"
    assert _status(Source("IMD", "static", "u", None, "m.parquet"), 9_999) == "STATIC"
    assert _status(Source("X", "computed", "u", 31, "nope.parquet"), None) == "MISSING"


def _run() -> None:
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} passed.")


if __name__ == "__main__":
    _run()
