"""Global SST-anomaly map with ENSO teleconnection zones (Plotly geo).

Renders the ERSSTv5 anomaly grid as a colored ocean field on a dark globe,
overlaid with the Niño-3.4 monitoring box and curated El Niño teleconnection
impact zones (typical dry / wet tendencies). Plotly Scattergeo is used rather
than deck.gl/pydeck because it is self-contained (no basemap tiles/token),
server-renderable for verification, and integrates cleanly with Panel; a pydeck
variant is a straightforward drop-in if a 3-D extruded look is wanted.

Teleconnection zones are *probabilistic tendencies* (modulated by IOD/MJO), not
guarantees — surfaced as a caveat on the page.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme import COLORS, FONT_FAMILY  # noqa: E402

# Niño-3.4 region: 5°S–5°N, 170°W–120°W.
NINO34_BOX = dict(lat0=-5, lat1=5, lon0=-170, lon1=-120)

# Canonical El Niño teleconnection tendencies (approximate bounding regions).
TELECONNECTIONS: list[dict] = [
    {"name": "Maritime Continent / Indonesia — drought", "impact": "dry",
     "lat0": -10, "lat1": 7, "lon0": 95, "lon1": 140},
    {"name": "E Australia — drought", "impact": "dry",
     "lat0": -38, "lat1": -15, "lon0": 140, "lon1": 154},
    {"name": "Southern Africa — drought", "impact": "dry",
     "lat0": -30, "lat1": -10, "lon0": 20, "lon1": 40},
    {"name": "Amazon / NE Brazil — drought", "impact": "dry",
     "lat0": -10, "lat1": 5, "lon0": -70, "lon1": -45},
    {"name": "India — weak monsoon", "impact": "dry",
     "lat0": 8, "lat1": 28, "lon0": 70, "lon1": 88},
    {"name": "Peru / Ecuador coast — flooding", "impact": "wet",
     "lat0": -12, "lat1": 2, "lon0": -82, "lon1": -72},
    {"name": "S Brazil / Uruguay / N Argentina — wet", "impact": "wet",
     "lat0": -35, "lat1": -20, "lon0": -62, "lon1": -48},
    {"name": "Horn of Africa — wet (short rains)", "impact": "wet",
     "lat0": -3, "lat1": 12, "lon0": 38, "lon1": 51},
    {"name": "US Gulf Coast / California — wet", "impact": "wet",
     "lat0": 28, "lat1": 38, "lon0": -122, "lon1": -82},
]

IMPACT_COLORS = {"dry": COLORS["el_nino"], "wet": COLORS["la_nina"]}


def _rect(lat0, lat1, lon0, lon1) -> tuple[list[float], list[float]]:
    """Return (lons, lats) tracing a closed rectangle."""
    lons = [lon0, lon1, lon1, lon0, lon0]
    lats = [lat0, lat0, lat1, lat1, lat0]
    return lons, lats


def build_sst_map(
    grid: pd.DataFrame,
    *,
    projection: str = "natural earth",
    show_zones: bool = True,
) -> go.Figure:
    """Build the global SST-anomaly map for a single month's ``grid``."""
    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
        lon=grid["lon"], lat=grid["lat"], mode="markers",
        marker=dict(
            size=7, color=grid["sst_anom"], colorscale="RdBu", reversescale=True,
            cmin=-2.5, cmax=2.5, opacity=1.0, line=dict(width=0),
            colorbar=dict(title="SST anom (°C)", thickness=14, len=0.65,
                          tickfont=dict(color=COLORS["text"]),
                          title_font=dict(color=COLORS["muted"])),
        ),
        name="SST anomaly", hoverinfo="lon+lat+text",
        text=[f"{v:+.1f}°C" for v in grid["sst_anom"]],
    ))

    if show_zones:
        for z in TELECONNECTIONS:
            lons, lats = _rect(z["lat0"], z["lat1"], z["lon0"], z["lon1"])
            color = IMPACT_COLORS[z["impact"]]
            fig.add_trace(go.Scattergeo(
                lon=lons, lat=lats, mode="lines",
                line=dict(color=color, width=2.4),
                name=z["name"], hoverinfo="name", showlegend=False,
            ))

    # Niño-3.4 monitoring box (teal, dashed outline).
    b = NINO34_BOX
    lons, lats = _rect(b["lat0"], b["lat1"], b["lon0"], b["lon1"])
    fig.add_trace(go.Scattergeo(
        lon=lons, lat=lats, mode="lines", line=dict(color=COLORS["teal"], width=2),
        name="Niño-3.4 box", hoverinfo="name", showlegend=False,
    ))

    fig.update_geos(
        projection_type=projection, bgcolor=COLORS["bg"],
        showland=True, landcolor="#222838",
        showocean=True, oceancolor="#070a12",
        showcoastlines=True, coastlinecolor="rgba(138,148,166,0.55)",
        showframe=False, lakecolor="#070a12",
        showcountries=True, countrycolor="rgba(138,148,166,0.18)",
    )
    fig.update_layout(
        paper_bgcolor=COLORS["bg"], font=dict(family=FONT_FAMILY, color=COLORS["text"]),
        margin=dict(l=0, r=0, t=10, b=0), height=520,
    )
    return fig


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"
