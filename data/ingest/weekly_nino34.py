"""Fetch CPC's *weekly* Niño-3.4 SST anomaly — the desk's freshest ENSO number.

Why this exists
---------------
The ONI is a 3-month running mean and is labelled by its **center month**, so the
newest published value (AMJ 2026) renders as "May 2026" and reads as stale even
when it is current. CPC also publishes a *weekly* Niño-3.4 SST anomaly every
Monday, ~1 week behind real time. Showing it next to the ONI gives the desk a
genuinely fresh reading and exposes the trajectory the 3-month mean smooths away.

Data source (free, no auth)
---------------------------
https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for   (1991-2020 base)

.. warning::
   The sibling file ``wksst8110.for`` (1981-2010 base) is **FROZEN at 27JAN2021**.
   It still returns HTTP 200, so fetching it silently ships 5-year-old data.
   Only ``wksst9120.for`` is live.

Format (fixed width, 62 chars)::

                 Nino1+2       Nino3        Nino34        Nino4
    Week          SST SSTA     SST SSTA     SST SSTA     SST SSTA
     22JUL2026     25.4 3.8     28.1 2.5     29.3 2.2     29.8 1.0
     04MAR2026     27.6 1.0     27.0 0.2     26.8-0.1     28.2 0.1

Note the second example: a **negative anomaly runs together with the SST**
(``26.8-0.1``), so ``str.split()`` yields the wrong number of fields. We match
numbers by regex instead, which keeps the leading minus sign attached.

Reading it
----------
``latest_weekly()`` is what the dashboard calls. Like
:func:`advisory_fetcher.get_advisory` it is a live read at page load and can
never raise: on any network/parse failure it falls back to the committed
``weekly_nino34.parquet`` snapshot, and returns ``None`` only if that is missing
too. Running this module as a script refreshes that snapshot.

This is NOT the same quantity as ``roni_calculator``'s monthly ``nino34_anom``
(ERSSTv5, monthly, in-repo) — different product and cadence. Never compare a
single weekly value against the ONI's ±0.5 degC event thresholds.

Output
------
``data/cache/weekly_nino34.parquet`` with columns:
    week_date    (datetime64) -- week-CENTERED date, e.g. 2026-07-22
    nino34_sst   (float)      -- absolute SST, degC
    nino34_anom  (float)      -- anomaly vs the 1991-2020 base, degC
    source       (str)        -- "cpc_wksst9120"
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass

import pandas as pd

from _common import CACHE_DIR, cache_path, get_session, save_parquet

logger = logging.getLogger(__name__)

WEEKLY_URL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
SOURCE = "cpc_wksst9120"
CACHE_NAME = "weekly_nino34.parquet"

# A data row starts with a week-centered date like "22JUL2026".
_DATE_RE = re.compile(r"^\s*(\d{2}[A-Za-z]{3}\d{4})\s")
# One-decimal numbers, minus sign attached (handles the "26.8-0.1" run-together).
_NUM_RE = re.compile(r"-?\d+\.\d")
# Nino1+2, Nino3, Nino34, Nino4 x (SST, SSTA) = 8 values; Nino-3.4 is the 3rd pair.
_N_FIELDS = 8
_N34_SST, _N34_ANOM = 4, 5


@dataclass(slots=True)
class WeeklyNino34:
    """Latest weekly Niño-3.4 reading, plus a noise-damped 4-week mean."""

    week_date: pd.Timestamp
    sst: float
    anom: float
    anom_4wk: float
    source: str = SOURCE


def parse_weekly(text: str) -> pd.DataFrame:
    """Parse the raw ``wksst*.for`` body into a tidy Niño-3.4 frame.

    Non-data lines (titles, column headers) and any row that does not yield
    exactly 8 numbers are skipped rather than guessed at.
    """
    rows = []
    for line in text.splitlines():
        m = _DATE_RE.match(line)
        if not m:
            continue
        nums = _NUM_RE.findall(line)
        if len(nums) != _N_FIELDS:
            logger.debug("Skipping malformed row (%d fields): %r", len(nums), line)
            continue
        rows.append(
            {
                "week_date": pd.to_datetime(m.group(1).upper(), format="%d%b%Y"),
                "nino34_sst": float(nums[_N34_SST]),
                "nino34_anom": float(nums[_N34_ANOM]),
                "source": SOURCE,
            }
        )
    if not rows:
        raise ValueError("No weekly data rows parsed — upstream format may have changed.")
    df = pd.DataFrame(rows).sort_values("week_date").reset_index(drop=True)
    logger.info("Parsed %d weekly rows (%s -> %s).", len(df),
                df["week_date"].min().date(), df["week_date"].max().date())
    return df


def fetch_weekly(timeout: float = 30.0) -> pd.DataFrame:
    """Download and parse the live weekly file. Raises on failure."""
    resp = get_session().get(WEEKLY_URL, timeout=timeout)
    resp.raise_for_status()
    return parse_weekly(resp.text)


def _summarise(df: pd.DataFrame) -> WeeklyNino34:
    last = df.iloc[-1]
    return WeeklyNino34(
        week_date=pd.Timestamp(last["week_date"]),
        sst=float(last["nino34_sst"]),
        anom=float(last["nino34_anom"]),
        anom_4wk=float(df["nino34_anom"].tail(4).mean()),
    )


def latest_weekly(timeout: float = 20.0) -> WeeklyNino34 | None:
    """Latest weekly reading: live, else cached snapshot, else ``None``.

    Never raises — the dashboard calls this during page build.
    """
    try:
        return _summarise(fetch_weekly(timeout=timeout))
    except Exception as exc:  # noqa: BLE001 - must never crash the dashboard
        logger.warning("Live weekly Niño-3.4 fetch failed (%s); trying cache.", exc)
    try:
        return _summarise(pd.read_parquet(CACHE_DIR / CACHE_NAME))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cached weekly Niño-3.4 unavailable: %s", exc)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh the weekly Niño-3.4 snapshot cache.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    df = fetch_weekly()
    path = save_parquet(df, cache_path(CACHE_NAME))
    latest = _summarise(df)
    print(f"Saved {len(df)} weekly rows -> {path}")
    print(f"Latest: week ctr. {latest.week_date:%d %b %Y}  "
          f"Nino-3.4 anom {latest.anom:+.1f} degC  (4-wk mean {latest.anom_4wk:+.2f})")


if __name__ == "__main__":
    main()
