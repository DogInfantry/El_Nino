"""India Deep-Dive — the first region tear-sheet, built on the shared region template.

Run with::

    panel serve dashboard/pages/07_india.py --show

Generic shell (bar / DESK VIEW / map / KPI rail / Economics=live Granger+CCM / History)
comes from ``dashboard/region_template.py``. India contributes a thin ``RegionConfig`` and
its own **Climate** exhibit — the computed ENSO×IOD scenario matrix + OLS regression
(n=117, from ERSSTv5 + IMD; caches built by ``data/process/enso_flavor_iod.py``).

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
    RegionConfig, REGION_CSS, build_region, causal_chain,
)

AMBER = COLORS.get("amber", "#f4b13a")
pn.extension("plotly", raw_css=[REGION_CSS], sizing_mode="stretch_width")

# ---- India-specific data + climate exhibit -------------------------------
GRID = pd.read_parquet(CACHE_DIR / "india_enso_iod.parquet")
REG = pd.read_parquet(CACHE_DIR / "india_regression.parquet").iloc[0].to_dict()
YEARS = pd.read_parquet(CACHE_DIR / "india_years.parquet")


def _pdef(enso: str, iod: str) -> float:
    r = GRID[(GRID["enso"] == enso) & (GRID["iodp"] == iod)]
    return float(r["p_deficient"].iloc[0]) if len(r) else float("nan")


def _dmi_son(year: int) -> float:
    r = YEARS[YEARS["year"] == year]
    return float(r["dmi_son"].iloc[0]) if len(r) else float("nan")


def _heatmap() -> go.Figure:
    rows, cols = ["La Nina", "Neutral", "El Nino"], ["IOD-neg", "IOD-neu", "IOD-pos"]
    piv = GRID.pivot(index="enso", columns="iodp", values="p_deficient").reindex(index=rows, columns=cols)
    z = piv.values.astype(float)
    xlab, ylab = ["IOD −", "IOD neutral", "IOD +"], ["La Niña", "Neutral", "El Niño"]
    fig = go.Figure(go.Heatmap(
        z=z, x=xlab, y=ylab, zmin=0, zmax=1,
        colorscale=[[0, "#123b33"], [0.5, AMBER], [1, COLORS["el_nino"]]],
        colorbar=dict(title="P(def)", thickness=10, len=0.7),
        hovertemplate="%{y} · %{x}<br>P(deficient)=%{z:.2f}<extra></extra>"))
    for i, yv in enumerate(ylab):
        for j, xv in enumerate(xlab):
            if not np.isnan(z[i, j]):
                fig.add_annotation(x=xv, y=yv, text=f"{z[i, j]:.2f}", showarrow=False,
                                   font=dict(color="#fff", size=14, family="ui-monospace"))
    fig.add_shape(type="rect", x0=1.5, x1=2.5, y0=1.5, y1=2.5, line=dict(color=COLORS["teal"], width=3))
    style_figure(fig, height=300, margin=dict(l=70, r=10, t=40, b=30),
                 title=dict(text="P(deficient monsoon) by ENSO × IOD", font=dict(size=14)))
    fig.update_xaxes(side="top"); fig.update_yaxes(autorange="reversed")
    return fig


def _regression_card() -> pn.pane.HTML:
    def sig(p):
        return "●●●●" if p < 1e-3 else "●●●○" if p < 0.05 else "●●○○"
    return pn.pane.HTML(
        f"<div class='card'><div class='lab'>What drives the monsoon? <span class='real'>OLS · n={int(REG['n'])}</span></div>"
        "<div class='reg'>"
        f"<div class='row'><span class='nm'>ENSO (Niño-3.4)</span>"
        f"<span style='color:{COLORS['el_nino']}'>{REG['nino34_coef']:+.1f} %/°C</span>"
        f"<span class='pv'>p&lt;0.0001</span><span class='sig'>{sig(REG['nino34_p'])}</span></div>"
        f"<div class='row'><span class='nm'>IOD (DMI)</span>"
        f"<span style='color:{COLORS['la_nina']}'>{REG['dmi_coef']:+.1f} %/unit</span>"
        f"<span class='pv'>p={REG['dmi_p']:.3f}</span><span class='sig'>{sig(REG['dmi_p'])}</span></div>"
        f"<div class='foot'>R² = {REG['r2']:.2f} · two SST indices explain ~⅓ of all-India monsoon "
        "variance since 1901. The IOD coefficient is the offset — positive, and significant.</div></div></div>")


def india_climate() -> pn.viewable.Viewable:
    p80, p50 = _pdef("El Nino", "IOD-neu"), _pdef("El Nino", "IOD-pos")
    heat = pn.pane.Plotly(_heatmap(), config={"displayModeBar": False}, sizing_mode="stretch_width")
    tk = pn.pane.HTML(
        f"<div class='tk'><span class='tg'>TAKEAWAY</span><b>El Niño cuts the monsoon ~8%/°C; a "
        f"positive IOD adds back ~4%.</b> This year's +IOD is the difference between the {p80:.2f} and "
        f"{p50:.2f} drought cell — the call hinges on whether it holds (SON DMI).</div>")
    return pn.Column(causal_chain(CFG),
                     pn.Row(pn.Column(heat, css_classes=["card"]), _regression_card()),
                     tk, sizing_mode="stretch_width")


# ---- India config --------------------------------------------------------
_P_NOW, _P_NOIOD = _pdef("El Nino", "IOD-pos"), _pdef("El Nino", "IOD-neu")

CFG = RegionConfig(
    name="INDIA", flag="🇮🇳", iso3="IND", regime="STRONG EL NIÑO · 2026",
    thesis=("El Niño suppresses the summer monsoon → India's ~50% rain-fed kharif belt takes the "
            "deficit → food inflation 1–3 quarters later. Strong but IOD-modulated."),
    desk=dict(
        badge="▲ CONSTRUCTIVE", instruments="Sugar · Rice",
        sub="supply-driven · long bias H2 · conviction 3/4 · horizon 6–9 mo",
        engine_read=(f"Engine read — current setup <b style='color:{COLORS['text']}'>El Niño + positive "
                     f"IOD</b> → modeled <b>P(deficient monsoon) ≈ {_P_NOW:.2f}</b> (vs {_P_NOIOD:.2f} "
                     "without the IOD hedge). That hedge is why conviction is 3/4, not 4/4."),
        catalyst="<b>India rice &amp; sugar export policy</b> — a Q3 ban/curb tightens global supply (2023 playbook).",
        risk="<b>IOD fades</b> — pushes the setup toward the 0.80 cell. Watch SON DMI."),
    kpis=[("Monsoon rainfall", "−12%", COLORS["el_nino"]), ("Food CPI", "+4.8%", COLORS["la_nina"]),
          ("Sugarcane yield", "−9%", COLORS["el_nino"]), ("Global exposure", "#2/10", COLORS["text"])],
    hotspots=[("Marathwada", 19.1, 76.6, -31), ("Rayalaseema", 14.6, 78.3, -28),
              ("Vidarbha", 20.8, 78.6, -24), ("Saurashtra", 22.3, 70.5, -22),
              ("Bundelkhand", 25.2, 79.4, -19)],
    geo_scope="asia", geo_lat=(5, 37), geo_lon=(66, 98),
    map_title="Monsoon rainfall deficit · Jun–Sep (vs 1991–2020)",
    commodity="Sugar, world",
    causal_chain=[("Driver", "Niño-3.4 +1.7°C", COLORS["el_nino"]), ("Atmos", "Walker cell east", AMBER),
                  ("Monsoon", "Convection ↓", AMBER), ("Weather", "Rainfall −12%", COLORS["text"]),
                  ("Economy", "Food CPI +4.8%", COLORS["la_nina"])],
    history_rows=[
        ("1982–83", "+2.2", "bad", "−14%", "Major kharif shortfall; S &amp; W India drought"),
        ("1997–98", "+2.4", "ok", "~normal",
         f"<b style='color:#c2cadb'>Broken link</b> — strong +IOD (SON DMI {_dmi_son(1997):+.2f}) offset it"),
        ("2015–16", "+2.6", "bad", "−14%", f"Only modest +IOD (DMI {_dmi_son(2015):+.2f}) → drought"),
        ("2023–24", "+2.0", "mid", "−6%", "Rice export ban; sugar curbs → global ripple")],
    econ_takeaway=("<b>The price link is causal and lagged ~7mo</b> — position during the monsoon "
                   "season, ahead of the Q4 price response."),
    footer=("<b>Sources:</b> ENSO/IOD computed from ERSSTv5 · monsoon = IMD 36-subdivision JJAS "
            "(1901–2017, r=0.77 vs official AISMR) · prices — World Bank Pink Sheet · causation — "
            "in-repo Granger+CCM. &nbsp;<b>Caveat:</b> El Niño-cell n is small (~20 events); the n=117 "
            "regression carries the significance. Not investment advice."),
)

build_region(CFG, climate_view=india_climate()).servable(title="India — ENSO Macro Risk Desk")
