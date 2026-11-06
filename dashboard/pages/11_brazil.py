"""Brazil / Arabica Deep-Dive — the region where the desk's answer is "no trade".

Run with::

    panel serve dashboard/pages/11_brazil.py --show

Brazil is on the desk because the ENSO→coffee trade is one the market actually makes,
not because it survives testing. It does not. The ENSO-phase composite is exactly the
trap this desk exists to catch: El Niño months average a visibly higher Arabica return
than La Niña ones, which reads like a premium — and the lag profile flattens to nothing,
peaking at r ≈ −0.07 on the *window edge*, which is not even a horizon. Both exhibits are
shown side by side for that reason.
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
    minus, phase_composite, price_kpis, region_numbers,
)

AMBER = COLORS.get("amber", "#f4b13a")
pn.extension("plotly", raw_css=[REGION_CSS], sizing_mode="stretch_width")

COMMODITY = "Coffee, Arabica"
NUM = region_numbers("BRA")
_NINO34, _ = latest_index("NINO34")
_EDGE = "the 24-month window edge" if NUM["on_edge"] else NUM["horizon"]
_RANK = (f"the smallest |r| of the {NUM['n_rows']} registry rows" if NUM["rank_from_weakest"] == 1
         else f"number {NUM['rank_from_weakest']} from the bottom of the {NUM['n_rows']} registry rows")


def brazil_climate() -> pn.viewable.Viewable:
    comp_fig, comp = phase_composite(COMMODITY)
    lag_fig, lag = lag_profile(COMMODITY)
    m = comp["means"]
    edge = " (window edge, the true peak may lie outside)" if lag["peak_lag"] == 24 else ""

    charts = pn.Row(
        pn.Column(pn.pane.Plotly(comp_fig, config={"displayModeBar": False}),
                  css_classes=["card"]),
        pn.Column(pn.pane.Plotly(lag_fig, config={"displayModeBar": False}),
                  css_classes=["card"]), sizing_mode="stretch_width")
    note = pn.pane.HTML(
        "<div class='card' style='font-size:12px;line-height:1.6;color:#c2cadb'>"
        "<div class='lab'>Two exhibits, two answers <span class='real'>COMPUTED</span></div>"
        f"The composite looks like a story: El Niño months average <b style='color:#e8edf5'>"
        f"{m['El Nino']:+.1f}%</b> YoY against La Niña's <b style='color:#e8edf5'>"
        f"{m['La Nina']:+.1f}%</b> (n={comp['n']['El Nino']}/{comp['n']['La Nina']} months). "
        "Coffee bulls quote exactly this. But a composite has no time axis, it cannot "
        "separate a drought transmitting into price from ENSO merely coinciding with a "
        "decade of coffee inflation. Put the lag axis back and the link collapses: peak "
        f"<b style='color:#e8edf5'>r = {minus(lag['peak_r'], 3)}</b> at "
        f"<b style='color:#e8edf5'>{lag['peak_lag']} mo</b>{edge}, {_RANK}.</div>")
    tk = pn.pane.HTML(
        "<div class='tk'><span class='tg'>MISATTRIBUTION GUARD</span>The frost risk that "
        "actually moves Arabica is a <b>mid-latitude cold-air outbreak</b>, not a tropical "
        "Pacific anomaly. Brazil earns its exposure score from structural share of world "
        "supply, not from a demonstrated ENSO link, and the desk says so rather than "
        "selling the composite.</div>")
    return pn.Column(causal_chain(CFG), charts, note, tk, sizing_mode="stretch_width")


CFG = RegionConfig(
    name="BRAZIL", flag="🇧🇷", iso3="BRA", regime="EL NIÑO",
    thesis=("Brazil is the world's largest Arabica producer, so any ENSO→coffee transmission "
            "would matter enormously. The desk's own lag test does not find one."),
    desk=dict(
        badge="● WATCH", badge_cls="watch", instruments="Coffee, Arabica",
        sub="stance cache missing",
        engine_read=(f"Engine read: peak lagged correlation is <b>r = {minus(NUM['r'])} at "
                     f"{_EDGE}</b>, {_RANK}, and the phase composite's apparent El Niño premium "
                     "does not survive putting time back on the axis. Arabica has no surrogate "
                     f"test on this desk, so the verdict reads <b>{NUM['verdict']}</b>. Exposure "
                     "here is <b>structural</b> (share of world supply), not causal."),
        catalyst="<b>A mid-latitude frost event in Minas Gerais</b>: which ENSO does not forecast.",
        risk="<b>Trading this as an ENSO story.</b> The composite invites it; the lag profile refuses."),
    kpis=price_kpis(NUM),
    hotspots=[("Minas Gerais", -19.9, -44.0, None), ("São Paulo", -22.0, -48.0, None),
              ("Espírito Santo", -19.5, -40.5, None), ("Bahia (Cerrado)", -12.5, -42.0, None)],
    geo_scope="south america", geo_lat=(-28, -2), geo_lon=(-60, -35),
    map_title="Brazilian Arabica belt · locations only, rainfall is not ingested",
    commodity=COMMODITY,
    causal_chain=[("Driver", f"Niño-3.4 {minus(_NINO34, 1)}°C", COLORS["el_nino"]),
                  ("Atmos", "Weak S. Atlantic signal", COLORS["muted"]),
                  ("Weather", "No robust skew", COLORS["muted"]),
                  ("Crop", "Frost = separate driver", AMBER),
                  ("Market", f"Peak r {minus(NUM['r'])}", COLORS["muted"])],
    history_rows=[
        event_row(1997, COMMODITY, "mid", "mixed", "Strong El Niño."),
        event_row(2015, COMMODITY, "mid", "mixed", "Cerrado drought, but price led by stocks."),
        event_row(2021, COMMODITY, "bad", "severe", "A non-ENSO cold outbreak.",
                  window=("2021-05-01", "2022-02-01"), label="2021 frost"),
        event_row(2023, COMMODITY, "mid", "mixed", "Attributed to Robusta substitution, not ENSO.")],
    econ_takeaway=("<b>The honest read is no trade.</b> The lag test finds little"
                   + (" and the peak sits on the window edge, so there is no horizon to position "
                      "against." if NUM["on_edge"] else ", and there is no surrogate test behind it.")),
    footer=("<b>Sources:</b> ENSO from NOAA CPC (ERSSTv5) · Arabica prices from the World Bank Pink "
            "Sheet · composite &amp; lag profile computed in-repo. &nbsp;<b>Caveat:</b> "
            "South-American rainfall is not ingested, so the map marks locations and the impact "
            "column is a qualitative note. The composite, the lag profile, the price moves and "
            "the stance are computed. Not investment advice."),
)

build_region(CFG, climate_view=brazil_climate()).servable(
    title="Brazil, ENSO Macro Risk Desk")
