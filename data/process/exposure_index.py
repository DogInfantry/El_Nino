"""ENSO Exposure Index — a per-country score for the landing choropleth + leaderboard.

This is a **constructed index**, labelled as such everywhere it appears (it is NOT an
observed quantity). It ranks the major ENSO-exposed agricultural exporters by how much
an ENSO swing should move their dominant export.

Definition (transparent, two factors)
--------------------------------------
    index = 100 * (0.5 * C + 0.5 * E)

  C — ENSO→commodity link strength (COMPUTED). The peak |detrended lagged correlation|
      between the ONI and the country's dominant Pink-Sheet commodity over lags 0–24 mo,
      scaled so |r| = 0.45 maps to 1.0 (|r| ~0.45 is strong for a detrended ENSO link).
  E — economic / production exposure (CURATED). The country's structural reliance on that
      commodity (global market share × agricultural weight), 0–1, from public production
      shares (FAO/USDA) — documented per row, not computed.

So half the score is data-driven (C) and half is a documented structural weight (E).
The `sign` field flags the ENSO direction (dry = El Niño drought-exposed; wet = flood/
La Niña-favoured) for the choropleth diverging palette.

Output
------
``data/cache/exposure_index.parquet``: iso3 · name · commodity · C · E · index · sign
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from lag_correlator import lagged_cross_correlation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
C_FULL_SCALE = 0.45   # |r| that maps to C = 1.0

# (iso3, country, dominant Pink-Sheet commodity, E [0-1 curated], sign)
REGISTRY: list[tuple[str, str, str, float, str]] = [
    ("CIV", "Côte d'Ivoire", "Cocoa", 0.90, "dry"),
    ("GHA", "Ghana", "Cocoa", 0.80, "dry"),
    ("IDN", "Indonesia", "Palm oil", 0.85, "dry"),
    ("MYS", "Malaysia", "Palm oil", 0.70, "dry"),
    ("IND", "India", "Sugar, world", 0.80, "dry"),
    ("THA", "Thailand", "Sugar, world", 0.60, "dry"),
    ("BRA", "Brazil", "Coffee, Arabica", 0.75, "mixed"),
    ("VNM", "Vietnam", "Coffee, Robusta", 0.70, "dry"),
    ("AUS", "Australia", "Wheat, US HRW", 0.65, "dry"),
    ("ARG", "Argentina", "Soybeans", 0.70, "mixed"),
    ("USA", "United States", "Soybeans", 0.45, "mixed"),
]


def _link_strength() -> dict[str, float]:
    """Computed C per commodity: peak |detrended lagged corr| with the ONI, scaled."""
    oni = (pd.read_parquet(CACHE_DIR / "oni.parquet")
           .set_index("date")["oni"].astype(float).sort_index())
    comm = pd.read_parquet(CACHE_DIR / "commodities.parquet")
    out: dict[str, float] = {}
    for c in {r[2] for r in REGISTRY}:
        s = comm[comm["commodity"] == c].set_index("date")["price"].astype(float).sort_index()
        if s.empty:
            out[c] = np.nan
            continue
        ccf = lagged_cross_correlation(oni, np.log(s.where(s > 0)), max_lag=24, do_detrend=True)
        peak = float(ccf.abs().max())
        out[c] = min(peak / C_FULL_SCALE, 1.0)
    return out


def compute() -> pd.DataFrame:
    cmap = _link_strength()
    rows = []
    for iso3, name, commodity, e, sign in REGISTRY:
        c = cmap.get(commodity, np.nan)
        idx = 100 * (0.5 * c + 0.5 * e)
        rows.append(dict(iso3=iso3, name=name, commodity=commodity,
                         C=round(c, 2), E=e, index=round(idx, 1), sign=sign))
    return pd.DataFrame(rows).sort_values("index", ascending=False).reset_index(drop=True)


def get_exposure(*, use_cache: bool = True) -> pd.DataFrame:
    path = CACHE_DIR / "exposure_index.parquet"
    if use_cache and path.exists():
        return pd.read_parquet(path)
    df = compute()
    df.to_parquet(path, index=False)
    return df


def main() -> None:
    df = compute()
    df.to_parquet(CACHE_DIR / "exposure_index.parquet", index=False)
    pd.set_option("display.width", 140)
    print("ENSO Exposure Index (constructed; C computed, E curated):")
    print(df.to_string(index=False))
    print(f"\nSaved: {CACHE_DIR / 'exposure_index.parquet'}")


if __name__ == "__main__":
    main()
