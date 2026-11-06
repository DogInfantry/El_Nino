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

import panel as pn

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
sys.path.insert(0, str(_DASH_DIR))

from theme import COLORS  # noqa: E402
from region_template import (  # noqa: E402
    RegionConfig, REGION_CSS, build_region, causal_chain, event_row, latest_index, minus,
    null_read, phase_composite, price_kpis, region_numbers,
)

AMBER = COLORS.get("amber", "#f4b13a")
pn.extension("plotly", raw_css=[REGION_CSS], sizing_mode="stretch_width")

COMMODITY = "Palm oil"
NUM = region_numbers("IDN")
_NINO34, _ = latest_index("NINO34")
_FIG, _COMP = phase_composite(COMMODITY)
_, _COMP_EX = phase_composite(COMMODITY, exclude_years=(1973, 1974))
_M, _MX = _COMP["means"], _COMP_EX["means"]


def seasia_climate() -> pn.viewable.Viewable:
    chart = pn.pane.Plotly(_FIG, config={"displayModeBar": False}, sizing_mode="stretch_width")
    note = pn.pane.HTML(
        "<div class='card' style='font-size:12px;line-height:1.6;color:#c2cadb'>"
        "<div class='lab'>Mechanism vs. the naive read <span class='real'>COMPUTED composite</span></div>"
        "Physically, El Niño shifts convection east → <b style='color:#e8edf5'>drought over Indonesia/"
        "Malaysia</b> → palm yield stress. <b style='color:#e8edf5'>But the contemporaneous composite "
        "does NOT show an El Niño premium</b>: "
        f"La Niña months average <b style='color:#e8edf5'>{minus(_M['La Nina'], 1)}%</b> YoY against "
        f"El Niño's <b style='color:#e8edf5'>{minus(_M['El Nino'], 1)}%</b>. The 1973–74 commodity and "
        f"oil-crisis inflation accounts for part of that, and dropping those years narrows the gap to "
        f"{minus(_MX['La Nina'], 1)}% against {minus(_MX['El Nino'], 1)}% without reversing it. Raw "
        "co-movement confounds ENSO with macro cycles, so the link is tested in Economics.</div>")
    tk = pn.pane.HTML(
        f"<div class='tk'><span class='tg'>MISATTRIBUTION GUARD</span>The naive composite <b>fails the "
        f"El Niño-premium story</b>, with or without 1973–74. Like cocoa &amp; wheat: trust the causal "
        "test, not the co-movement.</div>")
    return pn.Column(causal_chain(CFG), pn.Row(pn.Column(chart, css_classes=["card"]), note),
                     tk, sizing_mode="stretch_width")


CFG = RegionConfig(
    name="SE ASIA", flag="🌏", iso3="IDN", regime="EL NIÑO",
    thesis=("El Niño pushes convection east off the Maritime Continent → drought over Indonesia &amp; "
            "Malaysia → palm-oil supply stress (yields + fire/haze) → global edible-oil prices."),
    desk=dict(
        badge="● WATCH", badge_cls="watch", instruments=COMMODITY,
        sub="stance cache missing",
        engine_read=(f"Engine read: the <b>naive ENSO-phase composite does not confirm</b> an El Niño "
                     f"palm premium. Peak correlation is <b>r = {minus(NUM['r'])}</b> "
                     f"({NUM['horizon']}), Granger fires on {NUM['granger']} of 24 lags, and "
                     f"{null_read(NUM)}, so the link reads <b>{NUM['verdict']}</b>."),
        catalyst="<b>Indonesian export levy / biodiesel mandate</b> shifts on a genuine supply scare.",
        risk="<b>The ENSO→palm link is weaker / noisier than consensus</b>: the composite already says so."),
    kpis=price_kpis(NUM),
    hotspots=[("Sumatra", -0.5, 101.5, None), ("Kalimantan", -1.0, 113.5, None),
              ("Pen. Malaysia", 3.5, 102.0, None), ("Sulawesi", -2.0, 120.5, None)],
    geo_scope="asia", geo_lat=(-10, 8), geo_lon=(95, 122),
    map_title="Maritime Continent · locations only, rainfall is not ingested",
    commodity=COMMODITY,
    causal_chain=[("Driver", f"Niño-3.4 {minus(_NINO34, 1)}°C", COLORS["el_nino"]),
                  ("Atmos", "Convection shifts E", AMBER),
                  ("Weather", "MC drought", COLORS["text"]), ("Crop", "Palm yield + fire", AMBER),
                  ("Market", f"Palm oil r {minus(NUM['r'])}", COLORS["la_nina"])],
    history_rows=[
        event_row(1997, COMMODITY, "bad", "severe", "Record fires and haze."),
        event_row(2015, COMMODITY, "bad", "severe", "Major drought and fire crisis."),
        event_row(2018, COMMODITY, "mid", "mild", "Muted supply hit."),
        event_row(2023, COMMODITY, "mid", "moderate", "Dry skew.")],
    footer=("<b>Sources:</b> ENSO from NOAA CPC (ERSSTv5) · palm-oil prices from the World Bank Pink Sheet · "
            "causation from the in-repo Granger+CCM engine. &nbsp;<b>Caveat:</b> Maritime-Continent "
            "rainfall is not ingested, so the map marks locations and the impact column is a "
            "qualitative note. The composite, the price moves and the causation test are computed. "
            "Not investment advice."),
)

build_region(CFG, climate_view=seasia_climate()).servable(title="SE Asia, ENSO Macro Risk Desk")
