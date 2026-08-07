# CLAUDE.md — ENSO Intelligence Platform

This file is the complete working memory for any Claude session on this repo.
Read it before touching any file. Update it whenever state changes.

---

## Project

**Name:** ENSO Intelligence Platform (`El_Nino` repo)
**What it is:** A production-grade, GitHub-portfolio El Niño / ENSO interactive
intelligence dashboard. Target aesthetic: "Bloomberg-meets-climate-science
terminal." Not a plain Streamlit app — dark, data-dense, Bloomberg-quality.

**Product thesis (LOCKED 2026-06-28):** the **"ENSO Macro Risk Desk"** — for a
macro/commodity research analyst or climate-aware PM. Job: *"when the ENSO cycle
shifts, tell me what commodity & sector exposure to reposition, and which links are
causally real vs. spurious."* Moat = causal rigor (Granger+CCM). Real audience =
recruiters for commodity/climate-risk/energy-transition research. **Implication:
DESCRIBE → PRESCRIBE** — every region/commodity ends in a positioning view
(constructive/cautious/watch + swing catalyst + risk). See `memory/product-thesis.md`.

**Owner:** Anklesh Rawat — MBA, equity research background, Python/Streamlit
proficient, sector analysis (energy transition, metals, infrastructure).
Communication style: casual ("yooo dawgggg"). Wants sharp design rationale,
flagged data caveats, clear next-step guidance.

**COMMIT POLICY (hard rule):** every commit authored by **DogInfantry**, with
**no `Co-Authored-By: Claude` trailer** and no Claude attribution anywhere in the
message. This overrides the default harness behaviour. Verify after committing:
`git log -1 --format='%B' | grep -i claude` must find nothing.

**Tech stack:** Python 3.12 (NOT 3.14) · Panel 1.9.3 · Plotly 6.x · Altair 6.x ·
statsmodels · PyTorch 2.x · xarray/netCDF4 · imdlib · pandas/numpy/scipy ·
kaleido/vl-convert (static export). No Streamlit, no pydeck, no pyEDM.

**Run a page:**
```
.venv\Scripts\activate
panel serve dashboard/pages/01_enso_monitor.py --show
```

---

## Architecture

### Data pipeline (ingest → process → cache → dashboard)

```
NOAA CPC ASCII    ──► oni_fetcher.py       ──► oni.parquet
NOAA CPC weekly   ──► weekly_nino34.py     ──► weekly_nino34.parquet (+ live read)
NOAA CPC PDF      ──► advisory_fetcher.py  ──► (live at page load, never cached)
NOAA PSL indices  ──► climate_indices.py   ──► climate_indices.parquet
World Bank XLSX   ──► pink_sheet.py        ──► commodities.parquet
ERSSTv5 netCDF    ──► ersst_fetcher.py     ──► sst_anomaly_grids.parquet
IMD 0.25° grids   ──► imd_gridded.py       ──► monsoon_india_grid.parquet  (MANUAL, 3 GB)
data/raw/ + ONI   ──► roni_calculator.py   ──► roni.parquet
oni               ──► enso_phase_labeler   ──► enso_phases.parquet
oni + commodities ──► exposure_index.py    ──► exposure_index.parquet
oni + commodities ──► landing_causation.py ──► landing_{ccm,verdicts}.parquet
above + forecasts ──► positioning.py       ──► positioning.parquet
oni + indices     ──► analogs.py           ──► analogs.parquet
ERSST + IMD grid  ──► enso_flavor_iod.py   ──► india_{enso_iod,regression,years}.parquet

forecasting/baselines/arima_model.py    ──► arima_{forecast,backtest}.parquet
forecasting/ml_models/lstm_enso.py      ──► lstm_{forecast,backtest}.parquet
forecasting/ensemble.py                 ──► forecasts_all.parquet, skill_all.parquet
```

All caches are tracked in git (small, reproducible). Raw files (`data/raw/`, now
**3.1 GB**: ERSST netCDF + 124 IMD year-binaries) are gitignored. The dashboard reads
caches only.

### Key design decisions

- **ONI primary, RONI overlay.** ONI from CPC ASCII. RONI computed in-repo from
  ERSSTv5 (fixed 1991–2020 base) → approximate, not official.
