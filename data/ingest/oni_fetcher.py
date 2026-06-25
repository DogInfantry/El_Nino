"""Fetch the Oceanic Niño Index (ONI) and persist a tidy time series.

The ONI is NOAA CPC's operational ENSO index: the 3-month running mean of
Niño-3.4 region SST anomalies (ERSSTv5), expressed against a rolling 30-year
base period. Values >= +0.5 degC indicate El Niño conditions, <= -0.5 degC
La Niña. It is published as 12 overlapping 3-month "seasons" per year
(DJF, JFM, ... NDJ).

Data sources (free, no auth)
----------------------------
Primary  : CPC machine-readable ASCII feed
           https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
           Columns: SEAS YR TOTAL ANOM  (ANOM is the ONI value).
Fallback : CPC HTML table (same numbers, harder to parse)
           https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php

Notes / caveats
---------------
* The ASCII feed is preferred over the HDX CSV mirror because it is the
  canonical source, is updated ~5th of each month, and has a stable URL
  (the HDX mirror requires resolving per-resource UUIDs that change).
* ONI is a *rolling-base* index. As of 16 Feb 2026 NOAA adopted RONI
  (Relative ONI) as the official ENSO index; RONI is fetched separately by
  ``roni_fetcher.py``. Any chart built on this data must be labelled "ONI".

Output
------
``data/cache/oni.parquet`` with columns:
    date        (datetime64)  -- first day of the season's *center* month
    season      (str)         -- 3-letter overlapping season, e.g. "DJF"
    year        (int)         -- year as labelled by CPC
    sst_total   (float)       -- absolute SST of the Niño-3.4 region (degC)
    oni         (float)       -- ONI anomaly value (degC)
    source      (str)         -- "cpc_ascii" or "cpc_html"
"""

from __future__ import annotations

import argparse
import io
import logging
from pathlib import Path

import pandas as pd
import requests

from _common import cache_path, get_session, is_fresh, save_parquet

logger = logging.getLogger(__name__)

ONI_ASCII_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
ONI_HTML_URL = (
    "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/"
    "ensostuff/ONI_v5.php"
)

# Each overlapping 3-month season is centered on its middle month. CPC labels
# every season with the year of that center month, so the mapping is 1:1 within
# the labelled year (DJF -> Jan, ..., NDJ -> Dec).
SEASON_TO_MONTH: dict[str, int] = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
}

OUTPUT_COLUMNS = ["date", "season", "year", "sst_total", "oni", "source"]


def _add_center_date(df: pd.DataFrame) -> pd.DataFrame:
    """Attach a ``date`` column (center month of each season) and sort."""
    month = df["season"].map(SEASON_TO_MONTH)
    if month.isna().any():
        bad = sorted(df.loc[month.isna(), "season"].unique())
        raise ValueError(f"Unrecognized ONI season label(s): {bad}")
    df = df.assign(
        date=pd.to_datetime(
            dict(year=df["year"], month=month.astype(int), day=1)
        )
    )
    return df.sort_values("date").reset_index(drop=True)


def fetch_oni_ascii(session: requests.Session | None = None) -> pd.DataFrame:
    """Fetch and parse the canonical CPC ASCII ONI feed."""
    session = session or get_session()
    resp = session.get(ONI_ASCII_URL, timeout=30)
    resp.raise_for_status()

    # Whitespace-delimited fixed columns: SEAS YR TOTAL ANOM
    raw = pd.read_csv(
        io.StringIO(resp.text),
        sep=r"\s+",
        engine="python",
    )
    raw.columns = [c.strip().upper() for c in raw.columns]
    df = raw.rename(
        columns={
            "SEAS": "season",
            "YR": "year",
            "TOTAL": "sst_total",
            "ANOM": "oni",
        }
    )
    df["season"] = df["season"].astype(str).str.strip().str.upper()
    df["year"] = df["year"].astype(int)
    df = _add_center_date(df)
    df["source"] = "cpc_ascii"
    logger.info("Fetched ONI (ascii): %d rows, %s -> %s",
                len(df), df["date"].min().date(), df["date"].max().date())
    return df[OUTPUT_COLUMNS]


