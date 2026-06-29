"""Precompute the landing's causation strip — 6 ONI→commodity verdicts + CCM curves.

The landing's bottom strip shows, for six commodities, whether the ONI→price link
survives causal testing (Granger + CCM). Running six live CCM passes on every page load
is slow, so we precompute here and cache. Cocoa & wheat are expected to FAIL — that
honest result is the misattribution guard the whole desk is built around.

Output
------
``data/cache/landing_ccm.parquet``      : commodity · lib_size · fwd_rho · rev_rho
``data/cache/landing_verdicts.parquet`` : commodity · verdict · cls · granger_sig · ccm_rho · lag
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from granger_ccm import analyze

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"

# (Pink-Sheet commodity, short label) — six links the desk vets on the front page.
LINKS = [
    ("Palm oil", "Palm oil"), ("Coffee, Robusta", "Robusta"), ("Sugar, world", "Sugar"),
    ("Soybeans", "Soybeans"), ("Cocoa", "Cocoa"), ("Wheat, US HRW", "Wheat"),
]
ALPHA = 0.05


def _verdict(g_fwd: pd.DataFrame, ccm: pd.DataFrame) -> tuple[str, str, int, float, int]:
    sig = int((g_fwd["p_value"] < ALPHA).sum())
    fwd = ccm[ccm["direction"] == "ONI->target"].sort_values("lib_size")["rho"]
    rev = ccm[ccm["direction"] == "target->ONI"].sort_values("lib_size")["rho"]
    rho_end = float(fwd.iloc[-1])
    converges = (len(fwd) > 1 and (fwd.iloc[-1] - fwd.iloc[0]) > 0.03 and fwd.iloc[-1] > rev.iloc[-1])
    best_lag = int(g_fwd.loc[g_fwd["p_value"].idxmin(), "lag"])
    if sig >= 3 and converges and rho_end >= 0.30:
        return "CAUSAL", "causal", sig, rho_end, best_lag
    if sig >= 3 and converges:
        return "MODERATE", "mod", sig, rho_end, best_lag
    if sig >= 2 or converges:
        return "WEAK · confounded", "weak", sig, rho_end, best_lag
    return "NONE", "none", sig, rho_end, best_lag


def compute() -> tuple[pd.DataFrame, pd.DataFrame]:
    oni = (pd.read_parquet(CACHE_DIR / "oni.parquet")
           .set_index("date")["oni"].astype(float).asfreq("MS"))
    comm = pd.read_parquet(CACHE_DIR / "commodities.parquet")
    curves, verdicts = [], []
    for commodity, label in LINKS:
        s = comm[comm["commodity"] == commodity].set_index("date")["price"].astype(float).asfreq("MS")
        res = analyze(oni, s, maxlag=24, mode="detrend")
        ccm = res["ccm"]
        fwd = ccm[ccm["direction"] == "ONI->target"].sort_values("lib_size")
        rev = ccm[ccm["direction"] == "target->ONI"].sort_values("lib_size")
        for L, fr, rr in zip(fwd["lib_size"], fwd["rho"], rev["rho"]):
            curves.append(dict(commodity=label, lib_size=int(L), fwd_rho=float(fr), rev_rho=float(rr)))
        verdict, cls, sig, rho, lag = _verdict(res["granger_oni_to_target"], ccm)
        verdicts.append(dict(commodity=label, verdict=verdict, cls=cls,
                             granger_sig=sig, ccm_rho=round(rho, 2), lag=lag))
    return pd.DataFrame(curves), pd.DataFrame(verdicts)


def main() -> None:
    curves, verdicts = compute()
    curves.to_parquet(CACHE_DIR / "landing_ccm.parquet", index=False)
    verdicts.to_parquet(CACHE_DIR / "landing_verdicts.parquet", index=False)
    pd.set_option("display.width", 120)
    print("Landing causation verdicts (ONI → commodity):")
    print(verdicts.to_string(index=False))
    print(f"\nSaved: landing_ccm.parquet, landing_verdicts.parquet")


if __name__ == "__main__":
    main()
