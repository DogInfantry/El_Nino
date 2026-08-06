"""Positioning engine — the desk's *computed* stance per country/commodity.

Why this exists
---------------
The DESK VIEW badges on ``07_india`` / ``08_seasia`` were hand-typed when the ONI sat
near neutral. The ONI is now +0.98 (AMJ 2026) with the weekly Niño-3.4 at +2.2, so those
stances went stale silently — and a stale *prescription* costs more credibility than a
stale label ever did (the product thesis is DESCRIBE -> PRESCRIBE).

So the stance is computed here, from the same caches the rest of the desk reads, and
refreshed by ``scripts/refresh_data.py`` every month. A human can still pin a view via
:data:`OVERRIDES` — but the override is rendered *as* an override, with its reason.

The rule (published in ``docs/METHODOLOGY.md``, versioned by :data:`STANCE_VERSION`)
-----------------------------------------------------------------------------------
For each registry row (country -> dominant commodity):

1. ``r_peak``  signed Pearson r at the peak-|r| lag ``L`` over lags 0-24, detrended
   (``lag_correlator.lagged_cross_correlation``). The sign is the whole point: it says
   whether a warm ENSO pushes that price *up* or *down*. ``exposure_index`` deliberately
   throws this sign away (it only ranks link strength); the stance needs it.
2. ``state``   the ENSO forcing the price will respond to, in ONI standard deviations:
   the mean of the latest observed ONI and the ensemble path over the next ``L`` months.
3. ``impact = r_peak * state``  — expected direction and size of the lagged price move.
4. **Causal gate.** ``landing_verdicts.parquet`` decides whether we are allowed to hold a
   view at all. A WEAK (confounded) or entirely untested link is capped at **WATCH**, no
   matter how large ``impact`` is. This is the misattribution guard applied to the
   prescription, not just to the description.
5. **Conviction (1-4)** starts from the causal verdict, gains a notch for a large impact,
   and *loses* one when models and observation disagree — right now the ensemble decays
   toward neutral while the observed weekly reads +2.2, and a desk that hides that
   disagreement is bluffing.

What this is NOT
----------------
Not a trade recommendation and not a backtested signal. It is a triage ranking built from
one correlation and one causal test, with the judgement calls (thresholds, the override
list) written down rather than buried.

Output
------
``data/cache/positioning.parquet``:
    iso3 · name · commodity · r_peak · lag · state · impact · verdict · verdict_cls ·
    badge · badge_cls · conviction · horizon_mo · divergence · override_reason ·
    stance_version · date · regime
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / "ingest"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from enso_phase_labeler import classify_intensity, simple_phase  # noqa: E402
from exposure_index import REGISTRY  # noqa: E402
from lag_correlator import lagged_cross_correlation  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"

STANCE_VERSION = "stance-v1 (2026-08-07)"

# |impact| below this is noise -> WATCH. 0.25 ~ a 0.5-sigma ENSO through an r=0.5 link.
IMPACT_FLOOR = 0.25
# |impact| at or above this earns a conviction notch.
IMPACT_STRONG = 0.60
# Observed-minus-forecast gap (degC) that costs a conviction notch.
DIVERGENCE_TOL = 1.0
# Conviction seed by causal verdict class. Keys MUST match the classes emitted by
# landing_causation._verdict: causal | mod | weak | none  (+ untested, ours, for a
# commodity with no verdict row at all).
_CONVICTION_SEED = {"causal": 4, "mod": 3, "weak": 2, "none": 1, "untested": 1}
# Verdict classes allowed to carry a directional view at all.
_DIRECTIONAL_CLS = ("causal", "mod")

# Registry commodity (Pink Sheet name) -> the row name used in landing_verdicts.parquet.
# Anything unmapped is treated as UNTESTED, which caps the stance at WATCH by design.
VERDICT_KEY = {
    "Cocoa": "Cocoa",
    "Palm oil": "Palm oil",
    "Sugar, world": "Sugar",
    "Coffee, Robusta": "Robusta",
    "Wheat, US HRW": "Wheat",
    "Soybeans": "Soybeans",
}

# Human pins. iso3 -> {"badge", "badge_cls", "reason"}. Rendered AS an override.
OVERRIDES: dict[str, dict[str, str]] = {}


# ---- inputs -------------------------------------------------------------
def _oni() -> pd.Series:
    return (pd.read_parquet(CACHE_DIR / "oni.parquet")
            .set_index("date")["oni"].astype(float).sort_index())


def _verdicts() -> pd.DataFrame:
    path = CACHE_DIR / "landing_verdicts.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["commodity", "verdict", "cls"])
    return pd.read_parquet(path)


def _ensemble_path() -> pd.Series:
    """Ensemble forecast mean by date (empty Series if the cache is missing)."""
    path = CACHE_DIR / "forecasts_all.parquet"
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_parquet(path)
    df = df[df["model"] == "Ensemble"]
    if df.empty:
        return pd.Series(dtype=float)
    # One row per date per CI level — the mean is identical across levels.
    return df.groupby("date")["mean"].first().astype(float).sort_index()


def _weekly_anom() -> float | None:
    """Live 4-week Niño-3.4 mean, or None. Never raises (network is optional)."""
    try:
        from weekly_nino34 import latest_weekly
    except Exception:  # noqa: BLE001
        return None
    w = latest_weekly()
    return None if w is None else float(w.anom_4wk)


# ---- the rule -----------------------------------------------------------
def signed_peak(oni: pd.Series, price: pd.Series) -> tuple[float, int]:
    """Signed r at the peak-|r| lag, and that lag in months."""
    ccf = lagged_cross_correlation(oni, np.log(price.where(price > 0)),
                                   max_lag=24, do_detrend=True).dropna()
    if ccf.empty:
        return float("nan"), 0
    lag = int(ccf.abs().idxmax())
    return float(ccf.loc[lag]), lag


def enso_state(oni: pd.Series, fcst: pd.Series, lag: int) -> float:
    """Forcing the lagged price responds to, in ONI standard deviations.

    Blends the latest observed ONI with the ensemble path over the next ``lag`` months,
    so a stance inherits the forecast's decay instead of freezing today's reading.
    """
    sd = float(oni.std()) or 1.0
    levels = [float(oni.iloc[-1])]
    if not fcst.empty and lag > 0:
        ahead = fcst[fcst.index > oni.index[-1]].head(lag)
        levels.extend(float(v) for v in ahead)
    return float(np.mean(levels)) / sd


def stance(impact: float, verdict_cls: str) -> tuple[str, str]:
    """(badge, css class). The causal gate outranks the magnitude, always."""
    if verdict_cls not in _DIRECTIONAL_CLS or not np.isfinite(impact):
        return "● WATCH", "watch"
    if abs(impact) < IMPACT_FLOOR:
        return "● WATCH", "watch"
    return ("▲ CONSTRUCTIVE", "") if impact > 0 else ("▼ CAUTIOUS", "cautious")


def conviction(impact: float, verdict_cls: str, divergence: float | None) -> int:
    """1-4. Seeded by the causal verdict; a model/observation split costs a notch."""
    score = _CONVICTION_SEED.get(verdict_cls, 1)
    if np.isfinite(impact) and abs(impact) >= IMPACT_STRONG:
        score += 1
    if divergence is not None and abs(divergence) > DIVERGENCE_TOL:
        score -= 1
    return int(min(4, max(1, score)))


# Weekly-minus-ONI gap (degC) that earns a trajectory tag on the regime label.
TRAJECTORY_TOL = 0.75


def regime_label(oni_now: float, when: pd.Timestamp,
                 weekly: float | None = None) -> str:
    """e.g. 'WEAK EL NIÑO · 2026 · STRENGTHENING' — computed, never typed.

    The tier comes from the ONI, which is a 3-month mean labelled by its centre month
    and therefore lags reality by ~2.5 months. When the live weekly Niño-3.4 has already
    moved well past it, the label says so instead of quietly under-calling the regime.
    """
    phase = simple_phase(oni_now)
    if phase == "Neutral":
        base = f"NEUTRAL · {when:%Y}"
    else:
        tier = classify_intensity(abs(oni_now)).upper()
        name = "EL NIÑO" if phase == "El Nino" else "LA NIÑA"
        base = f"{tier} {name} · {when:%Y}"
    if weekly is None:
        return base
    gap = weekly - oni_now
    if gap >= TRAJECTORY_TOL:
        return f"{base} · STRENGTHENING"
    if gap <= -TRAJECTORY_TOL:
        return f"{base} · EASING"
    return base


# ---- assembly -----------------------------------------------------------
def compute() -> pd.DataFrame:
    oni = _oni()
    comm = pd.read_parquet(CACHE_DIR / "commodities.parquet")
    vdf = _verdicts()
    verdicts = vdf.set_index("commodity") if not vdf.empty else None
    fcst = _ensemble_path()
    weekly = _weekly_anom()

    ahead = fcst[fcst.index > oni.index[-1]] if not fcst.empty else fcst
    near_fcst = float(ahead.iloc[0]) if len(ahead) else float(oni.iloc[-1])
    divergence = None if weekly is None else weekly - near_fcst

    rows = []
    for iso3, name, commodity, _e, _sign in REGISTRY:
        price = (comm[comm["commodity"] == commodity]
                 .set_index("date")["price"].astype(float).sort_index())
        r_peak, lag = (float("nan"), 0) if price.empty else signed_peak(oni, price)

        key = VERDICT_KEY.get(commodity)
        if verdicts is not None and key is not None and key in verdicts.index:
            v_text = str(verdicts.loc[key, "verdict"])
            v_cls = str(verdicts.loc[key, "cls"])
        else:
            v_text, v_cls = "UNTESTED", "untested"

        state = enso_state(oni, fcst, lag)
        impact = r_peak * state
        badge, badge_cls = stance(impact, v_cls)
        conv = conviction(impact, v_cls, divergence)
        reason = ""

        if iso3 in OVERRIDES:
            o = OVERRIDES[iso3]
            badge, badge_cls = o["badge"], o.get("badge_cls", "")
            reason = o["reason"]

        rows.append(dict(
            iso3=iso3, name=name, commodity=commodity,
            r_peak=round(r_peak, 3), lag=lag, state=round(state, 3),
            impact=round(impact, 3), verdict=v_text, verdict_cls=v_cls,
            badge=badge, badge_cls=badge_cls, conviction=conv,
            horizon_mo=lag,
            divergence=None if divergence is None else round(divergence, 2),
            override_reason=reason, stance_version=STANCE_VERSION,
        ))

    df = pd.DataFrame(rows)
    df["date"] = oni.index[-1]        # vintage stamp — refresh_data.py checks this
    df["regime"] = regime_label(float(oni.iloc[-1]), oni.index[-1], weekly)
    return df.sort_values("impact", key=lambda s: s.abs(), ascending=False,
                          na_position="last").reset_index(drop=True)


def get_positioning(*, use_cache: bool = True) -> pd.DataFrame:
    path = CACHE_DIR / "positioning.parquet"
    if use_cache and path.exists():
        return pd.read_parquet(path)
    df = compute()
    df.to_parquet(path, index=False)
    return df


def main() -> None:
    df = compute()
    df.to_parquet(CACHE_DIR / "positioning.parquet", index=False)
    pd.set_option("display.width", 160)
    print(f"Positioning engine [{STANCE_VERSION}] — regime: {df['regime'].iloc[0]}")
    cols = ["iso3", "commodity", "r_peak", "lag", "state", "impact",
            "verdict", "badge", "conviction"]
    print(df[cols].to_string(index=False))
    div = df["divergence"].iloc[0]
    if div is not None and not pd.isna(div):
        print(f"\nObserved-minus-forecast divergence: {div:+.2f} degC "
              f"(tolerance {DIVERGENCE_TOL:.1f}) — conviction haircut where it bites.")
    print(f"\nSaved: {CACHE_DIR / 'positioning.parquet'}")


if __name__ == "__main__":
    main()