- **SARIMA beats LSTM** on this short univariate series — framed honestly.
- **CCM is self-coded** (numpy/scipy simplex projection), not pyEDM (Windows
  multiprocessing re-spawn crashes the Panel server).
- **Granger uses detrend, not first-difference** (differencing kills the ENSO band).
- **Map uses Plotly Scattergeo, not pydeck** (WebGL is unverifiable headless).
- **Stances are computed, not typed** (`positioning.py`), gated by the causal verdict.
- **Freshness is measured net of structural label lag** (`source_registry.py`).
- **The methodology doc is the single source of truth**, rendered by page 09 and
  enforced against code by a test.

---

## File Map

### Dashboard
| File | Role |
|------|------|
| `dashboard/theme.py` | Palette (`COLORS`), `plotly_dark_layout()`, `style_figure()`, loaders (`load_oni`, `load_phases`, `load_commodities`, `CACHE_DIR`) |
| `dashboard/region_template.py` | Generic region shell. **`stance_from_cache()` / `_apply_stance()` overlay computed stances**; `_horizon_txt()` renders lag 0 as "contemporaneous" and lag 24 as "24 mo (window edge)" |
| `dashboard/components/oni_gauge.py` · `timeseries.py` · `globe_layer.py` | Gauge, ONI series + event shading, ERSST Scattergeo |
| `dashboard/pages/00_landing.py` | Landing — command bar, exposure choropleth, leaderboard, causation strip (Option A honest verdicts) |
| `dashboard/pages/01_enso_monitor.py` | ONI/RONI cards, gauge, series, advisory badge, weekly nowcast card |
| `dashboard/pages/02_global_map.py` | ERSST anomaly globe, month slider, flat/ortho toggle |
| `dashboard/pages/03_forecast.py` | Fan chart, skill-vs-lead, observed-vs-forecast nowcast, **analog panel** (`build_analog_chart`, `_analog_card`) |
| `dashboard/pages/04_sector_impact.py` | Altair lag heatmap, ranked bar |
| `dashboard/pages/05_causation.py` | Live Granger + CCM per commodity |
| `dashboard/pages/06_historical.py` | Per-event cards since 1950 |
| `dashboard/pages/07_india.py` | India deep-dive. **Reads n from `india_regression.parquet`** — never hard-code it again |
| `dashboard/pages/08_seasia.py` | SE Asia (palm oil); ENSO-phase composite = second misattribution example |
| `dashboard/pages/09_methodology.py` | **NEW.** Renders `docs/METHODOLOGY.md` directly (no second copy) |
| `dashboard/pages/10_status.py` | **NEW.** Source freshness table; leads with "Behind", not "Age" |

### Data ingestion
| File | Role |
|------|------|
| `data/ingest/_common.py` | `cache_path`, `is_fresh`, `save_parquet`, `get_session` |
| `data/ingest/oni_fetcher.py` | CPC ASCII ONI → `oni.parquet` |
| `data/ingest/advisory_fetcher.py` | Live CPC/IRI ENSO Diagnostic Discussion PDF |
| `data/ingest/ersst_fetcher.py` | ERSSTv5 netCDF → anomaly grids |
| `data/ingest/pink_sheet.py` | World Bank Pink Sheet → `commodities.parquet` |
| `data/ingest/weekly_nino34.py` | CPC **weekly** Niño-3.4; live read at page load, parquet fallback |
| `data/ingest/monsoon_fetcher.py` | IMD 36-subdivision monthly (1901–2017). Superseded for all-India; kept for provenance |
| `data/ingest/climate_indices.py` | **NEW.** NOAA PSL SOI / Niño1+2,3,4 / TNI / PDO / AMO / PNA / WP + long DMI. `coverage()` flags frozen upstreams; **`model_features()` drops them before any model** |
| `data/ingest/imd_gridded.py` | **NEW.** IMD 0.25° daily grids 1901–2024 → cos(lat) area-weighted JJAS. **MANUAL, ~3 GB.** `--offline` rebuilds from disk |
| `data/ingest/source_registry.py` | **NEW.** One `Source` row per feed; `status_table()` returns FRESH/AGING/STALE/LIVE/SNAPSHOT/STATIC/MISSING |

