"""Single entry point for the ENSO Macro Risk Desk — serves the landing at the
site ROOT ("/") with the other eight pages at their own routes.

`panel serve dashboard/pages/*.py` puts every app at /<stem> and shows a Bokeh
directory listing at "/". This launcher instead maps the landing to "/" so the
desk opens immediately (no intermediate index page), while keeping the exact
route names the landing links to (07_india, 08_seasia, ...).

Run locally:
    python app.py
Served in the HF Docker Space via the same module (see Dockerfile CMD).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import panel as pn

ROOT = Path(__file__).resolve().parent
PAGES = ROOT / "dashboard" / "pages"
for _p in (ROOT / "dashboard", ROOT / "dashboard" / "components",
           ROOT / "data" / "process", ROOT / "data" / "ingest"):
    sys.path.insert(0, str(_p))

# stem -> route slug ("" == site root). Order = nav order.
_ROUTE = {
    "00_landing": "",
    "01_enso_monitor": "01_enso_monitor",
    "02_global_map": "02_global_map",
    "03_forecast": "03_forecast",
    "04_sector_impact": "04_sector_impact",
    "05_causation": "05_causation",
    "06_historical": "06_historical",
    "07_india": "07_india",
    "08_seasia": "08_seasia",
}


def _factory(stem: str):
    """Return a per-session builder for a page file.

    The pages aren't uniform — most define ``build_app()`` but the region pages
    (07/08) end in ``build_region(...).servable(...)`` with no such function. So
    rather than import a symbol, we exec the file fresh per session (exactly what
    `panel serve <file>` does) and capture whatever object it marks ``.servable()``.
    """
    path = PAGES / f"{stem}.py"
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")

    def _build():
        captured: list = []
        orig = pn.viewable.Viewable.servable

        def _spy(self, *a, **k):  # record the served root, don't double-register
            captured.append(self)
            return self

        pn.viewable.Viewable.servable = _spy
        try:
            exec(code, {"__name__": "__main__", "__file__": str(path)})
        finally:
            pn.viewable.Viewable.servable = orig
        return captured[-1]

    return _build


def routes() -> dict:
    out = {}
    for stem, slug in _ROUTE.items():
        out[slug] = _factory(stem)
    return out


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5006"))
    origin = os.environ.get("WS_ORIGIN", f"localhost:{port}")
    pn.serve(
        routes(),
        address="0.0.0.0",
        port=port,
        websocket_origin=[o.strip() for o in origin.split(",")],
        show=False,
        title="ENSO Macro Risk Desk",
    )
