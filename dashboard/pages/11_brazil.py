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
    RegionConfig, REGION_CSS, build_region, causal_chain, lag_profile, phase_composite,
)

AMBER = COLORS.get("amber", "#f4b13a")
pn.extension("plotly", raw_css=[REGION_CSS], sizing_mode="stretch_width")

COMMODITY = "Coffee, Arabica"


def brazil_climate() -> pn.viewable.Viewable:
    comp_fig, comp = phase_composite(COMMODITY)
    lag_fig, lag = lag_profile(COMMODITY)
    m = comp["means"]
    edge = " (window edge — the true peak may lie outside)" if lag["peak_lag"] == 24 else ""

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
        "Coffee bulls quote exactly this. But a composite has no time axis — it cannot "
        "separate a drought transmitting into price from ENSO merely coinciding with a "
        "decade of coffee inflation. Put the lag axis back and the link collapses: peak "
        f"<b style='color:#e8edf5'>r = {lag['peak_r']:+.3f}</b> at "
        f"<b style='color:#e8edf5'>{lag['peak_lag']} mo</b>{edge}. That is the weakest "
        "link in the whole registry.</div>")
    tk = pn.pane.HTML(
        "<div class='tk'><span class='tg'>MISATTRIBUTION GUARD</span>The frost risk that "
        "actually moves Arabica is a <b>mid-latitude cold-air outbreak</b>, not a tropical "
        "Pacific anomaly. Brazil earns its exposure score from structural share of world "
        "supply, not from a demonstrated ENSO link — and the desk says so rather than "
        "selling the composite.</div>")
    return pn.Column(causal_chain(CFG), charts, note, tk, sizing_mode="stretch_width")


CFG = RegionConfig(
    name="BRAZIL", flag="🇧🇷", iso3="BRA", regime="WEAK EL NIÑO · 2026",
    thesis=("Brazil grows roughly a third of the world's Arabica, so any ENSO→coffee "
            "transmission would matter enormously. The desk's own tests say there isn't one."),
    desk=dict(
        badge="● WATCH", badge_cls="watch", instruments="Coffee, Arabica",
        sub="no demonstrated ENSO link · structural exposure only",
        engine_read=("Engine read — peak lagged correlation is <b>r ≈ −0.07 at the 24-month "
                     "window edge</b>, the weakest in the registry, and the phase composite's "
                     "apparent El Niño premium does not survive putting time back on the "
                     "axis. Exposure here is <b>structural</b> (share of world supply), "
                     "not causal."),
        catalyst="<b>A mid-latitude frost event in Minas Gerais</b> — which ENSO does not forecast.",
        risk="<b>Trading this as an ENSO story.</b> The composite invites it; the lag profile refuses."),
    kpis=[("Peak |r|", "0.07", COLORS["muted"]), ("Peak lag", "24 mo †", AMBER),
          ("World Arabica share", "~1/3", COLORS["text"]),
          ("ENSO link", "none found", COLORS["muted"])],
    hotspots=[("Minas Gerais", -19.9, -44.0, -8), ("São Paulo", -22.0, -48.0, -6),
              ("Espírito Santo", -19.5, -40.5, -5), ("Bahia (Cerrado)", -12.5, -42.0, -7)],
    geo_scope="south america", geo_lat=(-28, -2), geo_lon=(-60, -35),
    map_title="Brazilian Arabica belt · illustrative rainfall skew",
    commodity=COMMODITY,
    causal_chain=[("Driver", "Niño-3.4 +1.0°C", COLORS["el_nino"]),
                  ("Atmos", "Weak S. Atlantic signal", COLORS["muted"]),
                  ("Weather", "No robust skew", COLORS["muted"]),
                  ("Crop", "Frost = separate driver", AMBER),
                  ("Market", "No lagged response", COLORS["muted"])],
    history_rows=[
        ("1997–98", "+2.4", "mid", "mixed", "Strong El Niño; Arabica fell through 1998"),
        ("2015–16", "+2.6", "mid", "mixed", "Cerrado drought, but price led by stocks"),
        ("2021 frost", "n/a", "bad", "severe", "Price doubled — a NON-ENSO cold outbreak"),
        ("2023–24", "+2.0", "mid", "mixed", "Rally driven by Robusta substitution, not ENSO")],
    econ_takeaway=("<b>The honest read is no trade.</b> The lag test finds nothing and the "
                   "peak sits on the window edge, so there is no horizon to position against."),
    footer=("<b>Sources:</b> ENSO — NOAA CPC (ERSSTv5) · Arabica prices — World Bank Pink "
            "Sheet · composite &amp; lag profile computed in-repo. &nbsp;<b>Caveat:</b> "
            "hotspot rainfall figures are illustrative pending South-American precip "
            "ingestion; the composite, the lag profile and the stance are computed. "
            "Not investment advice."),
)

build_region(CFG, climate_view=brazil_climate()).servable(
    title="Brazil — ENSO Macro Risk Desk")
