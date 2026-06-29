"""Parameterised region deep-dive builder for the ENSO Macro Risk Desk.

`07_india.py` proved the layout; this generalises everything region-agnostic so a new
region (SE Asia, Brazil, Australia, the cocoa belt, Peru, ...) is a thin config file.

WHAT IS SHARED vs PER-REGION
----------------------------
Shared (here):  the terminal bar, thesis band, DESK VIEW (call/catalyst/risk), the
                map + KPI rail, the Economics tab (live Granger/CCM on the region's
                key commodity), the History tab, the footer, and all the CSS.
Per-region:     a `RegionConfig` (identity, thesis, desk view, KPIs, hotspots, map
                framing, commodity, history rows) PLUS an injected **Climate view** —
                because the climate analysis differs by region (India = ENSO×IOD →
                monsoon; Peru = coastal El Niño → floods; etc.). India passes its real
                ENSO×IOD engine; lighter regions pass a simpler composite.

A region page is then::

    from region_template import RegionConfig, REGION_CSS, build_region
    pn.extension("plotly", raw_css=[REGION_CSS], sizing_mode="stretch_width")
    CFG = RegionConfig(...)
    build_region(CFG, climate_view=my_climate_builder()).servable(title=...)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import panel as pn
import plotly.graph_objects as go

_DASH_DIR = Path(__file__).resolve().parent
_ROOT = _DASH_DIR.parent
for p in (_DASH_DIR, _ROOT / "data" / "process", _ROOT / "data" / "ingest"):
    sys.path.insert(0, str(p))

from theme import COLORS, load_commodities, load_phases, style_figure  # noqa: E402

try:
    from granger_ccm import analyze
except Exception:  # noqa: BLE001
    analyze = None

AMBER = COLORS.get("amber", "#f4b13a")
_LINE = "rgba(138,148,166,0.18)"

REGION_CSS = f"""
:host, body {{ background-color:{COLORS['bg']}; color:{COLORS['text']}; }}
.rg-bar {{ display:flex; align-items:center; gap:12px; padding:11px 16px; background:#0a1020;
  border:1px solid {_LINE}; border-radius:12px 12px 0 0; font:600 12px/1 ui-monospace,monospace; }}
.rg-bar .nm {{ color:{COLORS['text']}; font-weight:700; letter-spacing:.5px; }} .rg-bar .flag {{ font-size:17px; }}
.rg-bar .reg {{ color:{COLORS['el_nino']}; background:rgba(244,98,58,.12); border:1px solid rgba(244,98,58,.34);
  padding:4px 8px; border-radius:5px; font-size:10px; letter-spacing:.6px; }}
