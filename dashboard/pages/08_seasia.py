"""SE Asia (Maritime Continent) Deep-Dive — proves the region template generalises.

Run with::

    panel serve dashboard/pages/08_seasia.py --show

Same shell as India (``region_template.build_region``); a different config and a
*different* Climate exhibit. India's deep analysis (ENSO×IOD → monsoon) is India-specific,
so SE Asia uses a generic, real, reusable climate view: an **ENSO-phase composite of
palm-oil returns** (computed from the ENSO phase labels × World Bank palm-oil prices).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import panel as pn
import plotly.graph_objects as go

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
sys.path.insert(0, str(_DASH_DIR))

from theme import COLORS, load_commodities, load_phases, style_figure  # noqa: E402
from region_template import RegionConfig, REGION_CSS, build_region, causal_chain  # noqa: E402

AMBER = COLORS.get("amber", "#f4b13a")
pn.extension("plotly", raw_css=[REGION_CSS], sizing_mode="stretch_width")

PHASE_COLOR = {"El Nino": COLORS["el_nino"], "La Nina": COLORS["la_nina"], "Neutral": COLORS["neutral"]}


def _enso_phase_composite() -> tuple[go.Figure, dict]:
    """Mean YoY palm-oil return by ENSO phase — real, from phases × Pink Sheet."""
    comm = load_commodities()
    palm = (comm[comm["commodity"] == "Palm oil"].set_index("date")["price"]
            .astype(float).sort_index())
    yoy = palm.pct_change(12) * 100.0
    phases = load_phases()[["date", "phase_simple"]]
    df = (pd.DataFrame({"date": yoy.index, "yoy": yoy.to_numpy()})
          .merge(phases, on="date").dropna())
    means = df.groupby("phase_simple")["yoy"].mean()
    order = ["El Nino", "Neutral", "La Nina"]
    means = means.reindex(order)
    fig = go.Figure(go.Bar(
        x=["El Niño", "Neutral", "La Niña"], y=means.values,
        marker_color=[PHASE_COLOR[p] for p in order],
        text=[f"{v:+.1f}%" for v in means.values], textposition="outside"))
    style_figure(fig, height=300, margin=dict(l=40, r=10, t=40, b=30),
                 title=dict(text="Palm-oil YoY return by ENSO phase", font=dict(size=14)),
                 yaxis=dict(title="mean YoY %"))
    return fig, {p: float(means[p]) for p in order}


def seasia_climate() -> pn.viewable.Viewable:
    fig, means = _enso_phase_composite()
    chart = pn.pane.Plotly(fig, config={"displayModeBar": False}, sizing_mode="stretch_width")
    note = pn.pane.HTML(
        "<div class='card' style='font-size:12px;line-height:1.6;color:#c2cadb'>"
        "<div class='lab'>Mechanism vs. the naive read <span class='real'>COMPUTED composite</span></div>"
        "Physically, El Niño shifts convection east → <b style='color:#e8edf5'>drought over Indonesia/"
        "Malaysia</b> → palm yield stress (1997 &amp; 2015 fire crises <i>did</i> spike CPO). <b "
        "style='color:#e8edf5'>But the contemporaneous composite does NOT show an El Niño premium</b> — "
        "La Niña actually reads higher, dominated by the 1973–74 global commodity/oil-crisis inflation. "
        "Raw co-movement confounds ENSO with macro cycles; the real link is supply-driven and "
        "<b style='color:#e8edf5'>lagged</b> — tested in Economics.</div>")
    tk = pn.pane.HTML(
        f"<div class='tk'><span class='tg'>MISATTRIBUTION GUARD</span>The naive composite <b>fails the "
        f"El Niño-premium story</b> (La Niña {means['La Nina']:+.0f}% &gt; El Niño {means['El Nino']:+.0f}%, "
        "driven by 1973–74 macro inflation — not ENSO). Like cocoa &amp; wheat: trust the lagged causal "
        "test, not the co-movement.</div>")
    return pn.Column(causal_chain(CFG), pn.Row(pn.Column(chart, css_classes=["card"]), note),
                     tk, sizing_mode="stretch_width")


CFG = RegionConfig(
    name="SE ASIA", flag="🌏", iso3="IDN", regime="STRONG EL NIÑO · 2026",
    thesis=("El Niño pushes convection east off the Maritime Continent → drought over Indonesia &amp; "
            "Malaysia → palm-oil supply stress (yields + fire/haze) → global edible-oil prices."),
    desk=dict(
        badge="● WATCH", badge_cls="watch", instruments="Palm oil",
        sub="naive bull case unproven · lagged-causal only · conviction 2/4 · horizon 6–12 mo",
        engine_read=("Engine read — the <b>naive ENSO-phase composite does NOT confirm</b> an El Niño palm "
                     "premium (La Niña reads higher, a 1973–74 macro-inflation artifact). The documented "
                     "supply link (1997/2015 fire spikes) is <b>lagged</b> — so the verdict hinges on the "
                     "live Granger/CCM in Economics, not the raw co-movement."),
        catalyst="<b>Indonesian export levy / biodiesel mandate</b> shifts on a genuine supply scare.",
        risk="<b>The ENSO→palm link is weaker / noisier than consensus</b> — the composite already says so."),
    kpis=[("MC rainfall (El Niño)", "−18%", COLORS["el_nino"]), ("1997/2015 CPO", "spiked", COLORS["la_nina"]),
          ("Fire/haze risk", "High", COLORS["el_nino"]), ("Composite premium", "unproven", AMBER)],
    hotspots=[("Sumatra", -0.5, 101.5, -20), ("Kalimantan", -1.0, 113.5, -22),
              ("Pen. Malaysia", 3.5, 102.0, -15), ("Sulawesi", -2.0, 120.5, -14)],
    geo_scope="asia", geo_lat=(-10, 8), geo_lon=(95, 122),
    map_title="Maritime Continent rainfall deficit · El Niño",
    commodity="Palm oil",
    causal_chain=[("Driver", "Niño-3.4 +1.7°C", COLORS["el_nino"]), ("Atmos", "Convection shifts E", AMBER),
                  ("Weather", "MC drought −18%", COLORS["text"]), ("Crop", "Palm yield + fire", AMBER),
                  ("Market", "Palm oil +20%", COLORS["la_nina"])],
    history_rows=[
        ("1997–98", "+2.4", "bad", "severe", "Record fires/haze; palm &amp; CPO prices spiked"),
        ("2015–16", "+2.6", "bad", "severe", "Major drought + fire crisis; CPO rallied into 2016"),
        ("2018–19", "+0.8", "mid", "mild", "Weak El Niño; muted supply hit"),
        ("2023–24", "+2.0", "mid", "moderate", "Dry skew; supportive for CPO vs trend")],
    econ_takeaway=("<b>Palm oil is the trade</b> — the ENSO→price link is supply-driven and lags the "
                   "drought; the CCM tests one-way forcing."),
    footer=("<b>Sources:</b> ENSO — NOAA CPC (ERSSTv5) · palm-oil prices — World Bank Pink Sheet · "
            "causation — in-repo Granger+CCM. &nbsp;<b>Caveat:</b> rainfall/hotspot figures are "
            "illustrative pending Maritime-Continent precip ingestion; the ENSO-phase price composite "
            "and the causation test are computed. Not investment advice."),
)

build_region(CFG, climate_view=seasia_climate()).servable(title="SE Asia — ENSO Macro Risk Desk")
