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


# --- EM-DAT overlay -------------------------------------------------------
# Optional cache: exists only after a manual EM-DAT export has been ingested (see
# data/ingest/emdat_disasters.py). Absent, the page renders exactly as it did before.
DISASTER_COLOR = {
    "Drought": COLORS["el_nino"], "Wildfire": COLORS.get("amber", "#f4b13a"),
    "Flood": COLORS["la_nina"], "Storm": COLORS["teal"],
}
# Events within this many months of the displayed SST field. One month is too narrow to
# show anything; a whole year would let a La Niña-onset event sit on an El Niño map.
WINDOW_MONTHS = 6


def load_disasters() -> "pd.DataFrame | None":
    path = CACHE_DIR / "emdat_disasters.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path).dropna(subset=["lat", "lon"])


DISASTERS = load_disasters()


def add_disaster_bubbles(fig, month_key: str) -> int:
    """Scatter geocoded EM-DAT events near ``month_key``. Returns how many were drawn."""
    if DISASTERS is None or DISASTERS.empty:
        return 0
    import plotly.graph_objects as go

    centre = pd.Timestamp(month_key + "-01")
    lo = centre - pd.DateOffset(months=WINDOW_MONTHS)
    hi = centre + pd.DateOffset(months=WINDOW_MONTHS)
    sub = DISASTERS[(DISASTERS["date"] >= lo) & (DISASTERS["date"] <= hi)]
    if sub.empty:
        return 0

    for dtype, grp in sub.groupby("dtype"):
        affected = pd.to_numeric(grp["affected"], errors="coerce").fillna(0.0)
        root = affected ** 0.5
        # sqrt so one 10-million-affected event does not shrink every other bubble to a
        # dot; the +6 floor keeps an event with no affected-count visible, because a
        # missing figure is not the same thing as a small disaster.
        size = 6 + 34 * (root / max(float(root.max()), 1.0))
        fig.add_trace(go.Scattergeo(
            lat=grp["lat"], lon=grp["lon"], mode="markers", name=str(dtype),
            marker=dict(size=size, color=DISASTER_COLOR.get(str(dtype), COLORS["muted"]),
                        opacity=0.55, line=dict(width=1, color="rgba(255,255,255,0.55)")),
            customdata=list(zip(grp["country"].astype(str),
                                grp["date"].dt.strftime("%b %Y"),
                                affected, grp["phase"].astype(str))),
            hovertemplate=("<b>%{customdata[0]}</b> — " + str(dtype) +
                           "<br>%{customdata[1]} · ENSO phase %{customdata[3]}"
                           "<br>affected %{customdata[2]:,.0f}<extra></extra>")))
    return len(sub)


def build_map_pane(month_key: str, projection: str, show_zones: bool,
                   show_disasters: bool = False):
    sub = GRID[GRID["date"].dt.strftime("%Y-%m") == month_key]
    fig = build_sst_map(sub, projection=projection, show_zones=show_zones)
    if show_disasters:
        add_disaster_bubbles(fig, month_key)
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

    have_disasters = DISASTERS is not None and not DISASTERS.empty
    disasters = pn.widgets.Switch(name="Disasters", value=False, disabled=not have_disasters)
    dis_label = ("<b>EM-DAT events</b>" if have_disasters
                 else "<b style='color:#8a94a6'>EM-DAT events (not ingested)</b>")
    dis_row = pn.Row(pn.pane.HTML(dis_label), disasters, width=230)

    controls = pn.Column(month, pn.Row(projection, zones_row, dis_row),
                         css_classes=["enso-card"])

    legend = pn.pane.HTML(
        f"<div class='enso-card' style='font-size:12px'>"
        f"<b>Legend</b>"
        f"<span class='swatch' style='background:{COLORS['teal']}'></span> Niño-3.4 box"
        f"<span class='swatch' style='background:{COLORS['el_nino']}'></span> typical drought zone"
        f"<span class='swatch' style='background:{COLORS['la_nina']}'></span> typical wet/flood zone"
        f"&nbsp;&nbsp;|&nbsp;&nbsp; ocean shading = SST anomaly "
        f"(<span style='color:{COLORS['el_nino']}'>warm</span> / "
        f"<span style='color:{COLORS['la_nina']}'>cool</span>)</div>")

    mapping = pn.bind(build_map_pane, month_key=month, projection=projection,
                      show_zones=zones, show_disasters=disasters)
    map_card = pn.Column(mapping, css_classes=["enso-card"])

    if have_disasters:
        n_total = len(pd.read_parquet(CACHE_DIR / "emdat_disasters.parquet"))
        pct = 100.0 * len(DISASTERS) / max(n_total, 1)
        emdat_txt = (
            f"<b>EM-DAT bubbles show only the geocoded subset — {len(DISASTERS):,} of "
            f"{n_total:,} events ({pct:.0f}%).</b> EM-DAT records point coordinates for a "
            "minority of rows, and that minority is <i>not</i> a random sample: large, "
            "well-reported events are likelier to be located, so the map under-draws small "
            "and poorly-documented disasters. Bubbles are sized by people affected "
            f"(√-scaled) and drawn within ±{WINDOW_MONTHS} months of the displayed field. "
            "A disaster co-occurring with an SST anomaly is <b>not</b> evidence ENSO caused "
            "it — that is the question pages 05 and 00 exist to test. "
            "Source: EM-DAT, CRED / UCLouvain."
        )
    else:
        emdat_txt = (
            "<b>EM-DAT disaster bubbles are available but not ingested.</b> EM-DAT is open "
            "access for non-commercial use, yet neither the portal nor the HDX mirror "
            "permits automated download, so this feed is manual by design: register at "
            "public.emdat.be, drop the export in <code>data/raw/emdat/</code>, and run "
            "<code>data/ingest/emdat_disasters.py</code>."
        )

    note = pn.pane.HTML(
        "<div class='enso-note'><b>Teleconnection zones are probabilistic "
        "tendencies, not guarantees.</b> They show the <i>typical</i> El Niño "
        "drought/wet response and are modulated by the Indian Ocean Dipole (IOD) "
        "and Madden–Julian Oscillation (MJO); any single event can differ. SST "
        "anomalies are ERSSTv5 (2°×2°) vs a 1991–2020 climatology — a different "
        "baseline than the ONI, so the Niño-3.4 box value here won't exactly "
        f"equal the ONI.<br><br>{emdat_txt}</div>")

    return pn.Column(
        header, pn.Spacer(height=8), controls, pn.Spacer(height=6), legend,
        pn.Spacer(height=8), map_card, pn.Spacer(height=8), note,
        styles={"background": COLORS["bg"], "padding": "22px",
                "min-height": "100vh", "max-width": "1500px", "margin": "0 auto"})


build_app().servable(title="Global Map")
