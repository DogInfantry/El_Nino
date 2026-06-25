"""Global Map — interactive SST anomaly + ENSO teleconnection zones.

Run with::

    panel serve dashboard/pages/02_global_map.py --show

Renders the ERSSTv5 anomaly field on a dark globe with the Niño-3.4 box and
curated teleconnection impact zones. A month selector animates across landmark
El Niño peaks (1982, 1997, 2015, 2023) and the latest available month; a
projection toggle switches between the flat map and an orthographic globe.

Requires the SST grid cache::

    python data/ingest/ersst_fetcher.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import panel as pn

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
for p in (_DASH_DIR, _DASH_DIR / "components"):
    sys.path.insert(0, str(p))

from theme import COLORS, CACHE_DIR  # noqa: E402
from globe_layer import build_sst_map  # noqa: E402

# Friendly labels for the snapshot months.
MONTH_LABELS = {
    "1982-12": "Dec 1982 — strong El Niño",
    "1997-12": "Dec 1997 — super El Niño",
    "2015-12": "Dec 2015 — super El Niño",
    "2023-12": "Dec 2023 — strong El Niño",
}

RAW_CSS = f"""
:host, body {{ background-color: {COLORS['bg']}; color: {COLORS['text']}; }}
.enso-card {{ background: {COLORS['surface']};
  border: 1px solid rgba(138,148,166,0.12); border-radius: 14px; padding: 16px 18px; }}
.enso-title {{ font-size: 26px; font-weight: 800; margin: 0; }}
.enso-subtitle {{ color: {COLORS['muted']}; font-size: 13px; margin-top: 2px; }}
.enso-note {{ background: rgba(0,212,180,0.07); border-left: 3px solid {COLORS['teal']};
  border-radius: 8px; padding: 12px 16px; font-size: 12px; line-height: 1.5; }}
.swatch {{ display:inline-block; width:12px; height:12px; border-radius:3px;
  margin:0 4px -1px 10px; }}
"""

pn.extension("plotly", raw_css=[RAW_CSS], sizing_mode="stretch_width")

GRID = pd.read_parquet(CACHE_DIR / "sst_anomaly_grids.parquet")
MONTH_KEYS = sorted(GRID["date"].dt.strftime("%Y-%m").unique())


def _label(key: str) -> str:
    return MONTH_LABELS.get(key, f"{pd.Timestamp(key + '-01'):%b %Y} — latest")


def build_map_pane(month_key: str, projection: str, show_zones: bool):
    sub = GRID[GRID["date"].dt.strftime("%Y-%m") == month_key]
    fig = build_sst_map(sub, projection=projection, show_zones=show_zones)
    return pn.pane.Plotly(fig, config={"displayModeBar": True}, sizing_mode="stretch_width")


def build_app() -> pn.viewable.Viewable:
    header = pn.pane.HTML(
        "<div><p class='enso-title'>🌎 Global Map</p>"
        "<p class='enso-subtitle'>ERSSTv5 sea-surface-temperature anomaly · Niño-3.4 box · "
        "El Niño teleconnection zones</p></div>")

    month = pn.widgets.DiscreteSlider(
        name="Month", options={_label(k): k for k in MONTH_KEYS},
        value=MONTH_KEYS[-1], sizing_mode="stretch_width")
    projection = pn.widgets.RadioButtonGroup(
        name="Projection", options={"Flat map": "natural earth", "Globe": "orthographic"},
        value="natural earth", button_type="default")
    zones = pn.widgets.Switch(name="Zones", value=True)
    zones_row = pn.Row(pn.pane.HTML("<b>Teleconnection zones</b>"), zones, width=210)

    controls = pn.Column(month, pn.Row(projection, zones_row), css_classes=["enso-card"])

    legend = pn.pane.HTML(
        f"<div class='enso-card' style='font-size:12px'>"
        f"<b>Legend</b>"
        f"<span class='swatch' style='background:{COLORS['teal']}'></span> Niño-3.4 box"
        f"<span class='swatch' style='background:{COLORS['el_nino']}'></span> typical drought zone"
        f"<span class='swatch' style='background:{COLORS['la_nina']}'></span> typical wet/flood zone"
        f"&nbsp;&nbsp;|&nbsp;&nbsp; ocean shading = SST anomaly "
        f"(<span style='color:{COLORS['el_nino']}'>warm</span> / "
        f"<span style='color:{COLORS['la_nina']}'>cool</span>)</div>")

    mapping = pn.bind(build_map_pane, month_key=month, projection=projection, show_zones=zones)
    map_card = pn.Column(mapping, css_classes=["enso-card"])

    note = pn.pane.HTML(
        "<div class='enso-note'><b>Teleconnection zones are probabilistic "
        "tendencies, not guarantees.</b> They show the <i>typical</i> El Niño "
        "drought/wet response and are modulated by the Indian Ocean Dipole (IOD) "
        "and Madden–Julian Oscillation (MJO); any single event can differ. SST "
        "anomalies are ERSSTv5 (2°×2°) vs a 1991–2020 climatology — a different "
        "baseline than the ONI, so the Niño-3.4 box value here won't exactly "
        "equal the ONI. EM-DAT disaster-event bubbles are a planned overlay.</div>")

    return pn.Column(
        header, pn.Spacer(height=8), controls, pn.Spacer(height=6), legend,
        pn.Spacer(height=8), map_card, pn.Spacer(height=8), note,
        styles={"background": COLORS["bg"], "padding": "22px",
                "min-height": "100vh", "max-width": "1500px", "margin": "0 auto"})


build_app().servable(title="Global Map")
