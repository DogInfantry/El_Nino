"""Causation Explorer — Granger + CCM, lag- and convergence-resolved.

Run with::

    panel serve dashboard/pages/05_causation.py --show

For a chosen commodity, this page runs two causal tests live against the ONI:
  * Granger causality across lags 0–24 (linear) — bars of -log10(p) with a
    significance line, both directions.
  * Convergent Cross Mapping (nonlinear) — cross-map skill (rho) vs library
    size; a rising/converging curve in one direction is the causal signature.
A plain-language verdict combines the two, with explicit caveats.

Requires the Phase-1 caches (oni.parquet, commodities.parquet).
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
for p in (_DASH_DIR, _ROOT / "data" / "process", _ROOT / "data" / "ingest"):
    sys.path.insert(0, str(p))

from theme import COLORS, load_commodities, load_oni, style_figure  # noqa: E402
from pink_sheet import FOCUS_COMMODITIES  # noqa: E402
from granger_ccm import analyze  # noqa: E402

RAW_CSS = f"""
:host, body {{ background-color: {COLORS['bg']}; color: {COLORS['text']}; }}
.enso-card {{ background: {COLORS['surface']};
  border: 1px solid rgba(138,148,166,0.12); border-radius: 14px; padding: 18px 20px; }}
.enso-title {{ font-size: 26px; font-weight: 800; margin: 0; }}
.enso-subtitle {{ color: {COLORS['muted']}; font-size: 13px; margin-top: 2px; }}
.enso-verdict {{ font-size: 15px; line-height: 1.5; }}
.enso-note {{ background: rgba(0,212,180,0.07); border-left: 3px solid {COLORS['teal']};
  border-radius: 8px; padding: 12px 16px; font-size: 12px; line-height: 1.5; }}
