"""EM-DAT disaster events → map bubbles, joined to the ENSO phase they occurred in.

**MANUAL INGEST.** EM-DAT is open access for non-commercial use, but it is not fetchable:
`public.emdat.be` serves the export behind a registration form and the Humanitarian Data
Exchange mirror returns 403 to automated clients. Both are the data owner setting terms,
so this module does not work around either — the same call already made for the Bureau of
Meteorology and IITM (see ``docs/METHODOLOGY.md``). You download the file once, by hand,
and this reads it.

How to use
----------
1. Register (free) at https://public.emdat.be/ and export the **natural** disaster set.
2. Drop the ``.xlsx`` (or ``.csv``) anywhere under ``data/raw/emdat/``.
3. ``python data/ingest/emdat_disasters.py -v``

Until then ``emdat_disasters.parquet`` simply does not exist, and page 02 renders without
the overlay rather than failing — the same graceful-degradation contract every other
optional cache follows.

Attribution required by the licence, and carried through to the page footer:
    EM-DAT, CRED / UCLouvain, Brussels, Belgium — https://www.emdat.be

A caveat that matters more than it looks
----------------------------------------
EM-DAT records point coordinates for only a minority of events; most rows carry a country
and no lat/lon. Bubbles can therefore only be drawn for the geocoded subset, and that
subset is **not** a random sample — large, well-reported events are likelier to be
located. This module reports the geocoded fraction on every run so the page can print it,
because a map that silently plots a third of the record looks exactly like a map of
everything.

Output
------
``data/cache/emdat_disasters.parquet`` :
    date · year · iso3 · country · dtype · lat · lon · deaths · affected · damage_kusd · phase
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from _common import cache_path, save_parquet  # noqa: E402

logger = logging.getLogger(__name__)

RAW_DIR = _HERE.parents[1] / "data" / "raw" / "emdat"
CACHE_NAME = "emdat_disasters.parquet"

# The ENSO-relevant natural hazards. Earthquakes and volcanoes are in EM-DAT too and have
# nothing to do with the Pacific ocean-atmosphere state; plotting them beside an SST field
# would invite exactly the false association this desk keeps arguing against.
KEEP_TYPES = {"drought", "flood", "wildfire", "storm"}

# EM-DAT renamed most columns in the 2023 rebuild, and people have both vintages on disk.
# Match on a squashed key (lowercase, alphanumerics only) so either export works.
_ALIASES: dict[str, tuple[str, ...]] = {
    "year": ("startyear", "year"),
    "month": ("startmonth",),
    "dtype": ("disastertype", "distype"),
    "group": ("disastergroup", "disgroup"),
    "iso3": ("iso",),
    "country": ("country", "countryname"),
    "lat": ("latitude",),
    "lon": ("longitude",),
    "deaths": ("totaldeaths",),
    "affected": ("totalaffected",),
    "damage_kusd": ("totaldamage000us", "totaldamages000us",
                    "totaldamageadjusted000us", "totaldamagesadjusted000us"),
}


def _squash(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def find_export(raw_dir: Path = RAW_DIR) -> Path:
    """Newest EM-DAT export under ``raw_dir``. Raises with instructions if absent."""
    if raw_dir.exists():
        files = [p for p in raw_dir.rglob("*")
                 if p.suffix.lower() in (".xlsx", ".xls", ".csv")]
        if files:
            return max(files, key=lambda p: p.stat().st_mtime)
    raise FileNotFoundError(
        f"No EM-DAT export found under {raw_dir}. Register at https://public.emdat.be/, "
        "export the natural-disaster set, and drop the .xlsx there. This feed is manual "
        "by design — see the module docstring."
    )


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Map either export vintage onto one column set."""
    squashed = {_squash(c): c for c in df.columns}
    out = pd.DataFrame(index=df.index)
    for target, candidates in _ALIASES.items():
        for cand in candidates:
            if cand in squashed:
                out[target] = df[squashed[cand]]
                break
    missing = {"year", "dtype", "iso3"} - set(out.columns)
    if missing:
        raise ValueError(
            f"EM-DAT export is missing required column(s) {sorted(missing)}. "
            f"Columns seen: {list(df.columns)[:12]}..."
        )
    return out


