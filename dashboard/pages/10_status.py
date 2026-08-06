"""Page 10 — Data Status.

Every upstream feed, its cadence, and how late it actually is. Built because on
2026-07-30 the desk *looked* stale (the ONI renders under its centre month) and nothing on
screen could settle the question — hours went into proving the data was fine.

The column that matters is **behind**, not **age**. ``age`` is what a reader sees ("this
says May 2026"); ``behind`` subtracts the structural label lag and says whether that is
actually late. A deliberate cutoff reads SNAPSHOT or STATIC, never STALE.

Run with::

    panel serve dashboard/pages/10_status.py --show
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import panel as pn

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
_ROOT = _DASH_DIR.parent
for _p in (_DASH_DIR, _ROOT / "data" / "ingest"):
    sys.path.insert(0, str(_p))

from theme import COLORS  # noqa: E402
from source_registry import status_table  # noqa: E402

AMBER = COLORS.get("amber", "#f4b13a")

# status -> (text colour, background). Only AGING/STALE/MISSING are meant to alarm.
CHIP = {
    "FRESH":    ("#04211d", COLORS["teal"]),
    "LIVE":     ("#04211d", COLORS["la_nina"]),
    "AGING":    ("#2a1e06", AMBER),
    "STALE":    ("#2a120b", COLORS["el_nino"]),
    "MISSING":  ("#2a120b", COLORS["el_nino"]),
    "SNAPSHOT": ("#c2cadb", "#243049"),
    "STATIC":   ("#c2cadb", "#243049"),
}

CSS = f"""
.st-bar {{ display:flex; align-items:center; gap:12px; padding:11px 16px; background:#0a1020;
  border:1px solid rgba(138,148,166,0.18); border-radius:12px;
  font:600 12px/1 ui-monospace,monospace; color:{COLORS['text']}; }}
.st-bar .tag {{ color:{COLORS['teal']}; background:rgba(0,212,180,.12);
  border:1px solid rgba(0,212,180,.34); padding:4px 8px; border-radius:5px; font-size:10px;
  letter-spacing:.6px; }}
.st-note {{ padding:11px 16px; font-size:12px; line-height:1.6; color:{COLORS['muted']};
  background:{COLORS['surface']}; border:1px solid rgba(138,148,166,0.14);
  border-radius:11px; margin:10px 0; }}
.st-note b {{ color:{COLORS['text']}; }}
table.st {{ width:100%; border-collapse:collapse; font-size:12px; }}
table.st th {{ text-align:left; font:700 9px ui-monospace,monospace; letter-spacing:.8px;
  text-transform:uppercase; color:{COLORS['muted']}; padding:8px 9px;
  border-bottom:1px solid rgba(138,148,166,0.22); }}
table.st td {{ padding:9px 9px; border-bottom:1px solid rgba(138,148,166,0.08);
  color:{COLORS['muted']}; vertical-align:top; }}
table.st td.nm {{ color:{COLORS['text']}; font-weight:600; white-space:nowrap; }}
table.st td.num {{ font:600 11.5px ui-monospace,monospace; text-align:right;
  white-space:nowrap; }}
table.st .note {{ font-size:11px; line-height:1.5; }}
.st-chip {{ font:800 9.5px ui-monospace,monospace; padding:3px 7px; border-radius:4px;
  letter-spacing:.5px; }}
"""

pn.extension(raw_css=[CSS], sizing_mode="stretch_width")


def _chip(status: str) -> str:
    fg, bg = CHIP.get(status, ("#c2cadb", "#243049"))
    return f"<span class='st-chip' style='color:{fg};background:{bg}'>{status}</span>"


def _days(value, *, signed: bool = False) -> str:
    """Render a day count that may be absent.

    A source with no cache (the live advisory) has no age at all. pandas stores that as
    NaN in a float column, not None, so an ``is None`` test silently misses it and
    ``int(NaN)`` raises — hence an explicit null check.
    """
    if value is None or pd.isna(value):
        return "—"
    return f"{int(value):+d} d" if signed else f"{int(value)} d"


def _table() -> pn.pane.HTML:
    df = status_table()
    rows = []
    for _, r in df.iterrows():
        latest = ("—" if pd.isna(r["latest"]) or r["latest"] is None
                  else str(r["latest"])[:10])
        age = _days(r["age_days"])
        # "Behind" is only meaningful where a cadence is expected.
        behind = (_days(r["behind_days"], signed=True)
                  if r["kind"] in ("feed", "computed") else "n/a")
        cadence = _days(r["cadence_days"])
        rows.append(
            f"<tr><td class='nm'>{r['name']}</td><td>{r['kind']}</td>"
            f"<td class='num'>{cadence}</td><td class='num'>{latest}</td>"
            f"<td class='num'>{age}</td><td class='num'>{behind}</td>"
            f"<td>{_chip(r['status'])}</td><td class='note'>{r['note'] or ''}</td></tr>")
    head = ("<tr><th>Source</th><th>Kind</th><th>Cadence</th><th>Newest label</th>"
            "<th>Age</th><th>Behind</th><th>Status</th><th>Notes</th></tr>")
    return pn.pane.HTML(f"<table class='st'>{head}{''.join(rows)}</table>")


def build_app() -> pn.viewable.Viewable:
    bar = pn.pane.HTML(
        "<div class='st-bar'><span style='color:#00d4b4'>← DESK</span>"
        "<span>DATA STATUS</span><span class='tag'>SOURCE FRESHNESS</span></div>")
    note = pn.pane.HTML(
        "<div class='st-note'><b>Read the “Behind” column, not “Age”.</b> The ONI is a "
        "3-month running mean stored under its <b>centre month</b>, so a perfectly current "
        "value carries a label ~75 days old. <b>Age</b> is that raw gap; <b>Behind</b> "
        "subtracts each source's structural label lag and is what actually indicates "
        "lateness. Sources marked <b>SNAPSHOT</b> or <b>STATIC</b> have deliberate cutoffs "
        "(the World Bank Pink Sheet ends 2024-12; the IMD subdivision set ends 2017) — "
        "stated decisions, not neglect. <b>LIVE</b> sources are fetched at page load and "
        "cannot go stale.</div>")
    return pn.Column(
        bar, note, pn.Column(_table(), css_classes=["st-note"]),
        styles={"background": COLORS["bg"], "padding": "22px", "min-height": "100vh",
                "max-width": "1180px", "margin": "0 auto"},
        sizing_mode="stretch_width")


build_app().servable(title="Data Status — ENSO Macro Risk Desk")
