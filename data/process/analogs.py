"""Analog engine — which historical months does the present most resemble, and what
happened next.

Why this exists
---------------
The desk's forecast is a model extrapolation with a confidence band. Analog forecasting is
the oldest complementary answer in the field: find the states the record has already been
in, and read off what followed. It is not a competing model — it is a sanity check with
provenance. "Closest match: June 1997" is checkable in a way a fan chart is not.

Right now it matters more than usual. The ensemble decays toward neutral while the observed
weekly Niño-3.4 sits at +2.15, so the models may be under-calling the event. If the nearest
analogs are strong-event years that kept intensifying, that is evidence a reader deserves
to weigh against the cone.

The state vector
----------------
Per month: the ONI trajectory over t-6..t (level *and* slope — a +1.0 rising is not a +1.0
fading), the Niño 1+2/3/4 pattern at t (east-vs-central structure, i.e. ENSO flavour), and
SOI, DMI and PDO at t (atmospheric coupling, Indian Ocean state, low-frequency backdrop).
Every feature is z-scored over the full record before distance is measured, so no component
dominates by virtue of its units.

**Euclidean distance, not cosine.** Cosine compares shape and discards magnitude, which
would let a weak El Niño match a very strong one because both are "warm and rising". For
climate analogs the magnitude *is* the signal, so distance in standardised space is the
correct metric.

Two exclusions, both necessary for the result to mean anything:

- **Neighbouring months are excluded** (``EXCLUDE_MONTHS``). Adjacent months share six of
  their seven trajectory features, so without this the top analogs for May 2026 are simply
  April and June 2026 — trivially true and useless.
- **Analogs must have a full forward window.** A match with no observed future cannot answer
  the only question being asked.

Output
------
``data/cache/analogs.parquet`` (long, one row per analog per lead):
    query_date  (datetime64) -- the month being matched (latest with a complete state)
    analog_date (datetime64) -- the historical month matched
    rank        (int)        -- 1 = closest
    distance    (float)      -- Euclidean distance in standardised feature space
    lead        (int)        -- 0..FORWARD_MONTHS, months after the analog
    oni_fwd     (float)      -- the ONI actually observed at that lead
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / "ingest"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from climate_indices import model_features  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"

ANALOG_VERSION = "analog-v1 (2026-08-07)"

TRAJECTORY_MONTHS = 6      # ONI lags t-6..t — captures level and direction
FORWARD_MONTHS = 12        # how far ahead "what happened next" runs
EXCLUDE_MONTHS = 12        # analogs within this many months of the query are skipped
TOP_K = 5
# Indices used at time t, beyond the ONI trajectory. Frozen upstreams are already dropped
# by model_features(), so this list is what is *wanted*, not what happens to be available.
#
# PDO is deliberately absent. It is the laggard of the pack (~11 months behind as of
# 2026-08), and because a state vector is only usable when every feature is present, one
# late index drags the newest complete state back to its own end date — the first run of
# this engine answered for Aug 2025 while reporting itself as current. Its low-frequency
# backdrop is not worth surrendering a year of recency, and forward-filling it would
# manufacture observations, which is the same sin as imputing the SOI.
POINT_INDICES = ("NINO12", "NINO3", "NINO4", "SOI", "DMI")

# The query must be this close to the newest ONI month, or the engine is answering a
# question about the past while presenting itself as a nowcast. Raise instead.
MAX_QUERY_LAG_MONTHS = 3


def _oni() -> pd.Series:
    return (pd.read_parquet(CACHE_DIR / "oni.parquet")
            .set_index("date")["oni"].astype(float).sort_index())


def state_matrix(oni: pd.Series | None = None,
                 feats: pd.DataFrame | None = None) -> pd.DataFrame:
    """Standardised state vector per month. Rows with any missing feature are dropped.

    Dropping incomplete rows rather than imputing them is deliberate: an imputed SOI would
    manufacture a match on a month where the atmosphere was never actually measured.
    """
    oni = _oni() if oni is None else oni
    feats = model_features() if feats is None else feats

    cols: dict[str, pd.Series] = {
        f"oni_lag{k}": oni.shift(k) for k in range(TRAJECTORY_MONTHS + 1)
    }
    for name in POINT_INDICES:
        if name in feats.columns:
            cols[name] = feats[name].reindex(oni.index)

    raw = pd.DataFrame(cols, index=oni.index).dropna()
    if raw.empty:
        raise ValueError("No complete state vectors — check the index caches.")

    # A state vector needs every feature, so the newest complete month is set by whichever
    # index is furthest behind. Fail loudly and name the culprit rather than quietly
    # answering for a month that is no longer the present.
    lag = (oni.index[-1].year - raw.index[-1].year) * 12 + \
          (oni.index[-1].month - raw.index[-1].month)
    if lag > MAX_QUERY_LAG_MONTHS:
        ends = {c: str(feats[c].dropna().index[-1].date())
                for c in POINT_INDICES if c in feats.columns}
        laggards = sorted(ends.items(), key=lambda kv: kv[1])[:2]
        raise ValueError(
            f"Newest complete state is {raw.index[-1]:%Y-%m} but the ONI runs to "
            f"{oni.index[-1]:%Y-%m} ({lag} months behind, limit {MAX_QUERY_LAG_MONTHS}). "
            f"Furthest-behind inputs: {', '.join(f'{k} ends {v}' for k, v in laggards)}. "
            "Refresh climate_indices, or drop the laggard from POINT_INDICES.")
    # z-score per feature so degC, pressure-derived and unitless indices weigh equally.
    return (raw - raw.mean()) / raw.std(ddof=0)


def find_analogs(query: pd.Timestamp | None = None, *, top_k: int = TOP_K,
                 states: pd.DataFrame | None = None,
                 oni: pd.Series | None = None) -> pd.DataFrame:
    """Closest historical months to ``query``, with the ONI path that followed each.

    ``query`` defaults to the most recent month with a complete state vector.
    """
    oni = _oni() if oni is None else oni
    states = state_matrix(oni) if states is None else states
    query = states.index[-1] if query is None else pd.Timestamp(query)
    if query not in states.index:
        raise KeyError(f"No complete state vector for {query:%Y-%m}")

    target = states.loc[query].to_numpy()
    distances = pd.Series(
        np.linalg.norm(states.to_numpy() - target, axis=1), index=states.index)

    # A month must be far enough from the query to be a real analog, and must have an
    # observed future to report.
    gap_months = abs((states.index.year - query.year) * 12
                     + (states.index.month - query.month))
    last_usable = oni.index[-1] - pd.DateOffset(months=FORWARD_MONTHS)
    eligible = distances[(gap_months > EXCLUDE_MONTHS) & (states.index <= last_usable)]
    if eligible.empty:
        raise ValueError("No eligible analogs — record too short for these settings.")

    rows = []
    for rank, (date, dist) in enumerate(eligible.nsmallest(top_k).items(), start=1):
        for lead in range(FORWARD_MONTHS + 1):
            fwd = date + pd.DateOffset(months=lead)
            if fwd in oni.index:
                rows.append(dict(query_date=query, analog_date=date, rank=rank,
                                 distance=round(float(dist), 4), lead=lead,
                                 oni_fwd=float(oni.loc[fwd])))
    return pd.DataFrame(rows)


def compute() -> pd.DataFrame:
    return find_analogs()


def get_analogs(*, use_cache: bool = True) -> pd.DataFrame:
    path = CACHE_DIR / "analogs.parquet"
    if use_cache and path.exists():
        return pd.read_parquet(path)
    df = compute()
    df.to_parquet(path, index=False)
    return df


def main() -> None:
    df = compute()
    df.to_parquet(CACHE_DIR / "analogs.parquet", index=False)
    query = df["query_date"].iloc[0]
    print(f"Analog engine [{ANALOG_VERSION}] — query month {query:%b %Y}")
    print(f"State: ONI trajectory t-{TRAJECTORY_MONTHS}..t + "
          f"{', '.join(POINT_INDICES)}, z-scored; Euclidean distance.\n")
    for _, r in df[df["lead"] == 0].iterrows():
        path = df[df["rank"] == r["rank"]].set_index("lead")["oni_fwd"]
        print(f"  #{int(r['rank'])}  {r['analog_date']:%b %Y}  d={r['distance']:.2f}  "
              f"ONI then {r['oni_fwd']:+.2f}  ->  +6mo {path.get(6, float('nan')):+.2f}"
              f"  +12mo {path.get(12, float('nan')):+.2f}")
    print(f"\nAnalog mean at +6mo: {df[df['lead'] == 6]['oni_fwd'].mean():+.2f}"
          f"  |  +12mo: {df[df['lead'] == 12]['oni_fwd'].mean():+.2f}")
    print(f"\nSaved: {CACHE_DIR / 'analogs.parquet'}")


if __name__ == "__main__":
    main()