### Data processing
| File | Role |
|------|------|
| `data/process/enso_phase_labeler.py` | `simple_phase`, `classify_intensity`, `label_phases`, `event_summary` |
| `data/process/lag_correlator.py` | `lagged_cross_correlation` (signed r by lag), `correlation_matrix`, `peak_lags` |
| `data/process/roni_calculator.py` | RONI from ERSSTv5 |
| `data/process/granger_ccm.py` | `analyze()`, self-coded `ccm_convergence()` |
| `data/process/enso_flavor_iod.py` | India engine. **`_monsoon_series()` prefers the gridded cache, falls back to subdivisions** |
| `data/process/exposure_index.py` | `REGISTRY`, `EXPOSURE_VERSION`, `index=100*(0.5C+0.5E)` |
| `data/process/landing_causation.py` | Verdicts. Emits classes `causal` / `mod` / `weak` / `none` |
| `data/process/positioning.py` | **NEW.** Computed stances: signed peak-lag r × ENSO state, causal gate, conviction haircut, `OVERRIDES` |
| `data/process/analogs.py` | **NEW.** Nearest historical states (Euclidean, z-scored) + forward ONI paths |

### Other
| File | Role |
|------|------|
| `docs/METHODOLOGY.md` | **NEW.** Published weights, thresholds, limits, ISRO decision. Rendered by page 09, enforced by a test |
| `tests/test_core.py` | **17 tests**, no network |
| `app.py` | Entry point; `_ROUTE` maps 11 pages |
| `scripts/refresh_data.py` | Chains ingest→process in order; `DATE_CACHES` regression gate |
| `Dockerfile` · `requirements-space.txt` | HF Space (serve-only deps) |
| `requirements.txt` | Full deps incl. `imdlib==0.1.21` (offline only) |
| `web/` | Next.js 15 static front-door on Vercel |

---

## Current State

### Done and verified ✅
- **All 11 pages build**; 17 tests pass; deploy live and healthy.
- **Phase 1 — credibility layer:** computed positioning stances, source freshness
  registry, published methodology + doc-vs-code test.
- **Phase 2a/2c — signal layer:** 10 ancillary climate indices; analog engine +
  panel on page 03.
- **Phase 3 — India:** IMD 0.25° gridded rainfall 1901–2024, area-weighted;
  India engine rewired; sample size read from cache.
- **Deployed:** https://huggingface.co/spaces/DogInfantry/enso-macro-risk-desk
  (verified `RUNNING`, all routes 200, `docs/` present on the Space).

### Key analytical results as of 2026-08-07
- Regime: **WEAK EL NIÑO · 2026 · STRENGTHENING** (ONI +0.98 AMJ; weekly Niño-3.4
  +2.15 4-wk; SOI −4.00 → atmosphere coupled).
- **Stances flipped vs the old hand-typed ones:** India CONSTRUCTIVE→**WATCH**,
  SE Asia WATCH→**CAUTIOUS**. `r_peak` is negative for 10 of 11 registry rows.
- **Conviction haircut is ACTIVE** (observed−forecast = +1.01 °C > 1.0 tolerance).
- **Analogs are bimodal:** May/Jun 1997 and May 2023 → +2.0…+2.4 at +6mo;
  Sep/Oct 2006 → −0.1/−0.3. The +6mo mean of +1.27 describes none of them.
- **India IOD hedge holds at full sample:** n=124, Niño-3.4 −8.01 (p<1e-4),
  DMI +5.26 (**p=0.0037**), R²=0.35. At n=75 it was p=0.059 — the record length
  changed the conclusion.

### Not done ❌ / deliberately deferred
- **Phase 2b — LSTM exogenous channels.** Not started. Expensive (torch retrain +
  ensemble re-run because of the vintage guard) and may still lose to SARIMA.
- **Phase 4 — JSON API + MCP server.** Not started. `pn.serve(..., extra_patterns=)`
  is confirmed supported; plan is `dashboard/api.py` + one line in `app.py`.
