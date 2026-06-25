"""Label ENSO phases from an SST-anomaly index (ONI or RONI).

Two notions of "phase" matter and are both produced here:

1. *Simple* threshold phase  -- per season, El Nino if anomaly >= +0.5 degC,
   La Nina if <= -0.5 degC, else Neutral. Useful for shading time series.

2. *Event* phase (official)  -- NOAA only declares an El Nino / La Nina
   *event* when the index meets the +/-0.5 degC threshold for at least FIVE
   consecutive overlapping 3-month seasons. Isolated exceedances do NOT count.
   This is the definition used to enumerate historical events (1950-present).

The module is deliberately *index-agnostic*: it operates on any tidy frame with
a value column, so the same logic labels ONI today and RONI once
``roni_fetcher.py`` is wired in. Always record which index produced a label --
NOAA adopted RONI as the official index on 16 Feb 2026 and historical
classifications differ between the two.

Intensity tiers (peak |anomaly| within an event, NOAA convention):
    Weak 0.5-0.9 | Moderate 1.0-1.4 | Strong 1.5-1.9 | Very Strong >= 2.0

Input  : ``data/cache/oni.parquet`` (default)
Output : ``data/cache/enso_phases.parquet`` with columns
    date, season, year, value, index, phase_simple, phase_event,
    intensity, event_id
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# data/process/enso_phase_labeler.py -> parents[2] is the project root.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
CACHE_DIR: Path = PROJECT_ROOT / "data" / "cache"

EL_NINO = "El Nino"
LA_NINA = "La Nina"
NEUTRAL = "Neutral"

DEFAULT_THRESHOLD = 0.5
DEFAULT_MIN_RUN = 5


def simple_phase(value: float, threshold: float = DEFAULT_THRESHOLD) -> str:
    """Classify a single anomaly value by the +/- threshold."""
    if pd.isna(value):
        return NEUTRAL
    if value >= threshold:
        return EL_NINO
    if value <= -threshold:
        return LA_NINA
    return NEUTRAL


def classify_intensity(peak_abs: float) -> str:
    """Map a peak absolute anomaly to a NOAA intensity tier."""
    if peak_abs >= 2.0:
        return "Very Strong"
    if peak_abs >= 1.5:
        return "Strong"
    if peak_abs >= 1.0:
        return "Moderate"
    if peak_abs >= 0.5:
        return "Weak"
    return "None"


def label_phases(
    df: pd.DataFrame,
    *,
    value_col: str = "oni",
    index_name: str = "ONI",
    threshold: float = DEFAULT_THRESHOLD,
    min_run: int = DEFAULT_MIN_RUN,
) -> pd.DataFrame:
    """Return ``df`` annotated with simple + event phase, intensity, event_id.

    Rows must be in chronological order of *consecutive overlapping seasons*
    (as produced by ``oni_fetcher``); consecutive rows are treated as
    consecutive seasons when measuring run length.
    """
    out = df.sort_values("date").reset_index(drop=True).copy()
    out["value"] = out[value_col]
    out["index"] = index_name
    out["phase_simple"] = out["value"].map(
        lambda v: simple_phase(v, threshold)
    )

    # Identify maximal runs where phase_simple stays constant, then keep only
    # the warm/cold runs that reach the minimum length as true "events".
    run_id = (out["phase_simple"] != out["phase_simple"].shift()).cumsum()
    out["phase_event"] = NEUTRAL
    out["intensity"] = "None"
    out["event_id"] = pd.NA

    event_counter = 0
    for _, idx in out.groupby(run_id).groups.items():
        block = out.loc[idx]
        phase = block["phase_simple"].iloc[0]
        if phase == NEUTRAL or len(block) < min_run:
            continue
        event_counter += 1
        peak_abs = block["value"].abs().max()
        out.loc[idx, "phase_event"] = phase
        out.loc[idx, "intensity"] = classify_intensity(peak_abs)
        out.loc[idx, "event_id"] = event_counter

    n_events = event_counter
    logger.info(
        "Labeled %d rows from %s: %d distinct events "
        "(El Nino seasons=%d, La Nina seasons=%d)",
        len(out),
        index_name,
        n_events,
        (out["phase_event"] == EL_NINO).sum(),
        (out["phase_event"] == LA_NINA).sum(),
    )
    cols = [
        "date",
        "season",
        "year",
        "value",
        "index",
        "phase_simple",
        "phase_event",
        "intensity",
        "event_id",
    ]
    return out[[c for c in cols if c in out.columns]]


def event_summary(labeled: pd.DataFrame) -> pd.DataFrame:
    """Collapse a labeled frame into one row per ENSO event.

    Feeds the historical event cards (peak value, duration, intensity).
    """
    events = labeled.dropna(subset=["event_id"]).copy()
    if events.empty:
        return pd.DataFrame(
            columns=[
                "event_id", "phase", "start", "end", "n_seasons",
                "peak_value", "peak_season", "intensity",
            ]
        )

    rows = []
    for eid, grp in events.groupby("event_id"):
        phase = grp["phase_event"].iloc[0]
        # Peak = most extreme value in the event's direction.
        peak_idx = (
            grp["value"].idxmax() if phase == EL_NINO else grp["value"].idxmin()
        )
        peak_row = grp.loc[peak_idx]
        rows.append(
            {
                "event_id": int(eid),
                "phase": phase,
                "start": grp["date"].min(),
                "end": grp["date"].max(),
                "n_seasons": len(grp),
                "peak_value": round(float(peak_row["value"]), 2),
                "peak_season": f"{peak_row['season']} {int(peak_row['year'])}",
                "intensity": grp["intensity"].iloc[0],
            }
        )
    summary = pd.DataFrame(rows).sort_values("start").reset_index(drop=True)
    return summary


def main() -> None:
    """CLI: label ONI (default) and write ``data/cache/enso_phases.parquet``."""
    parser = argparse.ArgumentParser(description="Label ENSO phases from an index.")
    parser.add_argument(
        "--input",
        default=str(CACHE_DIR / "oni.parquet"),
        help="Parquet with date/season/year + value column (default: oni.parquet).",
    )
    parser.add_argument("--value-col", default="oni")
    parser.add_argument("--index-name", default="ONI")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--min-run", type=int, default=DEFAULT_MIN_RUN)
    parser.add_argument(
        "--output", default=str(CACHE_DIR / "enso_phases.parquet")
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    df = pd.read_parquet(args.input)
    labeled = label_phases(
        df,
        value_col=args.value_col,
        index_name=args.index_name,
        threshold=args.threshold,
        min_run=args.min_run,
    )
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    labeled.to_parquet(out_path, engine="pyarrow", index=False)

    summary = event_summary(labeled)
    print(f"Labeled rows : {len(labeled):,}")
    print(f"Events found : {len(summary)}")
    print(f"Saved        : {out_path}\n")
    if not summary.empty:
        recent = summary.tail(8).copy()
        recent["start"] = recent["start"].dt.strftime("%Y-%m")
        recent["end"] = recent["end"].dt.strftime("%Y-%m")
        print("Most recent events:")
        print(
            recent[
                ["phase", "start", "end", "n_seasons", "peak_value", "intensity"]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
