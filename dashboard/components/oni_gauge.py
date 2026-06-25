"""Niño-3.4 / ONI speedometer gauge (Plotly indicator).

Renders the latest index value as a color-coded gauge spanning La Nina ->
Neutral -> El Nino, with NOAA-style threshold bands. The displayed value is
the latest available *3-month-mean* ONI; the raw weekly Niño-3.4 spikes ahead
of this smoothed index, which is noted in the page copy.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme import COLORS, FONT_FAMILY  # noqa: E402


def build_gauge(value: float, *, title: str = "Latest ONI (3-mo mean)") -> go.Figure:
    """Return a Plotly gauge figure for an ONI/Niño-3.4 anomaly ``value``."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=round(float(value), 2),
            number={"suffix": " °C", "font": {"color": COLORS["text"]}},
            delta={
                "reference": 0.5,  # El Nino advisory threshold
                "increasing": {"color": COLORS["el_nino"]},
                "decreasing": {"color": COLORS["la_nina"]},
            },
            title={"text": title, "font": {"size": 14, "color": COLORS["text"]}},
            gauge={
                "axis": {
                    "range": [-3, 3],
                    "tickwidth": 1,
                    "tickcolor": COLORS["muted"],
                    "tickvals": [-3, -2, -1, -0.5, 0.5, 1, 2, 3],
                },
                "bar": {"color": "rgba(232,237,245,0.9)", "thickness": 0.18},
                "bgcolor": COLORS["surface"],
                "borderwidth": 0,
                "steps": [
                    {"range": [-3, -1.5], "color": "rgba(58,154,244,0.55)"},
                    {"range": [-1.5, -0.5], "color": "rgba(58,154,244,0.30)"},
                    {"range": [-0.5, 0.5], "color": "rgba(138,148,166,0.25)"},
                    {"range": [0.5, 1.5], "color": "rgba(244,98,58,0.30)"},
                    {"range": [1.5, 3], "color": "rgba(244,98,58,0.55)"},
                ],
                "threshold": {
                    "line": {"color": COLORS["teal"], "width": 3},
                    "thickness": 0.85,
                    "value": round(float(value), 2),
                },
            },
        )
    )
    fig.update_layout(
        paper_bgcolor=COLORS["bg"],
        font={"family": FONT_FAMILY, "color": COLORS["text"]},
        height=280,
        margin=dict(l=30, r=30, t=50, b=10),
    )
    return fig
