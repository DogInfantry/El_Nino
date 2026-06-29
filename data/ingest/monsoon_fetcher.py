"""Fetch the all-India summer-monsoon (JJAS) rainfall series and cache it tidy.

The ENSO x IOD conditioning analysis (``data/process/enso_flavor_iod.py``) needs a
monsoon OUTCOME for every year, not just the handful of El Niño years we could quote
from memory. This fetcher builds that series from the public IMD sub-divisional
monthly rainfall dataset (36 meteorological sub-divisions, 1901-2017) and aggregates
it to an all-India June-September index.

Data source (free, no auth)
---------------------------
IMD sub-divisional monthly rainfall 1901-2017, mirrored as CSV:
  https://raw.githubusercontent.com/dcsavinod/weather-and-rainfall-data-from-1901-to-2022/main/Rainfall_State_Analysis_India_1901_2017.csv
Originating portal: data.gov.in (OGD India) / IMD. Columns include per-subdivision
monthly mm and a ``June-September`` (JJAS) seasonal total.

Aggregation
-----------
All-India JJAS = mean of the ``June-September`` total across mainland sub-divisions
(island groups excluded — see ISLAND_SUBDIVS — they are tiny, very wet, and not part
of the classical all-India monsoon index). Expressed as % departure from the
1951-2010 long-period average (LPA). This approximates IMD's official area-weighted
AISMR; the year-to-year % anomaly (what the conditioning uses) tracks it closely —
validated in ``__main__`` against documented El Niño-year departures.

Output
------
``data/cache/monsoon_india.parquet``: year · jjas_mm · lpa_pct · category
"""

from __future__ import annotations

import argparse
import io
import logging
from pathlib import Path

import pandas as pd

from _common import cache_path, get_session, is_fresh, save_parquet

logger = logging.getLogger(__name__)

CSV_URL = (
    "https://raw.githubusercontent.com/dcsavinod/"
    "weather-and-rainfall-data-from-1901-to-2022/main/"
    "Rainfall_State_Analysis_India_1901_2017.csv"
)
JJAS_COL = "June-September"
ISLAND_SUBDIVS = {"Andaman & Nicobar Islands", "Lakshadweep"}
LPA_BASE = (1951, 2010)   # long-period-average window for % departure

# Documented all-India JJAS departure (% LPA) for El Niño years — used ONLY to
# validate the computed series (correlation), never as the series itself. IMD/IITM.
_DOC_ELNINO_PCT = {
    1951: -19, 1965: -18, 1972: -24, 1982: -15, 1987: -19, 2002: -19,
    2004: -14, 2009: -22, 2014: -12, 2015: -14,
}


def fetch_raw(session=None) -> pd.DataFrame:
    """Download the IMD sub-divisional CSV into a DataFrame."""
    session = session or get_session()
    resp = session.get(CSV_URL, timeout=60)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text))


def all_india_jjas(raw: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sub-divisional JJAS totals to an all-India series + % departure."""
    df = raw[~raw["SUBDIVISION"].isin(ISLAND_SUBDIVS)].copy()
    df[JJAS_COL] = pd.to_numeric(df[JJAS_COL], errors="coerce")
    series = (
        df.groupby("YEAR")[JJAS_COL].mean()
        .rename("jjas_mm").reset_index().rename(columns={"YEAR": "year"})
    )
    base = series[series["year"].between(*LPA_BASE)]["jjas_mm"].mean()
    series["lpa_pct"] = ((series["jjas_mm"] - base) / base * 100).round(1)
    series["category"] = pd.cut(
        series["lpa_pct"], bins=[-100, -10, 10, 1000],
        labels=["DEFICIENT", "Normal", "EXCESS"],
    ).astype(str)
    logger.info("All-India JJAS: %d years, LPA(%d-%d)=%.0f mm",
                len(series), LPA_BASE[0], LPA_BASE[1], base)
    return series


def get_monsoon(*, use_cache: bool = True, max_age_days: float = 30.0) -> pd.DataFrame:
    """Return the all-India JJAS series, fetching + caching if needed."""
    path = cache_path("monsoon_india.parquet")
    if use_cache and is_fresh(path, max_age_days):
        return pd.read_parquet(path)
    series = all_india_jjas(fetch_raw())
    save_parquet(series, path)
    return series


def _validate(series: pd.DataFrame) -> float:
    """Correlate computed % departure vs documented El Niño-year values."""
    s = series.set_index("year")["lpa_pct"]
    pairs = [(s[y], v) for y, v in _DOC_ELNINO_PCT.items() if y in s.index]
    comp = pd.DataFrame(pairs, columns=["computed", "documented"])
    return float(comp["computed"].corr(comp["documented"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch all-India JJAS monsoon series.")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    series = get_monsoon(use_cache=not args.no_cache)
    r = _validate(series)
    print(f"All-India JJAS series: {len(series)} years "
          f"({series['year'].min()}-{series['year'].max()})")
    print(f"Driest years: "
          f"{series.nsmallest(5,'lpa_pct')[['year','lpa_pct']].to_dict('records')}")
    print(f"Validation vs documented El Niño departures: r = {r:+.2f} "
          f"({'GOOD — method tracks AISMR' if r > 0.8 else 'CHECK aggregation'})")
    print(f"Saved: {cache_path('monsoon_india.parquet')}")


if __name__ == "__main__":
    main()
