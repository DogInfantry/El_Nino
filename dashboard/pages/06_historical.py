"""Historical — ENSO event cards (1950–present).

Run with::

    panel serve dashboard/pages/06_historical.py --show

Each detected El Niño / La Niña event (from the official 5-season definition) is
rendered as a card: peak ONI, the RONI value at that peak (showing how the new
official index reclassifies it), duration, intensity tier, data-driven commodity
moves in the following 24 months (World Bank Pink Sheet), and — for landmark
events — the Callahan & Mankin (2023, Science) economic-loss estimates.

Requires Phase-1 caches; RONI and commodity enrichment degrade gracefully.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import panel as pn

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
_ROOT = _DASH_DIR.parent
for p in (_DASH_DIR, _ROOT / "data" / "process", _ROOT / "data" / "ingest"):
    sys.path.insert(0, str(p))

from theme import COLORS, CACHE_DIR, load_commodities, load_phases  # noqa: E402
from enso_phase_labeler import event_summary  # noqa: E402
from pink_sheet import FOCUS_COMMODITIES  # noqa: E402

# Curated context for landmark events (keyed by peak year). Economic figures:
# Callahan & Mankin 2023, Science (global GDP loss in the ~5 years after onset).
LANDMARK_FACTS: dict[int, dict] = {
    1983: {"cost": "≈ $4.1T", "regions": ["Australia drought", "Peru/Ecuador floods",
            "SE Asia drought"], "note": "Callahan & Mankin: ~$4.1T global GDP lost."},
    1998: {"cost": "≈ $5.7T", "regions": ["Indonesia drought/fires", "E Africa floods",
            "Horn of Africa"], "note": "Callahan & Mankin: ~$5.7T global GDP lost."},
    2016: {"cost": "multi-$T", "regions": ["Maritime Continent drought", "S Africa drought",
            "Cocoa belt (W Africa)"], "note": "Strong cocoa/sugar price response."},
    2024: {"cost": "assessing", "regions": ["Panama Canal low water", "S Asia heat",
            "W Africa cocoa"], "note": "Record cocoa prices; RONI ≈0.6°C below ONI."},
}
# Context: 21st-century cumulative ENSO losses projected up to ~$84T (C&M 2023).

PHASE_COLOR = {"El Nino": COLORS["el_nino"], "La Nina": COLORS["la_nina"]}

RAW_CSS = f"""
:host, body {{ background-color: {COLORS['bg']}; color: {COLORS['text']}; }}
.enso-title {{ font-size: 26px; font-weight: 800; margin: 0; }}
.enso-subtitle {{ color: {COLORS['muted']}; font-size: 13px; margin-top: 2px; }}
.evt-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 14px; }}
.evt-card {{ background: {COLORS['surface']}; border: 1px solid rgba(138,148,166,0.12);
  border-radius: 14px; padding: 16px 18px; border-top: 3px solid var(--accent); }}
