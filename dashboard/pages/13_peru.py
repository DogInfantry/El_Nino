"""Peru / Fishmeal Deep-Dive — the original El Niño, and the desk's best near-miss.

Run with::

    panel serve dashboard/pages/13_peru.py --show

Peru is the only `wet`-sign row in the registry and the only region whose price response
comes out **positive**. Every other entry is a drought story where El Niño suppresses
supply somewhere in the tropics; here the warm coastal water that gave the phenomenon its
name shuts down the upwelling the anchoveta feed on, the fishery closes, and fishmeal —
the world's protein-feed input — moves up.

It is also the most credible link on the desk and still not proven: 21 of 24 Granger lags
significant (the highest anywhere), cross-map ρ 0.29 against a seasonal null of 0.10, and
a surrogate p of 0.078. That misses α=0.05. It stays WEAK.
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

COMMODITY = "Fish meal"


def peru_climate() -> pn.viewable.Viewable:
    comp_fig, comp = phase_composite(COMMODITY)
    lag_fig, lag = lag_profile(COMMODITY)
    m = comp["means"]
    sign_word = "positive" if lag["peak_r"] > 0 else "negative"

    charts = pn.Row(
        pn.Column(pn.pane.Plotly(lag_fig, config={"displayModeBar": False}),
                  css_classes=["card"]),
        pn.Column(pn.pane.Plotly(comp_fig, config={"displayModeBar": False}),
                  css_classes=["card"]), sizing_mode="stretch_width")
    note = pn.pane.HTML(
        "<div class='card' style='font-size:12px;line-height:1.6;color:#c2cadb'>"
        "<div class='lab'>The one link that points up <span class='real'>COMPUTED</span></div>"
        f"Peak correlation is <b style='color:#e8edf5'>r = {lag['peak_r']:+.3f}</b> at "
        f"<b style='color:#e8edf5'>{lag['peak_lag']} months</b> — {sign_word}, and the only "
        "meaningfully positive row in the registry. The sign is the mechanism showing "
        "through: warm water suppresses upwelling → the anchoveta biomass disperses and "
        "quotas are cut → fishmeal tightens, roughly two to three quarters later. The "
        "composite is the weaker exhibit here, and shows why timing matters — El Niño months "
        f"average <b style='color:#e8edf5'>{m['El Nino']:+.1f}%</b> against La Niña's "
        f"<b style='color:#e8edf5'>{m['La Nina']:+.1f}%</b>, nearly a tie, because "
        "collapsing an 8-month lag into a contemporaneous average destroys the very signal "
        "the lag profile recovers.</div>")
    tk = pn.pane.HTML(
        "<div class='tk'><span class='tg'>HONEST NEAR-MISS</span>Granger fires on <b>21 of 24 "
        "lags</b> — the strongest on the desk — and cross-map ρ is <b>0.29</b> against a "
        "phase-randomized null averaging <b>0.10</b>. But the surrogate p is <b>0.078</b>, "
        "which does not clear 0.05, so the verdict stays <b>WEAK</b> and the stance stays "
        "<b>WATCH</b>. This is the link most likely to be real, and the desk still will not "
        "promote it on a near-miss.</div>")
    return pn.Column(causal_chain(CFG), charts, note, tk, sizing_mode="stretch_width")


CFG = RegionConfig(
    name="PERU", flag="🇵🇪", iso3="PER", regime="WEAK EL NIÑO · 2026",
    thesis=("Warm coastal water shuts down the Humboldt upwelling, the anchoveta fishery "
            "closes, and fishmeal tightens two to three quarters later — the oldest ENSO "
            "impact on record and this desk's only positive-sign link."),
    desk=dict(
        badge="● WATCH", badge_cls="watch", instruments="Fish meal",
        sub="strongest Granger on the desk · surrogate p 0.078 · misses the bar",
        engine_read=("Engine read — the only <b>positive</b> r_peak in the registry "
                     "(<b>+0.19 at 8 months</b>), the highest Granger count anywhere "
                     "(<b>21/24 lags</b>), and cross-map ρ 0.29 against a 0.10 null. The "
                     "surrogate test returns <b>p = 0.078</b>, so it is capped at WEAK — "
                     "the closest thing to a real ONI→price link the desk has found."),
        catalyst="<b>IMARPE biomass survey and the quota decision</b> for the following season.",
        risk="<b>A near-miss is not a result.</b> p = 0.078 on 500 surrogates sits one "
             "re-estimation away from either side of the line."),
    kpis=[("Peak r", "+0.19", COLORS["la_nina"]), ("Peak lag", "8 mo", COLORS["text"]),
          ("Granger", "21/24 lags", COLORS["la_nina"]), ("Surrogate p", "0.078", AMBER)],
    # pct > 0 renders wet/blue — Peru is the flood side of the phenomenon, not drought.
    hotspots=[("Chimbote", -9.1, -78.6, 35), ("Callao", -12.05, -77.15, 28),
              ("Pisco", -13.7, -76.2, 22), ("Paita", -5.1, -81.1, 40)],
    geo_scope="south america", geo_lat=(-19, -2), geo_lon=(-83, -67),
    map_title="Peruvian coast · El Niño rainfall surplus & upwelling shutdown",
    commodity=COMMODITY,
    causal_chain=[("Driver", "Niño-1+2 warm", COLORS["el_nino"]),
                  ("Ocean", "Upwelling suppressed", COLORS["el_nino"]),
                  ("Biology", "Anchoveta disperse", AMBER),
                  ("Quota", "Season cut / closed", AMBER),
                  ("Market", "Fishmeal +, ~8 mo", COLORS["la_nina"])],
    history_rows=[
        ("1972–73", "+2.1", "bad", "severe", "Fishery collapse; the classic protein-meal shock"),
        ("1982–83", "+2.2", "bad", "severe", "Catch fell sharply; fishmeal repriced"),
        ("1997–98", "+2.4", "bad", "severe", "Seasons cancelled; severe coastal flooding"),
        ("2015–16", "+2.6", "bad", "severe", "Quota cuts; fishmeal firm into 2016"),
        ("2023–24", "+2.0", "bad", "severe", "First season cancelled — a live rerun")],
    econ_takeaway=("<b>Direct mechanism, honest verdict.</b> Unmediated by global macro, "
                   "which is exactly why it scores best — and it still fails the null at "
                   "p = 0.078."),
    footer=("<b>Sources:</b> ENSO — NOAA CPC (ERSSTv5) · fishmeal prices — World Bank Pink "
            "Sheet · lag profile, composite and surrogate-tested verdict computed in-repo. "
            "&nbsp;<b>Caveat:</b> coastal rainfall figures are illustrative pending South-"
            "American precip ingestion; IMARPE catch and quota data are <b>not</b> ingested, "
            "so the biology step is documented, not measured here. Not investment advice."),
)

build_region(CFG, climate_view=peru_climate()).servable(
    title="Peru — ENSO Macro Risk Desk")
