"""Monthly data refresh — runs the existing pipeline modules in dependency order.

Usage (from the repo root, any Python works — it shells out to .venv):
    python scripts/refresh_data.py            # full refresh
    python scripts/refresh_data.py --no-lstm  # skip the slow LSTM re-train

Each step is an existing module's own `__main__` block; this script adds no
pipeline logic of its own. After a clean run: review `git diff data/cache`,
commit, push — the HF Space redeploys itself (deploy-hf.yml watches
data/cache/**). NOAA CPC publishes the new ONI value ~5th of each month, so
run this shortly after that. The Vercel front-door is static — never needs
a data refresh.

Deliberately NOT run: monsoon_fetcher.py (static 1901-2017 dataset),
advisory_fetcher.py (fetched live at page load), lag_correlator / granger
(computed on-demand in pages 04/05).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.exists():  # non-Windows fallback
    PY = ROOT / ".venv" / "bin" / "python"
if not PY.exists():  # no .venv at all (CI runner) — reuse this interpreter
    PY = Path(sys.executable)

# (label, module path) in dependency order.
STEPS = [
    ("ONI (CPC ascii)",          "data/ingest/oni_fetcher.py"),
    # Cheap (one small text file) and the freshest number on the desk. The pages
    # read it live; this only refreshes the offline-fallback snapshot.
    ("Weekly Nino-3.4 snapshot", "data/ingest/weekly_nino34.py"),
    # --no-cache: their 30-day caches can straddle a month boundary and miss
    # the newly published ERSST month (raw netCDF is also cleared below).
    ("ERSSTv5 grids (~150MB download)", "data/ingest/ersst_fetcher.py --no-cache"),
    ("RONI",                     "data/process/roni_calculator.py --no-cache"),
    ("ENSO phases",              "data/process/enso_phase_labeler.py"),
    ("Commodities (Pink Sheet — snapshot still ends 2024-12)", "data/ingest/pink_sheet.py"),
    ("SARIMA forecast+backtest", "forecasting/baselines/arima_model.py"),
    ("LSTM forecast+backtest (slow, torch)", "forecasting/ml_models/lstm_enso.py"),
    ("Ensemble + skill",         "forecasting/ensemble.py"),
    ("Exposure index",           "data/process/exposure_index.py"),
    ("Landing causation verdicts", "data/process/landing_causation.py"),
    ("India ENSO x IOD engine",  "data/process/enso_flavor_iod.py"),
    ("Unit tests (sanity gate)", "tests/test_core.py"),
]

DATE_CACHES = [
    "oni.parquet", "roni.parquet", "enso_phases.parquet",
    "sst_anomaly_grids.parquet", "forecasts_all.parquet",
    "weekly_nino34.parquet",
]


def cache_dates() -> dict[str, str]:
    import pandas as pd  # deferred so the run starts printing immediately
    out = {}
    for name in DATE_CACHES:
        p = ROOT / "data" / "cache" / name
        if not p.exists():
            out[name] = "MISSING"
            continue
        df = pd.read_parquet(p)
        col = next((c for c in df.columns if "date" in c.lower() or "month" in c.lower()), None)
        out[name] = str(df[col].max())[:10] if col else f"{len(df)} rows"
    return out


def main() -> int:
    skip_lstm = "--no-lstm" in sys.argv
    before = cache_dates()

    # Force a fresh ERSST download: the fetcher's 30-day raw cache can straddle
    # a month boundary and miss the newly published month (bit us 2026-07-10:
    # raw from Jun 25 was "fresh" but lacked June). 150 MB monthly is fine.
    raw = ROOT / "data" / "raw" / "ersst_v5_sst.mnmean.nc"
    if raw.exists():
        raw.unlink()
        print("-- CLEAR data/raw ERSST netCDF (forces re-download of newest month)")

    for label, rel in STEPS:
        if skip_lstm and "lstm" in rel:
            print(f"-- SKIP  {label}")
            continue
        print(f"== RUN   {label}  ({rel})", flush=True)
        r = subprocess.run(
            [str(PY), *rel.split()], cwd=ROOT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        if r.returncode != 0:
            print(f"!! FAILED at '{label}' (exit {r.returncode}). Caches from earlier "
                  "steps are already updated; fix and re-run — steps are idempotent.")
            return r.returncode

    after = cache_dates()
    print("\nCache freshness (max date, before -> after):")
    for name in DATE_CACHES:
        mark = "  (unchanged)" if before[name] == after[name] else ""
        print(f"  {name:28s} {before[name]} -> {after[name]}{mark}")

    # Regression gate. This is what makes an unattended CI refresh safe to commit:
    # a cache must never come back MISSING or with an OLDER max date than it had.
    # ponytail: date monotonicity only — a truncated series drops its max date too,
    # so a separate row-count check would earn nothing.
    regressions = [
        f"{name}: {before[name]} -> {after[name]}"
        for name in DATE_CACHES
        if after[name] == "MISSING"
        or (before[name] not in ("MISSING",) and after[name] < before[name])
    ]
    if regressions:
        print("\n!! REGRESSION — refusing to vouch for these caches:")
        for r in regressions:
            print(f"   {r}")
        print("Do NOT commit. Investigate upstream before pushing.")
        return 1

    print("\nNext: git diff data/cache  ->  commit  ->  push (HF Space redeploys itself).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