.evt-head {{ display:flex; justify-content:space-between; align-items:baseline; }}
.evt-phase {{ font-size: 17px; font-weight: 800; }}
.evt-period {{ color: {COLORS['muted']}; font-size: 12px; }}
.evt-badge {{ font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 999px;
  background: var(--accent); color: #0a0e1a; }}
.evt-metrics {{ display:flex; gap:18px; margin: 10px 0 6px; }}
.evt-metric .v {{ font-size: 20px; font-weight: 800; }}
.evt-metric .l {{ font-size: 10px; color: {COLORS['muted']}; text-transform: uppercase;
  letter-spacing: 0.06em; }}
.evt-chips {{ margin-top: 8px; }}
.chip {{ display:inline-block; font-size: 11px; padding: 2px 8px; border-radius: 6px;
  margin: 2px 4px 2px 0; background: rgba(138,148,166,0.12); }}
.evt-cost {{ margin-top: 10px; font-size: 12px; color: {COLORS['text']};
  background: rgba(244,98,58,0.10); border-radius: 6px; padding: 7px 10px; }}
.evt-regions {{ margin-top: 8px; font-size: 11px; color: {COLORS['muted']}; }}
.enso-note {{ background: rgba(0,212,180,0.07); border-left: 3px solid {COLORS['teal']};
  border-radius: 8px; padding: 12px 16px; font-size: 12px; line-height: 1.5; }}
"""

pn.extension(raw_css=[RAW_CSS], sizing_mode="stretch_width")

PHASES = load_phases()
EVENTS = event_summary(PHASES)

try:
    _RONI = pd.read_parquet(CACHE_DIR / "roni.parquet")[["date", "roni"]]
except Exception:  # noqa: BLE001
    _RONI = None

try:
    _COMM = load_commodities()
    COMM_WIDE = (
        _COMM[_COMM["commodity"].isin(FOCUS_COMMODITIES)]
        .pivot_table(index="date", columns="commodity", values="price")
        .sort_index()
    )
except Exception:  # noqa: BLE001
    COMM_WIDE = None

SHORT_NAME = {
    "Cocoa": "Cocoa", "Coffee, Arabica": "Arabica", "Coffee, Robusta": "Robusta",
    "Sugar, world": "Sugar", "Palm oil": "Palm oil", "Soybeans": "Soy",
    "Wheat, US HRW": "Wheat", "Liquefied natural gas, Japan": "LNG",
}


def _roni_at(peak_date: pd.Timestamp) -> float | None:
    if _RONI is None:
        return None
    row = _RONI.iloc[(_RONI["date"] - peak_date).abs().argmin()]
    if abs((row["date"] - peak_date).days) > 75:
        return None
    return float(row["roni"])


def _commodity_moves(peak_date: pd.Timestamp, window: int = 24) -> list[tuple[str, float]]:
    """Max % move of each focus commodity within ``window`` months after peak."""
    if COMM_WIDE is None:
        return []
    end = peak_date + pd.DateOffset(months=window)
    out: list[tuple[str, float]] = []
    for c in COMM_WIDE.columns:
        s = COMM_WIDE[c].dropna()
        base = s.asof(peak_date)
        after = s[(s.index > peak_date) & (s.index <= end)]
        if pd.notna(base) and base > 0 and not after.empty:
            mx = after.max()
            out.append((SHORT_NAME.get(c, c), (mx - base) / base * 100.0))
    out.sort(key=lambda kv: kv[1], reverse=True)
    return out[:4]


def _card(ev: pd.Series) -> str:
    accent = PHASE_COLOR.get(ev["phase"], COLORS["neutral"])
    start, end = pd.Timestamp(ev["start"]), pd.Timestamp(ev["end"])
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    roni = _roni_at(pd.Timestamp(ev["start"]) + (end - start) / 2)
    roni_html = (f"<div class='evt-metric'><div class='v' style='color:{COLORS['el_nino']}'>"
                 f"{roni:+.2f}</div><div class='l'>RONI peak*</div></div>"
                 if roni is not None else "")

    facts = LANDMARK_FACTS.get(end.year) or LANDMARK_FACTS.get(start.year)

    # Commodity chips ONLY for landmark events with documented teleconnection
    # responses — otherwise the post-event window naively captures unrelated
    # macro spikes (e.g. 2021-22) and misattributes them to a weak event.
    chips_html = ""
    if facts:
        chips = ""
        for name, pct in _commodity_moves(end, window=18):
            col = COLORS["el_nino"] if pct >= 0 else COLORS["la_nina"]
            chips += f"<span class='chip' style='color:{col}'>{name} {pct:+.0f}%</span>"
        chips_html = f"<div class='evt-chips'>{chips}</div>" if chips else ""

    cost_html = regions_html = ""
    if facts:
        cost_html = (f"<div class='evt-cost'>💸 <b>{facts['cost']}</b> — {facts['note']}</div>")
        regions_html = ("<div class='evt-regions'>🌍 " + " · ".join(facts["regions"]) + "</div>")

    return (
        f"<div class='evt-card' style='--accent:{accent}'>"
        f"<div class='evt-head'><span class='evt-phase' style='color:{accent}'>"
        f"{ev['phase']}</span><span class='evt-badge'>{ev['intensity']}</span></div>"
        f"<div class='evt-period'>{start:%b %Y} – {end:%b %Y} · {months} months</div>"
        f"<div class='evt-metrics'>"
        f"<div class='evt-metric'><div class='v' style='color:{COLORS['teal']}'>"
        f"{ev['peak_value']:+.2f}</div><div class='l'>Peak ONI</div></div>"
        f"{roni_html}"
        f"<div class='evt-metric'><div class='v'>{ev['n_seasons']}</div>"
        f"<div class='l'>Seasons</div></div></div>"
        f"{chips_html}{cost_html}{regions_html}</div>"
    )


def build_cards(phase_filter: str) -> pn.pane.HTML:
    evs = EVENTS.sort_values("start", ascending=False)
    if phase_filter != "All":
        evs = evs[evs["phase"] == phase_filter]
    cards = "".join(_card(ev) for _, ev in evs.iterrows())
    return pn.pane.HTML(f"<div class='evt-grid'>{cards}</div>", sizing_mode="stretch_width")


def build_app() -> pn.viewable.Viewable:
    header = pn.pane.HTML(
        "<div><p class='enso-title'>🗓️ Historical Events</p>"
        "<p class='enso-subtitle'>ENSO events since 1950 · peak ONI/RONI · "
        "post-event commodity moves · economic cost (Callahan & Mankin 2023)</p></div>")

    phase = pn.widgets.RadioButtonGroup(
        name="Phase", options=["El Nino", "La Nina", "All"], value="El Nino",
        button_type="default")

    cards = pn.bind(build_cards, phase_filter=phase)

    note = pn.pane.HTML(
        "<div class='enso-note'>Events use the official ±0.5°C / 5-overlapping-season "
        "definition (ONI). <b>*RONI peak</b> is our ERSST-computed RONI at the event "
        "centre (fixed 1991–2020 base) — note how recent strong events read cooler "
        "under RONI. Commodity chips (shown only for landmark events with documented "
        "responses) give the <i>largest</i> move in the 18 months after the event end "
        "(World Bank Pink Sheet, nominal USD; data ends 2024-12 so the latest event's "
        "window is partial). Economic losses are ~5-year global GDP "
        "estimates; 21st-century cumulative ENSO losses are projected up to ~$84T. "
        "Correlation ≠ causation — commodity moves have many drivers.</div>")

    return pn.Column(
        header, pn.Spacer(height=8), pn.Row(phase), pn.Spacer(height=8),
        cards, pn.Spacer(height=10), note,
        styles={"background": COLORS["bg"], "padding": "22px",
                "min-height": "100vh", "max-width": "1500px", "margin": "0 auto"})


build_app().servable(title="Historical Events")
