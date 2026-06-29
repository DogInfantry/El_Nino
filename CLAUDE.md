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
causally real vs. spurious."* Moat = causal rigor (Granger+CCM; cocoa & wheat
deliberately FAIL = the misattribution guard). Real audience = recruiters for
commodity/climate-risk/energy-transition research. **Implication: DESCRIBE → PRESCRIBE**
— every region/commodity should end in a positioning view (constructive/cautious/watch
+ swing catalyst + risk), not just data. See `memory/product-thesis.md`.

**Owner:** Anklesh Rawat — MBA, equity research background, Python/Streamlit
proficient, sector analysis (energy transition, metals, infrastructure).
Communication style: casual ("yooo dawgggg"). Wants sharp design rationale,
flagged data caveats, clear next-step guidance.

**Tech stack:**
- Python 3.12 (NOT 3.14 — see Gotchas)
- Panel 1.9.3 (HoloViz) — multi-page dashboard server
- Plotly 6.x — gauge, time series, fan chart, global map
- Altair 6.x — sector-impact heatmap (Vega pane in Panel)
- statsmodels — SARIMA + Granger causality
- PyTorch 2.x — LSTM forecaster
- xarray / netCDF4 — ERSSTv5 netCDF processing
- pandas, numpy, scipy — data layer
- kaleido, vl-convert-python — static PNG export (for CI verification)
- No Streamlit, no pydeck (see Gotchas), no pyEDM (see Gotchas)

**Run a page:**
```
.venv\Scripts\activate
panel serve dashboard/pages/01_enso_monitor.py --show
```

---

## Architecture

### Data pipeline (ingest → process → cache → dashboard)

```
NOAA CPC ASCII  ──► oni_fetcher.py      ──► data/cache/oni.parquet
NOAA CPC PDF    ──► advisory_fetcher.py ──► (runtime, no cache)
World Bank XLSX ──► pink_sheet.py       ──► data/cache/commodities.parquet
ERSSTv5 netCDF  ──► ersst_fetcher.py    ──► data/raw/ (gitignored, ~150 MB)
                                         ──► data/cache/sst_anomaly_grids.parquet
data/raw/ + ONI ──► roni_calculator.py  ──► data/cache/roni.parquet
oni.parquet     ──► enso_phase_labeler  ──► data/cache/enso_phases.parquet
enso_phases     ──► lag_correlator      ──► (computed on-demand in page 04)
oni + commod.   ──► granger_ccm         ──► (computed on-demand in page 05)

forecasting/baselines/arima_model.py ──► data/cache/arima_{forecast,backtest}.parquet
forecasting/ml_models/lstm_enso.py   ──► data/cache/lstm_{forecast,backtest}.parquet
forecasting/ensemble.py              ──► data/cache/forecasts_all.parquet
forecasting/verification/skill_metrics ──► data/cache/skill_all.parquet
```

All caches are tracked in git (small, reproducible snapshots). Raw files
(`data/raw/`) are gitignored. The dashboard reads caches only; fetchers are
run manually when refreshing data.

### Dashboard structure

Six Panel pages, each a standalone `.py` that calls `build_app().servable()`.
They share `dashboard/theme.py` (palette, Plotly dark layout, data loaders).
No entry-point `app.py` yet — pages served individually or via
`panel serve dashboard/pages/*.py --show` (not tested with glob on Windows,
use explicit file names or a manifest).

### Key design decisions

- **ONI primary, RONI overlay.** ONI from CPC ASCII (canonical, stable URL,
  updated ~5th of month). RONI is *computed* from ERSSTv5 in-repo because CPC
  has no clean machine feed. Fixed 1991–2020 base → approximate, not official.
- **SARIMA beats LSTM** on this short univariate ONI series — honest framing
  in the dashboard. Don't rig DL to win; frame as "LSTM needs ancillary indices
  / spatial SST (CNN track)."
- **CCM is self-coded** (numpy/scipy simplex projection), not pyEDM. pyEDM
  uses multiprocessing that recursively re-spawns on Windows outside
  `__main__` → crashes under the Panel server. Self-coded CCM is robust.
- **Granger uses detrend, not first-difference.** Differencing monthly data is
  a high-pass filter that kills the low-frequency ENSO signal → everything
  looks null. Linear detrend preserves ENSO-band coupling.
- **Map uses Plotly Scattergeo, not pydeck.** pydeck/deck.gl uses WebGL that
  can't be verified by kaleido screenshots in CI. Plotly is server-renderable.

