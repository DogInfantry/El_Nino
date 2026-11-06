"""India Deep-Dive — the first region tear-sheet, built on the shared region template.

Run with::

    panel serve dashboard/pages/07_india.py --show

Generic shell (bar / DESK VIEW / map / KPI rail / Economics=live Granger+CCM / History)
comes from ``dashboard/region_template.py``. India contributes a thin ``RegionConfig`` and
its own **Climate** exhibit — the computed ENSO×IOD scenario matrix + OLS regression
(from ERSSTv5 + IMD gridded rainfall; caches built by ``data/process/enso_flavor_iod.py``,
which now reports the sample size rather than the page hard-coding it).

Every number here comes from a cache. This page once typed "rainfall −12%" and "current
setup: positive IOD" for a season the rainfall record does not reach and a DMI that read
neutral, so nothing about the present is written by hand any more.

Other regions clone this file: new config + a (usually simpler) climate view.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import panel as pn
import plotly.graph_objects as go

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
for p in (_DASH_DIR, _DASH_DIR.parent / "data" / "process"):
    sys.path.insert(0, str(p))

from theme import COLORS, CACHE_DIR, style_figure  # noqa: E402
from region_template import (  # noqa: E402
    RegionConfig, REGION_CSS, build_region, causal_chain, stance_from_cache,
)

AMBER = COLORS.get("amber", "#f4b13a")
pn.extension("plotly", raw_css=[REGION_CSS], sizing_mode="stretch_width")

# ---- India-specific data + climate exhibit -------------------------------
GRID = pd.read_parquet(CACHE_DIR / "india_enso_iod.parquet")
GRID_HAD = pd.read_parquet(CACHE_DIR / "india_enso_iod_hadisst.parquet")
REG = pd.read_parquet(CACHE_DIR / "india_regression.parquet").iloc[0].to_dict()
ROBUST = pd.read_parquet(CACHE_DIR / "india_robustness.parquet")
YEARS = pd.read_parquet(CACHE_DIR / "india_years.parquet")
NOW = pd.read_parquet(CACHE_DIR / "india_iod_now.parquet").iloc[0]
_RAIN = pd.read_parquet(CACHE_DIR / "monsoon_india_grid.parquet")
_ONI = pd.read_parquet(CACHE_DIR / "oni.parquet").set_index("date")["oni"].astype(float)
_EXPOSURE = (pd.read_parquet(CACHE_DIR / "exposure_index.parquet")
             .sort_values("index", ascending=False).reset_index(drop=True))

_FIRST, _LAST = int(YEARS["year"].min()), int(YEARS["year"].max())
_IOD_COLS, _IOD_WORD = ["IOD-neg", "IOD-neu", "IOD-pos"], ["negative", "neutral", "positive"]
_ENSO_ROWS = ["La Nina", "Neutral", "El Nino"]
_NOW_YEAR = int(NOW["year"])
_NOW_WORD = _IOD_WORD[_IOD_COLS.index(NOW["iod_cell"])]
_SEASON = (f"JJAS {_NOW_YEAR}" if int(NOW["n_months"]) == 4
           else f"Jun–{pd.Timestamp(_NOW_YEAR, 5 + int(NOW['n_months']), 1):%b} {_NOW_YEAR}")


def _dmi_son(year: int) -> float:
    r = YEARS[YEARS["year"] == year]
    return float(r["dmi_son"].iloc[0]) if len(r) else float("nan")


def _signed(v: float, digits: int = 1) -> str:
    return f"{v:+.{digits}f}".replace("-", "−")


def _heatmap() -> go.Figure:
    piv = GRID.pivot(index="enso", columns="iodp", values="p_deficient").reindex(
        index=_ENSO_ROWS, columns=_IOD_COLS)
    z = piv.values.astype(float)
    xlab, ylab = ["IOD −", "IOD neutral", "IOD +"], ["La Niña", "Neutral", "El Niño"]
    fig = go.Figure(go.Heatmap(
        z=z, x=xlab, y=ylab, zmin=0, zmax=1,
        colorscale=[[0, "#123b33"], [0.5, AMBER], [1, COLORS["el_nino"]]],
        colorbar=dict(title="P(def)", thickness=10, len=0.7),
        hovertemplate="%{y} · %{x}<br>P(deficient)=%{z:.2f}<extra></extra>"))
    counts = GRID.set_index(["enso", "iodp"])
    for i, (enso, yv) in enumerate(zip(_ENSO_ROWS, ylab)):
        for j, (iod, xv) in enumerate(zip(_IOD_COLS, xlab)):
            if not np.isnan(z[i, j]):
                c = counts.loc[(enso, iod)]
                fig.add_annotation(
                    x=xv, y=yv, showarrow=False,
                    text=f"{z[i, j]:.2f}<br><span style='font-size:10px'>"
                         f"{int(c['n_deficient'])}/{int(c['n'])}</span>",
                    font=dict(color="#fff", size=14, family="ui-monospace"))
    # The box marks this season's cell, read from the data rather than assumed.
    bx, by = _IOD_COLS.index(NOW["iod_cell"]), _ENSO_ROWS.index(NOW["enso_cell"])
    fig.add_shape(type="rect", x0=bx - .5, x1=bx + .5, y0=by - .5, y1=by + .5,
                  line=dict(color=COLORS["teal"], width=3))
    style_figure(fig, height=300, margin=dict(l=70, r=10, t=40, b=30),
                 title=dict(text=f"P(deficient monsoon) by ENSO × IOD, {_FIRST}–{_LAST}",
                            font=dict(size=14)))
    fig.update_xaxes(side="top"); fig.update_yaxes(autorange="reversed")
    return fig


def _elnino_cells(grid: pd.DataFrame) -> str:
    g = grid[grid["enso"] == "El Nino"].set_index("iodp")
    return " · ".join(
        f"{word} <b>{g.loc[c, 'p_deficient']:.2f}</b> "
        f"({int(g.loc[c, 'n_deficient'])}/{int(g.loc[c, 'n'])})"
        for c, word in zip(_IOD_COLS, _IOD_WORD))


def _series_note() -> pn.pane.HTML:
    return pn.pane.HTML(
        "<div style='font-size:11px;line-height:1.6;color:#c2cadb;margin-top:6px'>"
        f"Teal box: {_SEASON}. <b>El Niño row on each DMI series:</b><br>"
        f"ERSST: {_elnino_cells(GRID)}<br>HadISST: {_elnino_cells(GRID_HAD)}<br>"
        "These cells are small and change with the series, so they show the shape of the "
        "record, not a probability to trade.</div>")


def _regression_card() -> pn.pane.HTML:
    def sig(p):
        return "●●●●" if p < 1e-3 else "●●●○" if p < 0.05 else "●●○○"
    rows = "".join(
        f"<tr><td>{spec}</td>" + "".join(
            f"<td>{_signed(r['coef'], 2)} <span style='color:#8a94a6'>p={r['p']:.3f}</span></td>"
            for _, r in g.set_index("series").loc[["ERSST", "HadISST"]].iterrows()) + "</tr>"
        for spec, g in ROBUST.groupby("spec", sort=False))
    same_sign = bool((ROBUST["coef"] > 0).all())
    all_sig = bool((ROBUST["p"] < 0.05).all())
    reading = ("The IOD coefficient is positive in every row"
               if same_sign else "The IOD coefficient changes sign across these rows")
    reading += (", and significant in every row." if all_sig else
                ", but not significant in every row, so read the direction rather than the "
                "p-value.")
    return pn.pane.HTML(
        f"<div class='card'><div class='lab'>What drives the monsoon? <span class='real'>OLS · n={int(REG['n'])}</span></div>"
        "<div class='reg'>"
        f"<div class='row'><span class='nm'>ENSO (Niño-3.4)</span>"
        f"<span style='color:{COLORS['el_nino']}'>{REG['nino34_coef']:+.1f} %/°C</span>"
        f"<span class='pv'>p&lt;0.0001</span><span class='sig'>{sig(REG['nino34_p'])}</span></div>"
        f"<div class='row'><span class='nm'>IOD (DMI)</span>"
        f"<span style='color:{COLORS['la_nina']}'>{REG['dmi_coef']:+.1f} %/unit</span>"
        f"<span class='pv'>p={REG['dmi_p']:.3f}</span><span class='sig'>{sig(REG['dmi_p'])}</span></div>"
        "<table style='width:100%;border-collapse:collapse;font-size:11px;margin-top:8px;color:#c2cadb'>"
        "<tr style='color:#8a94a6;font:700 9px ui-monospace,monospace;letter-spacing:.7px;"
        "text-transform:uppercase'><th align='left'>DMI coefficient</th><th align='left'>ERSST</th>"
        f"<th align='left'>HadISST</th></tr>{rows}</table>"
        f"<div class='foot'>R² = {REG['r2']:.2f} · two SST indices, all-India monsoon since "
        f"{_FIRST}. {reading}</div></div></div>")


def india_climate() -> pn.viewable.Viewable:
    full = ROBUST[ROBUST["spec"] == ROBUST["spec"].iloc[0]]["coef"] * 0.5
    heat = pn.pane.Plotly(_heatmap(), config={"displayModeBar": False}, sizing_mode="stretch_width")
    tk = pn.pane.HTML(
        f"<div class='tk'><span class='tg'>TAKEAWAY</span><b>El Niño cuts the monsoon about "
        f"{abs(REG['nino34_coef']):.0f}% per °C. A positive IOD offsets part of that: a DMI of "
        f"+0.5 adds back about {full.min():.1f} to {full.max():.1f} points, depending on the "
        f"DMI series.</b> It matters during the rains, so watch JJAS DMI: the regression is "
        "concurrent, and SON comes after the monsoon has ended.</div>")
    return pn.Column(causal_chain(CFG),
                     pn.Row(pn.Column(heat, _series_note(), css_classes=["card"]), _regression_card()),
                     tk, sizing_mode="stretch_width")


def _engine_read() -> str:
    text = COLORS["text"]
    parts = [f"Engine read: {_SEASON} Niño-3.4 <b style='color:{text}'>{_signed(NOW['nino34'], 2)} °C</b>, "
             f"ERSST DMI <b style='color:{text}'>{_signed(NOW['dmi'], 2)}</b> ({_NOW_WORD})."]
    if int(NOW["had_months"]):
        parts.append(f"HadISST DMI, the desk's other reading, averaged <b>{_signed(NOW['had_dmi'], 2)}</b> "
                     f"over the {int(NOW['had_months'])} of those months it has so far.")
    top = YEARS.loc[YEARS["nino34"].idxmax()]
    if NOW["nino34"] > top["nino34"]:
        parts.append(f"That Niño-3.4 is above anything in the {_FIRST}–{_LAST} rainfall record "
                     f"(max {_signed(top['nino34'], 2)}, {int(top['year'])}), so the regression "
                     "would be extrapolating.")
    if _NOW_YEAR > _LAST:
        parts.append(f"{_NOW_YEAR} rainfall is not in the record, which ends {_LAST}, so this "
                     "season's outcome is not shown here.")
    latest = pd.Timestamp(NOW["latest_date"])
    if latest > pd.Timestamp(_NOW_YEAR, 9, 1):
        parts.append(f"DMI has since moved to {_signed(NOW['latest_dmi'], 2)} ({latest:%b %Y}), "
                     "after the rains.")
    return " ".join(parts)


def _econ_takeaway() -> str:
    s = stance_from_cache("IND") or {}
    verdict = str(s.get("verdict", "UNTESTED"))
    if str(s.get("verdict_cls", "")).lower() in ("causal", "mod"):
        return (f"<b>The price link reads {verdict}</b>, peaking at a {int(s['horizon_mo'])} month "
                "lag. The chart above lets you check the cross-map yourself.")
    return (f"<b>The price link reads {verdict}</b>: it does not beat its surrogate null, so this "
            "page gives no basis for a lagged price position. The monsoon link above is the "
            "demonstrated one.")


def _history_row(year: int, note: str) -> tuple[str, str, str, str, str]:
    """ONI peak over the event year and the gridded departure, both from the caches."""
    r = YEARS[YEARS["year"] == year].iloc[0]
    lpa, peak = float(r["lpa_pct"]), float(_ONI.loc[f"{year}-06":f"{year + 1}-05"].max())
    cls = "bad" if r["category"] == "DEFICIENT" else "ok" if lpa >= -2.5 else "mid"
    return (f"{year}–{str(year + 1)[2:]}", f"{peak:+.1f}", cls, f"{_signed(lpa)}%", note)


# Box centres for the approximate regions imd_gridded.py averages.
_HOTSPOT_XY = {"Marathwada": (19.1, 76.6), "Rayalaseema": (14.6, 78.3), "Vidarbha": (20.8, 78.6),
               "Saurashtra": (22.3, 70.5), "Bundelkhand": (25.2, 79.4)}
_MAP_YEAR = int(YEARS.loc[YEARS["nino34"] >= 0.5, "year"].max())
_map_rain = _RAIN[_RAIN["year"] == _MAP_YEAR].set_index("region")["lpa_pct"]
_rain_all = YEARS[YEARS["year"] == _LAST].iloc[0]
_exposure_rank = int(_EXPOSURE.index[_EXPOSURE["iso3"] == "IND"][0]) + 1
_el_nino_years = int(GRID[GRID["enso"] == "El Nino"]["n"].sum())


# ---- India config --------------------------------------------------------
CFG = RegionConfig(
    name="INDIA", flag="🇮🇳", iso3="IND", regime="EL NIÑO",
    thesis=("El Niño suppresses the summer monsoon → India's ~50% rain-fed kharif belt takes the "
            "deficit → food inflation 1–3 quarters later. A positive IOD offsets part of it."),
    desk=dict(
        badge="● WATCH", instruments="Sugar · Rice",
        sub="stance cache missing",
        engine_read=_engine_read(),
        catalyst="<b>India rice &amp; sugar export policy</b>: a ban or curb tightens global supply (2023 playbook).",
        risk="<b>El Niño with no IOD offset</b>: the ENSO effect is larger and better established "
             "than the IOD's. Watch DMI during the rains, not after them."),
    kpis=[(f"Niño-3.4, {_SEASON}", _signed(NOW["nino34"], 2) + "°C", COLORS["el_nino"]),
          (f"DMI, {_SEASON} (ERSST)", _signed(NOW["dmi"], 2), COLORS["text"]),
          (f"Rainfall, {_LAST} (latest on record)", _signed(_rain_all["lpa_pct"]) + "%", COLORS["la_nina"]),
          ("Global exposure", f"#{_exposure_rank}/{len(_EXPOSURE)}", COLORS["text"])],
    hotspots=[(name, *xy, float(_map_rain[name])) for name, xy in _HOTSPOT_XY.items()],
    geo_scope="asia", geo_lat=(5, 37), geo_lon=(66, 98),
    map_title=(f"Monsoon departure, JJAS {_MAP_YEAR}, the latest El Niño year on record "
               "(vs 1971–2020, approximate boxes)"),
    commodity="Sugar, world",
    causal_chain=[("Driver", f"Niño-3.4 {_signed(NOW['nino34'], 2)}°C", COLORS["el_nino"]),
                  ("Atmos", "Walker cell east", AMBER), ("Monsoon", "Convection ↓", AMBER),
                  ("Weather", f"Rainfall {_signed(REG['nino34_coef'], 0)}% per °C", COLORS["text"]),
                  ("Economy", "Food prices", COLORS["la_nina"])],
    history_rows=[
        _history_row(1982, "Major kharif shortfall; S &amp; W India drought"),
        _history_row(1997, f"<b style='color:#c2cadb'>Broken link</b>: strong +IOD (SON DMI {_dmi_son(1997):+.2f}) offset it"),
        _history_row(2015, f"Only modest +IOD (DMI {_dmi_son(2015):+.2f}) → drought"),
        _history_row(2023, "Rice export ban; sugar curbs → global ripple")],
    econ_takeaway=_econ_takeaway(),
    footer=("<b>Sources:</b> ENSO/IOD computed from ERSSTv5, second DMI from NOAA PSL (HadISST) · "
            f"monsoon = IMD <b>0.25° gridded</b> JJAS, area-weighted by cos(lat), {_FIRST}–{_LAST} "
            "(1971–2020 normal 858.9 mm vs IMD's published ~868 mm; it approximates the official "
            "all-India series, it does not reproduce it) · prices from the World Bank Pink Sheet · "
            "causation from the in-repo Granger+CCM engine. "
            f"&nbsp;<b>Caveat:</b> the El Niño cells hold {_el_nino_years} seasons between them; "
            f"the n={int(REG['n'])} regression carries the significance. Not investment advice."),
)

build_region(CFG, climate_view=india_climate()).servable(title="India, ENSO Macro Risk Desk")