"""

pn.extension("plotly", raw_css=[RAW_CSS], sizing_mode="stretch_width")

ONI = load_oni().set_index("date")["oni"].astype(float).asfreq("MS")
COMM = load_commodities()
ALL_COMMODITIES = sorted(COMM["commodity"].unique())


def _commodity_series(name: str) -> pd.Series:
    return (
        COMM[COMM["commodity"] == name]
        .set_index("date")["price"].astype(float).asfreq("MS")
    )


def build_granger_chart(g_fwd: pd.DataFrame, g_rev: pd.DataFrame, name: str,
                        alpha: float) -> go.Figure:
    """-log10(p) by lag for both directions, with a significance line."""
    thresh = -np.log10(alpha)
    fwd = g_fwd.copy()
    fwd["nlp"] = -np.log10(fwd["p_value"].clip(lower=1e-12))
    rev = g_rev.copy()
    rev["nlp"] = -np.log10(rev["p_value"].clip(lower=1e-12))

    colors = [COLORS["teal"] if v >= thresh else "rgba(138,148,166,0.5)"
              for v in fwd["nlp"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=fwd["lag"], y=fwd["nlp"], marker_color=colors,
                         name=f"ONI → {name}",
                         hovertemplate="lag %{x}mo<br>-log10(p)=%{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=rev["lag"], y=rev["nlp"], mode="lines+markers",
                             line=dict(color=COLORS["el_nino"], width=1.6),
                             marker=dict(size=4), name=f"{name} → ONI (reverse)",
                             hovertemplate="lag %{x}mo<br>-log10(p)=%{y:.2f}<extra></extra>"))
    fig.add_hline(y=thresh, line=dict(color=COLORS["text"], width=1, dash="dash"),
                  annotation_text=f"p = {alpha:g}", annotation_position="right",
                  annotation_font_color=COLORS["muted"], annotation_font_size=10)
    style_figure(fig, height=320, margin=dict(l=60, r=30, t=46, b=70),
        title=dict(text="Granger causality by lag", font=dict(size=15)),
        yaxis=dict(title="-log10(p-value)", gridcolor="rgba(138,148,166,0.12)"),
        xaxis=dict(title="Lag (months)", dtick=2),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0))
    return fig


def build_ccm_chart(ccm: pd.DataFrame, name: str) -> go.Figure:
    """rho vs library size for both directions (convergence = causation)."""
    fig = go.Figure()
    spec = {"ONI->target": (f"ONI → {name}", COLORS["teal"]),
            "target->ONI": (f"{name} → ONI", COLORS["el_nino"])}
    for direction, (label, color) in spec.items():
        grp = ccm[ccm["direction"] == direction].sort_values("lib_size")
        fig.add_trace(go.Scatter(x=grp["lib_size"], y=grp["rho"], mode="lines+markers",
                                 line=dict(color=color, width=2.4), name=label,
                                 hovertemplate=label + "<br>L=%{x}: rho=%{y:.3f}<extra></extra>"))
    style_figure(fig, height=320, margin=dict(l=60, r=30, t=46, b=70),
        title=dict(text="Convergent Cross Mapping — skill vs library size", font=dict(size=15)),
        yaxis=dict(title="Cross-map skill ρ", gridcolor="rgba(138,148,166,0.12)"),
        xaxis=dict(title="Library size (months)"),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0))
    return fig


def _verdict(g_fwd, ccm, name, alpha) -> str:
    sig = int((g_fwd["p_value"] < alpha).sum())
    fwd = ccm[ccm["direction"] == "ONI->target"].sort_values("lib_size")["rho"]
    rev = ccm[ccm["direction"] == "target->ONI"].sort_values("lib_size")["rho"]
    converges = (len(fwd) > 1 and (fwd.iloc[-1] - fwd.iloc[0]) > 0.03
                 and fwd.iloc[-1] > rev.iloc[-1])
    if sig >= 3 and converges:
        head, color = "Evidence supports ONI → " + name, COLORS["teal"]
        body = (f"Granger significant at {sig}/24 lags AND CCM cross-map skill "
                f"converges upward for ONI → {name} (and exceeds the reverse). "
                "Both linear and nonlinear tests agree on direction.")
    elif sig >= 3 or converges:
        head, color = "Partial / mixed evidence for ONI → " + name, COLORS["el_nino"]
        body = (f"Granger significant at {sig}/24 lags; CCM convergence "
                f"{'present' if converges else 'weak/absent'}. Linear and nonlinear "
                "tests disagree — treat as suggestive, not conclusive.")
    else:
        head, color = "No robust causal signal", COLORS["neutral"]
        body = (f"Granger significant at only {sig}/24 lags and CCM does not "
                "converge. Any correlation is likely shared trend/seasonality.")
    return (f"<div class='enso-verdict'><b style='color:{color};font-size:17px'>"
            f"{head}</b><br><span style='color:{COLORS['muted']}'>{body}</span></div>")


def build_panels(name: str, maxlag: int, alpha: float):
    series = _commodity_series(name)
    res = analyze(ONI, series, maxlag=maxlag, mode="detrend")
    g_fwd, g_rev, ccm = (res["granger_oni_to_target"],
                         res["granger_target_to_oni"], res["ccm"])
    verdict = pn.pane.HTML(_verdict(g_fwd, ccm, name, alpha), css_classes=["enso-card"])
    granger = pn.pane.Plotly(build_granger_chart(g_fwd, g_rev, name, alpha),
                             config={"displayModeBar": True}, sizing_mode="stretch_width")
    ccm_fig = pn.pane.Plotly(build_ccm_chart(ccm, name),
                             config={"displayModeBar": True}, sizing_mode="stretch_width")
    return pn.Column(
        verdict, pn.Spacer(height=8),
        pn.Row(pn.Column(granger, css_classes=["enso-card"]),
               pn.Column(ccm_fig, css_classes=["enso-card"])))


def build_app() -> pn.viewable.Viewable:
    header = pn.pane.HTML(
        "<div><p class='enso-title'>🔗 Causation Explorer</p>"
        "<p class='enso-subtitle'>Granger causality + Convergent Cross Mapping · "
        f"ONI vs commodity prices · index: <b style='color:{COLORS['teal']}'>ONI</b></p></div>")

    commodity = pn.widgets.Select(name="Commodity", value="Wheat, US HRW",
                                  options=ALL_COMMODITIES, sizing_mode="stretch_width")
    maxlag = pn.widgets.IntSlider(name="Max Granger lag (months)", start=6, end=24,
                                  value=24, sizing_mode="stretch_width")
    alpha = pn.widgets.Select(name="Significance α", value=0.05,
                              options=[0.10, 0.05, 0.01], width=140)
    controls = pn.Column(commodity, pn.Row(maxlag, alpha), css_classes=["enso-card"])

    panels = pn.bind(build_panels, name=commodity, maxlag=maxlag, alpha=alpha)

    note = pn.pane.HTML(
        "<div class='enso-note'><b>Reading this honestly.</b> Series are linearly "
        "detrended (not differenced) to preserve the low-frequency ENSO signal; "
        "they remain autocorrelated, so <b>Granger over-detects</b> — note how the "
        "reverse direction (commodity → ONI) is often 'significant' too, which is "
        "physically implausible. <b>CCM is more discriminating</b>: genuine "
        "causation shows cross-map skill that <i>rises and converges</i> with "
        "library size in one direction only. Neither test includes "
        "phase-randomized <b>surrogate</b> significance yet (a planned addition), "
        "so treat verdicts as exploratory. Correlation ≠ causation; teleconnections "
        "are probabilistic and modulated by IOD/MJO.</div>")

    return pn.Column(
        header, pn.Spacer(height=8), controls, pn.Spacer(height=8),
        panels, pn.Spacer(height=8), note,
        styles={"background": COLORS["bg"], "padding": "22px",
                "min-height": "100vh", "max-width": "1500px", "margin": "0 auto"})


build_app().servable(title="Causation Explorer")
