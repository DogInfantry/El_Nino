"""Source registry — one row per upstream feed, and how stale each one is right now.

Why this exists
---------------
On 2026-07-30 the deployed desk appeared to be showing May-2026 data. It was not: the
ONI is a 3-month mean labelled by its **centre month**, so a current value renders under
an older month. Hours went into proving the data was fine. That was an *observability*
gap, not a data gap — nothing on the desk said what each source's cadence was, or when
it was next expected to move.

So every feed is declared here once, with its cadence and its kind, and the desk renders
the answer instead of leaving a reader to guess. A source that is *deliberately* frozen
(the Pink Sheet snapshot ends 2024-12; the IMD subdivision set ends 2017) reads as
SNAPSHOT — a stated decision, not neglect.

`scripts/refresh_data.py` computes the same max-dates for its regression gate; pointing
both at this registry is what stops the CI gate and the UI from drifting apart.

Kinds
-----
live      fetched at page load, never cached-stale (advisory, weekly nowcast)
feed      refreshed by the monthly cron; should move on a known cadence
snapshot  a dated upstream file that does not advance — by decision, with a reason
static    a fixed historical dataset that will never advance
computed  derived in-repo from the above; staleness is inherited
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"

# Grace multiplier: a feed is AGING once it is this many times its cadence behind.
AGING_FACTOR = 1.5
# ...and STALE at twice its cadence. Both are judgement calls, published in METHODOLOGY.md.
STALE_FACTOR = 2.0


@dataclass(frozen=True, slots=True)
class Source:
    name: str
    kind: str                 # live | feed | snapshot | static | computed
    url: str
    cadence_days: int | None  # None for snapshot/static — staleness is not meaningful
    cache: str | None         # parquet under data/cache, or None for live-only
    note: str = ""
    # Structural offset between today and the newest label a PERFECTLY CURRENT source
    # carries. The ONI is a 3-month mean stored under its centre month and published
    # ~the 5th, so a current value is ~75 days "old" by its own label. Measuring raw age
    # against cadence would flag it STALE forever — which is precisely the mistake this
    # module exists to stop.
    expected_lag_days: int = 0
    # Forecast caches are dated into the FUTURE; their vintage is the first row, not the last.
    forward: bool = False
    # Dateless derived caches (no date column at all) inherit the vintage of this cache.
    inherits: str | None = None


REGISTRY: tuple[Source, ...] = (
    Source("ONI (Niño-3.4, 3-mo mean)", "feed",
           "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt", 31, "oni.parquet",
           "CPC publishes ~the 5th. Labelled by CENTRE month — a current value reads ~2.5 mo old.",
           expected_lag_days=75),
    Source("Weekly Niño-3.4 SST anomaly", "live",
           "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for", 7, "weekly_nino34.parquet",
           "Read live at page load; the parquet is only the offline fallback. "
           "NOT comparable to the ONI's ±0.5 °C thresholds — different product and cadence."),
    Source("ENSO Diagnostic Discussion", "live",
           "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/", 31, None,
           "Fetched at page load and parsed from PDF. Never cached, so never stale."),
    Source("ERSSTv5 SST grids", "feed",
           "https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/", 31,
           "sst_anomaly_grids.parquet",
           "~150 MB netCDF, gitignored. Host 502s intermittently — the cron retries once.",
           expected_lag_days=45),
    Source("World Bank Pink Sheet", "snapshot",
           "https://www.worldbank.org/en/research/commodity-markets", None, "commodities.parquet",
           "Stable-UUID workbook ends 2024-12 by decision: splicing a second live source "
           "risks corrupting the lag/Granger/CCM work that is the moat, for recency the "
           "analysis does not need. Disclosed on page 04."),
    Source("IMD subdivision rainfall", "static",
           "https://data.gov.in/", None, "monsoon_india.parquet",
           "Fixed 1901–2017 dataset. All-India JJAS is an unweighted subdivision mean "
           "(r=0.77 vs the official area-weighted AISMR)."),
    Source("Ancillary climate indices", "feed",
           "https://psl.noaa.gov/data/correlation/", 31, "climate_indices.parquet",
           "SOI · Niño 1+2/3/4 · TNI · PDO · AMO · PNA · WP · DMI. Individual indices go "
           "frozen upstream while still serving HTTP 200 (AMO stopped at 2023-01); "
           "climate_indices.model_features() drops those before any model sees them.",
           expected_lag_days=31),
    Source("RONI (in-repo)", "computed",
           "derived from ERSSTv5", 31, "roni.parquet",
           "Fixed 1991–2020 base — approximates, does not reproduce, NOAA's official RONI. "
           "Also a 3-month running mean, so it carries the ONI's centre-month label lag.",
           expected_lag_days=75),
    Source("ENSO phase labels", "computed", "derived from the ONI", 31, "enso_phases.parquet",
           expected_lag_days=75),
    Source("SARIMA + LSTM ensemble", "computed", "derived from the ONI", 31,
           "forecasts_all.parquet",
           "Dated into the future, so its vintage is the FIRST forecast month, not the last. "
           "Members are vintage-guarded: refreshing one without the other raises.",
           expected_lag_days=45, forward=True),
    Source("ENSO Exposure Index", "computed", "derived from ONI × Pink Sheet", 31,
           "exposure_index.parquet", "Half computed (C), half curated (E). Carries no date "
           "column — vintage is inherited from the ONI it was built on.",
           expected_lag_days=75, inherits="oni.parquet"),
    Source("Causal verdicts (Granger+CCM)", "computed", "derived from ONI × Pink Sheet", 31,
           "landing_verdicts.parquet", "Dateless — vintage inherited from the ONI.",
           expected_lag_days=75, inherits="oni.parquet"),
    Source("Analog months", "computed", "derived from ONI × ancillary indices", 31,
           "analogs.parquet",
           "Nearest historical states + the ONI path that followed each. Refuses to run "
           "if the newest complete state vector lags the ONI by more than 3 months.",
           expected_lag_days=75),
    Source("Positioning stances", "computed", "derived from ONI × prices × verdicts", 31,
           "positioning.parquet", "Recomputed monthly so a stance cannot go regime-stale.",
           expected_lag_days=75),
)


def _vintage(cache: str, *, forward: bool = False) -> pd.Timestamp | None:
    """Newest data label in a cache, or None if missing/dateless. Never raises.

    ``forward=True`` takes the FIRST date instead of the last: a forecast cache is dated
    into the future, so its last row says when the horizon ends, not when it was built.
    """
    path = CACHE_DIR / cache
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
    except Exception:  # noqa: BLE001
        return None
    for col in df.columns:
        if "date" in col.lower():
            dates = pd.to_datetime(df[col])
            return dates.min() if forward else dates.max()
    if "year" in df.columns:                       # annual sets (monsoon)
        return pd.Timestamp(int(df["year"].max()), 12, 31)
    return None


def _status(s: Source, behind: int | None) -> str:
    """FRESH / AGING / STALE / LIVE / SNAPSHOT / STATIC / MISSING.

    ``behind`` is *excess* age — days late **after** subtracting the source's structural
    label lag. Only ``feed`` and ``computed`` rows can be stale; calling a deliberate
    snapshot "stale" would repeat the May-2026 scare in the other direction.
    """
    if s.kind == "live":
        return "LIVE"
    if s.kind == "snapshot":
        return "SNAPSHOT"
    if s.kind == "static":
        return "STATIC"
    if behind is None:
        return "MISSING"
    cadence = s.cadence_days or 31
    if behind > cadence * STALE_FACTOR:
        return "STALE"
    if behind > cadence * AGING_FACTOR:
        return "AGING"
    return "FRESH"


def status_table(today: pd.Timestamp | None = None) -> pd.DataFrame:
    """One row per source: newest label, raw age, excess lateness, and a status chip.

    ``age_days`` is what a reader sees on the page ("this says May 2026"). ``behind_days``
    is what actually matters ("...and that is exactly on schedule"). Publishing both is
    the whole point — the gap between them is what caused the 2026-07-30 false alarm.
    """
    now = pd.Timestamp(today or pd.Timestamp.today().normalize())
    rows = []
    for s in REGISTRY:
        latest = _vintage(s.cache, forward=s.forward) if s.cache else None
        if latest is None and s.inherits:
            latest = _vintage(s.inherits)
        age = None if latest is None else int((now - latest).days)
        behind = None if age is None else age - s.expected_lag_days
        rows.append(dict(
            name=s.name, kind=s.kind, cadence_days=s.cadence_days,
            latest=latest, age_days=age, behind_days=behind,
            expected_lag_days=s.expected_lag_days, status=_status(s, behind),
            url=s.url, note=s.note, cache=s.cache or "",
        ))
    return pd.DataFrame(rows)


def main() -> None:
    df = status_table()
    pd.set_option("display.width", 170)
    show = df[["name", "kind", "latest", "age_days", "behind_days", "status"]].copy()
    show["latest"] = show["latest"].astype(str).str.slice(0, 10)
    print("Source freshness  (age = days since the data's own label; "
          "behind = age minus that source's structural label lag)")
    print(show.to_string(index=False))
    bad = df[df["status"].isin(("STALE", "MISSING"))]
    if not bad.empty:
        print("\nNeeds attention:")
        for _, r in bad.iterrows():
            print(f"  {r['status']:8s} {r['name']} ({r['age_days']} d)")


if __name__ == "__main__":
    main()