---

## File Map

### Dashboard
| File | Role |
|------|------|
| `dashboard/theme.py` | Shared palette (`COLORS`), `plotly_dark_layout()`, `style_figure()`, data loaders (`load_oni`, `load_phases`, `load_commodities`, `CACHE_DIR`) |
| `dashboard/components/oni_gauge.py` | Plotly gauge for the Niño-3.4 reading |
| `dashboard/components/timeseries.py` | ONI time series with ENSO event shading + optional RONI secondary |
| `dashboard/components/globe_layer.py` | ERSSTv5 anomaly Scattergeo map with Niño-3.4 box and teleconnection zones |
| `dashboard/pages/00_landing.py` | **Landing — ENSO Macro Risk Desk.** The front door. `ENSO<GO>` command bar + ticker, left rail (compact gauge / ONI spark / Ensemble forecast cone), center `go.Choropleth` exposure map (signed by dry/wet), linked leaderboard, and the real-verdict causation strip (Granger+CCM, Option-A honest framing). Plotly/HTML only. |
| `dashboard/pages/01_enso_monitor.py` | **Page 1 — ENSO Monitor.** Live ONI/RONI stat cards, gauge, time series, advisory badge, CSV export. The visual MVP. |
| `dashboard/pages/02_global_map.py` | **Page 2 — Global Map.** ERSSTv5 anomaly globe, month slider (landmark peaks + latest), flat/orthographic toggle, teleconnection zones overlay. |
| `dashboard/pages/03_forecast.py` | **Page 3 — Forecast.** SARIMA/LSTM/Ensemble fan chart with CI bands, external-forecast reference markers, ACC-vs-lead skill chart. |
| `dashboard/pages/04_sector_impact.py` | **Page 4 — Sector Impact.** Altair heatmap of detrended Pearson r (ONI × log commodity price) at lags 0–24 months, ranked bar at chosen lag. |
| `dashboard/pages/05_causation.py` | **Page 5 — Causation Explorer.** Live Granger (-log10p by lag, both directions) + CCM (rho vs library size, both directions) for any commodity. Plain-language verdict. |
| `dashboard/pages/06_historical.py` | **Page 6 — Historical Events.** Per-event cards (El Niño/La Niña since 1950): peak ONI, RONI at peak, duration, intensity, post-event commodity moves (landmark events only), Callahan & Mankin 2023 economic losses. |

### Data ingestion
| File | Role |
|------|------|
| `data/ingest/_common.py` | Shared cache utilities (`cache_path`, `is_fresh`, `save_parquet`, `get_session`) |
| `data/ingest/oni_fetcher.py` | Fetches CPC ASCII ONI → `oni.parquet`. Fallback: CPC HTML table. |
| `data/ingest/advisory_fetcher.py` | Fetches live NOAA CPC/IRI ENSO Diagnostic Discussion PDF → parses status + synopsis |
| `data/ingest/ersst_fetcher.py` | Downloads ERSSTv5 netCDF (~150 MB, cached 30d), computes 1991–2020 anomalies for landmark months + latest → `sst_anomaly_grids.parquet` |
| `data/ingest/pink_sheet.py` | World Bank Pink Sheet XLSX → tidy `commodities.parquet`. Exposes `FOCUS_COMMODITIES` list. |
| `data/ingest/monsoon_fetcher.py` | **NEW (2026-06-28).** Fetches IMD 36-subdivision monthly rainfall CSV (github mirror of data.gov.in, 1901–2017) → all-India JJAS series → `monsoon_india.parquet` (year · jjas_mm · lpa_pct · category). Validated r=0.77 vs documented AISMR departures. |

