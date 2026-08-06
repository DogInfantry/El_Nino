"""Ancillary climate indices — the second opinions on the ONI.

Why this exists
---------------
The desk reads one number (the ONI) and forecasts it from its own history. That is a large
part of why the LSTM loses to SARIMA: a univariate model of a coupled ocean-atmosphere
system has nothing to couple to. These indices are the missing predictors, and they are
also a genuine cross-check — the SOI is the *atmospheric* half of ENSO, so a warm SST
anomaly with no SOI response is a different animal from one the atmosphere has confirmed.

Right now: ONI +0.98 (AMJ 2026), SOI -4.00 (Jul 2026). The atmosphere is coupled.

Sources (free, no auth)
-----------------------
NOAA PSL ``/data/correlation/*.data`` — year rows of 12 monthly values.
NOAA PSL ``dmi.had.long.csv``        — long HadISST Dipole Mode Index, 1870 onward.

.. note::
   **The Bureau of Meteorology is deliberately NOT used.** Requesting
   ``bom.gov.au/climate/mjo/graphics/rmm.74toRealtime.txt`` returns a block page stating
   the Bureau "does not support web scraping: if you are trying to access Bureau data
   through automated means, you should stop." That is the data owner declining automated
   access, so the RMM/MJO index is out of scope rather than worked around. MJO is a daily
   sub-seasonal index anyway — of limited use to a monthly desk.

.. warning::
   PSL's ``/data/correlation/`` directory mixes live and long-abandoned files. Some stop
   updating while still returning HTTP 200 — the same trap as CPC's frozen
   ``wksst8110.for``. :func:`coverage` reports each index's last valid month and
   :func:`main` flags any that trail the pack, so a dead feed cannot quietly ride along as
   a model input.

Output
------
``data/cache/climate_indices.parquet`` (tidy/long):
    date   (datetime64) -- month start, e.g. 2026-07-01
    index  (str)        -- SOI, NINO12, NINO3, NINO34, NINO4, TNI, PDO, AMO, PNA, WP, DMI
    value  (float)      -- the index value; sentinels dropped, never zero-filled
    source (str)        -- psl_correlation | psl_dmi_had_long
"""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from _common import cache_path, get_session, save_parquet

logger = logging.getLogger(__name__)

CACHE_NAME = "climate_indices.parquet"
PSL_BASE = "https://psl.noaa.gov/data/correlation/"
DMI_URL = "https://www.psl.noaa.gov/data/timeseries/month/data/dmi.had.long.csv"

# index name -> PSL filename. The Niño regions come from the same ERSSTv5 the ONI does,
# so they stay consistent with the desk's primary series rather than a competing product.
PSL_INDICES: dict[str, str] = {
    "SOI":    "soi.data",           # atmospheric half of ENSO (Tahiti - Darwin)
    "NINO12": "nina1.anom.data",    # 0-10S, 90W-80W   — coastal / far-eastern Pacific
    "NINO3":  "nina3.anom.data",    # 5N-5S, 150W-90W  — eastern Pacific
    "NINO34": "nina34.anom.data",   # 5N-5S, 170W-120W — the ONI region itself
    "NINO4":  "nina4.anom.data",    # 5N-5S, 160E-150W — central Pacific
    "TNI":    "tni.data",           # Trans-Niño: east-vs-central gradient (ENSO flavour)
    "PDO":    "pdo.data",           # Pacific Decadal Oscillation — low-frequency backdrop
    "AMO":    "amon.us.data",       # Atlantic Multidecadal Oscillation, unsmoothed
    "PNA":    "pna.data",           # Pacific-North American teleconnection
    "WP":     "wp.data",            # Western Pacific pattern
}

# An index trailing the freshest one by more than this is treated as abandoned upstream.
FROZEN_TOLERANCE_DAYS = 400


def parse_psl_data(text: str) -> pd.DataFrame:
    """Parse a NOAA PSL ``/data/correlation/*.data`` file into tidy (date, value) rows.

    Layout::

            1948        2026        <- start and end year
        1948 -99.99 -99.99 ...      <- 12 monthly values
        ...
        2026   1.80   2.40 ... -99.99
          -99.99                    <- the missing-value sentinel, on its own line
          SOI Index from CPC        <- free-text footer

    The sentinel is read from the file rather than assumed: these files do not all use
    -99.99, and hard-coding it would silently turn a real -9.9 reading into data.
    """
    lines = text.splitlines()
    if not lines:
        raise ValueError("Empty PSL file.")
    head = lines[0].split()
    if len(head) < 2:
        raise ValueError(f"Unexpected PSL header: {lines[0]!r}")
    start_yr, end_yr = int(head[0]), int(head[1])

    rows: list[tuple[int, list[float]]] = []
    sentinel: float | None = None
    for line in lines[1:]:
        parts = line.split()
        if len(parts) == 13 and parts[0].isdigit() and start_yr <= int(parts[0]) <= end_yr:
            rows.append((int(parts[0]), [float(p) for p in parts[1:]]))
        elif len(parts) == 1 and sentinel is None:
            try:                       # first lone number after the block is the sentinel
                sentinel = float(parts[0])
            except ValueError:
                pass
    if not rows:
        raise ValueError("No PSL data rows parsed — upstream format may have changed.")
    if sentinel is None:
        sentinel = -99.99
        logger.warning("No sentinel line found; assuming %.2f", sentinel)

    out = []
    for year, values in rows:
        for month, value in enumerate(values, start=1):
            if value != sentinel:
                out.append((pd.Timestamp(year, month, 1), value))
    return pd.DataFrame(out, columns=["date", "value"]).sort_values("date")