- **README.md does not link `docs/METHODOLOGY.md`.**
- **IITM AISMR dropped** — TLS chain failure, see Gotchas.
- **BoM RMM/MJO dropped** — the Bureau blocks automated access, see Gotchas.

---

## Active Task

**NOTHING IN FLIGHT. Working tree clean.**

**3 commits are ahead of `origin/master` and NOT pushed:** `4d37cdb`, `ce0a372`,
`48be828` (all of Phase 3). Pushing triggers `deploy-hf.yml` → the Space rebuilds
itself. Phases 1 and 2 are already pushed and live (`3bbdf19`).

Everything else in the plan is optional and unstarted. The approved plan is at
`C:\Users\Anklesh\.claude\plans\i-came-across-https-github-com-koala73-w-shimmying-cocke.md`.

---

## Next Steps (ordered)

1. **Push Phase 3** — `git push origin master`. Then verify the Space (see Gotchas
   for why HTTP 200 is not proof).
2. **README.md** — link `docs/METHODOLOGY.md`, mention pages 09/10 and the analog panel.
3. **Phase 2b — LSTM exogenous channels.** Feed `climate_indices.model_features()`
   as extra input channels; add a `variant` column to `skill_all.parquet`; chart
   univariate vs multivariate on page 03. **If SARIMA still wins, say so.**
4. **Phase 4 — machine-readable surface.** `dashboard/api.py` Tornado handlers
   (`/api/state`, `/api/positioning`, `/api/exposure`, `/api/verdicts`,
   `/api/analogs`, `/api/sources`) + `mcp_server.py` (stdio, offline only).
5. **Optional:** more regions (Brazil/coffee, Australia/wheat, Peru/floods) as
   ~60-line clones of `08_seasia.py`; EM-DAT bubbles; CCM surrogate significance.

---

## Deployment

**Live:** https://huggingface.co/spaces/DogInfantry/enso-macro-risk-desk
(app host `doginfantry-enso-macro-risk-desk.hf.space`). Docker SDK, free `cpu-basic`.

- `app.py` serves the landing at `/` and 10 pages at route slugs.
- `.github/workflows/deploy-hf.yml` — push to `master` syncs `dashboard/`,
  `data/cache/`, `data/process/`, `data/ingest/`, **`docs/`**, `app.py`, `Dockerfile`,
  `requirements-space.txt` to the Space. Token = repo secret `HF_TOKEN`.
- `.github/workflows/refresh-data.yml` — 6th monthly; runs `scripts/refresh_data.py`,
  commits only if caches changed, then explicitly dispatches the deploy (a
  `GITHUB_TOKEN` push does not trigger other workflows).
- `.github/workflows/keepalive.yml` — 6-hourly ping.
- `web/` — Next.js static front-door on Vercel.

---

## Gotchas

### Commit authorship
Author **DogInfantry**, **never** a `Co-Authored-By: Claude` trailer. See the hard
rule under **Project**.

### GateGuard fact-forcing hook
Every first Write/Edit per file and the first Bash call demand a "facts" preamble
(importers, affected API, data schemas, verbatim user instruction) before the tool
runs. It is not a bug. Supply the facts and retry the identical call. `ECC_GATEGUARD=off`
disables it. **Batched edits partially apply** — if two edits are sent together, one
can land while the other is gated, leaving the file half-edited. Re-check before retrying.

### The ONI is labelled by its CENTER month — that is NOT staleness
A 3-month running mean stored under its centre month, so a current value looks ~2.5
months old. `source_registry.expected_lag_days` (75 for the ONI) exists precisely for
this. **The first cut of the freshness module reproduced the 2026-07-30 false alarm
inside the tool built to prevent it** — it called a current ONI STALE at 98 days.
Always measure lateness net of structural label lag.

### Frozen upstreams that still return HTTP 200
- CPC `wksst8110.for` — frozen at 2021-01-27. Only `wksst9120.for` is live.
- PSL `amon.us.data` (AMO) — frozen at 2023-01. `climate_indices.coverage()` flags
  anything >400 d behind the pack; **`model_features()` drops it at the source**.
- PSL `pdo.data` — ~11 months behind. Passes the frozen test but is the laggard, and
  because a state vector needs every feature it dragged the analog query back a year.
  **Deliberately excluded from `analogs.POINT_INDICES`.**

