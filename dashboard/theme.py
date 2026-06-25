"""Shared visual theme + data loaders for the ENSO dashboard.

Centralizes the project color palette, a reusable Plotly dark template, and
thin loaders that read the parquet caches produced by the ``data`` layer.
Every page imports from here so the look-and-feel is consistent and the data
access is in one place.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

# dashboard/theme.py -> parents[1] is the project root.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
CACHE_DIR: Path = PROJECT_ROOT / "data" / "cache"

# --- Palette (from project brief) -----------------------------------------
COLORS: dict[str, str] = {
    "bg": "#0a0e1a",        # near-black background
    "surface": "#141929",   # card surface
    "el_nino": "#f4623a",   # coral-orange (warm)
    "la_nina": "#3a9af4",   # ocean-blue (cold)
    "neutral": "#8a94a6",   # grey
    "teal": "#00d4b4",      # highlight
    "text": "#e8edf5",      # primary text
    "muted": "#5b6577",     # subtle text / gridlines
}

PHASE_COLORS: dict[str, str] = {
    "El Nino": COLORS["el_nino"],
    "La Nina": COLORS["la_nina"],
    "Neutral": COLORS["neutral"],
}

FONT_FAMILY = "Inter, 'Segoe UI', system-ui, sans-serif"


def plotly_dark_layout(**overrides) -> dict:
    """Return a base Plotly layout dict matching the dashboard dark theme."""
    layout = dict(
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        font=dict(family=FONT_FAMILY, color=COLORS["text"], size=13),
        margin=dict(l=60, r=30, t=50, b=40),
        xaxis=dict(
            gridcolor="rgba(138,148,166,0.12)",
            zerolinecolor="rgba(138,148,166,0.25)",
            linecolor=COLORS["muted"],
        ),
        yaxis=dict(
            gridcolor="rgba(138,148,166,0.12)",
            zerolinecolor="rgba(138,148,166,0.25)",
            linecolor=COLORS["muted"],
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=COLORS["text"])),
        hoverlabel=dict(
            bgcolor=COLORS["surface"],
            font=dict(color=COLORS["text"], family=FONT_FAMILY),
        ),
    )
    layout.update(overrides)
    return layout


def style_figure(fig: go.Figure, **overrides) -> go.Figure:
    """Apply the dark theme layout to an existing Plotly figure in place."""
    fig.update_layout(**plotly_dark_layout(**overrides))
    return fig


# --- Data loaders ----------------------------------------------------------
def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing cache file: {path.name}. Run the matching fetcher in "
            f"data/ingest or data/process first (e.g. `python oni_fetcher.py`)."
        )
    return path


def load_oni() -> pd.DataFrame:
    """Load the ONI time series (``oni.parquet``)."""
    return pd.read_parquet(_require(CACHE_DIR / "oni.parquet"))


def load_phases() -> pd.DataFrame:
    """Load the labeled ENSO phase series (``enso_phases.parquet``)."""
    return pd.read_parquet(_require(CACHE_DIR / "enso_phases.parquet"))


def load_commodities() -> pd.DataFrame:
    """Load tidy commodity prices (``commodities.parquet``)."""
    return pd.read_parquet(_require(CACHE_DIR / "commodities.parquet"))
