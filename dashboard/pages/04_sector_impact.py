"""Sector Impact — lagged ONI × commodity-price cross-correlation heatmap.

Run with::

    panel serve dashboard/pages/04_sector_impact.py --show

Shows, for each ENSO-sensitive commodity, the detrended Pearson correlation
between the ONI and the (log) price at every forward lag from 0 to 24 months.
A lag slider highlights a chosen lead time and ranks commodities at that lag.

Methodology and the correlation≠causation caveat are surfaced in-page.
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import panel as pn

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
_ROOT = _DASH_DIR.parent
for p in (
    _DASH_DIR,
    _ROOT / "data" / "process",
    _ROOT / "data" / "ingest",
):
    sys.path.insert(0, str(p))

from theme import COLORS, load_commodities, load_phases  # noqa: E402
from pink_sheet import FOCUS_COMMODITIES  # noqa: E402
from lag_correlator import correlation_matrix, peak_lags  # noqa: E402

MAX_LAG = 24

RAW_CSS = f"""
:host, body {{ background-color: {COLORS['bg']}; color: {COLORS['text']}; }}
.enso-card {{
    background: {COLORS['surface']};
    border: 1px solid rgba(138,148,166,0.12);
    border-radius: 14px; padding: 18px 20px;
}}
.enso-title {{ font-size: 26px; font-weight: 800; margin: 0; }}
.enso-subtitle {{ color: {COLORS['muted']}; font-size: 13px; margin-top: 2px; }}
.enso-note {{
    background: rgba(0,212,180,0.07); border-left: 3px solid {COLORS['teal']};
    border-radius: 8px; padding: 12px 16px; font-size: 12px; line-height: 1.5;
}}
"""

pn.extension("vega", raw_css=[RAW_CSS], sizing_mode="stretch_width")


def _load_inputs() -> tuple[pd.Series, pd.DataFrame]:
    """Return (ONI monthly series, wide log-price commodity frame)."""
    phases = load_phases()
    oni = phases.set_index("date")["value"].astype(float)

    comm = load_commodities()
    focus = comm[comm["commodity"].isin(FOCUS_COMMODITIES)]
    wide = focus.pivot_table(index="date", columns="commodity", values="price")
    wide = np.log(wide)  # multiplicative price dynamics -> log space
    return oni, wide


ONI, WIDE = _load_inputs()


def _alt_dark(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure(background=COLORS["bg"])
        .configure_axis(
            labelColor=COLORS["text"],
            titleColor=COLORS["muted"],
            gridColor="rgba(138,148,166,0.12)",
            domainColor=COLORS["muted"],
            tickColor=COLORS["muted"],
        )
        .configure_legend(
            labelColor=COLORS["text"], titleColor=COLORS["muted"], orient="right"
        )
        .configure_view(strokeWidth=0)
        .configure_title(color=COLORS["text"])
    )


def build_charts(commodities: list[str], do_detrend: bool, highlight_lag: int):
    """Return (heatmap+highlight, ranked bar) Vega panes for the selection."""
    if not commodities:
        return pn.pane.Markdown("**Select at least one commodity.**")

    matrix = correlation_matrix(
        ONI, WIDE[commodities], max_lag=MAX_LAG, do_detrend=do_detrend
    )
    order = list(peak_lags(matrix)["target"])

    base = alt.Chart(matrix)
    heat = base.mark_rect().encode(
        x=alt.X("lag:O", title="Lag (months) — ONI leads →"),
        y=alt.Y("target:N", title=None, sort=order),
        color=alt.Color(
            "r:Q",
            title="Pearson r",
            scale=alt.Scale(scheme="redblue", domain=[-0.4, 0.4], domainMid=0,
                            reverse=True, clamp=True),
        ),
        tooltip=[
            alt.Tooltip("target:N", title="Commodity"),
            alt.Tooltip("lag:Q", title="Lag (mo)"),
            alt.Tooltip("r:Q", title="r", format="+.3f"),
        ],
    )
    highlight = (
        base.transform_filter(alt.datum.lag == highlight_lag)
        .mark_rect(fill=None, stroke=COLORS["teal"], strokeWidth=2.5)
        .encode(x="lag:O", y=alt.Y("target:N", sort=order))
    )
    heatmap = (heat + highlight).properties(
        height=max(220, 34 * len(commodities)),
        title=f"Detrended ONI × commodity correlation (lag 0–{MAX_LAG} mo)"
        + ("" if do_detrend else "  [detrend OFF]"),
    )

    at_lag = matrix[matrix["lag"] == highlight_lag].copy()
    bar = (
        alt.Chart(at_lag)
        .mark_bar()
        .encode(
            x=alt.X("r:Q", title=f"Pearson r at lag = {highlight_lag} mo",
                    scale=alt.Scale(domain=[-0.4, 0.4])),
            y=alt.Y("target:N", sort="-x", title=None),
            color=alt.Color(
                "r:Q",
                scale=alt.Scale(scheme="redblue", domain=[-0.4, 0.4],
                                domainMid=0, reverse=True, clamp=True),
                legend=None,
            ),
            tooltip=[alt.Tooltip("target:N"), alt.Tooltip("r:Q", format="+.3f")],
        )
        .properties(height=max(160, 30 * len(commodities)),
                    title=f"Ranked correlation at {highlight_lag}-month lag")
    )

    return pn.Column(
        pn.pane.Vega(_alt_dark(heatmap), sizing_mode="stretch_width"),
        pn.Spacer(height=6),
        pn.pane.Vega(_alt_dark(bar), sizing_mode="stretch_width"),
    )


def build_app() -> pn.viewable.Viewable:
    header = pn.pane.HTML(
        "<div><p class='enso-title'>📊 Sector Impact</p>"
        "<p class='enso-subtitle'>Lagged cross-correlation · ONI vs World Bank "
        "commodity prices (detrended, log-price) · index: "
        f"<b style='color:{COLORS['teal']}'>ONI</b></p></div>"
    )

    commodities = pn.widgets.MultiChoice(
        name="Commodities",
        value=list(FOCUS_COMMODITIES),
        options=list(WIDE.columns),
        sizing_mode="stretch_width",
    )
    detrend = pn.widgets.Switch(name="Detrend", value=True)
    detrend_row = pn.Row(pn.pane.HTML("<b>Detrend trend</b>"), detrend, width=180)
    lag = pn.widgets.IntSlider(
        name="Highlight lag (months)", start=0, end=MAX_LAG, value=12,
        sizing_mode="stretch_width",
    )

    controls = pn.Column(
        commodities, pn.Row(lag, detrend_row), css_classes=["enso-card"],
    )

    charts = pn.bind(
        build_charts, commodities=commodities, do_detrend=detrend, highlight_lag=lag
    )
    charts_card = pn.Column(charts, css_classes=["enso-card"])

    note = pn.pane.HTML(
        "<div class='enso-note'>"
        "<b>Correlation ≠ causation.</b> These are detrended Pearson correlations, "
        "not causal effects; shared seasonality or third factors (IOD, MJO, global "
        "demand) can drive co-movement. Positive lag means the ONI <i>leads</i> the "
        "price. Agricultural impacts typically lag the ONI peak by 6–24 months. "
        "Causal direction is tested with Granger / CCM in the Causation explorer "
        "(Phase 2). Prices are nominal USD (World Bank Pink Sheet).</div>"
    )

    return pn.Column(
        header, pn.Spacer(height=8), controls, pn.Spacer(height=8),
        charts_card, pn.Spacer(height=8), note,
        styles={"background": COLORS["bg"], "padding": "22px",
                "min-height": "100vh", "max-width": "1500px", "margin": "0 auto"},
    )


build_app().servable(title="Sector Impact")
