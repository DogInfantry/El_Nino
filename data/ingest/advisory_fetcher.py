"""Fetch the live NOAA CPC/IRI ENSO advisory synopsis at runtime.

Per project policy, the dashboard must NOT hardcode the current ENSO phase --
it reads the official advisory live. This module downloads the ENSO Diagnostic
Discussion PDF and extracts the one-line "synopsis" plus a coarse status label
(El Nino / La Nina / ENSO-neutral + Watch/Advisory if present).

Data source (free, no auth)
---------------------------
https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.pdf

Everything here degrades gracefully: any failure returns ``None`` so the UI can
fall back to a data-derived status rather than crash.
"""

from __future__ import annotations

import datetime as dt
import io
import logging
import re
from dataclasses import dataclass

from _common import get_session

logger = logging.getLogger(__name__)

ENSO_DISC_PDF = (
    "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/"
    "enso_advisory/ensodisc.pdf"
)

_STATUS_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"el\s*ni[nñ]o\s+advisory", "El Niño Advisory"),
    (r"el\s*ni[nñ]o\s+watch", "El Niño Watch"),
    (r"la\s*ni[nñ]a\s+advisory", "La Niña Advisory"),
    (r"la\s*ni[nñ]a\s+watch", "La Niña Watch"),
    (r"final\s+el\s*ni[nñ]o\s+advisory", "Final El Niño Advisory"),
    (r"final\s+la\s*ni[nñ]a\s+advisory", "Final La Niña Advisory"),
    (r"enso[-\s]*neutral", "ENSO-Neutral"),
)


@dataclass(slots=True)
class Advisory:
    """A parsed ENSO advisory."""

    status: str
    synopsis: str
    fetched_at: dt.datetime
    url: str = ENSO_DISC_PDF


def _extract_synopsis(text: str) -> str:
    """Pull the 'synopsis' sentence from the discussion text."""
    # The PDF typically contains "Synopsis: <one sentence>."
    m = re.search(r"synopsis\s*[:\-]?\s*(.+?)(?:\n\n|\.\s)", text, re.I | re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".") + "."
    # Fallback: first non-empty line mentioning El/La Nina or ENSO.
    for line in text.splitlines():
        if re.search(r"(el\s*ni|la\s*ni|enso)", line, re.I) and len(line) > 30:
            return re.sub(r"\s+", " ", line).strip()
    return ""


def _detect_status(text: str) -> str:
    for pattern, label in _STATUS_PATTERNS:
        if re.search(pattern, text, re.I):
            return label
    return "Unknown"


def get_advisory(timeout: float = 30.0) -> Advisory | None:
    """Return the current :class:`Advisory`, or ``None`` on any failure."""
    try:
        import pypdf

        resp = get_session().get(ENSO_DISC_PDF, timeout=timeout)
        resp.raise_for_status()
        reader = pypdf.PdfReader(io.BytesIO(resp.content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            logger.warning("Advisory PDF parsed but contained no text.")
            return None
        advisory = Advisory(
            status=_detect_status(text),
            synopsis=_extract_synopsis(text),
            fetched_at=dt.datetime.now(),
        )
        logger.info("Advisory: %s | %s", advisory.status, advisory.synopsis[:80])
        return advisory
    except Exception as exc:  # noqa: BLE001 - must never crash the dashboard
        logger.warning("Advisory fetch/parse failed: %s", exc)
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    adv = get_advisory()
    if adv is None:
        print("Advisory unavailable (see warnings).")
    else:
        print(f"Status   : {adv.status}")
        print(f"Synopsis : {adv.synopsis}")
        print(f"Fetched  : {adv.fetched_at:%Y-%m-%d %H:%M}")
