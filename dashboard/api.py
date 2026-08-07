"""Read-only JSON surface over the same caches the dashboard renders.

The desk's whole argument is that its numbers are computed and inspectable rather
than asserted. A dashboard only half-honours that: you can look at a stance, but you
cannot check it, diff it against last month, or pull it into a notebook. These
endpoints publish exactly what the pages read — same parquet, same version stamps —
so a reader can verify a claim without screenshotting a chart.

Deliberately read-only and unauthenticated. Every byte here is already public on the
rendered pages, and the caches are static files refreshed by a monthly cron, so there
is nothing to write and nothing to protect. There is no rate limiter either: the Space
runs on free cpu-basic and Panel's own WebSocket traffic dwarfs anything this serves.

Mounted by ``app.py`` via ``pn.serve(..., extra_patterns=api_patterns())``.

Routes
------
``/api``               index of endpoints
``/api/state``         current ENSO regime: newest ONI season, phase, weekly nowcast
``/api/positioning``   computed stances per registry row (the describe -> prescribe layer)
``/api/exposure``      ENSO Exposure Index per region/commodity
``/api/verdicts``      Granger + CCM causal verdicts
``/api/analogs``       nearest historical states and their forward ONI paths
``/api/sources``       per-feed freshness, net of structural label lag
``/api/skill``         forecast skill by lead
``/api/skill_variants`` paired LSTM skill, ONI-only vs ONI + exogenous indices
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from tornado.web import RequestHandler

API_VERSION = "api-1.0"
_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = _ROOT / "data" / "cache"


def _records(name: str) -> list[dict]:
    """Load a cache as plain JSON-able records.

    Round-tripping through pandas' own JSON writer rather than ``to_dict`` is not
    laziness for its own sake: it is what turns NaN into ``null`` and Timestamps into
    ISO-8601 without hand-written coercion per column. ``json.dumps`` would otherwise
    emit bare ``NaN``, which is invalid JSON that lenient clients accept silently and a
    strict parser rejects — the worst kind of bug to ship in a verification surface.
    """
    path = CACHE_DIR / name
    if not path.exists():
        raise FileNotFoundError(name)
    df = pd.read_parquet(path)
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _state() -> dict:
    """Current regime — the one call a client makes before deciding to make others."""
    oni = pd.read_parquet(CACHE_DIR / "oni.parquet").sort_values("date")
    last = oni.iloc[-1]
    out: dict = {
        "oni": {
            "date": last["date"].date().isoformat(),
            "season": last["season"],
            "value": round(float(last["oni"]), 2),
            # The ONI is a 3-month mean stored under its CENTRE month, so a fully
            # current value reads ~2.5 months old. Say so in the payload rather than
            # letting every client re-derive the same false-staleness alarm.
            "label_convention": "3-month running mean, stamped with its centre month",
        },
    }

    phases = pd.read_parquet(CACHE_DIR / "enso_phases.parquet").sort_values("date")
    p = phases.iloc[-1]
    out["phase"] = {
        "simple": p["phase_simple"],
        "event": p["phase_event"],
        "intensity": p["intensity"],
    }

    # regime / stance_version live on positioning, which is what actually gates the
    # prescriptive layer — read them from there rather than recomputing a second copy.
    pos = pd.read_parquet(CACHE_DIR / "positioning.parquet")
    if len(pos):
        out["regime"] = pos.iloc[0].get("regime")
        out["stance_version"] = pos.iloc[0].get("stance_version")
        out["stances_computed"] = int(len(pos))

    # The weekly Niño-3.4 is a DIFFERENT quantity from the ONI — one week of OISST, not
    # a 3-month mean — so it ships beside the ONI with that stated, never merged into it.
    wk = CACHE_DIR / "weekly_nino34.parquet"
    if wk.exists():
        w = pd.read_parquet(wk)
        if len(w):
            row = json.loads(w.tail(1).to_json(orient="records", date_format="iso"))[0]
            row["note"] = (
                "single week of OISST, not a 3-month mean - do not read against the "
                "ONI's +/-0.5 degC event thresholds"
            )
            out["weekly_nino34"] = row
    return out


def _sources() -> list[dict]:
    sys.path.insert(0, str(_ROOT / "data" / "ingest"))
    from source_registry import status_table

    df = status_table()
    return json.loads(df.reset_index().to_json(orient="records", date_format="iso"))


# route suffix -> (loader, one-line description for the index)
LOADERS: dict[str, tuple] = {
    "state": (_state, "Current ENSO regime, phase, and weekly nowcast"),
    "positioning": (
        lambda: _records("positioning.parquet"),
        "Computed positioning stances, gated by the causal verdict",
    ),
    "exposure": (
        lambda: _records("exposure_index.parquet"),
        "ENSO Exposure Index per region/commodity",
    ),
    "verdicts": (
        lambda: _records("landing_verdicts.parquet"),
        "Granger + CCM causal verdicts per commodity",
    ),
    "analogs": (
        lambda: _records("analogs.parquet"),
        "Nearest historical ENSO states and their forward ONI paths",
    ),
    "sources": (_sources, "Per-feed freshness, measured net of structural label lag"),
    "skill": (
        lambda: _records("skill_all.parquet"),
        "Forecast skill by lead, verified against persistence",
    ),
    "skill_variants": (
        lambda: _records("skill_variants.parquet"),
        "Paired LSTM skill: ONI-only vs ONI + 7 exogenous indices",
    ),
}


class _JSONHandler(RequestHandler):
    """One handler for every endpoint; the route suffix selects the loader."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json; charset=utf-8")
        # The Vercel front-door is a different origin, and everything served here is
        # already public on the rendered pages.
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self, endpoint: str = "") -> None:
        endpoint = (endpoint or "").strip("/")
        if not endpoint:
            self._write(
                {
                    "service": "ENSO Macro Risk Desk",
                    "api_version": API_VERSION,
                    "endpoints": {
                        f"/api/{k}": desc for k, (_fn, desc) in LOADERS.items()
                    },
                }
            )
            return

        entry = LOADERS.get(endpoint)
        if entry is None:
            self.set_status(404)
            self._write({"error": f"unknown endpoint '{endpoint}'", "see": "/api"})
            return

        try:
            data = entry[0]()
        except FileNotFoundError as exc:
            # A cache that has not been built yet is an operational state, not a bug.
            # 503 says "ask again after the next refresh"; 500 would say "this is broken".
            self.set_status(503)
            self._write(
                {"error": f"cache '{exc}' not built", "hint": "run scripts/refresh_data.py"}
            )
            return

        self._write(
            {
                "api_version": API_VERSION,
                "endpoint": endpoint,
                "count": len(data) if isinstance(data, list) else 1,
                "data": data,
            }
        )

    def _write(self, payload: dict) -> None:
        # allow_nan=False so an unsanitized NaN fails here, loudly, instead of being
        # emitted as invalid JSON that a lenient client silently accepts.
        self.write(json.dumps(payload, allow_nan=False, indent=2))


def api_patterns() -> list[tuple]:
    """Tornado URL patterns to hand to ``pn.serve(extra_patterns=...)``."""
    return [(r"/api/?", _JSONHandler), (r"/api/([a-z_]+)/?", _JSONHandler)]