### Sources deliberately not used
- **Bureau of Meteorology (RMM/MJO)** — returns a block page: the Bureau "does not
  support web scraping… you should stop." Data owner declining; do not work around.
- **IITM AISMR** (`mol.tropmet.res.in`) — incomplete TLS chain that Python rejects and
  browsers silently repair. `verify=False` in a pipeline that commits unattended would
  admit unauthenticated data into the caches the causal work rests on. Dropped.
- **ISRO/MOSDAC/Bhoonidhi/IIRS** — INSAT-3D sits at 82°E, so its disk spans ~1°E–163°E
  and **physically cannot see Niño-3.4 (170°W–120°W)**. Impact-side instruments only.
  MOSDAC and Bhoonidhi are auth-gated scene archives. IIRS is a training institute.
  Full reasoning in `docs/METHODOLOGY.md`.

### Verdict class literals
`landing_causation._verdict()` emits `causal` / `mod` / `weak` / `none`. `positioning.py`
gates on `("causal", "mod")`. It originally tested for `"strong"`, which is never
emitted — a genuinely CAUSAL link would have been silently capped at WATCH. Covered by
a test now.

### pandas turns None into NaN in float columns
`status_table()` returns `None` ages for sources with no cache; pandas stores them as
`NaN`, so `is None` misses them and `int(NaN)` raises. Use `pd.isna()`.
Also: `df.sub` is the subtract **method** — `j.sub` silently returns a bound method
instead of a column. Use `df["sub"]`.

### Sample length can change a conclusion
The IMD grid was first pulled from 1950 on the reasoning that pre-1950 has no ONI to
pair with — but the India regression uses ERSST-derived Niño-3.4/DMI, which run to 1854.
At n=75 the IOD term read p=0.059 (marginal); at n=124 it is p=0.0037. **Check what a
cutoff actually costs the specific estimator before choosing it.**

### The gridded India series approximates, does not reproduce, official AISMR
1971–2020 normal 858.9 mm vs IMD's published ~868 (within 1.1%); r=0.945 vs the old
subdivision series. But 2009 reads −15.0% against a cited ~−22% — IMD weights its own
subdivisions rather than cos(lat) grid cells. **Never quote these as IMD's published
departures.** The old unweighted subdivision mean sat at ~1045 mm, ~20% too high — that
was the real cause of the r=0.77 caveat.

### Python version — 3.12, not 3.14
System default is 3.14, which lacks wheels for the Phase-2 stack. Always activate `.venv`.

### Windows console encoding
`UnicodeEncodeError` on `−`, `ñ`, `°` under cp1252. Always run with
`PYTHONIOENCODING=utf-8`.

### Verifying Panel pages
Import the module (that runs `build_app()` / `build_region`) and export figures via
kaleido. For the LIVE Space, `get_page_text`/curl return **empty** — Panel mounts into
shadow DOM; walk `shadowRoot`s via JS eval, and allow ~30 s after a deploy. **HTTP 200
is not proof**: page 09 returns 200 while rendering its "docs not found" fallback, so
also check `HfApi().list_repo_files(...)`.

### kaleido Timestamp serialization
A single-point marker trace must pass a Series slice (`x.iloc[[-1]]`), never a
list-wrapped scalar (`[x.iloc[-1]]`).

### Peak lags on the search boundary
`lagged_cross_correlation` searches lags 0–24. Cocoa and Arabica peak at exactly 24 —
the true peak may lie outside the window, so it must not be read as a horizon. Rendered
as "24 mo (window edge)"; lag 0 renders as "contemporaneous".

### Other standing gotchas
- World Bank Pink Sheet ends **2024-12** by decision (a two-source seam would risk the
  lag/Granger/CCM work that is the moat). Disclosed on page 04.
- Commodity moves on page 06 are gated to landmark events only.
- `git pull --rebase` before pushing: the monthly cron commits to `master` unattended.
- `.claude/data/` holds plugin sqlite scratch DBs — gitignored.
- **jq is NOT installed.** Use PowerShell `ConvertFrom-Json` or sed/grep.
- Design mockups live in gitignored `.superpowers/brainstorm/`.