### Data processing
| File | Role |
|------|------|
| `data/process/enso_phase_labeler.py` | Labels each ONI season (El Nino/La Nina/Neutral), applies 5-consecutive-season event definition, intensity tiers (Weak/Moderate/Strong/Very Strong), `event_summary()` → `enso_phases.parquet` |
| `data/process/lag_correlator.py` | `correlation_matrix(ONI, wide_prices, max_lag, do_detrend)` → tidy df of Pearson r; `peak_lags()` for sort order |
| `data/process/roni_calculator.py` | Computes RONI from ERSSTv5 (Niño-3.4 anom minus 20S–20N tropical-mean anom, 3-month running mean, fixed 1991–2020 base) → `roni.parquet` |
| `data/process/granger_ccm.py` | `analyze(ONI, series, maxlag, mode)` → dict with `granger_oni_to_target`, `granger_target_to_oni`, `ccm`. Self-coded CCM (`ccm_convergence`) via simplex projection. |
| `data/process/enso_flavor_iod.py` | **The India "depth" engine.** From ERSSTv5: ENSO flavor (Niño-3/4, EMI), IOD/DMI (SON peak). `scenario_outputs()`/`write_cache()` → `india_enso_iod.parquet` (grid), `india_regression.parquet` (OLS n=117), `india_years.parquet`. `powered()` prints. Needs `monsoon_india.parquet`. |
| `data/process/exposure_index.py` | **NEW (2026-06-29).** Constructed ENSO Exposure Index per country (`index=100*(0.5*C+0.5*E)`; C=computed peak |lagged ONI-commodity corr|, E=curated). → `exposure_index.parquet`. Drives the landing choropleth + leaderboard. |
| `data/process/landing_causation.py` | **NEW (2026-06-29).** Precomputes the landing's 6 ONI→commodity causal verdicts (live Granger+CCM) → `landing_ccm.parquet` (curves) + `landing_verdicts.parquet`. Real result: mostly WEAK (see Gotchas). |

### Forecasting
| File | Role |
|------|------|
| `forecasting/baselines/arima_model.py` | SARIMA(2,0,1)(1,0,0,12) walk-forward backtest + 12-month forward forecast with prediction intervals → `arima_{forecast,backtest}.parquet` |
| `forecasting/ml_models/lstm_enso.py` | PyTorch LSTM forecaster, same backtest framework → `lstm_{forecast,backtest}.parquet` |
| `forecasting/ensemble.py` | Combines SARIMA + LSTM → `forecasts_all.parquet`. Also merges skill scores → `skill_all.parquet` |
| `forecasting/verification/skill_metrics.py` | `acc()`, `rmse()`, `msss()`, `skill_by_lead()` — evaluation metrics |

### Other
| File | Role |
|------|------|
| `tests/test_core.py` | Unit tests for pure logic: phase labeling, detrend, lag correlation, CCM, skill metrics. No network required. Run: `python tests/test_core.py` |
| `requirements.txt` | Full pinned dependency list (Python 3.12) |
| `.gitignore` | Excludes `.venv/`, `data/raw/`, `.env`, `.cdsapirc`, `*.nc`, `_*.png`, `_*.html`, `.superpowers/` |
| `.env.example` | Template for ERA5/CDS credentials (Phase 2 optional) |
| `README.md` | Polished GitHub README with badges, per-page descriptions, FAQ, data-source table, known caveats |

### Caches (tracked in git)
`data/cache/`: `oni.parquet`, `enso_phases.parquet`, `commodities.parquet`,
`sst_anomaly_grids.parquet`, `roni.parquet`, `arima_forecast.parquet`,
`arima_backtest.parquet`, `lstm_forecast.parquet`, `lstm_backtest.parquet`,
`forecasts_all.parquet`, `skill_all.parquet`, `monsoon_india.parquet`,
`india_enso_iod.parquet`, `india_regression.parquet`, `india_years.parquet`,
`exposure_index.parquet`, `landing_ccm.parquet`, `landing_verdicts.parquet` (NEW 2026-06-28/29)

---

## Current State

### Fully done ✅
- **All 6 dashboard pages** — complete, polished, production-quality
- **Full data pipeline** — ONI, advisory, Pink Sheet commodities, ERSSTv5 grids, RONI
- **Forecasting engine** — SARIMA + LSTM + ensemble, verified against persistence
- **Causal inference** — Granger + self-coded CCM in page 05
- **RONI** — computed from ERSSTv5, dual ONI/RONI overlay on page 01
- **Historical event cards** — page 06 with landmark economic loss data
- **Tests** — 7 unit tests, all passing, no network deps
- **README** — SEO/AEO/LLMEO optimized, badges, FAQ
- **Git history** — 5 commits on `master` (latest: `ddd4b0f`)

### Built FOR REAL this session (2026-06-28/29) ✅
- **India deep-dive — `dashboard/pages/07_india.py`** — BUILT + verified (Plotly figures
  render). Climate tab = real **ENSO×IOD heatmap + OLS regression**; Economics = live
  Granger/CCM (sugar); History = computed SON-DMI 1997-vs-2015. Reads caches, not the netCDF.
