"""ENSO Monitor — live ONI time series, advisory badge, and Niño-3.4 gauge.

The visual MVP of the platform. Run with::

    panel serve dashboard/pages/01_enso_monitor.py --show

Composition:
    - Header with title + LIVE advisory badge (fetched at runtime, never hardcoded)
    - Stat-card row (latest ONI, simple phase, intensity, data-through)
    - Niño-3.4 gauge (left) + event-shaded ONI time series (right)
    - RONI-vs-ONI disclaimer footer + CSV export

All ENSO classifications here use ONI. NOAA adopted RONI as the official index
on 16 Feb 2026; the RONI overlay is a fast-follow once ``roni_fetcher`` lands.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import panel as pn

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
_ROOT = _DASH_DIR.parent
for p in (
    _DASH_DIR,
    _DASH_DIR / "components",
    _ROOT / "data" / "process",
    _ROOT / "data" / "ingest",
):
    sys.path.insert(0, str(p))

from theme import COLORS, CACHE_DIR, load_phases  # noqa: E402
from oni_gauge import build_gauge  # noqa: E402
from timeseries import build_oni_timeseries  # noqa: E402
from enso_phase_labeler import event_summary  # noqa: E402

try:
    from advisory_fetcher import get_advisory
except Exception:  # noqa: BLE001
    def get_advisory():  # type: ignore[misc]
        return None

ACCENT = COLORS["teal"]

RAW_CSS = f"""
:host, body {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
}}
.enso-card {{
    background: {COLORS['surface']};
    border: 1px solid rgba(138,148,166,0.12);
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.35);
}}
.enso-stat-label {{
    font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
    color: {COLORS['muted']}; margin-bottom: 6px;
}}
.enso-stat-value {{ font-size: 30px; font-weight: 700; line-height: 1; }}
.enso-stat-sub {{ font-size: 12px; color: {COLORS['muted']}; margin-top: 6px; }}
.enso-badge {{
    display: inline-block; padding: 7px 16px; border-radius: 999px;
    font-weight: 700; font-size: 14px; letter-spacing: 0.02em;
}}
.enso-title {{ font-size: 26px; font-weight: 800; margin: 0; }}
.enso-subtitle {{ color: {COLORS['muted']}; font-size: 13px; margin-top: 2px; }}
.enso-disclaimer {{
    background: rgba(244,98,58,0.08);
    border-left: 3px solid {COLORS['el_nino']};
    border-radius: 8px; padding: 12px 16px; font-size: 12px;
    color: {COLORS['text']}; line-height: 1.5;
}}
"""

pn.extension("plotly", raw_css=[RAW_CSS], sizing_mode="stretch_width")


def _badge_color(status: str) -> str:
    s = status.lower()
    if "el ni" in s:
        return COLORS["el_nino"]
    if "la ni" in s:
        return COLORS["la_nina"]
    return COLORS["neutral"]


def _stat_card(label: str, value: str, sub: str, color: str | None = None) -> pn.pane.HTML:
    color = color or COLORS["text"]
    html = (
        f"<div class='enso-card'>"
        f"<div class='enso-stat-label'>{label}</div>"
        f"<div class='enso-stat-value' style='color:{color}'>{value}</div>"
        f"<div class='enso-stat-sub'>{sub}</div></div>"
    )
    return pn.pane.HTML(html, sizing_mode="stretch_width")


def build_app() -> pn.viewable.Viewable:
    """Assemble and return the ENSO Monitor page."""
    phases = load_phases()
    events = event_summary(phases)
    latest = phases.iloc[-1]
    latest_value = float(latest["value"])
    latest_label = f"{latest['season']} {int(latest['year'])}"

    # RONI overlay (computed from ERSSTv5); degrade gracefully if not generated.
    roni_df = None
    latest_roni = None
    try:
        _r = pd.read_parquet(CACHE_DIR / "roni.parquet")
        roni_df = _r[["date", "roni"]].rename(columns={"roni": "value"})
        latest_roni = float(_r.iloc[-1]["roni"])
    except Exception:  # noqa: BLE001 - overlay is optional
        pass

    # Current phase/intensity from the labeled record (live data, not hardcoded).
    in_event = pd.notna(latest.get("event_id"))
    simple_phase = latest["phase_simple"]
    intensity = latest["intensity"] if in_event else "—"
    phase_color = {
        "El Nino": COLORS["el_nino"],
        "La Nina": COLORS["la_nina"],
        "Neutral": COLORS["neutral"],
    }.get(simple_phase, COLORS["text"])

    # Live advisory (graceful fallback to data-derived status).
    advisory = get_advisory()
    if advisory is not None:
        status_text = advisory.status
        synopsis = advisory.synopsis
        adv_source = "NOAA CPC/IRI ENSO Diagnostic Discussion (live)"
    else:
        status_text = (
            "El Niño conditions" if latest_value >= 0.5
            else "La Niña conditions" if latest_value <= -0.5
            else "ENSO-Neutral"
        )
        synopsis = "Live advisory unavailable — status derived from latest ONI."
        adv_source = "Derived from latest ONI (advisory feed unreachable)"

    badge_color = _badge_color(status_text)

    header = pn.pane.HTML(
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"flex-wrap:wrap;gap:12px;'>"
        f"<div><p class='enso-title'>🌊 ENSO Monitor</p>"
        f"<p class='enso-subtitle'>El Niño–Southern Oscillation · live NOAA CPC data · "
        f"indices: <b style='color:{COLORS['teal']}'>ONI</b> + "
        f"<b style='color:{COLORS['el_nino']}'>RONI</b></p></div>"
        f"<div style='text-align:right;'>"
        f"<span class='enso-badge' style='background:{badge_color};color:#0a0e1a;'>"
        f"{status_text}</span>"
        f"<div class='enso-stat-sub' style='max-width:420px;margin-top:8px;'>{synopsis}</div>"
        f"</div></div>",
        sizing_mode="stretch_width",
    )

    if latest_roni is not None:
        roni_card = _stat_card(
            "Latest RONI", f"{latest_roni:+.2f}°C",
            f"{latest_value - latest_roni:+.2f}°C vs ONI (warming removed)",
            COLORS["el_nino"])
    else:
        roni_card = _stat_card("Latest RONI", "—", "run roni_calculator", COLORS["muted"])

    cards = pn.Row(
        _stat_card("Latest ONI", f"{latest_value:+.2f}°C", latest_label, COLORS["teal"]),
        roni_card,
        _stat_card("Phase", simple_phase, "±0.5°C threshold", phase_color),
        _stat_card("Event intensity", intensity,
                   "NOAA tier" if in_event else "no active event", COLORS["text"]),
        _stat_card("Data through", latest_label,
                   f"{len(phases):,} seasons since 1950", COLORS["text"]),
        sizing_mode="stretch_width",
    )

    gauge = pn.pane.Plotly(
        build_gauge(latest_value),
        config={"displayModeBar": True, "toImageButtonOptions": {"format": "png"}},
        sizing_mode="stretch_width",
    )
    gauge_card = pn.Column(
        pn.pane.HTML("<div class='enso-stat-label'>Niño-3.4 Gauge</div>"),
        gauge,
        css_classes=["enso-card"],
        width=380,
    )

    ts = pn.pane.Plotly(
        build_oni_timeseries(phases, events, index_label="ONI",
                             secondary=roni_df, secondary_label="RONI (ERSST)"),
        config={"displayModeBar": True, "toImageButtonOptions": {"format": "png"}},
        sizing_mode="stretch_width",
    )
    ts_card = pn.Column(ts, css_classes=["enso-card"], sizing_mode="stretch_width")

    main_row = pn.Row(gauge_card, ts_card, sizing_mode="stretch_width")

    # CSV export of the labeled series.
    def _csv() -> io.BytesIO:
        buf = io.BytesIO()
        phases.to_csv(buf, index=False)
        buf.seek(0)
        return buf

    export = pn.widgets.FileDownload(
        callback=_csv,
        filename="enso_phases.csv",
        label="⬇ Export labeled ONI series (CSV)",
        button_type="primary",
        width=300,
    )

    disclaimer = pn.pane.HTML(
        "<div class='enso-disclaimer'>"
        "<b>Index disclaimer.</b> Teal line = official CPC <b>ONI</b> (rolling 3-month "
        "Niño-3.4 anomaly). Dotted coral line = <b>RONI</b>, which NOAA adopted as the "
        "official ENSO index on 16 Feb 2026; it subtracts tropical-mean SST so recent "
        "events register cooler (e.g. 2023–24 ≈0.6°C lower) — visible as RONI sitting "
        "below ONI in recent decades. Our RONI is <i>computed from ERSSTv5</i> on a fixed "
        "1991–2020 base (the official RONI uses ONI's rolling base), so it approximates "
        "rather than reproduces the operational value. The ONI 3-month mean also lags the "
        "raw weekly Niño-3.4. &nbsp;<i>Advisory source: " + adv_source + ".</i></div>",
        sizing_mode="stretch_width",
    )

    return pn.Column(
        header,
        pn.Spacer(height=8),
        cards,
        pn.Spacer(height=8),
        main_row,
        pn.Spacer(height=8),
        pn.Row(export, sizing_mode="stretch_width"),
        disclaimer,
        styles={"background": COLORS["bg"], "padding": "22px",
                "min-height": "100vh", "max-width": "1500px", "margin": "0 auto"},
        sizing_mode="stretch_width",
    )


build_app().servable(title="ENSO Monitor")
