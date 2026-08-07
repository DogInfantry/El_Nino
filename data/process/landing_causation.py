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

# Phase-randomized surrogate draws per link. 500 puts the p-value's resolution at 1/501,
# finer than the 0.05 the gate tests against, and costs a few seconds per commodity.
N_SURROGATES = 500


def _verdict(
    g_fwd: pd.DataFrame, ccm: pd.DataFrame, surr: dict | None = None
) -> tuple[str, str, int, float, int, float, float, int]:
    """Classify one ONI->commodity link. A raw rho no longer earns a causal label.

    The surrogate gate is the substantive change. Cross-map skill on smooth, seasonal
    series is high even when the two series are independent — a synthetic pair sharing
    only an annual cycle scores rho ~= 0.83 — so a bare ``rho_end >= 0.30`` threshold was
    measuring smoothness as much as coupling. CAUSAL and MODERATE now additionally
    require the observed rho to beat a same-spectrum, phase-randomized null at
    p < ALPHA. A link that fails that is capped at WEAK, whatever its rho.

    ``surr=None`` keeps the old behaviour, so the live page-05 explorer — which cannot
    afford 500 extra cross-map passes on a page load — still works unchanged.
    """
    sig = int((g_fwd["p_value"] < ALPHA).sum())
    fwd = ccm[ccm["direction"] == "ONI->target"].sort_values("lib_size")["rho"]
    rev = ccm[ccm["direction"] == "target->ONI"].sort_values("lib_size")["rho"]
    rho_end = float(fwd.iloc[-1])
    converges = (len(fwd) > 1 and (fwd.iloc[-1] - fwd.iloc[0]) > 0.03 and fwd.iloc[-1] > rev.iloc[-1])
    best_lag = int(g_fwd.loc[g_fwd["p_value"].idxmin(), "lag"])

    p = float(surr["p_value"]) if surr else float("nan")
    null_mean = float(surr["null_mean"]) if surr else float("nan")
    n_surr = int(surr["n_surrogates"]) if surr else 0
    # An untested link is not a passing link. Only an explicit p < ALPHA opens the gate;
    # NaN (test skipped or failed) leaves it shut, so a silent failure downgrades rather
    # than promotes. `p == p` is False for NaN.
    beats_null = bool(p == p and p < ALPHA)
    extras = (p, null_mean, n_surr)

    if sig >= 3 and converges and rho_end >= 0.30 and beats_null:
        return ("CAUSAL", "causal", sig, rho_end, best_lag, *extras)
    if sig >= 3 and converges and beats_null:
        return ("MODERATE", "mod", sig, rho_end, best_lag, *extras)
    if sig >= 2 or converges:
        return ("WEAK · confounded", "weak", sig, rho_end, best_lag, *extras)
    return ("NONE", "none", sig, rho_end, best_lag, *extras)


def compute() -> tuple[pd.DataFrame, pd.DataFrame]:
    oni = (pd.read_parquet(CACHE_DIR / "oni.parquet")
           .set_index("date")["oni"].astype(float).asfreq("MS"))
    comm = pd.read_parquet(CACHE_DIR / "commodities.parquet")
    curves, verdicts = [], []
    for commodity, label in LINKS:
        s = comm[comm["commodity"] == commodity].set_index("date")["price"].astype(float).asfreq("MS")
        res = analyze(oni, s, maxlag=24, mode="detrend", surrogates=N_SURROGATES)
        ccm = res["ccm"]
        fwd = ccm[ccm["direction"] == "ONI->target"].sort_values("lib_size")
        rev = ccm[ccm["direction"] == "target->ONI"].sort_values("lib_size")
        for L, fr, rr in zip(fwd["lib_size"], fwd["rho"], rev["rho"]):
            curves.append(dict(commodity=label, lib_size=int(L), fwd_rho=float(fr), rev_rho=float(rr)))
        verdict, cls, sig, rho, lag, p, null_mean, n_surr = _verdict(
            res["granger_oni_to_target"], ccm, res.get("ccm_surrogate"))
        verdicts.append(dict(commodity=label, verdict=verdict, cls=cls,
                             granger_sig=sig, ccm_rho=round(rho, 2), lag=lag,
                             ccm_p=round(p, 4), ccm_null=round(null_mean, 2),
                             n_surrogates=n_surr))
    return pd.DataFrame(curves), pd.DataFrame(verdicts)


def main() -> None:
    curves, verdicts = compute()
    curves.to_parquet(CACHE_DIR / "landing_ccm.parquet", index=False)
    verdicts.to_parquet(CACHE_DIR / "landing_verdicts.parquet", index=False)
    pd.set_option("display.width", 140)
    print(f"Landing causation verdicts (ONI → commodity), "
          f"{N_SURROGATES} phase-randomized surrogates:")
    print(verdicts.to_string(index=False))
    # The gap between ccm_rho and ccm_null is the whole point: a rho that sits inside its
    # own null is a number about smoothness, not coupling.
    inside = verdicts[verdicts["ccm_rho"] <= verdicts["ccm_null"]]
    if not inside.empty:
        print(f"\n{len(inside)} link(s) score at or BELOW their own seasonal null: "
              f"{', '.join(inside['commodity'])}")
    print(f"\nSaved: landing_ccm.parquet, landing_verdicts.parquet")


if __name__ == "__main__":
    main()
