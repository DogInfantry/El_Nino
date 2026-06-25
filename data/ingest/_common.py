"""Shared ingestion plumbing for the ENSO Intelligence Platform.

Centralizes the things every ``data/ingest`` fetcher needs: a retrying HTTP
session, project-relative cache paths, freshness checks, and a parquet writer.
Keeping these here means each fetcher stays focused on *parsing* its source,
not on boilerplate.

No external credentials are used or required by anything in this module.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# data/ingest/_common.py -> parents: [ingest, data, <project root>]
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
CACHE_DIR: Path = PROJECT_ROOT / "data" / "cache"

# A descriptive UA is polite to public agencies (NOAA, World Bank) and reduces
# the odds of being treated as an anonymous scraper.
USER_AGENT: str = (
    "enso-intelligence-platform/0.1 "
    "(+https://github.com/; research/portfolio; contact via repo)"
)


def get_session(
    *,
    total_retries: int = 4,
    backoff_factor: float = 0.6,
    timeout_status: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> requests.Session:
    """Return a :class:`requests.Session` with sane retry/backoff defaults.

    Public climate endpoints occasionally return 5xx or rate-limit; retrying
    with exponential backoff makes the fetchers resilient in CI and on flaky
    networks without hammering the source.
    """
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=timeout_status,
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def cache_path(filename: str) -> Path:
    """Resolve ``filename`` inside ``data/cache`` (created if missing)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / filename


def is_fresh(path: Path, max_age_days: float) -> bool:
    """True if ``path`` exists and is newer than ``max_age_days``.

    Used to skip network round-trips when a recent cache already exists.
    """
    if not path.exists():
        return False
    age = dt.datetime.now() - dt.datetime.fromtimestamp(path.stat().st_mtime)
    return age <= dt.timedelta(days=max_age_days)


def save_parquet(df: pd.DataFrame, path: Path) -> Path:
    """Write ``df`` to ``path`` as parquet (snappy), returning the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)
    return path