def load_export(path: Path | None = None) -> pd.DataFrame:
    path = path or find_export()
    logger.info("Reading EM-DAT export: %s", path)
    raw = (pd.read_csv(path) if path.suffix.lower() == ".csv"
           else pd.read_excel(path))
    df = _normalise(raw)

    # Natural hazards only, then the ENSO-relevant subset.
    if "group" in df.columns:
        df = df[df["group"].astype(str).str.strip().str.lower() == "natural"]
    df = df.copy()
    df["dtype"] = df["dtype"].astype(str).str.strip().str.title()
    df = df[df["dtype"].str.lower().isin(KEEP_TYPES)].copy()

    for col in ("lat", "lon", "deaths", "affected", "damage_kusd", "month"):
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])

    # Month is often blank. Defaulting it to January would invent a date that a +/- window
    # query would then treat as real, so unknown months are dropped rather than guessed —
    # and the count is logged.
    no_month = int(df["month"].isna().sum())
    if no_month:
        logger.warning("Dropping %d event(s) with no start month.", no_month)
    df = df.dropna(subset=["month"])
    df["date"] = pd.to_datetime(
        dict(year=df["year"].astype(int), month=df["month"].astype(int), day=1),
        errors="coerce")
    df = df.dropna(subset=["date"])
    df["year"] = df["year"].astype(int)
    return df


def attach_phase(df: pd.DataFrame) -> pd.DataFrame:
    """Label each event with the ENSO phase of the month it started in."""
    phases_path = Path(cache_path("enso_phases.parquet"))
    if not phases_path.exists():
        logger.warning("enso_phases.parquet missing — events will carry no phase.")
        df = df.copy()
        df["phase"] = pd.NA
        return df
    phases = pd.read_parquet(phases_path)[["date", "phase_simple"]]
    merged = df.merge(phases, on="date", how="left")
    return merged.rename(columns={"phase_simple": "phase"})


def build(path: Path | None = None) -> tuple[pd.DataFrame, dict]:
    df = attach_phase(load_export(path))
    cols = ["date", "year", "iso3", "country", "dtype", "lat", "lon",
            "deaths", "affected", "damage_kusd", "phase"]
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[cols].sort_values("date").reset_index(drop=True)

    geocoded = int(df[["lat", "lon"]].notna().all(axis=1).sum())
    stats = {
        "events": len(df),
        "geocoded": geocoded,
        "geocoded_pct": round(100.0 * geocoded / len(df), 1) if len(df) else 0.0,
        "first_year": int(df["year"].min()) if len(df) else None,
        "last_year": int(df["year"].max()) if len(df) else None,
    }
    return df, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a manual EM-DAT export.")
    parser.add_argument("--path", type=Path, default=None,
                        help="Explicit export file (default: newest under data/raw/emdat/)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    try:
        df, stats = build(args.path)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    out = save_parquet(df, cache_path(CACHE_NAME))
    print(f"EM-DAT: {stats['events']} ENSO-relevant events "
          f"{stats['first_year']}-{stats['last_year']}")
    print(f"Geocoded: {stats['geocoded']} ({stats['geocoded_pct']}%) — only these can be "
          "drawn as bubbles, and they are NOT a random sample of the record.")
    print("\nBy type:")
    print(df["dtype"].value_counts().to_string())
    if df["phase"].notna().any():
        print("\nBy ENSO phase (start month):")
        print(df["phase"].value_counts().to_string())
    print(f"\nSaved: {out}")
    print("Source: EM-DAT, CRED / UCLouvain, Brussels, Belgium — https://www.emdat.be")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
