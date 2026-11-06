"""ENSO flavor (CP vs EP), the Indian Ocean Dipole (IOD/DMI), and the ENSO x IOD
conditional base-rate matrix for the Indian monsoon — computed from ERSSTv5.

WHY (the analytical edge, not the textbook first-order story)
-------------------------------------------------------------
"El Niño -> weak monsoon" is shallow. Two conditioning variables carry the variance:

  1. ENSO *flavor* — Central-Pacific (Modoki) El Niños suppress the monsoon more
     reliably than Eastern-Pacific (canonical) ones (Kumar et al., Science 2006).
     Magnitude (ONI) is flavor-blind. Classified here on the MATURE (DJF) phase via
     the El Niño Modoki Index (EMI, Ashok 2007), with an AMPLITUDE CONTROL so flavor
     is not just a proxy for "weak event".
  2. The IOD (DMI) — a positive IOD can offset El Niño's drying (Ashok et al. 2001).
     Measured at its SON PEAK (a JJAS season-mean blurs the 1997-vs-2015 contrast).

Significance of the IOD conditioning is tested with Fisher's exact (n is small — be
honest about power).

INDICES (monthly SSTA, cos-lat weighted boxes, 1991-2020 base; 0-360 lon)
  Niño-3 210-270E / Niño-4 160-210E / Niño-3.4 190-240E (5S-5N)
  EMI = A(165-220E,10S-10N) - 0.5*B(250-290E,15S-5N) - 0.5*C(125-145E,10S-20N)
  DMI = SSTA(50-70E,10S-10N) - SSTA(90-110E,10S-0N)

Monsoon OUTCOME (all-India JJAS % departure from LPA) is the only non-SST input —
documented IMD/IITM values for El Niño years; wire to the live IMD feed in production.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import statsmodels.formula.api as smf
from scipy.stats import fisher_exact

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "ersst_v5_sst.mnmean.nc"
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CLIM_BASE = ("1991-01-01", "2020-12-31")

BOXES = {
    "nino3": dict(lat=(-5, 5), lon=(210, 270)),
    "nino4": dict(lat=(-5, 5), lon=(160, 210)),
    "nino34": dict(lat=(-5, 5), lon=(190, 240)),
    "iod_w": dict(lat=(-10, 10), lon=(50, 70)),
    "iod_e": dict(lat=(-10, 0), lon=(90, 110)),
    "emi_a": dict(lat=(-10, 10), lon=(165, 220)),
    "emi_b": dict(lat=(-15, 5), lon=(250, 290)),
    "emi_c": dict(lat=(-10, 20), lon=(125, 145)),
}

# all-India JJAS rainfall departure (% of LPA), El Niño years. Source: IMD / IITM.
MONSOON_PCT = {
    1951: -19, 1957: -4, 1963: -1, 1965: -18, 1972: -24, 1982: -15,
    1987: -19, 1991: -9, 1994: 10, 1997: 2, 2002: -19, 2004: -14,
    2006: 0, 2009: -22, 2014: -12, 2015: -14, 2018: -9, 2023: -6,
}

# Seasonal windows as (month, year_delta) relative to the monsoon year Y.
JJAS = [(6, 0), (7, 0), (8, 0), (9, 0)]   # developing-phase / monsoon season
SON = [(9, 0), (10, 0), (11, 0)]          # IOD peak
DJF = [(12, 0), (1, 1), (2, 1)]           # ENSO mature phase (flavor classified here)


def _wmean(anom: xr.DataArray, lat, lon) -> xr.DataArray:
    sub = anom.sel(lat=slice(*lat), lon=slice(*lon))
    w = np.cos(np.deg2rad(sub.lat))
    return sub.weighted(w).mean(("lat", "lon"))


def monthly_indices() -> pd.DataFrame:
    ds = xr.open_dataset(RAW_FILE).sortby("lat")
    sst = ds["sst"]
    clim = sst.sel(time=slice(*CLIM_BASE)).groupby("time.month").mean("time")
    anom = sst.groupby("time.month") - clim
    cols = {k: _wmean(anom, **b).to_numpy() for k, b in BOXES.items()}
    df = pd.DataFrame(cols)
    df["date"] = pd.DatetimeIndex(ds["time"].values)
    ds.close()
    df["y"] = df["date"].dt.year
    df["mo"] = df["date"].dt.month
    df["emi"] = df["emi_a"] - 0.5 * df["emi_b"] - 0.5 * df["emi_c"]
    df["dmi"] = df["iod_w"] - df["iod_e"]
    return df


def _season(lut: pd.DataFrame, col: str, year: int, spec) -> float:
    vals = [lut.loc[(year + dy, mo), col] for mo, dy in spec
            if (year + dy, mo) in lut.index]
    return float(np.mean(vals)) if vals else np.nan


def build_table() -> pd.DataFrame:
    df = monthly_indices()
    lut = df.set_index(["y", "mo"])
    rows = []
    for yr, pct in sorted(MONSOON_PCT.items()):
        n34_djf = _season(lut, "nino34", yr, DJF)
        n3_djf = _season(lut, "nino3", yr, DJF)
        n4_djf = _season(lut, "nino4", yr, DJF)
        emi_djf = _season(lut, "emi", yr, DJF)
        dmi_son = _season(lut, "dmi", yr, SON)
        dmi_jjas = _season(lut, "dmi", yr, JJAS)
        # flavor on mature phase: CP if central pole >= eastern pole AND EMI positive
        flavor = "CP" if (n4_djf >= n3_djf and emi_djf > 0) else "EP"
        iod = ("positive" if dmi_son >= 0.40 else
               "negative" if dmi_son <= -0.40 else "neutral")
        rows.append(dict(
            year=yr, n34_djf=round(n34_djf, 2), emi_djf=round(emi_djf, 2),
            flavor=flavor, dmi_son=round(dmi_son, 2), dmi_jjas=round(dmi_jjas, 2),
            iod=iod, monsoon_pct=pct,
            outcome=("DEFICIENT" if pct <= -10 else "EXCESS" if pct >= 10 else "Normal"),
            deficient=int(pct <= -10),
        ))
    return pd.DataFrame(rows)


def analyse(tbl: pd.DataFrame) -> None:
    pd.set_option("display.width", 170)
    print("=== ENSO x IOD x flavor — El Niño monsoon years (computed from ERSSTv5) ===")
    print(tbl.to_string(index=False))

    # --- IOD conditioning (SON peak), with significance ---
    pos = tbl[tbl["iod"] == "positive"]
    other = tbl[tbl["iod"] != "positive"]
    a, b = int(pos["deficient"].sum()), int((1 - pos["deficient"]).sum())
    c, d = int(other["deficient"].sum()), int((1 - other["deficient"]).sum())
    odds, p = fisher_exact([[a, b], [c, d]], alternative="less")
    print("\n=== IOD conditioning (SON-peak DMI) ===")
    print(f"  El Niño + positive IOD : n={len(pos):2d}  P(deficient)={pos['deficient'].mean():.2f}"
          f"  mean monsoon={pos['monsoon_pct'].mean():+.1f}%")
    print(f"  El Niño + neutral/-ve  : n={len(other):2d}  P(deficient)={other['deficient'].mean():.2f}"
          f"  mean monsoon={other['monsoon_pct'].mean():+.1f}%")
    print(f"  Fisher exact (one-sided, +IOD less deficient): p = {p:.3f}"
          f"   -> {'significant' if p < 0.05 else 'NOT significant at n=18 (underpowered)'}")

    # --- flavor with amplitude control (moderate+ events only: |N3.4 DJF|>=1.0) ---
    strong = tbl[tbl["n34_djf"] >= 1.0]
    print("\n=== Flavor (DJF EMI), amplitude-controlled to moderate+ El Niño (N3.4 DJF >= 1.0) ===")
    if len(strong):
        g = strong.groupby("flavor").agg(n=("year", "size"),
                                         P_deficient=("deficient", "mean"),
                                         mean_monsoon=("monsoon_pct", "mean"))
        print(g.round(2).to_string())
        print(f"  (strong-event years: {sorted(strong['year'])})")
    print("  Full-sample flavor (incl. weak events, for contrast):")
    gf = tbl.groupby("flavor").agg(n=("year", "size"),
                                   P_deficient=("deficient", "mean"),
                                   mean_monsoon=("monsoon_pct", "mean"))
    print(gf.round(2).to_string())

    # --- did SON timing separate 1997 vs 2015? ---
    y97, y15 = tbl[tbl.year == 1997].iloc[0], tbl[tbl.year == 2015].iloc[0]
    print("\n=== 1997 vs 2015 — does SON-peak IOD separate them? ===")
    print(f"  1997: DMI_JJAS={y97['dmi_jjas']:+.2f}  DMI_SON={y97['dmi_son']:+.2f} ({y97['iod']})"
          f"  -> {y97['outcome']} ({y97['monsoon_pct']:+d}%)")
    print(f"  2015: DMI_JJAS={y15['dmi_jjas']:+.2f}  DMI_SON={y15['dmi_son']:+.2f} ({y15['iod']})"
          f"  -> {y15['outcome']} ({y15['monsoon_pct']:+d}%)")


# DEFICIENT / Normal / EXCESS cut, matching monsoon_fetcher so the two series stay
# directly comparable when the gridded cache is absent.
_CATEGORY_BINS = [-100, -10, 10, 1000]
_CATEGORY_LABELS = ["DEFICIENT", "Normal", "EXCESS"]


def _monsoon_series() -> pd.DataFrame:
    """All-India JJAS departures: the gridded product when available, else subdivisions.

    The gridded series is area-weighted by cos(lat) and its 1971-2020 normal lands within
    1.1% of IMD's published ~868 mm, where the unweighted subdivision mean sits ~20% high.
    It also runs to 2024 rather than 2017. But it needs a ~1.9 GB manual download, so a
    fresh clone will not have it — falling back keeps this engine runnable rather than
    making the whole India analysis contingent on a bulk fetch.
    """
    grid_path = CACHE_DIR / "monsoon_india_grid.parquet"
    if grid_path.exists():
        g = pd.read_parquet(grid_path)
        g = g[g["region"] == "All-India"][["year", "jjas_mm", "lpa_pct"]].copy()
        g["category"] = pd.cut(g["lpa_pct"], bins=_CATEGORY_BINS,
                               labels=_CATEGORY_LABELS).astype(str)
        g.attrs["source"] = "imd_gridded_0p25_area_weighted"
        return g.sort_values("year").reset_index(drop=True)
    mon = pd.read_parquet(CACHE_DIR / "monsoon_india.parquet")
    mon.attrs["source"] = "imd_subdivision_unweighted"
    return mon


# The P(deficient) grid's bins, shared with iod_now() so the page's "current cell" is the
# same cut the grid was built on.
_ENSO_BINS, _ENSO_LABELS = [-9, -0.5, 0.5, 9], ["La Nina", "Neutral", "El Nino"]
_IOD_BINS, _IOD_LABELS = [-9, -0.2, 0.2, 9], ["IOD-neg", "IOD-neu", "IOD-pos"]
_JJAS_MONTHS = (6, 7, 8, 9)


def _hadisst_dmi() -> pd.Series:
    """PSL's HadISST DMI from the indices cache: the desk's second reading of the IOD."""
    idx = pd.read_parquet(CACHE_DIR / "climate_indices.parquet")
    return idx[idx["index"] == "DMI"].set_index("date")["value"].astype(float).sort_index()


def _jjas_mean(s: pd.Series, year: int) -> float:
    """JJAS mean, NaN unless all four months exist. A partial season is not a season."""
    vals = s.reindex([pd.Timestamp(year, m, 1) for m in _JJAS_MONTHS])
    return float(vals.mean()) if vals.notna().all() else np.nan


def _cells(d: pd.DataFrame, dmi_col: str) -> pd.DataFrame:
    """P(deficient) by ENSO x IOD, on one DMI series. Keeps counts: these cells are small."""
    t = d[["nino34", dmi_col, "category"]].dropna()
    enso = pd.cut(t["nino34"], _ENSO_BINS, labels=_ENSO_LABELS).rename("enso")
    iodp = pd.cut(t[dmi_col], _IOD_BINS, labels=_IOD_LABELS).rename("iodp")
    deficient = (t["category"] == "DEFICIENT").astype(int)
    return (deficient.groupby([enso, iodp], observed=False)
            .agg(p_deficient="mean", n="size", n_deficient="sum").reset_index())


def robustness(d: pd.DataFrame) -> pd.DataFrame:
    """The DMI coefficient on both series, across the specifications that move it.

    A single p-value oversold this result. ERSST and HadISST read the same ocean with
    r~0.8 and different trends, so the published OLS is shown beside a trend control and
    the shorter samples rather than standing alone.
    """
    hi = int(d["year"].max())
    specs = [(f"1901–{hi}", d, ""), (f"1901–{hi}, year trend", d, " + year"),
             (f"1951–{hi}", d[d["year"] >= 1951], ""), (f"1981–{hi}", d[d["year"] >= 1981], "")]
    rows = []
    for label, sub, extra in specs:
        for series, col in (("ERSST", "dmi"), ("HadISST", "dmi_had")):
            m = smf.ols(f"lpa_pct ~ nino34 + {col}{extra}", data=sub.dropna(subset=[col])).fit()
            rows.append(dict(spec=label, series=series, coef=float(m.params[col]),
                             p=float(m.pvalues[col]), n=int(m.nobs)))
    return pd.DataFrame(rows)


def iod_now(df: pd.DataFrame, had: pd.Series) -> pd.DataFrame:
    """This monsoon season's ENSO and IOD reading, from the latest SST rather than prose.

    The season is the newest year with a June in the record, so January to May still
    reports last year's monsoon. ``n_months`` is under 4 while a season is in progress.
    """
    df = df.dropna(subset=["dmi", "nino34"])
    year = int(df.loc[df["mo"] == 6, "y"].max())
    season = df[(df["y"] == year) & df["mo"].isin(_JJAS_MONTHS)]
    had_vals = had.reindex([pd.Timestamp(year, m, 1) for m in _JJAS_MONTHS]).dropna()
    nino34, dmi = float(season["nino34"].mean()), float(season["dmi"].mean())
    return pd.DataFrame([dict(
        year=year, n_months=len(season), nino34=nino34, dmi=dmi,
        enso_cell=str(pd.cut([nino34], _ENSO_BINS, labels=_ENSO_LABELS)[0]),
        iod_cell=str(pd.cut([dmi], _IOD_BINS, labels=_IOD_LABELS)[0]),
        had_dmi=float(had_vals.mean()) if len(had_vals) else np.nan,
        had_months=len(had_vals), latest_date=df["date"].iloc[-1],
        latest_dmi=float(df["dmi"].iloc[-1]))])


def scenario_outputs() -> dict:
    """Full-sample (n~117) analysis — returns data (no printing) for the dashboard.

    The El Niño-only 2x2 is inherently underpowered (~18 events exist). The proper
    test regresses the monsoon on concurrent ENSO and IOD across ALL years.
    Returns dict(reg=<coef/p/R² dict>, grid=<long ENSO×IOD P(deficient) df>, years=df).
    """
    mon = _monsoon_series()
    df = monthly_indices()
    lut = df.set_index(["y", "mo"])
    rows = [dict(year=int(yr),
                 nino34=_season(lut, "nino34", yr, JJAS),  # concurrent monsoon-season ENSO
                 dmi=_season(lut, "dmi", yr, JJAS),         # concurrent IOD
                 dmi_son=_season(lut, "dmi", yr, SON))      # IOD peak
            for yr in mon["year"]]
    d = pd.DataFrame(rows).merge(mon[["year", "lpa_pct", "category"]], on="year").dropna()

    m = smf.ols("lpa_pct ~ nino34 + dmi", data=d).fit()
    reg = dict(nino34_coef=float(m.params["nino34"]), nino34_p=float(m.pvalues["nino34"]),
               dmi_coef=float(m.params["dmi"]), dmi_p=float(m.pvalues["dmi"]),
               r2=float(m.rsquared), n=int(m.nobs))

    had = _hadisst_dmi()
    d["dmi_had"] = [_jjas_mean(had, int(y)) for y in d["year"]]
    return dict(reg=reg, grid=_cells(d, "dmi"), grid_had=_cells(d, "dmi_had"),
                robustness=robustness(d), now=iod_now(df, had), years=d)


def write_cache() -> None:
    """Persist the scenario outputs so the dashboard never touches the netCDF."""
    out = scenario_outputs()
    out["grid"].to_parquet(CACHE_DIR / "india_enso_iod.parquet", index=False)
    out["grid_had"].to_parquet(CACHE_DIR / "india_enso_iod_hadisst.parquet", index=False)
    out["robustness"].to_parquet(CACHE_DIR / "india_robustness.parquet", index=False)
    out["now"].to_parquet(CACHE_DIR / "india_iod_now.parquet", index=False)
    pd.DataFrame([out["reg"]]).to_parquet(CACHE_DIR / "india_regression.parquet", index=False)
    out["years"][["year", "nino34", "dmi", "dmi_had", "dmi_son", "lpa_pct", "category"]].to_parquet(
        CACHE_DIR / "india_years.parquet", index=False)


def powered() -> None:
    out = scenario_outputs()
    reg, grid = out["reg"], out["grid"]
    print("\n" + "=" * 72)
    print(f"POWERED full-sample analysis — n={reg['n']}, monsoon = all-India JJAS % dep.")
    print("=" * 72)
    print("OLS: monsoon% ~ ENSO(Nino3.4) + IOD(DMI), concurrent JJAS")
    print(f"  nino34  coef={reg['nino34_coef']:+6.2f}  p={reg['nino34_p']:.4f}")
    print(f"  dmi     coef={reg['dmi_coef']:+6.2f}  p={reg['dmi_p']:.4f}")
    print(f"  R2 = {reg['r2']:.2f}")
    print("\nP(deficient monsoon) by ENSO x IOD (all years):")
    print(grid.pivot(index="enso", columns="iodp", values="p_deficient").round(2).to_string())
    print("\nSame grid on HadISST DMI. Cells that move between series carry no call:")
    print(out["grid_had"].pivot(index="enso", columns="iodp", values="p_deficient").round(2).to_string())
    print("\nDMI coefficient across series and specifications:")
    print(out["robustness"].round(4).to_string(index=False))
    print("\nThis season:")
    print(out["now"].round(2).to_string(index=False))


if __name__ == "__main__":
    analyse(build_table())
    powered()
    write_cache()
    print("\nCached: india_{enso_iod,enso_iod_hadisst,regression,robustness,iod_now,years}.parquet")