def parse_dmi_csv(text: str) -> pd.DataFrame:
    """Parse PSL's long DMI csv (``YYYY-MM-DD,value``, sentinel -9999).

    The file pads the rest of the current year with the sentinel, so dropping it is what
    keeps "latest DMI" honest instead of reporting December of this year.
    """
    rows = []
    for line in text.splitlines()[1:]:          # line 0 is a free-text header
        parts = line.split(",")
        if len(parts) != 2:
            continue
        try:
            date, value = pd.Timestamp(parts[0].strip()), float(parts[1])
        except ValueError:
            continue
        if value <= -999:                        # -9999 sentinel
            continue
        rows.append((date, value))
    if not rows:
        raise ValueError("No DMI rows parsed — upstream format may have changed.")
    return pd.DataFrame(rows, columns=["date", "value"]).sort_values("date")


def fetch_all(timeout: float = 45.0) -> pd.DataFrame:
    """Download every index into one tidy frame. Raises only if nothing could be fetched.

    A single failing index is logged and skipped rather than aborting the run — one dead
    PSL file should not cost the desk the other ten.
    """
    session = get_session()
    frames = []
    for name, filename in PSL_INDICES.items():
        try:
            resp = session.get(PSL_BASE + filename, timeout=timeout)
            resp.raise_for_status()
            df = parse_psl_data(resp.text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping %s (%s): %s", name, filename, exc)
            continue
        df["index"], df["source"] = name, "psl_correlation"
        frames.append(df)

    try:
        resp = session.get(DMI_URL, timeout=timeout)
        resp.raise_for_status()
        dmi = parse_dmi_csv(resp.text)
        dmi["index"], dmi["source"] = "DMI", "psl_dmi_had_long"
        frames.append(dmi)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Skipping DMI: %s", exc)

    if not frames:
        raise RuntimeError("No climate indices could be fetched.")
    out = pd.concat(frames, ignore_index=True)[["date", "index", "value", "source"]]
    return out.sort_values(["index", "date"]).reset_index(drop=True)


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Per-index first/last month and row count, with a frozen-upstream flag."""
    g = df.groupby("index")["date"]
    cov = pd.DataFrame({"first": g.min(), "last": g.max(), "n": g.count()})
    newest = cov["last"].max()
    cov["days_behind"] = (newest - cov["last"]).dt.days
    cov["frozen"] = cov["days_behind"] > FROZEN_TOLERANCE_DAYS
    return cov.sort_values("last")


def load(*, use_cache: bool = True) -> pd.DataFrame:
    path = cache_path(CACHE_NAME)
    if use_cache and path.exists():
        return pd.read_parquet(path)
    df = fetch_all()
    save_parquet(df, path)
    return df


def wide(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Month-indexed wide frame, one column per index. Includes frozen ones."""
    df = load() if df is None else df
    return df.pivot(index="date", columns="index", values="value").sort_index()


def model_features(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Wide frame with frozen upstreams removed — what a model may actually consume.

    An index that stopped updating still has a valid history, so it looks like a perfectly
    good training feature. At inference time it is simply absent, and the model quietly
    extrapolates from whatever fill the pipeline used. Dropping it here means the exclusion
    happens once, at the source, instead of being remembered at every call site.

    As of 2026-08: AMO is frozen at 2023-01 and is dropped.
    """
    df = load() if df is None else df
    frozen = coverage(df).query("frozen").index.tolist()
    if frozen:
        logger.warning("Excluding frozen indices from model features: %s", ", ".join(frozen))
    return wide(df).drop(columns=frozen, errors="ignore")


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the ancillary climate indices.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    df = fetch_all()
    path = save_parquet(df, cache_path(CACHE_NAME))
    cov = coverage(df)
    pd.set_option("display.width", 130)
    print(f"Saved {len(df)} rows across {df['index'].nunique()} indices -> {path}\n")
    show = cov.copy()
    show["first"] = show["first"].dt.strftime("%Y-%m")
    show["last"] = show["last"].dt.strftime("%Y-%m")
    print(show.to_string())
    frozen = cov[cov["frozen"]]
    if not frozen.empty:
        print("\n!! FROZEN UPSTREAM — these still return HTTP 200 but stopped updating.")
        print("   Do NOT feed them to a model as if they were current:")
        for name, r in frozen.iterrows():
            print(f"   {name:7s} last {r['last']:%Y-%m}  ({int(r['days_behind'])} d behind)")


if __name__ == "__main__":
    main()
