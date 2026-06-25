"""Forecast — probabilistic ONI fan chart + model verification.

Run with::

    panel serve dashboard/pages/03_forecast.py --show

Shows recent ONI history, the SARIMA / LSTM / Ensemble forward forecasts with
prediction intervals, landmark thresholds, and — critically — the *spread* of
external operational forecasts (CPC dynamical models vs a skeptical published
estimate). A skill-by-lead panel reports ACC against persistence so the viewer
can judge how far out each model is actually trustworthy.

Requires the forecasting engine to have been run::

    python forecasting/baselines/arima_model.py
    python forecasting/ml_models/lstm_enso.py
    python forecasting/ensemble.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import panel as pn
import plotly.graph_objects as go

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
_ROOT = _DASH_DIR.parent
sys.path.insert(0, str(_DASH_DIR))
from theme import COLORS, CACHE_DIR, load_oni, style_figure  # noqa: E402

MODEL_COLORS = {
    "SARIMA": COLORS["el_nino"],
    "LSTM": COLORS["la_nina"],
    "Ensemble": COLORS["teal"],
}

# External operational forecasts for the SON 2026 peak (from project brief) —
# illustrate genuine disagreement; these are reference markers, not our output.
EXTERNAL = [
    {"label": "CPC / IRI dynamical (~strong–super, ≥+2.0)", "date": "2026-10-01",
     "value": 2.0, "color": COLORS["el_nino"]},
    {"label": "arXiv:2602.14773 (skeptical onset ~37.5%)", "date": "2026-10-01",
     "value": 0.6, "color": COLORS["neutral"]},
]

RAW_CSS = f"""
:host, body {{ background-color: {COLORS['bg']}; color: {COLORS['text']}; }}
.enso-card {{ background: {COLORS['surface']};
  border: 1px solid rgba(138,148,166,0.12); border-radius: 14px; padding: 18px 20px; }}
.enso-title {{ font-size: 26px; font-weight: 800; margin: 0; }}
.enso-subtitle {{ color: {COLORS['muted']}; font-size: 13px; margin-top: 2px; }}
.enso-warn {{ background: rgba(244,98,58,0.08); border-left: 3px solid {COLORS['el_nino']};
  border-radius: 8px; padding: 12px 16px; font-size: 12px; line-height: 1.5; }}
