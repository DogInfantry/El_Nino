"""Fetch World Bank "Pink Sheet" monthly commodity prices.

The World Bank Commodity Markets "Pink Sheet" is the standard free reference
for global commodity prices. For ENSO impact analysis we need the full monthly
*history* (to run lagged cross-correlation against the ONI), so this module
targets the canonical historical workbook rather than the latest dated bulletin.

Data source (free, no auth)
---------------------------
CMO-Historical-Data-Monthly.xlsx (monthly nominal USD prices, 1960-present)
https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx

Sheet layout ("Monthly Prices")
-------------------------------
    rows 0..n : title / "Updated on ..." metadata
    header-2  : commodity names  (e.g. "Cocoa", "Coffee, Arabica")
    header-1  : units            (e.g. "($/kg)", "($/mt)")
    data      : col 0 = "YYYYMmm" (e.g. "1960M01"); remaining cols = prices
Missing values use sentinel text ("..", ellipsis) -> coerced to NaN.

Caveats
-------
* This historical file is republished periodically; the embedded "Updated on"
  date can lag the latest monthly bulletin by a few weeks.
* Prices are *nominal* USD (not inflation-adjusted). Note this on any chart.

Output
------
``data/cache/commodities.parquet`` (tidy long) with columns:
    date       (datetime64) -- first day of the price month
    commodity  (str)        -- World Bank commodity label
    unit       (str)        -- price unit, e.g. "($/kg)"
    price      (float)      -- nominal USD price
    source     (str)        -- "worldbank_pinksheet"
"""

from __future__ import annotations

import argparse
import io
import logging
import re
from pathlib import Path

import pandas as pd
import requests

from _common import cache_path, get_session, is_fresh, save_parquet

logger = logging.getLogger(__name__)

PINK_SHEET_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "5d903e848db1d1b83e0ec8f744e55570-0350012021/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)
PRICES_SHEET = "Monthly Prices"
DATE_RE = re.compile(r"^\s*(\d{4})M(\d{2})\s*$")

# Commodities with the clearest ENSO teleconnection signal (per project brief).
# Substring match against World Bank labels -> used by the sector-impact page.
FOCUS_COMMODITIES: tuple[str, ...] = (
    "Cocoa",
    "Coffee, Arabica",
    "Coffee, Robusta",
    "Sugar, world",
    "Palm oil",
    "Soybeans",
    "Wheat, US HRW",
    "Liquefied natural gas, Japan",
)

OUTPUT_COLUMNS = ["date", "commodity", "unit", "price", "source"]


def _find_data_start(col0: pd.Series) -> int:
    """Return the row index of the first ``YYYYMmm`` date in column 0."""
    for idx, val in col0.items():
        if isinstance(val, str) and DATE_RE.match(val):
            return int(idx)
    raise ValueError(
        "Could not locate the first 'YYYYMmm' data row in the Pink Sheet."
    )


def _parse_yyyymmm(values: pd.Series) -> pd.Series:
    """Convert a ``YYYYMmm`` string series to month-start timestamps."""
    cleaned = values.astype(str).str.strip().str.replace("M", "-", regex=False)
    return pd.to_datetime(cleaned, format="%Y-%m", errors="coerce")


def fetch_pink_sheet(session: requests.Session | None = None) -> pd.DataFrame:
    """Download and tidy the World Bank historical monthly price workbook."""
    session = session or get_session()
    resp = session.get(PINK_SHEET_URL, timeout=60)
    resp.raise_for_status()

    raw = pd.read_excel(
        io.BytesIO(resp.content), sheet_name=PRICES_SHEET, header=None
    )

    data_start = _find_data_start(raw.iloc[:, 0])
    # Commodity names sit two rows above the first data row; units one above.
    names = raw.iloc[data_start - 2].tolist()
    units = raw.iloc[data_start - 1].tolist()

    body = raw.iloc[data_start:].reset_index(drop=True).copy()
    body[0] = _parse_yyyymmm(body[0])
    body = body.dropna(subset=[0]).rename(columns={0: "date"})

    # Melt every commodity column (cols 1..N) into long format.
    records: list[pd.DataFrame] = []
    for col in range(1, raw.shape[1]):
        name = names[col]
        if not isinstance(name, str) or not name.strip():
            continue  # skip spacer / unnamed columns
        unit = units[col] if isinstance(units[col], str) else ""
        series = pd.DataFrame(
            {
                "date": body["date"],
                "commodity": name.strip(),
                "unit": unit.strip(),
                "price": pd.to_numeric(body[col], errors="coerce"),
            }
        )
        records.append(series)

    long = pd.concat(records, ignore_index=True)
    long = long.dropna(subset=["price"]).reset_index(drop=True)
    long["source"] = "worldbank_pinksheet"
    long = long.sort_values(["commodity", "date"]).reset_index(drop=True)

    logger.info(
        "Fetched Pink Sheet: %d commodities, %d price points, %s -> %s",
        long["commodity"].nunique(),
        len(long),
        long["date"].min().date(),
        long["date"].max().date(),
    )
    return long[OUTPUT_COLUMNS]


def get_commodities(
    *,
    use_cache: bool = True,
    max_age_days: float = 30.0,
    cache_file: str = "commodities.parquet",
) -> pd.DataFrame:
    """Return tidy commodity prices, with cache and graceful fallback.

    Pink Sheet updates monthly, so the default cache window is 30 days.
    """
    path = cache_path(cache_file)
    if use_cache and is_fresh(path, max_age_days):
        logger.info("Using fresh commodities cache: %s", path)
        return pd.read_parquet(path)

    try:
        df = fetch_pink_sheet()
    except Exception as exc:  # noqa: BLE001 - broad on purpose for fallback
        if path.exists():
            logger.error(
                "Pink Sheet fetch failed (%s); serving STALE cache %s", exc, path
            )
            return pd.read_parquet(path)
        raise RuntimeError(
            "Commodity prices unavailable: live fetch failed and no cache exists."
        ) from exc

    save_parquet(df, path)
    return df


def focus_subset(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to the ENSO-relevant commodities in :data:`FOCUS_COMMODITIES`."""
    mask = df["commodity"].isin(FOCUS_COMMODITIES)
    missing = [c for c in FOCUS_COMMODITIES if c not in set(df["commodity"])]
    if missing:
        logger.warning("Focus commodities not found in source: %s", missing)
    return df[mask].reset_index(drop=True)


def main() -> None:
    """CLI: fetch Pink Sheet and write ``data/cache/commodities.parquet``."""
    parser = argparse.ArgumentParser(
        description="Fetch World Bank Pink Sheet monthly commodity prices."
    )
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--max-age-days", type=float, default=30.0)
    parser.add_argument(
        "--list", action="store_true", help="Print available commodity labels."
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    df = get_commodities(use_cache=not args.no_cache, max_age_days=args.max_age_days)
    out = cache_path("commodities.parquet")

    if args.list:
        print("Available commodities:")
        for name in sorted(df["commodity"].unique()):
            print(f"  - {name}")
        print()

    focus = focus_subset(df)
    print(f"Commodities total : {df['commodity'].nunique()}")
    print(f"Price points      : {len(df):,}")
    print(f"Date range        : {df['date'].min().date()} -> {df['date'].max().date()}")
    print(f"Focus set found   : {focus['commodity'].nunique()}/{len(FOCUS_COMMODITIES)}")
    print(f"Saved             : {out}")


if __name__ == "__main__":
    main()
