"""Does feeding the LSTM other climate indices actually buy anything?

The univariate LSTM loses to SARIMA on this series, and the standing explanation
has been that it is starved of signal: ONI alone is a short, smooth, quasi-periodic
line that SARIMA's seasonal AR structure already exploits. The obvious test is to
give the recurrent model what SARIMA structurally cannot use — other basins, the
atmospheric half of the coupling, and the extratropical response — and see whether
the extra channels move the skill curve.

This module runs that test as a **paired experiment**. Extra channels are only
available from 1951-01 (the SOI's start), so a multivariate model scored against
the existing 1950-start univariate run would be compared across different training
data, different origins and a different test split — a difference that says nothing
about the channels. So both arms train here, on the identical span, split, seed,
architecture and epoch budget. The only thing that varies is the input width.

Neither arm replaces the ensemble member. ``lstm_enso.py`` still writes the model
that ``ensemble.py`` averages with SARIMA; this writes a comparison only.

Output (under data/cache/)
-------------------------
``skill_variants.parquet`` : (model, variant, lead, rmse, mae, acc, msss_vs_persistence)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = _ROOT / "data" / "cache"
sys.path.insert(0, str(_ROOT / "forecasting" / "verification"))
sys.path.insert(0, str(_ROOT / "data" / "ingest"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from climate_indices import model_features  # noqa: E402
from lstm_enso import get_oni_series, run  # noqa: E402
from skill_metrics import skill_by_lead  # noqa: E402

logger = logging.getLogger(__name__)

# What the model is allowed to see besides the ONI.
#
# Chosen for what each channel adds that the ONI does not already carry:
#   NINO12, NINO3, NINO4 — unsmoothed, spatially resolved SST. The ONI is a 3-month
#       mean of Niño-3.4, so it lags its own raw signal, and the east-vs-central
#       contrast (1+2 against 4) is the EP/CP flavour distinction the single index
#       averages away.
#   SOI  — the atmospheric half of the coupling. ENSO is ocean AND atmosphere; a
#       warm anomaly with no SOI response is a different animal from a coupled one.
#   DMI  — the other basin. The IOD is the confounder the causal work keeps running
#       into, so it belongs inside the model rather than only in the caveats.
#   PNA, WP — the extratropical response, which is where the teleconnection that
#       matters for the impact side actually shows up.
#
# PDO and TNI are deliberately absent, on the same reasoning as analogs.POINT_INDICES:
# both run months behind the pack (PDO ~11 months, TNI ~4 as of 2026-08), and because
# the forward forecast needs a complete 24-month window on every channel, one laggard
# drags the whole forecast origin back to its own end date. Buying a slow-moving
# backdrop with a year of recency is a bad trade, and forward-filling it would invent
# observations. AMO never reaches here at all — model_features() drops it at source.
EXOG = ("NINO12", "NINO3", "NINO4", "SOI", "DMI", "PNA", "WP")

# If the exogenous channels cannot reach the ONI's own last month, the multivariate
# arm would be forecasting from an older origin than the control and the comparison
# would silently stop being paired. Fail loudly instead.
MAX_EXOG_LAG_MONTHS = 1


def common_span(
    oni: pd.Series | None = None, feats: pd.DataFrame | None = None
) -> tuple[pd.Series, pd.DataFrame]:
    """Slice the ONI and the exogenous frame to the span every channel covers."""
    oni = get_oni_series() if oni is None else oni
    feats = model_features() if feats is None else feats

    missing = [c for c in EXOG if c not in feats.columns]
    if missing:
        raise ValueError(
            f"Exogenous channels absent from model_features(): {', '.join(missing)}. "
            "They may have gone frozen upstream and been dropped at source."
        )
    sub = feats[list(EXOG)]
    lo = max(sub[c].dropna().index[0] for c in EXOG)
    hi = min(sub[c].dropna().index[-1] for c in EXOG)

    lag = (oni.index[-1].year - hi.year) * 12 + (oni.index[-1].month - hi.month)
    if lag > MAX_EXOG_LAG_MONTHS:
        ends = {c: f"{sub[c].dropna().index[-1]:%Y-%m}" for c in EXOG}
        laggards = sorted(ends.items(), key=lambda kv: kv[1])[:2]
        raise ValueError(
            f"Exogenous channels end {hi:%Y-%m} but the ONI runs to "
            f"{oni.index[-1]:%Y-%m} ({lag} months behind, limit {MAX_EXOG_LAG_MONTHS}). "
            f"Furthest behind: {', '.join(f'{k} ends {v}' for k, v in laggards)}. "
            "Refresh climate_indices, or drop the laggard from EXOG."
        )

    lo, hi = max(lo, oni.index[0]), min(hi, oni.index[-1])
    logger.info("Paired span %s..%s (%d months)", f"{lo:%Y-%m}", f"{hi:%Y-%m}",
                len(oni.loc[lo:hi]))
    return oni.loc[lo:hi], sub.loc[lo:hi]


def compare(*, epochs: int = 400, hidden: int = 64, origin_step: int = 1) -> pd.DataFrame:
    """Train both arms on the identical span and return their skill side by side."""
    oni, feats = common_span()

    frames = []
    for variant, exog in (("univariate", None), ("multivariate", feats)):
        backtest, _ = run(
            oni, exog=exog, hidden=hidden, epochs=epochs, origin_step=origin_step
        )
        sk = skill_by_lead(backtest)
        sk.insert(0, "variant", variant)
        sk.insert(0, "model", "LSTM")
        frames.append(sk)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Paired univariate-vs-multivariate LSTM skill comparison."
    )
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--origin-step", type=int, default=1)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    skill = compare(
        epochs=args.epochs, hidden=args.hidden, origin_step=args.origin_step
    )
    path = CACHE_DIR / "skill_variants.parquet"
    skill.to_parquet(path, index=False)

    wide = skill.pivot(index="lead", columns="variant", values="acc")
    wide["delta"] = wide["multivariate"] - wide["univariate"]
    print(f"Exogenous channels: {', '.join(EXOG)}")
    print("\nACC by lead - same span, same split, same seed, only input width differs:")
    print(wide.to_string(float_format=lambda v: f"{v:+7.3f}"))

    mean = skill.groupby("variant")["acc"].mean()
    gain = mean["multivariate"] - mean["univariate"]
    better = int((wide["delta"] > 0).sum())
    print(f"\nMean ACC  univariate {mean['univariate']:.3f}  ->  "
          f"multivariate {mean['multivariate']:.3f}  ({gain:+.3f})")
    print(f"Multivariate is ahead at {better}/{len(wide)} leads.")
    if gain <= 0:
        print("\nThe extra channels did NOT help. Report that, do not bury it.")
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
