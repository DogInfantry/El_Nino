"""ENSO Macro Risk Desk — the landing / front door.

The "Bloomberg-meets-climate" command surface that ties the region deep-dives
together. Run with::

    panel serve dashboard/pages/00_landing.py --show

Layout (locked v4 mockup `landing-risk-desk-v4.html`):
    - ENSO<GO> command bar + tab chips + LIVE advisory stamp
    - scrolling ticker (real ONI / forecast / exposure facts — not fabricated moves)
    - main grid:  left rail (Niño-3.4 gauge · ONI 24-mo spark · 12-mo forecast cone)
                  | center  world EXPOSURE-INDEX choropleth (diverging by dry/wet sign)
                  | right   most-exposed-regions leaderboard (India & SE Asia link live)
    - bottom CAUSATION STRIP: 6 ONI->commodity cards with the REAL precomputed
      Granger+CCM verdicts and the honest reframed headline.

Honesty note (LOCKED decision, Option A — see CLAUDE.md "ONI->commodity-PRICE
causation is genuinely weak"): the v4 mockup's "palm/robusta CAUSAL, cocoa &
wheat FAIL" is illustrative and factually wrong vs our own data. NONE of the six
links is strongly causal (max CCM rho 0.32). We render the *computed* verdicts
from `landing_verdicts.parquet` and reframe the headline: most ENSO->price trades
the market makes don't survive causal testing — the clean ENSO signal is on the
climate/production side (monsoon, Maritime-Continent drought), not noisy prices.

All figures are Plotly / inline-SVG / HTML — NO pydeck / WebGL (un-verifiable).
The page reads parquet caches only; no fetchers run at serve time.
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
_ROOT = _DASH_DIR.parent
for p in (_DASH_DIR, _DASH_DIR / "components", _ROOT / "data" / "ingest"):
    sys.path.insert(0, str(p))

from theme import COLORS, CACHE_DIR, FONT_FAMILY, load_oni  # noqa: E402
from oni_gauge import build_gauge  # noqa: E402

try:
    from advisory_fetcher import get_advisory
except Exception:  # noqa: BLE001
    def get_advisory():  # type: ignore[misc]
        return None

AMBER = COLORS.get("amber", "#f4b13a")
_LINE = "rgba(138,148,166,0.16)"

# Which regions have a live deep-dive page served alongside this one.
# Maps an exposure-index iso3 -> (panel route, label) so leaderboard rows link out.
DEEP_DIVES: dict[str, tuple[str, str]] = {
    "IND": ("07_india", "India deep-dive"),
    "IDN": ("08_seasia", "SE Asia deep-dive"),
    "MYS": ("08_seasia", "SE Asia deep-dive"),
    "THA": ("08_seasia", "SE Asia deep-dive"),
}

RAW_CSS = f"""
:host, body {{ background-color:{COLORS['bg']}; color:{COLORS['text']}; }}
.rd {{ background:#070b14; border:1px solid {_LINE}; border-radius:14px; overflow:hidden; }}
.cmd {{ display:flex; align-items:center; gap:7px; padding:9px 14px; background:#0a1020;
  border-bottom:1px solid {_LINE}; font:600 11.5px/1 ui-monospace,monospace; flex-wrap:wrap; }}
.cmd .go {{ color:{COLORS['teal']}; font-weight:800; letter-spacing:.5px; }}
.cmd .fn {{ color:#aeb8cc; background:#141c30; border:1px solid {_LINE}; padding:5px 9px; border-radius:5px; }}
.cmd .fn.on {{ color:#070b14; background:{COLORS['teal']}; border-color:{COLORS['teal']}; }}
.cmd a.fn {{ text-decoration:none; cursor:pointer; transition:.15s; }}
.cmd a.fn:hover {{ border-color:{COLORS['teal']}; color:{COLORS['text']}; }}
.cmd a.fn.on:hover {{ color:#070b14; }}
.cmd .live {{ margin-left:auto; color:{COLORS['el_nino']}; }}
.cmd .live::before {{ content:'\\25cf'; margin-right:5px; animation:bl 1.4s infinite; }}
@keyframes bl {{ 50%{{opacity:.3}} }}
.tick {{ background:#0a0f1c; border-bottom:1px solid {_LINE}; overflow:hidden; white-space:nowrap; padding:7px 0; }}
.tick .run {{ display:inline-block; padding-left:100%; animation:mar 34s linear infinite;
  font:600 11px ui-monospace,monospace; color:#aeb8cc; }}
.tick b.u {{ color:{COLORS['la_nina']} }} .tick b.d {{ color:{COLORS['el_nino']} }}
.tick .sep {{ color:#445; margin:0 14px; }}
@keyframes mar {{ from{{transform:translateX(0)}} to{{transform:translateX(-100%)}} }}
.h {{ font:700 9px/1 ui-monospace,monospace; letter-spacing:1.3px; text-transform:uppercase;
  color:{COLORS['neutral']}; margin:0 0 9px; }}
.cap {{ text-align:center; font-size:10.5px; color:{COLORS['neutral']}; margin-top:2px; }} .cap b {{ color:{COLORS['text']}; }}
.railwrap {{ padding:14px; border-right:1px solid {_LINE}; }}
.wid {{ margin-bottom:16px; }}
.mapwrap {{ padding:6px 6px 0; }}
.boardwrap {{ padding:14px; border-left:1px solid {_LINE}; }}
.lrow {{ display:grid; grid-template-columns:15px 1fr 32px; gap:8px; align-items:center;
  padding:5px 0; text-decoration:none; }}
.lrow:hover .lbar i {{ filter:brightness(1.3); }}
.lrow .rk {{ font:700 9px ui-monospace,monospace; color:{COLORS['neutral']}; }}
.lrow .ln {{ font-size:10.5px; color:{COLORS['text']}; margin-bottom:3px; display:flex; align-items:center; gap:5px; }}
.lrow .dot {{ width:7px; height:7px; border-radius:50%; flex:none; }}
.lrow .link {{ color:{COLORS['teal']}; font-size:8.5px; letter-spacing:.4px; margin-left:auto; }}
.lrow .lbar {{ height:7px; background:#161f34; border-radius:4px; overflow:hidden; }}
.lrow .lbar i {{ display:block; height:7px; border-radius:4px; }}
.lrow .sc {{ font:700 12px ui-monospace,monospace; color:{AMBER}; text-align:right; }}
.czstrip {{ padding:13px 15px; border-top:1px solid {_LINE}; background:#0a0f1c; }}
.czhead {{ display:flex; align-items:baseline; gap:10px; margin-bottom:4px; flex-wrap:wrap; }}
.czhead .h {{ margin:0; }} .czhead .sub {{ font-size:10px; color:{COLORS['neutral']}; }}
.czlead {{ font-size:12px; color:#aeb8cc; line-height:1.5; margin:0 0 11px; }} .czlead b {{ color:{COLORS['text']}; }}
.czgrid {{ display:grid; grid-template-columns:repeat(6,1fr); gap:9px; }}
@media(max-width:900px){{ .czgrid{{ grid-template-columns:repeat(2,1fr);}} }}
.cz {{ border:1px solid {_LINE}; border-radius:9px; padding:9px 10px; background:#0e1424; }}
.zlink {{ font:700 10.5px ui-monospace,monospace; color:{COLORS['text']}; margin-bottom:6px; }}
.zbadge {{ display:inline-block; font:700 8.5px ui-monospace,monospace; letter-spacing:.4px;
  padding:3px 6px; border-radius:5px; margin-bottom:7px; }}
.zbadge.mod{{ color:#2a1e06; background:{AMBER}; }}
.zbadge.weak{{ color:#2a120b; background:{COLORS['el_nino']}; }}
.zstat {{ font-size:9.5px; color:#aeb8cc; line-height:1.55; }}
.czcap {{ font-size:9.5px; color:{COLORS['neutral']}; margin-top:10px; font-style:italic; line-height:1.5; }}
.disc {{ background:rgba(0,212,180,0.06); border-left:3px solid {COLORS['teal']}; border-radius:8px;
  padding:11px 15px; font-size:11.5px; color:{COLORS['text']}; line-height:1.55; margin-top:14px; }}
"""

pn.extension("plotly", raw_css=[RAW_CSS], sizing_mode="stretch_width")

_PLOTLY_CFG = {"displayModeBar": False, "responsive": True}


# --------------------------------------------------------------------------
# Left-rail instruments
# --------------------------------------------------------------------------
def build_compact_gauge(value: float) -> go.Figure:
    """Niño-3.4 gauge, sized down for the 212px rail."""
    fig = build_gauge(value, title="Niño-3.4 · latest ONI")
    fig.update_layout(height=170, margin=dict(l=14, r=14, t=34, b=4),
                      paper_bgcolor="rgba(0,0,0,0)")
    fig.update_traces(number={"font": {"size": 22, "color": COLORS["text"]}, "suffix": " °C"},
                      title={"font": {"size": 11, "color": COLORS["neutral"]}})
    return fig


def build_oni_spark(oni: pd.DataFrame, months: int = 24) -> go.Figure:
    """Filled ONI sparkline over the last `months`, with the +0.5 advisory line."""
    d = oni.dropna(subset=["oni"]).tail(months)
    x, y = d["date"], d["oni"].astype(float)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=COLORS["el_nino"], width=2),
                             fill="tozeroy", fillcolor="rgba(244,98,58,0.16)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x.iloc[[-1]], y=y.iloc[[-1]], mode="markers",
                             marker=dict(color=COLORS["el_nino"], size=6), hoverinfo="skip"))
    fig.add_hline(y=0.5, line=dict(color=COLORS["el_nino"], width=0.8, dash="dot"), opacity=0.5)
    fig.add_hline(y=0.0, line=dict(color="rgba(138,148,166,0.35)", width=1))
    fig.update_layout(height=70, margin=dict(l=4, r=4, t=2, b=2),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      showlegend=False, font=dict(family=FONT_FAMILY),
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def build_forecast_cone(fc: pd.DataFrame, oni_tail: pd.DataFrame) -> go.Figure:
    """12-mo Ensemble forecast cone (90% band) anchored to recent observed ONI."""
    ens = fc[fc["model"] == "Ensemble"].sort_values("date")
    obs = oni_tail.dropna(subset=["oni"]).tail(6)
    fig = go.Figure()
    # 90% band
    fig.add_trace(go.Scatter(x=pd.concat([ens["date"], ens["date"][::-1]]),
                             y=pd.concat([ens["upper"], ens["lower"][::-1]]),
                             fill="toself", fillcolor="rgba(244,98,58,0.16)",
                             line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=obs["date"], y=obs["oni"], mode="lines",
                             line=dict(color=COLORS["neutral"], width=1.5), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ens["date"], y=ens["mean"], mode="lines",
                             line=dict(color=COLORS["el_nino"], width=2), hoverinfo="skip"))
    fig.add_hline(y=0.5, line=dict(color="rgba(244,98,58,0.5)", width=0.8, dash="dot"))
    fig.add_hline(y=0.0, line=dict(color="rgba(138,148,166,0.3)", width=1))
    fig.update_layout(height=90, margin=dict(l=4, r=4, t=2, b=2),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      showlegend=False, font=dict(family=FONT_FAMILY),
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


# --------------------------------------------------------------------------
# Center: exposure choropleth
# --------------------------------------------------------------------------
def build_exposure_map(exp: pd.DataFrame) -> go.Figure:
    """World choropleth of the constructed ENSO Exposure Index, diverging by sign.

    z is signed: dry-impact countries read warm (coral), wet-impact read cool
    (blue), so the map shows *direction* of the ENSO hit as well as magnitude.
    Hover always reports the unsigned index plus the driver commodity and the
    C/E split, so nothing is hidden by the sign encoding.
    """
    sign_mult = {"dry": 1.0, "mixed": 0.6, "wet": -1.0}
    z = exp["index"] * exp["sign"].map(sign_mult).fillna(0.6)
    custom = np.stack([exp["index"], exp["commodity"], exp["sign"],
                       exp["C"], exp["E"]], axis=-1)
    fig = go.Figure(go.Choropleth(
        locations=exp["iso3"], z=z, locationmode="ISO-3",
        customdata=custom,
        colorscale=[[0.0, COLORS["la_nina"]], [0.42, "#172033"], [0.5, "#1b2336"],
                    [0.58, "#6b3a26"], [0.8, "#d4562b"], [1.0, "#ff5a2a"]],
        zmid=0, zmin=-95, zmax=95, showscale=False,
        marker_line_color="#0a1020", marker_line_width=0.4,
        hovertemplate=("<b>%{customdata[1]}</b> · %{location}<br>"
                       "Exposure index <b>%{customdata[0]:.0f}</b> "
                       "(%{customdata[2]})<br>"
                       "computed C %{customdata[3]:.2f} · curated E %{customdata[4]:.2f}"
                       "<extra></extra>"),
    ))
    fig.update_geos(bgcolor="#0a1224", showframe=False, showcoastlines=False,
                   showland=True, landcolor="#101a30", showocean=True, oceancolor="#0a1224",
                   projection_type="natural earth", lataxis_range=[-58, 78])
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", geo=dict(bgcolor="rgba(0,0,0,0)"),
                      font=dict(family=FONT_FAMILY, color=COLORS["text"]),
                      hoverlabel=dict(bgcolor=COLORS["surface"],
                                      font=dict(color=COLORS["text"], family=FONT_FAMILY)))
    return fig


# --------------------------------------------------------------------------
# Right: leaderboard (HTML; India & SE Asia rows link to live deep-dives)
# --------------------------------------------------------------------------
def build_leaderboard(exp: pd.DataFrame) -> str:
    sign_color = {"dry": COLORS["el_nino"], "wet": COLORS["la_nina"], "mixed": AMBER}
    rows = []
    ranked = exp.sort_values("index", ascending=False).reset_index(drop=True)
    for i, r in ranked.iterrows():
        col = sign_color.get(r["sign"], COLORS["neutral"])
        label = f"{r['name']} · {r['commodity'].split(',')[0]}"
        dd = DEEP_DIVES.get(r["iso3"])
        if dd:
            href = f"href='/{dd[0]}' title='Open {dd[1]}'"
            tag = "<span class='link'>OPEN ↗</span>"
        else:
            href = ("href='/04_sector_impact' "
                    "title='Explore this commodity in Sector Impact'")
            tag = "<span class='link' style='color:#7e8aa3'>impact ↗</span>"
        rows.append(
            f"<a class='lrow' style='cursor:pointer;' {href}>"
            f"<span class='rk'>{i + 1}</span>"
            f"<div><div class='ln'><span class='dot' style='background:{col}'></span>"
            f"{label}{tag}</div>"
            f"<div class='lbar'><i style='width:{r['index']:.0f}%;"
            f"background:linear-gradient(90deg,{AMBER},{col})'></i></div></div>"
            f"<span class='sc'>{r['index']:.0f}</span></a>"
        )
    return "<div>" + "".join(rows) + "</div>"


# --------------------------------------------------------------------------
# Bottom: causation strip (REAL verdicts + Option-A reframed headline)
# --------------------------------------------------------------------------
def _mini_curve(fwd: list[float], rev: list[float]) -> str:
    """Inline SVG: teal = forward cross-map skill (converges if causal), grey = reverse."""
    lo, hi = -0.05, 0.6

    def pts(arr: list[float]) -> str:
        n = len(arr)
        return " ".join(
            f"{2 + i * (96 / (n - 1)):.1f},{27 - (v - lo) / (hi - lo) * 24:.1f}"
            for i, v in enumerate(arr))

    return (
        "<svg viewBox='0 0 100 30' style='display:block;width:100%;height:30px;margin-top:6px'>"
        "<line x1='2' y1='27' x2='98' y2='27' stroke='#222c44'/>"
        f"<polyline points='{pts(fwd)}' fill='none' stroke='{COLORS['teal']}' stroke-width='2'/>"
        f"<polyline points='{pts(rev)}' fill='none' stroke='{COLORS['neutral']}' "
        "stroke-width='1.3' stroke-dasharray='3 2'/></svg>")


def build_causation_strip(verdicts: pd.DataFrame, ccm: pd.DataFrame) -> str:
    """Six ONI->commodity cards rendered from the *computed* Granger+CCM verdicts."""
    badge_label = {"mod": "MODERATE", "weak": "WEAK · confounded"}
    cards = []
    for _, v in verdicts.iterrows():
        curve = ccm[ccm["commodity"] == v["commodity"]].sort_values("lib_size")
        fwd = curve["fwd_rho"].tolist()
        rev = curve["rev_rho"].tolist()
        cls = v["cls"]
        g = v["granger_sig"]
        gtxt = (f"Granger {g}/24 lags sig" if g else "Granger n.s.")
        cards.append(
            f"<div class='cz'><div class='zlink'>ONI → {v['commodity']}</div>"
            f"<span class='zbadge {cls}'>{badge_label.get(cls, v['verdict'])}</span>"
            f"<div class='zstat'>{gtxt} · lag {int(v['lag'])}mo<br>"
            f"CCM ρ {v['ccm_rho']:.2f} · {'partial' if cls == 'mod' else 'flat'}</div>"
            f"{_mini_curve(fwd, rev)}</div>"
        )
    return "<div class='czgrid'>" + "".join(cards) + "</div>"


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------
def _ticker(latest_oni: float, exp: pd.DataFrame, fc: pd.DataFrame) -> str:
    ens = fc[fc["model"] == "Ensemble"].sort_values("date")
    peak = ens.loc[ens["mean"].idxmax()]
    top = exp.sort_values("index", ascending=False).head(4)
    arrow = "u" if latest_oni < 0 else "d"
    items = [
        f"Niño-3.4 ONI <b class='{arrow}'>{latest_oni:+.2f}°C</b>",
        f"Ensemble peak <b class='d'>{peak['mean']:+.2f}°C</b> by {peak['date']:%b %Y}",
    ]
    for _, r in top.iterrows():
        items.append(f"{r['name']} {r['commodity'].split(',')[0]} "
                     f"<b class='d'>exp {r['index']:.0f}</b>")
    items.append("Causal guard: max ONI→price CCM ρ <b class='d'>0.32</b> — most price links don't survive")
    seg = "<span class='sep'>•</span>".join(items)
    return f"<div class='tick'><span class='run'>{seg}</span></div>"


def build_app() -> pn.viewable.Viewable:
    oni = load_oni()
    exp = pd.read_parquet(CACHE_DIR / "exposure_index.parquet")
    fc = pd.read_parquet(CACHE_DIR / "forecasts_all.parquet")
    verdicts = pd.read_parquet(CACHE_DIR / "landing_verdicts.parquet")
    ccm = pd.read_parquet(CACHE_DIR / "landing_ccm.parquet")

    latest = oni.dropna(subset=["oni"]).iloc[-1]
    latest_oni = float(latest["oni"])
    asof = pd.Timestamp(latest["date"]).strftime("%b %Y")

    advisory = get_advisory()
    status = advisory.status if advisory is not None else (
        "El Niño-ish" if latest_oni >= 0.5 else
        "La Niña-ish" if latest_oni <= -0.5 else "ENSO-Neutral")

    # --- command bar + ticker (chips are REAL links to every page) ---
    nav = [("DESK", "/", True), ("MONITOR", "/01_enso_monitor", False),
           ("MAP", "/02_global_map", False), ("FCST", "/03_forecast", False),
           ("IMPACT", "/04_sector_impact", False), ("CAUSAL", "/05_causation", False),
           ("HIST", "/06_historical", False), ("INDIA", "/07_india", False),
           ("SEASIA", "/08_seasia", False)]
    chips = "".join(
        f"<a class='fn{' on' if on else ''}' href='{href}'>{label}</a>"
        for label, href, on in nav)
    cmd = pn.pane.HTML(
        "<div class='cmd'><span class='go'>ENSO&lt;GO&gt;</span>" + chips
        + f"<span class='live'>LIVE · NOAA CPC · {status} · as of {asof}</span></div>",
        margin=0)
    ticker = pn.pane.HTML(_ticker(latest_oni, exp, fc), margin=0)

    # --- left rail ---
    rail = pn.Column(
        pn.pane.HTML("<div class='wid'><div class='h'>Niño-3.4 · now</div></div>", margin=0),
        pn.pane.Plotly(build_compact_gauge(latest_oni), config=_PLOTLY_CFG, margin=0),
        pn.pane.HTML(f"<div class='cap'>ONI <b>{latest_oni:+.2f}</b> · "
                     f"3-mo mean · {asof}</div>", margin=0),
        pn.pane.HTML("<div class='wid' style='margin-top:14px'><div class='h'>"
                     "ONI trajectory · 24 mo</div></div>", margin=0),
        pn.pane.Plotly(build_oni_spark(oni), config=_PLOTLY_CFG, margin=0),
        pn.pane.HTML("<div class='wid' style='margin-top:14px'><div class='h'>"
                     "12-mo forecast cone</div></div>", margin=0),
        pn.pane.Plotly(build_forecast_cone(fc, oni), config=_PLOTLY_CFG, margin=0),
        pn.pane.HTML("<div class='cap'>Ensemble · 90% band · SARIMA+LSTM</div>", margin=0),
        css_classes=["railwrap"], margin=0)

    # --- center map ---
    map_col = pn.Column(
        pn.pane.HTML("<div class='h' style='padding:8px 8px 0'>ENSO "
                     f"<span style='color:{COLORS['teal']}'>EXPOSURE INDEX</span> · by country "
                     "<span style='color:#5b6577;font-weight:400;text-transform:none;"
                     "letter-spacing:0'>— coral = dry-impact · blue = wet-impact · "
                     "hover for detail; use the leaderboard → or nav bar to drill in</span></div>",
                     margin=0),
        pn.pane.Plotly(build_exposure_map(exp), config=_PLOTLY_CFG, margin=0),
        css_classes=["mapwrap"], margin=0)

    # --- right leaderboard ---
    board = pn.Column(
        pn.pane.HTML("<div class='h'>Most-exposed regions</div>"
                     + build_leaderboard(exp), margin=0),
        css_classes=["boardwrap"], margin=0)

    main = pn.Row(
        pn.Column(rail, width=220, margin=0),
        pn.Column(map_col, sizing_mode="stretch_width", margin=0),
        pn.Column(board, width=290, margin=0),
        sizing_mode="stretch_width", margin=0)

    # --- causation strip (real verdicts, Option-A headline) ---
    strip = pn.pane.HTML(
        "<div class='czstrip'>"
        "<div class='czhead'><div class='h'>ONI → Commodity-price · causal test</div>"
        "<span class='sub'>teal = forward cross-map skill (converges if causal) · grey = reverse</span></div>"
        "<p class='czlead'><b>Most ENSO→commodity-price trades the market makes don't survive "
        "causal testing.</b> Of six links, none is strongly causal (max CCM ρ 0.32); palm &amp; "
        "wheat are only MODERATE, the rest WEAK / confounded. The clean ENSO signal lives on the "
        "<b>climate &amp; production</b> side — the monsoon and Maritime-Continent drought we prove in "
        "the region deep-dives — not in noisy monthly prices.</p>"
        + build_causation_strip(verdicts, ccm)
        + "<div class='czcap'>Verdicts computed live by the in-repo Granger + CCM engine on "
        "linearly-detrended series (CCM = self-coded simplex projection). This is the "
        "misattribution guard: the headline trade is usually spurious.</div></div>",
        margin=0)

    disclaimer = pn.pane.HTML(
        "<div class='disc'><b>What you're looking at.</b> A constructed <b>ENSO Exposure Index</b> "
        "(50% computed peak lagged ONI–commodity correlation + 50% curated structural exposure) "
        "ranks where an ENSO swing reprices commodity &amp; sector risk. Click <b>India</b> or "
        "<b>SE Asia</b> in the leaderboard for the live deep-dive. The causal strip below is the "
        "honesty layer — it shows which ONI→price links actually survive testing (few do). "
        "ONI/forecast are live NOAA CPC; the index blends computed correlations with curated weights "
        "and is a research construct, not an official product.</div>", margin=0)

    return pn.Column(
        pn.pane.HTML("<h2 style='font-size:22px;margin:0 0 3px'>ENSO Macro Risk Desk</h2>"
                     "<p style='color:#7e8aa3;font-size:13px;margin:0 0 14px;line-height:1.5'>"
                     "When the ENSO cycle shifts, what commodity &amp; sector exposure do you "
                     "reposition — and which links are <b style='color:#e8edf5'>causally real "
                     "vs. spurious</b>?</p>", margin=0),
        pn.Column(cmd, ticker, main, strip, css_classes=["rd"], margin=0),
        disclaimer,
        styles={"background": COLORS["bg"], "padding": "22px",
                "min-height": "100vh", "max-width": "1240px", "margin": "0 auto"},
        sizing_mode="stretch_width")


build_app().servable(title="ENSO Macro Risk Desk")