- **Region template — `dashboard/region_template.py`** — generic shell (bar / DESK VIEW with
  CONSTRUCTIVE/WATCH/CAUTIOUS badges / map / KPI rail / live-Granger+CCM Economics / History)
  + a pluggable per-region Climate exhibit. India + SE Asia both build on it.
- **SE Asia — `dashboard/pages/08_seasia.py`** — 2nd region (palm oil), honest **WATCH**: its
  ENSO-phase composite FAILS the El-Niño-premium story (La Niña reads higher = a 1973-74
  macro-inflation artifact) → a SECOND misattribution example; weak live CCM confirms.
- **ENSO Exposure Index** (`exposure_index.py` → cache) + **landing causation precompute**
  (`landing_causation.py` → caches) — the landing's data layer is ready.

### Landing page — "ENSO Macro Risk Desk" v4 — BUILT + verified ✅ (2026-06-30)
`dashboard/pages/00_landing.py` — DONE. Reuses `oni_gauge.build_gauge` (compact) for the
left-rail gauge; Plotly for the ONI 24-mo sparkline + Ensemble 12-mo forecast cone
(`forecasts_all.parquet`); `go.Choropleth` exposure map (`exposure_index.parquet`, **signed z
— dry=coral / wet=blue / mixed=amber**, hover gives the unsigned index + C/E split); HTML
leaderboard (India & SE Asia rows hyperlink to the live `/07_india` · `/08_seasia` routes);
and the **causation strip** built from `landing_verdicts.parquet` + `landing_ccm.parquet`
inline-SVG mini-curves. **Causation-strip decision RESOLVED = Option A** (honest real
verdicts + reframed headline "most ENSO→commodity-PRICE trades don't survive causal testing";
NONE strongly causal, palm/wheat MODERATE, rest WEAK·confounded — the mockup's "cocoa & wheat
FAIL" was illustrative & wrong, never used). Plotly/HTML only, NO WebGL. Verified by importing
the module (runs `build_app()`) + kaleido PNG export of all 4 Plotly figs. Mockup ref:
`.superpowers/brainstorm/1954-1782430142/landing-risk-desk-v4.html`.
- **HF Spaces / Gradio deploy** — deferred. **EM-DAT bubbles** (page 02), **CCM surrogate
  significance**, **ERA5 CNN** — still planned. Other regions (Brazil/Australia/Peru/cocoa
  belt) = ~60-line config clones of `08_seasia.py`.

### Half-done / rough edges
- `panel serve dashboard/pages/*.py --show` glob may not work on Windows;
  pages must be served individually or with an explicit list
- The Granger caveat note in page 05 says "series are first-differenced" in
  the docstring header but the actual implementation uses `mode="detrend"` —
  minor doc inconsistency (the behavior is correct; the docstring is stale)

### Broken ❌
Nothing is broken. All caches are present; all pages load.

---

## Active Task

**Landing page is BUILT + committed (2026-06-30).** The causation-strip A/B/C decision is
**RESOLVED = Option A** (honest real verdicts + reframed headline). `00_landing.py` ties the
whole desk together: gauge + ONI spark + forecast cone (rail), exposure choropleth (center),
linked leaderboard (right), real-verdict causation strip (bottom). Verified via module import
+ kaleido PNG export. Product thesis locked: "ENSO Macro Risk Desk" — DESCRIBE → PRESCRIBE.

**No open blocker.** Next obvious moves (pick with the user): (1) add more region clones
(Brazil/coffee, Australia/wheat, Peru/floods sign="wet", cocoa belt) on `region_template.py`;
(2) optionally wire the choropleth/leaderboard country-click to actually navigate to 07/08
(currently the leaderboard rows are `<a href="/07_india">` links that work under
`panel serve`; the Plotly map itself is hover-only — a Panel click callback could route it);
(3) build a single `app.py` entry point / multi-page nav so the 7 pages serve as one site;
(4) push to GitHub (still no remote).

**Verify Panel pages** by importing the module (runs `build_*()`) + exporting Plotly figs to
PNG via kaleido — you CANNOT screenshot the live Bokeh server (websocket). Use
`PYTHONIOENCODING=utf-8` (Windows console chokes on −/ñ). The kaleido Timestamp gotcha bit
the landing too: a single-point marker trace must pass a Series slice (`x.iloc[[-1]]`), NOT a
list-wrapped scalar (`[x.iloc[-1]]`) — the latter is un-serializable under kaleido.

---

## Next Steps (ordered)

1. **Add more regions** — Brazil/coffee, Australia/wheat, Peru/floods (sign="wet"), cocoa
   belt — each a ~60-line config clone of `08_seasia.py` on `region_template.py`.
2. **Single entry point / nav** — `app.py` or a header nav so the 7 pages serve as one site;
   optionally make the landing choropleth click route to 07/08 (leaderboard rows already do).
3. **Wire India's illustrative tabs** — KPI rail + Agriculture crop bars need real crop/CPI
   ingestion (USDA/FAOSTAT). Climate/Economics/History are already real.
4. **Push to GitHub** — repo still has no remote. `git remote add origin ...` then push.
   README assumes a remote for badges.
5. **(Optional)** HF Spaces deploy · EM-DAT bubbles (page 02) · CCM surrogate significance.

---

## Gotchas

### Python version — use 3.12, not 3.14
System default is Python 3.14. Phase 2 stack (PyTorch, xarray, cartopy, pyEDM
equivalents) lacks wheels for 3.14, and HF Spaces runs 3.10–3.12.
Always activate `.venv` (Python 3.12) before running anything.

```
.venv\Scripts\activate
```

### Monsoon data + the ENSO×IOD engine (NEW 2026-06-28)
- All-India JJAS is computed in `monsoon_fetcher.py` as the **unweighted mean** of the
  IMD 36-subdivision JJAS totals (islands excluded). It correlates **r=0.77** with the
  official area-weighted AISMR departures — fine for conditioning, would tighten with
  area weighting (we have no subdivision areas, only lat/lon centroids).
- `enso_flavor_iod.py` reads the ERSST netCDF directly (same file/clim as RONI). Boxes are
  in **0–360 lon**. IOD must be measured at its **SON peak** (JJAS-mean blurs 1997 vs 2015).
  ENSO *flavor* (Niño4−Niño3 / EMI) is confounded with magnitude on a tiny sample — we
  computed it, found it inconclusive, and **dropped it** rather than over-claim.
- **Windows console can't print U+2212 (−) or ñ** under cp1252 → `UnicodeEncodeError`. Use
  ASCII labels in any `print`/`to_string`, or run with `PYTHONIOENCODING=utf-8`.

### ONI→commodity-PRICE causation is genuinely weak — render computed, not asserted (2026-06-29)
`landing_verdicts.parquet` found NONE of the 6 ONI→price links strongly CAUSAL (max CCM
ρ=0.32). Granger over-detects (palm sig=13/24) but CCM doesn't confirm. The v4 mockup's
"palm/robusta CAUSAL, cocoa & wheat FAIL" is ILLUSTRATIVE and factually wrong vs the data
(wheat is MODERATE, robusta WEAK). **Never hardcode the mockup verdicts** — always show the
computed one. The honest, on-moat story: the strong clean ENSO signal is on the climate/
production side (monsoon, MC drought — proven), not noisy monthly prices. This is the
misattribution guard, just more sweeping than the mockup. (Awaiting the user's A/B/C call.)

### ONI data source — CPC ASCII, not HDX CSV
Primary source: `https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt`
The HDX CSV mirror requires resolving per-resource UUIDs that change.
HTML table is the programmed fallback; both normalize to the same tidy schema.
CPC updates ~5th of each month.

### World Bank Pink Sheet is stale after 2024-12
The stable-UUID URL serves a snapshot ending **2024-12** ("Updated Jan 2025").
Fine for 1960–2024 correlation analysis. For live commodity prices, supplement
with the latest dated bulletin.

### No pyEDM — CCM is self-coded
pyEDM uses Python multiprocessing that recursively re-spawns worker processes
on Windows when the module is imported outside of `if __name__ == "__main__"`.
This crashes the Panel server. The CCM implementation in `granger_ccm.py` uses
numpy/scipy simplex projection and is robust under the server.

### Granger — detrend, do NOT first-difference
First-differencing monthly data is a high-pass filter that kills the
low-frequency (multi-month to multi-year) ENSO signal. Everything becomes
null. Use `mode="detrend"` (linear detrend) in `granger_ccm.analyze()`.
The stale docstring at the top of `granger_ccm.py` says "first-differenced" —
**ignore the docstring, the implementation is correct.**

### Plotly kaleido serialization
Lists containing `pd.Timestamp` scalars are not JSON-serializable under
kaleido (Bokeh live server tolerates them). Pass `datetime64` Series/arrays
or ISO strings into `vrect`, `annotations`, and traces. See `03_forecast.py`
for the pattern: `pd.DataFrame({"date": [last_date], ...})` where `last_date`
is a Timestamp — this works because kaleido serializes the DataFrame column,
not the scalar.

### Can't screenshot live Panel/Bokeh apps
The Panel dev server uses a persistent WebSocket → the browser never hits
`networkidle` → screenshot tools time out. To verify visuals:
- Export Plotly charts via kaleido → PNG
- Export Altair charts via vl-convert → PNG
- Do NOT try `playwright` / `selenium` against the live server in CI

### Map: Plotly Scattergeo, NOT pydeck
pydeck uses WebGL (deck.gl). WebGL can't be verified by headless screenshot
tools. Plotly Scattergeo is server-renderable. Both flat and orthographic
projections are already implemented in `globe_layer.py`.

### Commodity moves — landmark events ONLY
The `_commodity_moves()` function in `06_historical.py` is intentionally
gated on `LANDMARK_FACTS`. Showing post-event commodity moves for weak events
naively captures unrelated macro spikes (e.g. 2021–22 post-COVID supply chain)
and misattributes them to an ENSO signal. This is a deliberate design choice.

### RONI vs official RONI
This repo computes RONI from ERSSTv5 on a **fixed 1991–2020 base**. The
official NOAA RONI uses ONI's rolling 30-year base periods. The values
*approximate* (not reproduce) the official RONI. NOAA adopted RONI as the
official ENSO index on **16 Feb 2026**. Any new chart that uses the ENSO
index must be labelled appropriately (ONI or RONI).
Observable signal: ONI runs ~0.34°C warmer than RONI since 2015 (background
warming). The 2023–24 event is ≈0.6°C lower under RONI.

### SARIMA beats LSTM — be honest
SARIMA outperforms the small LSTM on this short univariate ONI series. Both
beat persistence at all 12 leads. Do NOT rig the DL model to look better.
Correct framing: "LSTM needs ancillary indices / spatial SST (CNN track)."

### Forecasting confidence horizon
Both models beat persistence at 1–12 leads. Skill (ACC) typically falls below
the "useful skill" 0.5 threshold around 6–8 months — the ENSO spring
predictability barrier. The fan chart shows the uncertainty bands; the model
spread vs CPC dynamical models is the real signal.

### Git state
5 commits on `master`. No remote configured (user deferred push).
`.gitignore` excludes `.claude/settings.local.json` but tracks
`.claude/launch.json`. Data caches (`data/cache/*.parquet`) are intentionally
tracked — they're small and let the dashboard run without re-fetching.
`CLAUDE.md` itself is currently untracked (commit it when convenient).

### Design mockups live in gitignored `.superpowers/brainstorm/`
The landing + India designs are HTML mockups (superpowers Visual Companion), NOT
repo source — they won't show in `git status`/`git ls-files`. Sessions:
- `1954-1782430142/` — landing-risk-desk v1→**v4** (v4 locked), `region-detail-india.html`
  (old India), impact-explorer/map explorations. **Its server (port 53853) is DEAD.**
- `363-1782522811/` — `region-india-research-note.html` (the new India). **Its server
  is LIVE at http://localhost:50963.** Brainstorm server serves the NEWEST .html in a
  session dir; it auto-exits after ~30 min idle (check `.server-info` / `.server-stopped`).

### jq is NOT installed on this machine
Bash hook/command one-liners that rely on `jq` silently no-op. Use PowerShell
(`ConvertFrom-Json`) or sed/grep for JSON parsing. (Bit us setting up the PreCompact hook.)

### Handoff / save-state system (global, set up 2026-06-27)
- `/handoff` command → `~/.claude/commands/handoff.md`: regenerates THIS file + writes a
  dated `handoff-<date>.md` into the project `memory/` dir. Run it on "save state".
- PreCompact hook in `~/.claude/settings.json` → `~/.claude/hooks/precompact-backup.ps1`
  copies the transcript to `~/.claude/handoff-backups/` before every compaction (raw
  safety net). If a compaction yields no backup file, open `/hooks` or restart to reload.
- Global protocol in `~/.claude/CLAUDE.md`. The "~50% proactive" trigger is best-effort
  only — there's no real context-% signal.
