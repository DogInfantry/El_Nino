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
    RegionConfig, REGION_CSS, build_region, causal_chain, lag_profile, phase_composite,
)

AMBER = COLORS.get("amber", "#f4b13a")
pn.extension("plotly", raw_css=[REGION_CSS], sizing_mode="stretch_width")

COMMODITY = "Wheat, US HRW"


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
        "The drought mechanism is real — El Niño reliably suppresses winter rainfall over "
        "the eastern wheatbelt, and 2002, 2006 and 2019 were all severe production years. "
        "The <b style='color:#e8edf5'>price</b> response is the part that fails. Peak "
        f"correlation is <b style='color:#e8edf5'>r = {lag['peak_r']:+.3f}</b> at "
        f"<b style='color:#e8edf5'>{lag['peak_lag']} months</b> — El Niño is followed by "
        f"{direction} wheat, not higher. The composite agrees and is blunter: La Niña "
        f"months average <b style='color:#e8edf5'>{m['La Nina']:+.1f}%</b> YoY against El "
        f"Niño's <b style='color:#e8edf5'>{m['El Nino']:+.1f}%</b>.</div>")
    tk = pn.pane.HTML(
        "<div class='tk'><span class='tg'>MISATTRIBUTION GUARD</span>Australia is ~3–4% of "
        "world wheat production but a much larger share of the traded market, and the price "
        "here is <b>US HRW</b> — a global benchmark set mostly by Northern-Hemisphere supply, "
        "the dollar and energy costs. A regional drought can be entirely real and still be "
        "swamped in the benchmark. <b>Correct physics, wrong instrument.</b></div>")
    return pn.Column(causal_chain(CFG), charts, note, tk, sizing_mode="stretch_width")


CFG = RegionConfig(
    name="AUSTRALIA", flag="🇦🇺", iso3="AUS", regime="WEAK EL NIÑO · 2026",
    thesis=("El Niño suppresses winter rainfall over the eastern wheatbelt and the crop "
            "shrinks — a well-documented physical link whose price transmission this desk "
            "cannot confirm, and whose sign it in fact reverses."),
    desk=dict(
        badge="● WATCH", badge_cls="watch", instruments="Wheat (US HRW benchmark)",
        sub="physical link solid · price link inverted · benchmark mismatch",
        engine_read=("Engine read — the strongest |r| of the drought group at <b>0.27</b>, "
                     "but <b>negative</b> at a 4-month lag: El Niño is followed by <i>lower</i> "
                     "benchmark wheat. The ENSO-phase composite says the same. Granger fires "
                     "on 8 of 24 lags, CCM does not confirm, and the surrogate test leaves "
                     "it WEAK."),
        catalyst="<b>ABARES crop downgrades</b> plus a Northern-Hemisphere supply shock in one season.",
        risk="<b>Buying wheat on an Australian drought headline.</b> The desk's own history "
             "says the benchmark has not paid that trade."),
    kpis=[("Peak r", "−0.27", COLORS["el_nino"]), ("Peak lag", "4 mo", COLORS["text"]),
          ("Granger", "8/24 lags", AMBER), ("Surrogate p", "0.47", COLORS["muted"])],
    hotspots=[("NSW Riverina", -34.5, 146.0, -22), ("WA Wheatbelt", -31.5, 117.5, -14),
              ("SA Eyre Pen.", -33.5, 136.0, -17), ("Vic Mallee", -35.5, 142.5, -19)],
    geo_scope="world", geo_lat=(-44, -10), geo_lon=(110, 156),
    map_title="Australian wheatbelt rainfall deficit · El Niño",
    commodity=COMMODITY,
    causal_chain=[("Driver", "Niño-3.4 +1.0°C", COLORS["el_nino"]),
                  ("Atmos", "Subsidence over E. Aus", AMBER),
                  ("Weather", "Winter rain deficit", COLORS["text"]),
                  ("Crop", "Yield down", AMBER),
                  ("Market", "Benchmark does NOT rally", COLORS["muted"])],
    history_rows=[
        ("1982–83", "+2.2", "bad", "severe", "Drought + Ash Wednesday fires; crop halved"),
        ("2002–03", "+1.5", "bad", "severe", "One of the worst wheat years on record"),
        ("2006–07", "+1.0", "bad", "severe", "Millennium-drought trough; big production loss"),
        ("2015–16", "+2.6", "mid", "moderate", "Dry east, but benchmark wheat kept falling"),
        ("2018–19", "+0.8", "mid", "moderate", "Severe east-coast drought; global price flat")],
    econ_takeaway=("<b>The physics is not the trade.</b> A real production loss expressed in "
                   "the wrong instrument reads as noise — which is precisely what the lag "
                   "profile shows."),
    footer=("<b>Sources:</b> ENSO — NOAA CPC (ERSSTv5) · wheat prices — World Bank Pink Sheet "
            "(US HRW) · composite, lag profile and causal verdict computed in-repo. "
            "&nbsp;<b>Caveat:</b> hotspot rainfall figures are illustrative — Bureau of "
            "Meteorology data is <b>not</b> ingested, because the Bureau declines automated "
            "access and this project does not work around that. Not investment advice."),
)

build_region(CFG, climate_view=australia_climate()).servable(
    title="Australia — ENSO Macro Risk Desk")
