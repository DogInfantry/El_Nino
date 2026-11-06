"""Peru / Fishmeal Deep-Dive — the original El Niño, and the desk's best near-miss.

Run with::

    panel serve dashboard/pages/13_peru.py --show

Peru is the only `wet`-sign row in the registry and the only region whose price response
comes out **positive**. Every other entry is a drought story where El Niño suppresses
supply somewhere in the tropics; here the warm coastal water that gave the phenomenon its
name shuts down the upwelling the anchoveta feed on, the fishery closes, and fishmeal —
the world's protein-feed input — moves up.

It also has the highest Granger count on the desk and is still not proven: the surrogate p
misses α=0.05. Those figures move with each refresh, so the page reads them from the cache.
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

COMMODITY = "Fish meal"
NUM = region_numbers("PER")
_NINO12, _ = latest_index("NINO12")
_NEAR_MISS = 0.05 <= NUM["p"] < 0.10
_GRANGER = (f"<b>{NUM['granger']} of 24 lags</b>"
            + (", the most on the desk" if NUM["granger_top"] else ""))


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
        f"Peak correlation is <b style='color:#e8edf5'>r = {minus(lag['peak_r'], 3)}</b> at "
        f"<b style='color:#e8edf5'>{lag['peak_lag']} months</b>: {sign_word}, and the only "
        "meaningfully positive row in the registry. The sign is the mechanism showing "
        "through: warm water suppresses upwelling → the anchoveta biomass disperses and "
        "quotas are cut → fishmeal tightens, roughly two to three quarters later. The "
        "composite is the weaker exhibit here, and shows why timing matters, El Niño months "
        f"average <b style='color:#e8edf5'>{m['El Nino']:+.1f}%</b> against La Niña's "
        f"<b style='color:#e8edf5'>{m['La Nina']:+.1f}%</b>, nearly a tie, because "
        f"collapsing the {lag['peak_lag']}-month lag into a contemporaneous average destroys the "
        "very signal the lag profile recovers.</div>")
    tag = "HONEST NEAR-MISS" if _NEAR_MISS else "VERDICT"
    tail = " The desk does not promote a link on a near-miss." if _NEAR_MISS else ""
    tk = pn.pane.HTML(
        f"<div class='tk'><span class='tg'>{tag}</span>Granger fires on {_GRANGER}, and cross-map "
        f"ρ is <b>{NUM['rho']:.2f}</b> against a phase-randomized null averaging "
        f"<b>{NUM['null']:.2f}</b>. But {null_read(NUM)}, so the verdict reads "
        f"<b>{NUM['verdict']}</b> and the stance reads <b>{NUM['badge']}</b>.{tail}</div>")
    return pn.Column(causal_chain(CFG), charts, note, tk, sizing_mode="stretch_width")


CFG = RegionConfig(
    name="PERU", flag="🇵🇪", iso3="PER", regime="EL NIÑO",
    thesis=("Warm coastal water shuts down the Humboldt upwelling, the anchoveta fishery "
            "closes, and fishmeal tightens two to three quarters later, the oldest ENSO "
            "impact on record and this desk's clearest positive-sign link."),
    desk=dict(
        badge="● WATCH", badge_cls="watch", instruments="Fish meal",
        sub="stance cache missing",
        engine_read=(("Engine read: the largest <b>positive</b> r_peak in the registry "
                      if NUM["biggest_positive"] else "Engine read: peak correlation ")
                     + f"(<b>{minus(NUM['r'])} at {NUM['horizon']}</b>), Granger on {_GRANGER}, and "
                     f"cross-map ρ {NUM['rho']:.2f} against a {NUM['null']:.2f} null. "
                     f"{null_read(NUM)[0].upper()}{null_read(NUM)[1:]}, and the verdict reads "
                     f"<b>{NUM['verdict']}</b>."),
        catalyst="<b>IMARPE biomass survey and the quota decision</b> for the following season.",
        risk=(f"<b>Reading one p-value as a result.</b> p = {NUM['p']:.3f} on {NUM['n_surrogates']} "
              "surrogates moves with each monthly re-estimation.")),
    kpis=price_kpis(NUM),
    hotspots=[("Chimbote", -9.1, -78.6, None), ("Callao", -12.05, -77.15, None),
              ("Pisco", -13.7, -76.2, None), ("Paita", -5.1, -81.1, None)],
    geo_scope="south america", geo_lat=(-19, -2), geo_lon=(-83, -67),
    map_title="Peruvian coast · locations only, rainfall and catch are not ingested",
    commodity=COMMODITY,
    causal_chain=[("Driver", f"Niño-1+2 {minus(_NINO12, 1)}°C", COLORS["el_nino"]),
                  ("Ocean", "Upwelling suppressed", COLORS["el_nino"]),
                  ("Biology", "Anchoveta disperse", AMBER),
                  ("Quota", "Season cut / closed", AMBER),
                  ("Market", f"Fishmeal r {minus(NUM['r'])}, {NUM['horizon']}", COLORS["la_nina"])],
    history_rows=[
        event_row(1972, COMMODITY, "bad", "severe", "Fishery collapse."),
        event_row(1982, COMMODITY, "bad", "severe", "Catch fell sharply."),
        event_row(1997, COMMODITY, "bad", "severe", "Seasons cancelled; severe coastal flooding."),
        event_row(2015, COMMODITY, "bad", "severe", "Quota cuts."),
        event_row(2023, COMMODITY, "bad", "severe", "First season cancelled.")],
    econ_takeaway=("<b>Direct mechanism, honest verdict.</b> Unmediated by global macro, and "
                   f"{null_read(NUM)}: the link reads {NUM['verdict']}."),
    footer=("<b>Sources:</b> ENSO from NOAA CPC (ERSSTv5) · fishmeal prices from the World Bank Pink "
            "Sheet · lag profile, composite, price moves and surrogate-tested verdict computed "
            "in-repo. &nbsp;<b>Caveat:</b> coastal rainfall is not ingested, so the map marks "
            "locations. IMARPE catch and quota data are <b>not</b> ingested either, so the biology "
            "step and the impact column are documented, not measured here. Not investment advice."),
)

build_region(CFG, climate_view=peru_climate()).servable(
    title="Peru, ENSO Macro Risk Desk")
