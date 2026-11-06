"""Australia / Wheat Deep-Dive — where the data contradicts the consensus trade.

Run with::

    panel serve dashboard/pages/12_australia.py --show

The consensus story is clean and widely traded: El Niño dries eastern Australia, the
wheat crop fails, wheat rallies. The physical half is well documented. The price half is
not — and this desk's own numbers point the *other* way. Peak lagged correlation is
r ≈ −0.27 at 4 months (El Niño → wheat *lower*), and the phase composite has La Niña
months averaging far higher returns than El Niño ones. Both are shown, because a region
page that only printed the thesis would be selling the trade its evidence refuses.
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
    RegionConfig, REGION_CSS, build_region, causal_chain, event_row, lag_profile, latest_index,
    minus, null_read, phase_composite, price_kpis, region_numbers,
)

AMBER = COLORS.get("amber", "#f4b13a")
pn.extension("plotly", raw_css=[REGION_CSS], sizing_mode="stretch_width")

COMMODITY = "Wheat, US HRW"
NUM = region_numbers("AUS")
_NINO34, _ = latest_index("NINO34")


def australia_climate() -> pn.viewable.Viewable:
    comp_fig, comp = phase_composite(COMMODITY)
    lag_fig, lag = lag_profile(COMMODITY)
    m = comp["means"]
    direction = "lower" if lag["peak_r"] < 0 else "higher"

    charts = pn.Row(
        pn.Column(pn.pane.Plotly(comp_fig, config={"displayModeBar": False}),
                  css_classes=["card"]),
        pn.Column(pn.pane.Plotly(lag_fig, config={"displayModeBar": False}),
                  css_classes=["card"]), sizing_mode="stretch_width")
    note = pn.pane.HTML(
        "<div class='card' style='font-size:12px;line-height:1.6;color:#c2cadb'>"
        "<div class='lab'>The sign is the finding <span class='real'>COMPUTED</span></div>"
        "The drought mechanism is real, El Niño reliably suppresses winter rainfall over "
        "the eastern wheatbelt, and 2002, 2006 and 2019 were all severe production years. "
        "The <b style='color:#e8edf5'>price</b> response is the part that fails. Peak "
        f"correlation is <b style='color:#e8edf5'>r = {minus(lag['peak_r'], 3)}</b> at "
        f"<b style='color:#e8edf5'>{lag['peak_lag']} months</b>: El Niño is followed by "
        f"{direction} wheat, not higher. The composite agrees and is blunter: La Niña "
        f"months average <b style='color:#e8edf5'>{minus(m['La Nina'], 1)}%</b> YoY against El "
        f"Niño's <b style='color:#e8edf5'>{minus(m['El Nino'], 1)}%</b>.</div>")
    tk = pn.pane.HTML(
        "<div class='tk'><span class='tg'>MISATTRIBUTION GUARD</span>Australia is a small "
        "share of world wheat production but a much larger share of the traded market, and the "
        "price here is <b>US HRW</b>: a global benchmark set mostly by Northern-Hemisphere supply, "
        "the dollar and energy costs. A regional drought can be entirely real and still be "
        "swamped in the benchmark. <b>Correct physics, wrong instrument.</b></div>")
    return pn.Column(causal_chain(CFG), charts, note, tk, sizing_mode="stretch_width")


CFG = RegionConfig(
    name="AUSTRALIA", flag="🇦🇺", iso3="AUS", regime="EL NIÑO",
    thesis=("El Niño suppresses winter rainfall over the eastern wheatbelt and the crop "
            "shrinks, a well-documented physical link whose price transmission this desk "
            "cannot confirm, and whose sign it in fact reverses."),
    desk=dict(
        badge="● WATCH", badge_cls="watch", instruments="Wheat (US HRW benchmark)",
        sub="stance cache missing",
        engine_read=(("Engine read: the strongest |r| on the desk at " if NUM["strongest_r"]
                      else "Engine read: peak correlation of ")
                     + f"<b>r = {minus(NUM['r'])}</b> at <b>{NUM['horizon']}</b>: El Niño is followed "
                     "by <i>lower</i> benchmark wheat. The ENSO-phase composite says the same. "
                     f"Granger fires on {NUM['granger']} of 24 lags, cross-map ρ is {NUM['rho']:.2f} "
                     f"against a {NUM['null']:.2f} null, and {null_read(NUM)}, so the link reads "
                     f"<b>{NUM['verdict']}</b>."),
        catalyst="<b>ABARES crop downgrades</b> plus a Northern-Hemisphere supply shock in one season.",
        risk="<b>Buying wheat on an Australian drought headline.</b> The lag test points the other "
             "way, and the benchmark has moved both ways through past droughts (History tab)."),
    kpis=price_kpis(NUM),
    hotspots=[("NSW Riverina", -34.5, 146.0, None), ("WA Wheatbelt", -31.5, 117.5, None),
              ("SA Eyre Pen.", -33.5, 136.0, None), ("Vic Mallee", -35.5, 142.5, None)],
    geo_scope="world", geo_lat=(-44, -10), geo_lon=(110, 156),
    map_title="Australian wheatbelt · locations only, Bureau rainfall is not ingested",
    commodity=COMMODITY,
    causal_chain=[("Driver", f"Niño-3.4 {minus(_NINO34, 1)}°C", COLORS["el_nino"]),
                  ("Atmos", "Subsidence over E. Aus", AMBER),
                  ("Weather", "Winter rain deficit", COLORS["text"]),
                  ("Crop", "Yield down", AMBER),
                  ("Market", f"Benchmark r {minus(NUM['r'])}", COLORS["muted"])],
    history_rows=[
        event_row(1982, COMMODITY, "bad", "severe", "Drought and Ash Wednesday fires."),
        event_row(2002, COMMODITY, "bad", "severe", "One of the worst wheat years on record."),
        event_row(2006, COMMODITY, "bad", "severe", "Millennium-drought trough."),
        event_row(2015, COMMODITY, "mid", "moderate", "Dry east."),
        event_row(2018, COMMODITY, "mid", "moderate", "Severe east-coast drought.")],
    econ_takeaway=("<b>The physics is not the trade.</b> A real production loss expressed in "
                   f"the wrong instrument: the benchmark's lag profile peaks at {minus(NUM['r'])}, "
                   "the opposite sign to the drought story."),
    footer=("<b>Sources:</b> ENSO from NOAA CPC (ERSSTv5) · wheat prices from the World Bank Pink Sheet "
            "(US HRW) · composite, lag profile, price moves and causal verdict computed in-repo. "
            "&nbsp;<b>Caveat:</b> Bureau of Meteorology data is <b>not</b> ingested, because the "
            "Bureau declines automated access and this project does not work around that, so the "
            "map marks locations and the impact column is a qualitative note. Not investment advice."),
)

build_region(CFG, climate_view=australia_climate()).servable(
    title="Australia, ENSO Macro Risk Desk")