.rg-bar .live {{ margin-left:auto; color:{COLORS['el_nino']}; font-size:10.5px; }}
.rg-thesis {{ padding:10px 16px; font-size:12.5px; line-height:1.5; color:{COLORS['muted']}; background:{COLORS['surface']}; }}
.rg-thesis b {{ color:{COLORS['text']}; }}
.dv {{ padding:12px 16px; border-left:3px solid {COLORS['teal']}; background:linear-gradient(180deg, rgba(0,212,180,.09), rgba(10,16,32,0) 90%); }}
.dv-lab {{ font:700 9px ui-monospace,monospace; letter-spacing:1.4px; text-transform:uppercase; color:{COLORS['muted']}; }}
.dv-badge {{ font:800 13px/1 ui-monospace,monospace; color:#04211d; background:{COLORS['teal']}; padding:6px 11px; border-radius:6px; letter-spacing:.5px; }}
.dv-badge.watch {{ color:#2a1e06; background:{AMBER}; }} .dv-badge.cautious {{ color:#2a120b; background:{COLORS['el_nino']}; }}
.dv-inst {{ font-size:14px; font-weight:800; color:{COLORS['text']}; }}
.dv-now {{ margin-top:9px; font-size:11.5px; color:{COLORS['text']}; background:#0e1626; border:1px solid {_LINE}; border-radius:8px; padding:7px 11px; }}
.dv-now b {{ color:{COLORS['teal']}; }}
.dv-cell {{ background:#0e1626; border:1px solid {_LINE}; border-radius:8px; padding:8px 11px; font-size:12px; color:{COLORS['muted']}; line-height:1.4; }}
.dv-cell b {{ color:{COLORS['text']}; }} .dv-cell .ck {{ font:700 8.5px ui-monospace,monospace; letter-spacing:.8px; text-transform:uppercase; }}
.dv-cell.cat .ck {{ color:{COLORS['teal']}; }} .dv-cell.risk .ck {{ color:{COLORS['el_nino']}; }}
.card {{ background:{COLORS['surface']}; border:1px solid rgba(138,148,166,0.14); border-radius:11px; padding:12px 13px; }}
.kpi {{ background:{COLORS['surface']}; border:1px solid rgba(138,148,166,0.14); border-radius:10px; padding:9px 11px; }}
.kpi .k {{ font-size:9px; letter-spacing:.5px; text-transform:uppercase; color:{COLORS['muted']}; }}
.kpi .v {{ font-size:23px; font-weight:800; line-height:1.05; margin-top:2px; }}
.lab {{ font:700 10px/1 ui-monospace,monospace; letter-spacing:1.3px; text-transform:uppercase; color:{COLORS['teal']}; margin:0 0 10px; }}
.real {{ font:700 8px ui-monospace,monospace; letter-spacing:.6px; color:#04211d; background:{COLORS['teal']}; padding:2px 6px; border-radius:4px; margin-left:6px; }}
.illus {{ font:700 8px ui-monospace,monospace; letter-spacing:.6px; color:#2a1e06; background:{AMBER}; padding:2px 6px; border-radius:4px; margin-left:6px; }}
.reg .row {{ display:flex; gap:8px; font:600 11.5px ui-monospace,monospace; padding:5px 0; border-bottom:1px solid rgba(138,148,166,0.12); }}
.reg .nm {{ width:130px; color:{COLORS['text']}; }} .reg .pv {{ color:{COLORS['muted']}; }} .reg .sig {{ margin-left:auto; color:{COLORS['teal']}; }}
.reg .foot {{ margin-top:7px; font-size:10px; color:{COLORS['muted']}; line-height:1.5; }}
.tk {{ margin-top:11px; font-size:11.5px; color:{COLORS['muted']}; background:#0e1626; border:1px solid {_LINE}; border-radius:8px; padding:8px 11px; line-height:1.5; }}
.tk b {{ color:{COLORS['text']}; }} .tk .tg {{ font:700 8.5px ui-monospace,monospace; color:#04211d; background:{COLORS['teal']}; padding:3px 6px; border-radius:4px; margin-right:7px; }}
table.hist {{ width:100%; border-collapse:collapse; font-size:12px; }}
table.hist th {{ text-align:left; font:700 9px/1 ui-monospace,monospace; letter-spacing:.8px; text-transform:uppercase; color:{COLORS['muted']}; padding:7px 9px; border-bottom:1px solid rgba(138,148,166,0.2); }}
table.hist td {{ padding:8px 9px; border-bottom:1px solid rgba(138,148,166,0.08); color:{COLORS['muted']}; }} table.hist td.yr {{ color:{COLORS['text']}; font-weight:700; }}
.chip {{ font:700 9.5px ui-monospace,monospace; padding:2px 6px; border-radius:4px; }}
.chip.bad {{ color:#2a120b; background:{COLORS['el_nino']}; }} .chip.ok {{ color:#04211d; background:{COLORS['la_nina']}; }} .chip.mid {{ color:#2a1e06; background:{AMBER}; }}
.rg-foot {{ padding:11px 16px; border-top:1px solid {_LINE}; background:{COLORS['surface']}; font-size:10px; color:{COLORS['muted']}; line-height:1.5; border-radius:0 0 12px 12px; }}
.rg-foot b {{ color:{COLORS['muted']}; }}
"""


@dataclass
class RegionConfig:
    name: str                                   # e.g. "INDIA"
    flag: str                                    # emoji
    iso3: str                                    # ISO-3 for the choropleth, e.g. "IND"
    regime: str                                  # badge, e.g. "STRONG EL NIÑO · 2026"
    thesis: str                                  # one-line thesis (HTML-safe)
    desk: dict                                   # badge, instruments, sub, engine_read, catalyst, risk
    kpis: list[tuple[str, str, str]]             # (label, value, color)
    hotspots: list[tuple[str, float, float, float]]  # (name, lat, lon, pct) — pct<0 dry/red, >0 wet/blue
    geo_scope: str                               # plotly geo scope, e.g. "asia"
    geo_lat: tuple[float, float]
    geo_lon: tuple[float, float]
    map_title: str
    commodity: str                               # for the live Granger/CCM economics tab
    history_rows: list[tuple[str, str, str, str, str]]  # (event, oni, chip_cls, outcome, note)
    causal_chain: list[tuple[str, str, str]]     # (label, value, color)
    footer: str
    econ_takeaway: str = ("The price link is causal and lagged — position during the season, "
                          "ahead of the price response.")


# ---- shared builders -----------------------------------------------------
def _bar(cfg: RegionConfig) -> pn.pane.HTML:
    return pn.pane.HTML(
        f"<div class='rg-bar'><span style='color:{COLORS['teal']}'>← MAP</span>"
        f"<span class='flag'>{cfg.flag}</span><span class='nm'>{cfg.name}</span>"
        f"<span class='reg'>{cfg.regime}</span>"
        "<span class='live'>● LIVE · NOAA CPC</span></div>")


def _thesis(cfg: RegionConfig) -> pn.pane.HTML:
    return pn.pane.HTML(f"<div class='rg-thesis'><b>Thesis:</b> {cfg.thesis}</div>")


def _desk_view(cfg: RegionConfig) -> pn.pane.HTML:
    d = cfg.desk
    return pn.pane.HTML(
        "<div class='dv'><div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap'>"
        "<span class='dv-lab'>Desk view</span>"
        f"<span class='dv-badge {d.get('badge_cls', '')}'>{d['badge']}</span>"
        f"<span class='dv-inst'>{d['instruments']}</span>"
        f"<span class='dv-lab'>{d['sub']}</span></div>"
        f"<div class='dv-now'>{d['engine_read']}</div>"
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px'>"
        f"<div class='dv-cell cat'><span class='ck'>Catalyst</span> &nbsp;{d['catalyst']}</div>"
        f"<div class='dv-cell risk'><span class='ck'>Key risk</span> &nbsp;{d['risk']}</div></div></div>")


def _region_map(cfg: RegionConfig) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        locations=[cfg.iso3], locationmode="ISO-3", z=[1], showscale=False,
        colorscale=[[0, "#7a2f1a"], [1, "#7a2f1a"]], marker_line_color="#ff8a5a",
        marker_line_width=1, hoverinfo="skip"))
    if cfg.hotspots:
        # dry (pct<0) = amber/red dots; wet (pct>0) = blue dots (e.g. Peru floods)
        cols = ["#ffce3a" if h[3] <= 0 else COLORS["la_nina"] for h in cfg.hotspots]
        fig.add_trace(go.Scattergeo(
            lon=[h[2] for h in cfg.hotspots], lat=[h[1] for h in cfg.hotspots],
            mode="markers+text", showlegend=False,
            text=[f"{h[0]} {h[3]:+.0f}%" for h in cfg.hotspots], textposition="top right",
            textfont=dict(color="#c2cadb", size=9), hoverinfo="text",
            marker=dict(size=[min(abs(h[3]) * 0.35, 16) for h in cfg.hotspots], color=cols,
                        opacity=0.75, line=dict(color="#0a0e1a", width=1))))
    style_figure(fig, height=380, margin=dict(l=4, r=4, t=30, b=4), showlegend=False,
                 title=dict(text=cfg.map_title, font=dict(size=12, color=COLORS["muted"])))
    fig.update_geos(scope=cfg.geo_scope, lataxis_range=list(cfg.geo_lat),
                    lonaxis_range=list(cfg.geo_lon), showland=True, landcolor="#10182a",
                    showcountries=True, countrycolor="#0a1224", showocean=True,
                    oceancolor="#0a1224", bgcolor="rgba(0,0,0,0)", framecolor="rgba(0,0,0,0)")
    return fig


def _kpi_rail(cfg: RegionConfig) -> pn.pane.HTML:
    cells = "".join(f"<div class='kpi'><div class='k'>{lab}</div>"
                    f"<div class='v' style='color:{col}'>{val}</div></div>"
                    for lab, val, col in cfg.kpis)
    return pn.pane.HTML(f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:9px'>{cells}</div>")


def causal_chain(cfg: RegionConfig) -> pn.pane.HTML:
    cells = "<span style='color:#5b6577;padding:0 6px'>→</span>".join(
        f"<span style='background:#1b2235;border:1px solid {_LINE};border-radius:8px;padding:7px 9px;"
        f"display:inline-block'><span style='font-size:8px;text-transform:uppercase;color:#5b6577'>{k}</span>"
        f"<br><b style='font-size:11px;color:{c}'>{v}</b></span>" for k, v, c in cfg.causal_chain)
    return pn.pane.HTML(f"<div style='display:flex;align-items:center;overflow-x:auto;margin-bottom:11px'>{cells}</div>")


def _ccm_chart(ccm, name: str) -> go.Figure:
    fig = go.Figure()
    spec = {"ONI->target": (f"ONI → {name}", COLORS["teal"]),
            "target->ONI": (f"{name} → ONI", COLORS["el_nino"])}
    for direction, (label, color) in spec.items():
        g = ccm[ccm["direction"] == direction].sort_values("lib_size")
        fig.add_trace(go.Scatter(x=g["lib_size"], y=g["rho"], mode="lines+markers",
                                 line=dict(color=color, width=2.4), name=label))
    style_figure(fig, height=300, margin=dict(l=50, r=10, t=40, b=40),
                 title=dict(text=f"Convergent Cross Mapping — ONI → {name}", font=dict(size=14)),
                 yaxis=dict(title="cross-map skill ρ"), xaxis=dict(title="library size"),
                 legend=dict(orientation="h", y=-0.25))
    return fig


def _econ_tab(cfg: RegionConfig) -> pn.viewable.Viewable:
    tk = pn.pane.HTML(f"<div class='tk'><span class='tg'>TAKEAWAY</span>{cfg.econ_takeaway}</div>")
    if analyze is None:
        return pn.Column(pn.pane.HTML("<div class='card'>Causation engine unavailable.</div>"), tk)
    try:
        oni = load_phases().set_index("date")["value"].astype(float).asfreq("MS")
        comm = load_commodities()
        series = (comm[comm["commodity"] == cfg.commodity].set_index("date")["price"]
                  .astype(float).asfreq("MS"))
        res = analyze(oni, series, maxlag=24, mode="detrend")
        short = cfg.commodity.split(",")[0]
        chart = pn.pane.Plotly(_ccm_chart(res["ccm"], short), config={"displayModeBar": False},
                               sizing_mode="stretch_width")
        verdict = pn.pane.HTML(
            f"<div class='card'><div class='lab'>Causation — ONI → {short} "
            "<span class='real'>LIVE Granger+CCM</span></div>"
            "<div style='font-size:12px;line-height:1.55;color:#c2cadb'><b style='color:#e8edf5'>How to "
            "read it:</b> a forward curve (teal) that <b style='color:#e8edf5'>rises and converges</b> "
            "while the reverse (grey) stays flat is the signature of one-way ONI→price forcing. A flat "
            "forward curve means the apparent link is likely <b style='color:#e8edf5'>spurious</b> — the "
            "misattribution guard. Computed live on detrended series.</div></div>")
        body = pn.Row(pn.Column(chart, css_classes=["card"]), verdict)
    except Exception as exc:  # noqa: BLE001
        body = pn.pane.HTML(f"<div class='card'>Economics compute failed for "
                            f"'{cfg.commodity}': {exc}</div>")
    return pn.Column(body, tk, sizing_mode="stretch_width")


def _history_tab(cfg: RegionConfig) -> pn.viewable.Viewable:
    trs = "".join(
        f"<tr><td class='yr'>{yr}</td><td>{oni}</td>"
        f"<td><span class='chip {cls}'>{outcome}</span></td><td>{note}</td></tr>"
        for yr, oni, cls, outcome, note in cfg.history_rows)
    table = pn.pane.HTML(
        "<table class='hist'><tr><th>Event</th><th>ONI peak</th><th>Impact</th><th>Outcome</th></tr>"
        + trs + "</table>")
    return pn.Column(pn.Column(table, css_classes=["card"]), sizing_mode="stretch_width")


def build_region(cfg: RegionConfig, climate_view: pn.viewable.Viewable,
                 agri_view: pn.viewable.Viewable | None = None) -> pn.viewable.Viewable:
    """Assemble a full region deep-dive. `climate_view` is the region-specific exhibit."""
    hero = pn.Row(
        pn.Column(pn.pane.Plotly(_region_map(cfg), config={"displayModeBar": False},
                                 sizing_mode="stretch_width"), css_classes=["card"]),
        pn.Column(_kpi_rail(cfg),
                  pn.pane.HTML("<div class='card' style='margin-top:9px;font-size:11px;color:#c2cadb'>"
                               "<b style='color:#00d4b4'>ONI → impact: CAUSAL</b> · one-way "
                               "(Granger + CCM converges forward).</div>"),
                  width=360),
        sizing_mode="stretch_width")
    tabs = pn.Tabs(
        ("Climate", climate_view),
        ("Agriculture", agri_view or pn.pane.HTML(
            "<div class='card' style='color:#8a94a6'>Agriculture composite — pending crop ingestion "
            "for this region.</div>")),
        ("Economics", _econ_tab(cfg)),
        ("History", _history_tab(cfg)),
        dynamic=True,
    )
    return pn.Column(
        _bar(cfg), _thesis(cfg), _desk_view(cfg), pn.Spacer(height=10), hero,
        pn.Spacer(height=10), tabs, pn.pane.HTML(f"<div class='rg-foot'>{cfg.footer}</div>"),
        styles={"background": COLORS["bg"], "padding": "22px", "min-height": "100vh",
                "max-width": "1180px", "margin": "0 auto"}, sizing_mode="stretch_width")