def fetch_oni_html(session: requests.Session | None = None) -> pd.DataFrame:
    """Fallback parser for the CPC HTML ONI table.

    The HTML page exposes a wide table (year rows x 12 season columns) of
    anomalies only; absolute SST is not available here, so ``sst_total`` is NaN.
    """
    session = session or get_session()
    resp = session.get(ONI_HTML_URL, timeout=30)
    resp.raise_for_status()

    tables = pd.read_html(io.StringIO(resp.text))
    # Pick the table whose header row contains the season labels.
    wanted = set(SEASON_TO_MONTH)
    table = None
    for cand in tables:
        cols = {str(c).strip().upper() for c in cand.columns}
        if wanted.issubset(cols) or wanted.issubset(
            {str(v).strip().upper() for v in cand.iloc[0].tolist()}
        ):
            table = cand
            break
    if table is None:
        raise ValueError("Could not locate the ONI season table in CPC HTML")

    # Normalize header: some renderings put seasons in the first data row.
    cols_upper = {str(c).strip().upper() for c in table.columns}
    if not wanted.issubset(cols_upper):
        table.columns = [str(v).strip().upper() for v in table.iloc[0].tolist()]
        table = table.iloc[1:].reset_index(drop=True)

    table = table.rename(columns={c: str(c).strip().upper() for c in table.columns})
    year_col = next(
        c for c in table.columns if c in {"YEAR", "YR"}
    )
    long = table.melt(
        id_vars=[year_col],
        value_vars=[s for s in SEASON_TO_MONTH if s in table.columns],
        var_name="season",
        value_name="oni",
    ).rename(columns={year_col: "year"})

    long["year"] = pd.to_numeric(long["year"], errors="coerce")
    long["oni"] = pd.to_numeric(long["oni"], errors="coerce")
    long = long.dropna(subset=["year", "oni"]).copy()
    long["year"] = long["year"].astype(int)
    long["sst_total"] = pd.NA
    long = _add_center_date(long)
    long["source"] = "cpc_html"
    logger.info("Fetched ONI (html fallback): %d rows", len(long))
    return long[OUTPUT_COLUMNS]


def get_oni(
    *,
    use_cache: bool = True,
    max_age_days: float = 7.0,
    cache_file: str = "oni.parquet",
) -> pd.DataFrame:
    """Return the ONI time series, fetching live with cache + fallback.

    Resolution order:
      1. Fresh local parquet cache (if ``use_cache`` and within ``max_age_days``)
      2. CPC ASCII feed (primary)
      3. CPC HTML table (fallback)
      4. Stale local cache (last resort, if a previous run saved one)
    """
    path = cache_path(cache_file)
    if use_cache and is_fresh(path, max_age_days):
        logger.info("Using fresh ONI cache: %s", path)
        return pd.read_parquet(path)

    session = get_session()
    try:
        df = fetch_oni_ascii(session)
    except Exception as exc:  # noqa: BLE001 - want broad fallback here
        logger.warning("ONI ASCII fetch failed (%s); trying HTML fallback", exc)
        try:
            df = fetch_oni_html(session)
        except Exception as exc2:  # noqa: BLE001
            if path.exists():
                logger.error(
                    "Both live sources failed (%s); serving STALE cache %s",
                    exc2, path,
                )
                return pd.read_parquet(path)
            raise RuntimeError(
                "ONI unavailable: ASCII and HTML sources both failed and no "
                "cache exists."
            ) from exc2

    save_parquet(df, path)
    return df


def main() -> None:
    """CLI entry point: fetch ONI and write ``data/cache/oni.parquet``."""
    parser = argparse.ArgumentParser(description="Fetch NOAA CPC ONI time series.")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore any existing cache and force a live fetch.",
    )
    parser.add_argument(
        "--max-age-days",
        type=float,
        default=7.0,
        help="Reuse cache if newer than this many days (default: 7).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    df = get_oni(use_cache=not args.no_cache, max_age_days=args.max_age_days)
    out = cache_path("oni.parquet")
    latest = df.iloc[-1]
    print(f"ONI rows: {len(df):,}")
    print(f"Range   : {df['date'].min().date()} -> {df['date'].max().date()}")
    print(
        f"Latest  : {latest['season']} {latest['year']} = "
        f"{latest['oni']:+.2f} degC (source: {latest['source']})"
    )
    print(f"Saved   : {out}")


if __name__ == "__main__":
    main()
