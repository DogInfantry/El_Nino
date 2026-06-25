"""Fetch ERSSTv5 and build SST-anomaly grids for the global map.

ERSSTv5 (NOAA, 2°x2°, monthly, 1854-present) is free and needs no auth. The raw
netCDF is ~150 MB so it lives in gitignored ``data/raw/``; this module computes
anomalies against a 1991–2020 climatology and persists only a small tidy parquet
of selected month snapshots (the latest month plus landmark El Niño peaks) for
the dashboard's time slider.

Data source (free, no auth)
---------------------------
https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mnmean.nc

Output
------
``data/cache/sst_anomaly_grids.parquet`` with columns:
    date (datetime64) · lat · lon (−180..180) · sst_anom (°C)
NaN (land) cells are dropped. Longitudes are wrapped to [−180, 180] for deck.gl.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from _common import CACHE_DIR, PROJECT_ROOT, get_session, is_fresh

logger = logging.getLogger(__name__)

ERSST_URL = "https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mnmean.nc"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_FILE = RAW_DIR / "ersst_v5_sst.mnmean.nc"

CLIM_BASE = ("1991-01-01", "2020-12-31")
# Landmark El Niño peak months to include for the time slider (plus latest).
LANDMARK_MONTHS = ["1982-12", "1997-12", "2015-12", "2023-12"]


def download_raw(*, max_age_days: float = 30.0) -> Path:
    """Download the ERSSTv5 netCDF to data/raw (cached up to ``max_age_days``)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if is_fresh(RAW_FILE, max_age_days):
        logger.info("Using cached ERSST netCDF: %s", RAW_FILE)
        return RAW_FILE
    logger.info("Downloading ERSSTv5 (~150 MB)…")
    with get_session().get(ERSST_URL, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        tmp = RAW_FILE.with_suffix(".tmp")
        with open(tmp, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
        tmp.replace(RAW_FILE)
    logger.info("Saved %s (%.1f MB)", RAW_FILE, RAW_FILE.stat().st_size / 1e6)
    return RAW_FILE


def _wrap_longitude(df: pd.DataFrame) -> pd.DataFrame:
    """Wrap 0..360 longitudes to −180..180 for deck.gl."""
    df = df.copy()
    df["lon"] = ((df["lon"] + 180) % 360) - 180
    return df


def build_anomaly_grids(path: Path | None = None) -> pd.DataFrame:
    """Compute anomaly grids for the latest + landmark months as tidy long df."""
    path = path or RAW_FILE
    ds = xr.open_dataset(path)
    sst = ds["sst"]

    clim = (
        sst.sel(time=slice(*CLIM_BASE)).groupby("time.month").mean("time")
    )
    anom = sst.groupby("time.month") - clim

    # Resolve the months we want (landmarks that exist + the latest available).
    wanted: list[pd.Timestamp] = []
    times = pd.DatetimeIndex(ds["time"].values)
    for m in LANDMARK_MONTHS:
        ts = pd.Timestamp(m)
        if times.min() <= ts <= times.max():
            wanted.append(times[times.get_indexer([ts], method="nearest")[0]])
    wanted.append(times[-1])  # latest
    wanted = sorted(set(wanted))

    frames: list[pd.DataFrame] = []
    for ts in wanted:
        grid = anom.sel(time=ts)
        df = grid.to_dataframe(name="sst_anom").reset_index()
        df = df[["lat", "lon", "sst_anom"]].dropna(subset=["sst_anom"])
        df = _wrap_longitude(df)
        df.insert(0, "date", pd.Timestamp(ts).normalize())
        frames.append(df)
        logger.info("Anomaly grid %s: %d ocean cells", pd.Timestamp(ts).date(), len(df))

    out = pd.concat(frames, ignore_index=True)
    out["sst_anom"] = out["sst_anom"].astype("float32").round(2)
    out["lat"] = out["lat"].astype("float32")
    out["lon"] = out["lon"].astype("float32")
    ds.close()
    return out


def get_sst_grids(*, use_cache: bool = True, max_age_days: float = 30.0) -> pd.DataFrame:
    """Return the tidy anomaly grids, building from raw netCDF if needed."""
    out_path = CACHE_DIR / "sst_anomaly_grids.parquet"
    if use_cache and is_fresh(out_path, max_age_days):
        logger.info("Using fresh SST grid cache: %s", out_path)
        return pd.read_parquet(out_path)
    download_raw(max_age_days=max_age_days)
    grids = build_anomaly_grids()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grids.to_parquet(out_path, index=False)
    return grids


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ERSSTv5 SST anomaly grids.")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    grids = get_sst_grids(use_cache=not args.no_cache)
    print(f"SST anomaly grids: {len(grids):,} rows")
    print(f"Months: {sorted(grids['date'].dt.strftime('%Y-%m').unique())}")
    print(f"Anomaly range: {grids['sst_anom'].min():+.1f} … {grids['sst_anom'].max():+.1f} °C")
    print(f"Saved: {CACHE_DIR / 'sst_anomaly_grids.parquet'}")


if __name__ == "__main__":
    main()
