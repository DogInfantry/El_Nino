"""Compute the Relative ONI (RONI) from ERSSTv5.

NOAA adopted **RONI** (Relative Oceanic Niño Index) as the official ENSO index
on 16 Feb 2026. RONI subtracts the tropical-mean SST anomaly from the Niño-3.4
anomaly, removing the background-warming signal that ONI retains. Under RONI,
recent strong El Niños register cooler (e.g. 2023–24 ≈ 0.6 °C lower) and some
"neutral" periods reclassify.

Why compute it here (vs. fetch)
-------------------------------
The CPC RONI page does not expose a clean machine-readable feed, but RONI is a
simple, well-defined transform of gridded SST — so we compute it directly from
the ERSSTv5 netCDF already downloaded by ``ersst_fetcher.py``. We also emit an
ERSST-derived ONI-equivalent on the *same* climatology so the two are directly
comparable on one chart.

Definition (this implementation)
--------------------------------
    anomaly      : SST minus 1991–2020 monthly climatology
    nino34_anom  : cos(lat)-weighted mean over 5°S–5°N, 170°W–120°W
    tropical_anom: cos(lat)-weighted mean over 20°S–20°N, all longitudes
    oni_equiv    : 3-month running mean of nino34_anom   (ERSST-based ONI)
    roni         : 3-month running mean of (nino34_anom − tropical_anom)

Caveat: NOAA's official RONI uses ONI's rolling 30-year base periods; this uses
a fixed 1991–2020 base, so values approximate (not reproduce) the official RONI.

Output
------
``data/cache/roni.parquet``: date · nino34_anom · tropical_anom · oni_equiv · roni
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "ersst_v5_sst.mnmean.nc"

CLIM_BASE = ("1991-01-01", "2020-12-31")
NINO34 = dict(lat=(-5, 5), lon=(190, 240))   # 170°W–120°W in 0–360 convention
TROPICS = dict(lat=(-20, 20))                # all longitudes


def _weighted_box_mean(anom: xr.DataArray, lat_rng, lon_rng=None) -> xr.DataArray:
    """cos(lat)-weighted spatial mean over a lat/lon box."""
    sub = anom.sel(lat=slice(*lat_rng))
    if lon_rng is not None:
        sub = sub.sel(lon=slice(*lon_rng))
    weights = np.cos(np.deg2rad(sub.lat))
    return sub.weighted(weights).mean(("lat", "lon"))


def compute_roni(path: Path | None = None) -> pd.DataFrame:
    """Compute the ONI-equivalent and RONI series from ERSSTv5."""
    path = path or RAW_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run data/ingest/ersst_fetcher.py first."
        )
    ds = xr.open_dataset(path).sortby("lat")
    sst = ds["sst"]
    clim = sst.sel(time=slice(*CLIM_BASE)).groupby("time.month").mean("time")
    anom = sst.groupby("time.month") - clim

    nino34 = _weighted_box_mean(anom, NINO34["lat"], NINO34["lon"])
    tropical = _weighted_box_mean(anom, TROPICS["lat"])
    relative = nino34 - tropical

    oni_equiv = nino34.rolling(time=3, center=True).mean()
    roni = relative.rolling(time=3, center=True).mean()

    df = pd.DataFrame(
        {
            "date": pd.DatetimeIndex(ds["time"].values).normalize(),
            "nino34_anom": nino34.to_numpy(),
            "tropical_anom": tropical.to_numpy(),
            "oni_equiv": oni_equiv.to_numpy(),
            "roni": roni.to_numpy(),
        }
    )
    ds.close()
    df = df.dropna(subset=["roni"]).reset_index(drop=True)
    # Restrict to the modern era to match the ONI record.
    df = df[df["date"] >= "1950-01-01"].reset_index(drop=True)
    for col in ("nino34_anom", "tropical_anom", "oni_equiv", "roni"):
        df[col] = df[col].astype("float32").round(3)
    logging.getLogger(__name__).info(
        "Computed RONI: %d months, %s -> %s",
        len(df), df["date"].min().date(), df["date"].max().date(),
    )
    return df


def get_roni(*, use_cache: bool = True) -> pd.DataFrame:
    """Return the RONI table, computing + caching if needed."""
    out = CACHE_DIR / "roni.parquet"
    if use_cache and out.exists():
        return pd.read_parquet(out)
    df = compute_roni()
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute RONI from ERSSTv5.")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    df = get_roni(use_cache=not args.no_cache)
    out = CACHE_DIR / "roni.parquet"

    # Show the background-warming effect: ONI-equiv vs RONI by decade.
    df = df.assign(decade=(df["date"].dt.year // 10 * 10))
    by_decade = df.groupby("decade")[["oni_equiv", "roni"]].mean()
    by_decade["oni_minus_roni"] = by_decade["oni_equiv"] - by_decade["roni"]
    print("ERSST-based ONI-equiv vs RONI, decade means (warming signal = ONI-minus-RONI):")
    print(by_decade.to_string(float_format=lambda v: f"{v:+.3f}"))
    print(f"\nRows: {len(df):,}  Saved: {out}")


if __name__ == "__main__":
    main()
