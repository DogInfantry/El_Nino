"""Event-shaded ONI/RONI time series (Plotly).

Plots the index line over 1950-present with shaded vertical bands for each
detected El Nino (coral) and La Nina (blue) *event*, +/-0.5 degC threshold
guides, and annotations for landmark events.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme import COLORS, style_figure  # noqa: E402

# Landmark events to annotate (year label -> approx peak date).
LANDMARKS: dict[str, str] = {
    "1982-83": "1983-01-01",
    "1997-98": "1998-01-01",
    "2015-16": "2016-01-01",
    "2023-24": "2024-01-01",
}


def build_oni_timeseries(
    phases: pd.DataFrame,
    events: pd.DataFrame,
    *,
    index_label: str = "ONI",
    title: str | None = None,
    secondary: pd.DataFrame | None = None,
    secondary_label: str = "RONI",
) -> go.Figure:
    """Build the shaded index time series.

    Parameters
    ----------
    phases : tidy frame with ``date`` and ``value`` columns (labeled output).
    events : per-event summary with ``phase``, ``start``, ``end`` columns.
    secondary : optional tidy frame (``date``, ``value``) drawn as a second
        overlaid line (e.g. RONI vs ONI), with the legend enabled.
    """
    fig = go.Figure()

    # Shaded event bands behind the line.
    for _, ev in events.iterrows():
        color = (
            "rgba(244,98,58,0.16)"
            if ev["phase"] == "El Nino"
            else "rgba(58,154,244,0.16)"
        )
        fig.add_vrect(
            x0=pd.Timestamp(ev["start"]).isoformat(),
            x1=pd.Timestamp(ev["end"]).isoformat(),
            fillcolor=color,
            line_width=0,
            layer="below",
        )

    # Threshold guides.
    for y, dash in ((0.5, "dot"), (-0.5, "dot"), (0.0, "solid")):
        fig.add_hline(
            y=y,
            line=dict(
                color=COLORS["muted"] if y == 0 else "rgba(138,148,166,0.4)",
                width=1,
                dash=dash,
            ),
        )

    # The index line, colored by sign via two overlaid traces is overkill;
    # a single teal line over shaded bands reads cleanly.
    fig.add_trace(
        go.Scatter(
            x=phases["date"],
            y=phases["value"],
            mode="lines",
            name=index_label,
            line=dict(color=COLORS["teal"], width=1.6),
            hovertemplate="%{x|%b %Y}<br>" + index_label + ": %{y:+.2f} °C<extra></extra>",
        )
    )

    # Optional secondary index (e.g. RONI) overlaid for comparison.
    if secondary is not None and not secondary.empty:
        fig.add_trace(
            go.Scatter(
                x=secondary["date"],
                y=secondary["value"],
                mode="lines",
                name=secondary_label,
                line=dict(color=COLORS["el_nino"], width=1.4, dash="dot"),
                hovertemplate="%{x|%b %Y}<br>" + secondary_label
                + ": %{y:+.2f} °C<extra></extra>",
            )
        )

    # Landmark annotations.
    for label, date in LANDMARKS.items():
        ts = pd.Timestamp(date)
        if ts < phases["date"].min() or ts > phases["date"].max():
            continue
        row = phases.loc[(phases["date"] - ts).abs().idxmin()]
        fig.add_annotation(
            x=pd.Timestamp(row["date"]).isoformat(),
            y=row["value"],
            text=label,
            showarrow=True,
            arrowcolor=COLORS["muted"],
            arrowwidth=1,
            ax=0,
            ay=-30,
            font=dict(color=COLORS["text"], size=10),
            bgcolor="rgba(20,25,41,0.85)",
            bordercolor=COLORS["muted"],
            borderpad=2,
        )

    style_figure(
        fig,
        title=dict(
            text=title or f"{index_label} — Niño-3.4 SST anomaly (1950–present)",
            font=dict(size=16),
        ),
        height=420,
        yaxis=dict(
            title="Anomaly (°C)",
            gridcolor="rgba(138,148,166,0.12)",
            zerolinecolor="rgba(138,148,166,0.25)",
        ),
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.06),
            gridcolor="rgba(138,148,166,0.08)",
        ),
        showlegend=secondary is not None and not secondary.empty,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    bgcolor="rgba(0,0,0,0)"),
    )
    return fig
