"""IMD 0.25° gridded daily rainfall → area-weighted JJAS series for India.

Why this exists
---------------
The India page runs on ``monsoon_india.parquet``: IMD's 36-subdivision monthly set, frozen
at 2017, whose all-India figure is an **unweighted mean of subdivisions**. That correlates
r = 0.77 with the official area-weighted AISMR — good enough to condition on, wrong enough
to keep apologising for, and eight years out of date.

This replaces it at the source. IMD's 0.25° × 0.25° daily gridded rainfall runs 1901–2024
on a 135 × 129 grid (6.5–38.5 N, 66.5–100 E), and an area-weighted mean over it *is* the
quantity the subdivision average was approximating — and it reaches 2024 instead of 2017.

How well it validates, stated plainly
-------------------------------------
- **Climatology: very good.** The 1971–2020 all-India normal computed here is **858.9 mm**
  against IMD's published ~868 mm — within 1.1%. The old unweighted subdivision mean gives
  ~1045 mm, ~20% too high, because averaging subdivisions equally over-weights small very
  wet ones (the north-east, the Konkan coast). That bias is the r = 0.77 caveat, and area
  weighting is what removes it.
- **Year-to-year: very good.** r = **0.945** against the subdivision series over the 68
  overlapping years (1950–2017) — two independent constructions agreeing.
- **Individual extremes: close, not identical.** 1972 reads −22.5% here against a cited
  ~−24%, but 2009 reads −15.0% against a cited ~−22%. IMD's headline "country as a whole"
  figure uses subdivision-area weights over its own subdivision set, which is not the same
  estimator as a cos(lat) mean over every valid grid cell. **These numbers are therefore
  internally consistent and close to the official series, but they do not reproduce it.**
  Do not quote them as IMD's published departures.

.. note::
   The IITM official AISMR series was to be the validation cross-check. Its host
   (``mol.tropmet.res.in``) serves an incomplete certificate chain that Python refuses and
   browsers paper over by fetching the missing intermediate. Rather than disable
   verification in a pipeline that commits unattended — accepting unauthenticated data into
   the caches the causal work depends on — the series is dropped. An area-weighted mean
   computed here supersedes it anyway.

Area weighting
--------------
On a regular lat/lon grid, cell area shrinks with latitude as cos(lat). Ignoring that
over-weights the Himalaya and under-weights the peninsula. Weights are cos(lat) applied to
valid cells only, so the ocean and the missing-data mask never enter the mean.

Cost and cadence
----------------
**Run manually, never in CI.** 1950–2024 is ~75 yearly binaries (~1.9 GB); the raw download
lives in the gitignored ``data/raw/imd/`` and only the small aggregate parquet is committed.
IMD publishes annually, so this is a once-a-year job, deliberately outside the monthly cron.

Regions
-------
All-India plus five drought-prone regions the India page already annotates. These are
**approximate bounding boxes**, not official IMD subdivision polygons — a box around
Marathwada is not Marathwada. They are labelled approximate wherever they surface.

Output
------
``data/cache/monsoon_india_grid.parquet``:
    year     (int)   -- monsoon year
    region   (str)   -- "All-India" or a region name
    jjas_mm  (float) -- June-September total, area-weighted mean over the region
    lpa_pct  (float) -- % departure from that region's 1971-2020 long-period average
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from _common import cache_path, save_parquet

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "imd"
CACHE_NAME = "monsoon_india_grid.parquet"

START_YEAR, END_YEAR = 1950, 2024      # 1950 matches the ONI record; earlier years would
                                       # only serve climatology and cost ~1 GB more.
JJAS = (6, 7, 8, 9)
MISSING = -999.0
# IMD's current official normal period. Departures must be measured against a FIXED
# baseline, not the series' own mean, or they cannot be compared with published figures —
# against its own mean the 2009 drought reads -15.4% where IMD cites roughly -22%.
LPA_BASE = (1971, 2020)

# name -> (lat_min, lat_max, lon_min, lon_max). APPROXIMATE boxes, not subdivisions.
REGIONS: dict[str, tuple[float, float, float, float]] = {
    "Marathwada":  (17.5, 20.5, 74.8, 78.5),
    "Rayalaseema": (13.0, 16.0, 76.5, 80.0),
    "Vidarbha":    (19.5, 22.0, 76.5, 80.5),
    "Saurashtra":  (20.8, 23.5, 68.5, 72.5),
    "Bundelkhand": (24.0, 26.5, 78.0, 81.0),
}


def download(start: int = START_YEAR, end: int = END_YEAR):
    """Fetch IMD rainfall binaries into ``data/raw/imd`` and return the imdlib handle.

    imdlib is an offline-pipeline dependency only — deliberately absent from
    ``requirements-space.txt``, because the deployed dashboard reads parquet and never runs
    an ingest.
    """
    import imdlib as imd                       # imported late: heavy, and optional

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading IMD rain %d-%d into %s", start, end, RAW_DIR)
    return imd.get_data("rain", start, end, fn_format="yearwise", file_dir=str(RAW_DIR))


def open_local(start: int = START_YEAR, end: int = END_YEAR):
    """Open already-downloaded binaries without re-fetching."""
    import imdlib as imd

    return imd.open_data("rain", start, end, fn_format="yearwise", file_dir=str(RAW_DIR))


def _to_dataarray(handle):
    """imdlib handle -> a (time, lat, lon) DataArray with missing values masked."""
    ds = handle.get_xarray()
    da = ds["rain"] if hasattr(ds, "data_vars") and "rain" in ds.data_vars else ds
    return da.where(da != MISSING)


def regional_jjas(da) -> pd.DataFrame:
    """Area-weighted JJAS totals and % departure per region, one row per year."""
    weights = np.cos(np.deg2rad(da["lat"]))
    jjas = da.sel(time=da["time.month"].isin(JJAS))

    rows = []
    targets: dict[str, tuple[float, float, float, float] | None] = {
        "All-India": None, **REGIONS}
    for region, box in targets.items():
        sub = jjas
        if box is not None:
            lat0, lat1, lon0, lon1 = box
            sub = jjas.sel(lat=slice(lat0, lat1), lon=slice(lon0, lon1))
        w = weights.sel(lat=sub["lat"])
        # Seasonal total FIRST, then the spatial mean: averaging daily rates and scaling up
        # would mishandle cells whose count of valid days differs.
        season_total = sub.groupby("time.year").sum(dim="time", skipna=True, min_count=1)
        series = season_total.weighted(w.fillna(0)).mean(dim=("lat", "lon"), skipna=True)
        s = series.to_series().dropna()
        if s.empty:
            logger.warning("No data for region %s", region)
            continue
        base = s[(s.index >= LPA_BASE[0]) & (s.index <= LPA_BASE[1])]
        if len(base) < 20:      # too short a normal period to be meaningful
            logger.warning("%s: only %d years in %d-%d, using the full-series mean",
                           region, len(base), *LPA_BASE)
            base = s
        lpa = float(base.mean())
        for year, value in s.items():
            rows.append(dict(year=int(year), region=region,
                             jjas_mm=round(float(value), 1),
                             lpa_pct=round(100.0 * (float(value) - lpa) / lpa, 2)))
    return pd.DataFrame(rows).sort_values(["region", "year"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the area-weighted IMD gridded JJAS series (manual, ~1.9 GB).")
    parser.add_argument("--start", type=int, default=START_YEAR)
    parser.add_argument("--end", type=int, default=END_YEAR)
    parser.add_argument("--offline", action="store_true",
                        help="use binaries already in data/raw/imd, skip downloading")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    handle = (open_local(args.start, args.end) if args.offline
              else download(args.start, args.end))
    df = regional_jjas(_to_dataarray(handle))
    path = save_parquet(df, cache_path(CACHE_NAME))

    allin = df[df["region"] == "All-India"]
    print(f"Saved {len(df)} rows ({df['region'].nunique()} regions, "
          f"{allin['year'].min()}-{allin['year'].max()}) -> {path}")
    base = allin[(allin["year"] >= LPA_BASE[0]) & (allin["year"] <= LPA_BASE[1])]
    print(f"All-India LPA ({LPA_BASE[0]}-{LPA_BASE[1]}): {base['jjas_mm'].mean():.1f} mm "
          f"— IMD's published normal is ~868 mm\n")
    print("Driest all-India monsoons on record (area-weighted):")
    print(allin.nsmallest(5, "lpa_pct")[["year", "jjas_mm", "lpa_pct"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