"""

pn.extension("plotly", raw_css=[RAW_CSS], sizing_mode="stretch_width")


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def build_fan_chart(history: pd.DataFrame, forecasts: pd.DataFrame) -> go.Figure:
    """Recent ONI history + per-model forecast means with CI bands."""
    fig = go.Figure()

    # Threshold guides.
    for y, label in ((0.5, "El Niño +0.5"), (2.0, "Very strong +2.0"), (-0.5, "La Niña −0.5")):
        fig.add_hline(y=y, line=dict(color="rgba(138,148,166,0.35)", width=1, dash="dot"),
                      annotation_text=label, annotation_position="right",
                      annotation_font_color=COLORS["muted"], annotation_font_size=10)

    # History (last ~6 years).
    hist = history.tail(72)
    fig.add_trace(go.Scatter(
        x=hist["date"], y=hist["oni"], mode="lines", name="ONI (observed)",
        line=dict(color=COLORS["text"], width=2),
        hovertemplate="%{x|%b %Y}<br>ONI: %{y:+.2f}°C<extra></extra>"))

    last_date, last_val = hist["date"].iloc[-1], hist["oni"].iloc[-1]

    for model, grp in forecasts.groupby("model"):
        color = MODEL_COLORS.get(model, COLORS["muted"])
        # Prepend the last observation for visual continuity. Use a Series for
        # the x-axis (datetime64) — Plotly/kaleido reject Python lists of
        # Timestamp scalars but handle datetime64 Series/arrays fine.
        connect = pd.DataFrame({"date": [last_date], "mean": [last_val],
                                "upper": [last_val], "lower": [last_val]})
        g = pd.concat([connect, grp.sort_values("date")], ignore_index=True)
        fig.add_trace(go.Scatter(x=g["date"], y=g["upper"], mode="lines",
                                 line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=g["date"], y=g["lower"], mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor=_hex_to_rgba(color, 0.13),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=g["date"], y=g["mean"], mode="lines", name=f"{model} forecast",
            line=dict(color=color, width=2.4, dash="solid"),
            hovertemplate="%{x|%b %Y}<br>" + model + ": %{y:+.2f}°C<extra></extra>"))

    # External operational references (disagreement markers).
    for ext in EXTERNAL:
        fig.add_trace(go.Scatter(
            x=[ext["date"]], y=[ext["value"]], mode="markers",
            name=ext["label"], marker=dict(color=ext["color"], size=12, symbol="diamond",
                                           line=dict(color=COLORS["text"], width=1)),
            hovertemplate=ext["label"] + "<br>%{x|%b %Y}: ~%{y:+.1f}°C<extra></extra>"))

    style_figure(fig, height=480, margin=dict(l=60, r=30, t=50, b=90),
        title=dict(text="ONI forecast fan chart — model spread to 12 months",
                   font=dict(size=16)),
        yaxis=dict(title="ONI anomaly (°C)", gridcolor="rgba(138,148,166,0.12)"),
        xaxis=dict(gridcolor="rgba(138,148,166,0.08)"),
        legend=dict(orientation="h", yanchor="top", y=-0.14, x=0))
    return fig


def build_skill_chart(skill: pd.DataFrame) -> go.Figure:
    """ACC vs lead per model, with the 0.5 'useful skill' line."""
    fig = go.Figure()
    fig.add_hline(y=0.5, line=dict(color="rgba(138,148,166,0.4)", width=1, dash="dash"),
                  annotation_text="useful-skill 0.5", annotation_position="right",
                  annotation_font_color=COLORS["muted"], annotation_font_size=10)
    for model, grp in skill.groupby("model"):
        grp = grp.sort_values("lead")
        color = MODEL_COLORS.get(model, COLORS["muted"])
        fig.add_trace(go.Scatter(
            x=grp["lead"], y=grp["acc"], mode="lines+markers", name=model,
            line=dict(color=color, width=2.2),
            hovertemplate=model + " lead %{x}mo<br>ACC %{y:.3f}<extra></extra>"))
    style_figure(fig, height=320, title=dict(
        text="Forecast skill (ACC) vs lead — verified against persistence", font=dict(size=15)),
        yaxis=dict(title="Anomaly correlation (ACC)", range=[0, 1.02],
                   gridcolor="rgba(138,148,166,0.12)"),
        xaxis=dict(title="Lead (months)", dtick=1, gridcolor="rgba(138,148,166,0.08)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    return fig


def build_app() -> pn.viewable.Viewable:
    history = load_oni()[["date", "oni"]]
    forecasts = pd.read_parquet(CACHE_DIR / "forecasts_all.parquet")
    skill = pd.read_parquet(CACHE_DIR / "skill_all.parquet")

    header = pn.pane.HTML(
        "<div><p class='enso-title'>🔮 Forecast</p>"
        "<p class='enso-subtitle'>SARIMA · LSTM · Ensemble · verified vs persistence · "
        f"index: <b style='color:{COLORS['teal']}'>ONI</b></p></div>")

    fan = pn.pane.Plotly(build_fan_chart(history, forecasts),
                         config={"displayModeBar": True}, sizing_mode="stretch_width")
    skl = pn.pane.Plotly(build_skill_chart(skill),
                         config={"displayModeBar": True}, sizing_mode="stretch_width")

    warn = pn.pane.HTML(
        "<div class='enso-warn'><b>Never trust a single forecast.</b> The shaded "
        "bands are prediction intervals; the spread <i>between</i> models — and "
        "between these statistical baselines and CPC's dynamical models (which "
        "expect a stronger event) — is the real signal. Our linear/recurrent "
        "baselines mean-revert and under-call strong events; coupled dynamical "
        "models (and the ERA5 CNN track) capture growth dynamics they cannot. "
        "Skill (ACC) typically falls below the useful 0.5 line beyond ~6–8 months "
        "— the ENSO spring predictability barrier. Index: ONI (see Monitor for the "
        "RONI caveat).</div>")

    return pn.Column(
        header, pn.Spacer(height=8),
        pn.Column(fan, css_classes=["enso-card"]), pn.Spacer(height=8),
        pn.Column(skl, css_classes=["enso-card"]), pn.Spacer(height=8), warn,
        styles={"background": COLORS["bg"], "padding": "22px",
                "min-height": "100vh", "max-width": "1500px", "margin": "0 auto"})


build_app().servable(title="ENSO Forecast")
