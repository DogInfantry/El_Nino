"""Page 9 — Methodology.

Renders ``docs/METHODOLOGY.md`` directly. The document is the single source of truth: it
is asserted against the code by ``tests/test_core.py``, so re-typing any of it here would
create a second copy that can drift silently — exactly what the doc-vs-code gate exists to
prevent.

Run with::

    panel serve dashboard/pages/09_methodology.py --show
"""

from __future__ import annotations

import sys
from pathlib import Path

import panel as pn

_PAGE_DIR = Path(__file__).resolve().parent
_DASH_DIR = _PAGE_DIR.parent
_ROOT = _DASH_DIR.parent
sys.path.insert(0, str(_DASH_DIR))

from theme import COLORS  # noqa: E402

DOC = _ROOT / "docs" / "METHODOLOGY.md"

CSS = f"""
.md-wrap {{ background:{COLORS['surface']}; border:1px solid rgba(138,148,166,0.14);
  border-radius:12px; padding:26px 30px; }}
.md-wrap h1 {{ font-size:22px; color:{COLORS['text']}; margin:0 0 4px; }}
.md-wrap h2 {{ font-size:15px; color:{COLORS['teal']}; text-transform:uppercase;
  letter-spacing:.9px; margin:26px 0 8px; }}
.md-wrap h3 {{ font-size:13px; color:{COLORS['text']}; margin:18px 0 6px; }}
.md-wrap p, .md-wrap li {{ font-size:12.5px; line-height:1.65; color:{COLORS['muted']}; }}
.md-wrap strong {{ color:{COLORS['text']}; }}
.md-wrap code {{ font:600 11.5px ui-monospace,monospace; background:#0e1626;
  border:1px solid rgba(138,148,166,0.18); border-radius:4px; padding:1px 5px;
  color:{COLORS['teal']}; }}
.md-wrap pre {{ background:#0b1322; border:1px solid rgba(138,148,166,0.18);
  border-radius:8px; padding:11px 13px; overflow-x:auto; }}
.md-wrap table {{ width:100%; border-collapse:collapse; font-size:11.5px; margin:10px 0;
  display:block; overflow-x:auto; }}
.md-wrap th {{ text-align:left; font:700 9px ui-monospace,monospace; letter-spacing:.8px;
  text-transform:uppercase; color:{COLORS['muted']}; padding:7px 9px;
  border-bottom:1px solid rgba(138,148,166,0.24); white-space:nowrap; }}
.md-wrap td {{ padding:7px 9px; border-bottom:1px solid rgba(138,148,166,0.08);
  color:{COLORS['muted']}; }}
.md-wrap hr {{ border:0; border-top:1px solid rgba(138,148,166,0.14); margin:22px 0; }}
.md-wrap a {{ color:{COLORS['teal']}; }}
.mth-bar {{ display:flex; align-items:center; gap:12px; padding:11px 16px; background:#0a1020;
  border:1px solid rgba(138,148,166,0.18); border-radius:12px; margin-bottom:12px;
  font:600 12px/1 ui-monospace,monospace; color:{COLORS['text']}; }}
.mth-bar .tag {{ color:{COLORS['teal']}; background:rgba(0,212,180,.12);
  border:1px solid rgba(0,212,180,.34); padding:4px 8px; border-radius:5px; font-size:10px;
  letter-spacing:.6px; }}
"""

pn.extension(raw_css=[CSS], sizing_mode="stretch_width")


def build_app() -> pn.viewable.Viewable:
    if DOC.exists():
        body = pn.pane.Markdown(DOC.read_text(encoding="utf-8"),
                                extensions=["tables", "fenced_code"],
                                css_classes=["md-wrap"], sizing_mode="stretch_width")
    else:  # a deploy shipping code without docs/ should say so, not render blank
        body = pn.pane.HTML(
            f"<div class='md-wrap'>METHODOLOGY.md not found at <code>{DOC}</code>.</div>")
    bar = pn.pane.HTML(
        "<div class='mth-bar'><span style='color:#00d4b4'>← DESK</span>"
        "<span>METHODOLOGY</span><span class='tag'>WEIGHTS · THRESHOLDS · LIMITS</span>"
        "</div>")
    return pn.Column(
        bar, body,
        styles={"background": COLORS["bg"], "padding": "22px", "min-height": "100vh",
                "max-width": "1000px", "margin": "0 auto"},
        sizing_mode="stretch_width")


build_app().servable(title="Methodology — ENSO Macro Risk Desk")
