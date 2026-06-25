<a name="top"></a>

<div align="center">

# 🌊 ENSO Intelligence Platform

**A Bloomberg-meets-climate-science terminal for El Niño / La Niña monitoring, forecasting, and economic impact analysis.**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3120/)
[![Panel](https://img.shields.io/badge/Dashboard-HoloViz%20Panel-purple)](https://panel.holoviz.org/)
[![Plotly](https://img.shields.io/badge/Viz-Plotly%206-3F4F75?logo=plotly)](https://plotly.com/)
[![PyTorch](https://img.shields.io/badge/ML-PyTorch%20LSTM-EE4C2C?logo=pytorch)](https://pytorch.org/)
[![Data: NOAA](https://img.shields.io/badge/Data-NOAA%20CPC-00559B)](https://www.cpc.ncep.noaa.gov/)
[![Data: World Bank](https://img.shields.io/badge/Data-World%20Bank-009FDA)](https://www.worldbank.org/en/research/commodity-markets)
[![License: Research](https://img.shields.io/badge/License-Research%20%26%20Educational-green)](#license--attribution)

**[Features](#-features-at-a-glance) · [Quickstart](#-quickstart) · [6 Dashboard Pages](#-the-6-dashboard-pages) · [Methodology](#-forecasting--causation-methodology) · [Data Sources](#-data-sources) · [Roadmap](#️-roadmap) · [FAQ](#-faq)**

</div>

---

## What is the ENSO Intelligence Platform?

The **ENSO Intelligence Platform** is a production-grade, open-source Python dashboard for monitoring, forecasting, and mapping the economic and agricultural consequences of **El Niño–Southern Oscillation (ENSO)** events.

It ingests canonical ENSO indices directly from **NOAA CPC**, **ERSSTv5 sea-surface temperature grids**, and the **World Bank Pink Sheet** commodity database. It then runs a dual-model forecasting engine (SARIMA + PyTorch LSTM) and a causal-inference engine (Granger + Convergent Cross Mapping) across six interactive dashboard pages — all in a dark terminal-style UI with no API keys required to start.

> **Who it is for:** climate researchers, commodity analysts, agricultural economists, finance professionals tracking ENSO-driven supply shocks, and data science portfolio reviewers.

---

## ✨ Features at a Glance

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Live ONI + RONI Monitor** | Dual-index time series from 1950–present; real-time NOAA advisory fetched at runtime |
| 2 | **Global SST Anomaly Map** | ERSSTv5 2°×2° grids rendered as flat + orthographic globe via Plotly Scattergeo |
| 3 | **12-Month Ensemble Forecast** | SARIMA baseline + LSTM fan chart; walk-forward backtested vs. persistence |
| 4 | **Sector Impact Heatmap** | Detrended lag-correlations between ONI and 71 World Bank commodities |
| 5 | **Causation Explorer** | Granger (linear) + Convergent Cross Mapping (nonlinear) — ONI vs. commodity series |
| 6 | **Historical Event Cards** | Per-event cards: peak ONI/RONI, Callahan & Mankin 2023 cost estimates, commodity moves |

**916 ENSO seasons · 42 events detected · 71 commodities · 2°×2° global SST grids from 1854 · 12-month forecast horizon · zero API keys required**

---

## 📊 Status

**Phase 1 MVP + core Phase 2 (forecasting & causation) — complete and verified against live data.**

| Capability | Module | Status |
|:-----------|:-------|:-------|
| ONI ingestion (1950–present) | `data/ingest/oni_fetcher.py` | ✅ live — 916 seasons |
| Commodity prices (1960–present) | `data/ingest/pink_sheet.py` | ✅ live — 71 commodities |
| Live ENSO advisory (PDF parse) | `data/ingest/advisory_fetcher.py` | ✅ live at runtime |
| ENSO phase / event labeling | `data/process/enso_phase_labeler.py` | ✅ 42 events detected |
| RONI (Relative ONI) | `data/process/roni_calculator.py` | ✅ computed from ERSSTv5 |
| Lagged cross-correlation engine | `data/process/lag_correlator.py` | ✅ |
| SARIMA baseline + backtest | `forecasting/baselines/arima_model.py` | ✅ beats persistence 12/12 leads |
| LSTM forecaster | `forecasting/ml_models/lstm_enso.py` | ✅ PyTorch, same harness |
| Skill verification (ACC / RMSE / MSSS) | `forecasting/verification/skill_metrics.py` | ✅ vs. persistence |
| Ensemble | `forecasting/ensemble.py` | ✅ model averaging |
| Granger + CCM causation engine | `data/process/granger_ccm.py` | ✅ self-contained CCM |
| ERSSTv5 SST-anomaly grids | `data/ingest/ersst_fetcher.py` | ✅ 2°×2° from 1854 |
| **01 ENSO Monitor** | `dashboard/pages/01_enso_monitor.py` | ✅ ONI/RONI dual series |
| **02 Global SST Map** | `dashboard/pages/02_global_map.py` | ✅ flat + orthographic globe |
| **03 Forecast** | `dashboard/pages/03_forecast.py` | ✅ fan chart + ensemble |
| **04 Sector Impact** | `dashboard/pages/04_sector_impact.py` | ✅ |
| **05 Causation Explorer** | `dashboard/pages/05_causation.py` | ✅ |
| **06 Historical Events** | `dashboard/pages/06_historical.py` | ✅ event cards + cost |

Remaining Phase 2 items (HF Spaces deployment, EM-DAT bubbles, ERA5 CNN) — see [Roadmap](#️-roadmap).

---

## 🚀 Quickstart

**Requires Python 3.12** — chosen for Hugging Face Spaces deploy parity; the ML/geo stack (PyTorch, xarray, netCDF4) lacks wheels on newer builds.

```bash
# 1 — Create and activate the virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 2 — Install dependencies
pip install -r requirements.txt

# 3 — Pull live data into data/cache/*.parquet
python data/ingest/oni_fetcher.py -v
python data/ingest/pink_sheet.py -v
python data/process/enso_phase_labeler.py -v

# 4 — Launch any dashboard page
panel serve dashboard/pages/01_enso_monitor.py --show
panel serve dashboard/pages/04_sector_impact.py --show
```

**No API keys required** for any Phase 1 or Phase 2 module. Every data source is free and publicly accessible.

---

## 🖥️ The 6 Dashboard Pages

### Page 01 — ENSO Monitor
**Live ONI and RONI time series from 1950–present.** The monitor fetches the canonical NOAA CPC ONI ASCII feed at runtime and computes RONI from ERSSTv5 grids (subtracting the tropical-mean SST to remove background warming). The dual-index view exposes the ~0.34 °C warming divergence between ONI and RONI since 2015. Current ENSO phase, event classification, and the live NOAA advisory text are all displayed.

### Page 02 — Global SST Anomaly Map
**ERSSTv5 2°×2° sea-surface temperature anomaly grids rendered on a flat and orthographic globe.** Teleconnection overlays mark the canonical ENSO-driven precipitation and temperature response regions (Walker Circulation suppression zone, PNA/NAM/PDO boxes). Built with Plotly Scattergeo — no basemap token, server-renderable.

### Page 03 — 12-Month Ensemble Forecast
**Fan chart showing the SARIMA + LSTM ensemble spread to 12 lead months.** Models are walk-forward backtested and scored against a persistence reference using Anomaly Correlation Coefficient (ACC), Root Mean Square Skill Score (MSSS), and RMSE. Skill drops below the ACC = 0.5 useful-skill threshold at 6–8 months, consistent with the ENSO spring predictability barrier.

### Page 04 — Sector Impact Heatmap
**Detrended Pearson lag-correlations between ONI and 71 World Bank Pink Sheet commodity prices,** at lags 0–24 months. Agricultural commodities (wheat, maize, rice, coffee, cocoa) dominate the signal; energy correlations are weaker and lag-sensitive. Raw correlations only — causal direction is tested on Page 05.

### Page 05 — Causation Explorer
**Granger causality (linear) and Convergent Cross Mapping / CCM (nonlinear) on detrended ONI vs. commodity series.** CCM is the more discriminating test: genuine causation shows cross-map skill that rises and converges with library size in one direction only (e.g. ONI → wheat converges while wheat → ONI collapses). CCM is implemented in-repo via simplex projection — no pyEDM dependency.

### Page 06 — Historical Event Cards
**Per-event cards for all 42 ENSO events since 1950.** Landmark events include peak ONI/RONI (illustrating reclassification), Callahan & Mankin 2023 GDP cost estimates in 2023 USD, and observed commodity price moves. Non-landmark events show classification data only, avoiding spurious attribution of macro-driven price spikes to weak ENSO signals.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — DATA INGESTION & PROCESSING                               │
│                                                                      │
│  data/ingest/          →   data/process/         →   data/cache/    │
│  oni_fetcher.py            enso_phase_labeler.py      *.parquet      │
│  pink_sheet.py             lag_correlator.py                         │
│  advisory_fetcher.py       roni_calculator.py                        │
│  ersst_fetcher.py          granger_ccm.py                            │
└────────────────────────────────┬────────────────────────────────────┘
                                  │  parquet / netCDF
┌────────────────────────────────▼────────────────────────────────────┐
│  LAYER 2 — FORECASTING ENGINE                                        │
│                                                                      │
│  forecasting/baselines/    arima_model.py   (SARIMA, statsmodels)    │
│  forecasting/ml_models/    lstm_enso.py     (PyTorch)                │
│  forecasting/verification/ skill_metrics.py (ACC / RMSE / MSSS)     │
│  forecasting/              ensemble.py      (model averaging)        │
└────────────────────────────────┬────────────────────────────────────┘
                                  │
┌────────────────────────────────▼────────────────────────────────────┐
│  LAYER 3 — VISUALIZATION DASHBOARD  (HoloViz Panel + Plotly)         │
│                                                                      │
│  01 ENSO Monitor   02 Global Map   03 Forecast                       │
│  04 Sector Impact  05 Causation    06 Historical Events              │
│  components/ — oni_gauge · timeseries · globe_layer                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 Forecasting & Causation Methodology

### Forecasting
Two models share an identical walk-forward verification harness and are scored against a **persistence reference** (last observed ONI held constant):

| Model | Type | Architecture | Result |
|-------|------|-------------|--------|
| **SARIMA** | Statistical | statsmodels SARIMAX | Beats persistence at all 12 leads ✅ |
| **LSTM** | Deep Learning | PyTorch, 2-layer, 64 hidden | Beats persistence at all 12 leads ✅ |

**Honest result:** SARIMA outperforms the LSTM on this short univariate ONI series. The LSTM needs ancillary climate indices or spatial SST fields (CNN track) to close the gap — framing it any other way would misrepresent the evidence.

Both models' skill (ACC) drops below the 0.5 useful-skill threshold at **6–8 months lead**, consistent with the well-documented ENSO spring predictability barrier.

### Causation
Two complementary tests run on **linearly detrended** (not differenced — differencing kills the low-frequency ENSO band) ONI vs. commodity series:

- **Granger causality** (linear): F-test across lags 0–24. Tests whether lagged ONI adds predictive power over lagged commodity values alone.
- **Convergent Cross Mapping (CCM)** (nonlinear): Simplex projection implemented in-repo using NumPy/SciPy — no pyEDM dependency (pyEDM's multiprocessing is incompatible with Panel's server on Windows). Genuine causation shows cross-map skill that rises and converges with library size in *one direction only*.

Surrogate (phase-randomized) significance testing is on the roadmap. Current verdicts are exploratory.

---

## 📚 Data Sources

| Source | Provider | Module | Requires Auth |
|:-------|:---------|:-------|:-------------|
| [ONI ASCII feed](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt) | NOAA CPC | `oni_fetcher.py` | None |
| [ONI HTML table](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php) | NOAA CPC | `oni_fetcher.py` (fallback) | None |
| [ENSO Diagnostic Discussion (PDF)](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.pdf) | NOAA CPC / IRI | `advisory_fetcher.py` | None |
| [Pink Sheet — historical monthly](https://www.worldbank.org/en/research/commodity-markets) | World Bank | `pink_sheet.py` | None |
| [ERSSTv5 netCDF grids](https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/netcdf/) | NOAA NCEI | `ersst_fetcher.py` | None |
| [ERA5 reanalysis](https://cds.climate.copernicus.eu/) | Copernicus CDS | *(Phase 2 roadmap)* | Free key |
| [USDA NASS](https://quickstats.nass.usda.gov) / [FAOSTAT](https://www.fao.org/faostat/) | USDA / FAO | *(Phase 2 roadmap)* | Free key / None |
| [EM-DAT disaster database](https://www.emdat.be/) | CRED / UCLouvain | *(Phase 2 roadmap)* | Account |

---

## ⚠️ Data Caveats & Known Limitations

Rigorous analysis requires disclosing limitations. Read this before drawing conclusions from the dashboard.

**1. ONI vs RONI.** Charts use **ONI** (3-month running mean Niño-3.4 SST anomaly, rolling 30-year base). On **16 Feb 2026 NOAA formally adopted RONI (Relative ONI)** — which subtracts the tropical-mean SST to remove long-term background warming — as the *official* ENSO index. Under RONI the 2023–24 El Niño is ~0.6 °C cooler, and some "neutral" periods reclassify. Every index chart is labeled; do not compare ONI- and RONI-classified events directly.

**2. The 3-month mean lags the raw Niño-3.4.** A weekly spike (e.g. +1.7 °C) can precede the smoothed ONI crossing the ±0.5 °C threshold by ~2 months. The monitor shows both views; the current phase is fetched live from the NOAA advisory and never hardcoded.

**3. Forecast spread is real.** CPC and independent model estimates can differ sharply (e.g. ~65% strong-El-Niño probability vs. ~37.5% in arXiv:2602.14773). The forecast page shows the ensemble range and external operational outlooks; model disagreement is never hidden.

**4. Correlation ≠ causation.** Sector correlations are detrended Pearson coefficients. Shared seasonality, the Indian Ocean Dipole (IOD), and the Madden–Julian Oscillation (MJO) can drive spurious co-movement. Causal direction requires Granger / CCM (Page 05).

**5. Teleconnections are probabilistic tendencies**, modulated by IOD and MJO. They are not deterministic.

**6. Source freshness / sunset risks:**
- The World Bank Pink Sheet currently serves a workbook ending **2024-12**; supplement recent months with the dated bulletin for live prices. Fetchers degrade gracefully to cached data.
- **CHIRPS v2** precipitation ends **Dec 2026** → planned migration to CHIRPS v3.
- The **IRI Data Library (IRIDL)** was sunset ~Apr 2026; NOAA PSL is the fallback.

---

## 🗂️ Project Structure

```
El_Nino/
├── data/
│   ├── ingest/        oni_fetcher · pink_sheet · advisory_fetcher · ersst_fetcher · _common
│   ├── process/       enso_phase_labeler · lag_correlator · granger_ccm · roni_calculator
│   ├── raw/           ERSSTv5 netCDF files (gitignored, ~150 MB)
│   └── cache/         oni · commodities · enso_phases · sst_anomaly_grids
├── forecasting/
│   ├── baselines/     arima_model.py
│   ├── ml_models/     lstm_enso.py
│   ├── verification/  skill_metrics.py
│   └── ensemble.py
├── dashboard/
│   ├── theme.py       dark terminal palette · Plotly template · cache loaders
│   ├── components/    oni_gauge · timeseries · globe_layer
│   └── pages/         01 · 02 · 03 · 04 · 05 · 06
├── tests/
│   └── test_core.py
├── requirements.txt
└── README.md
```

---

## 🎨 Design System

Dark "terminal" theme — inspired by Bloomberg Terminal and climate-science dashboards.

| Token | Value | Use |
|-------|-------|-----|
| Background | `#0a0e1a` | Page / app shell |
| Surface | `#141929` | Cards, panels |
| El Niño | `#f4623a` | Warm-phase indicators |
| La Niña | `#3a9af4` | Cool-phase indicators |
| Neutral | `#8a94a6` | Neutral-phase, muted text |
| Highlight teal | `#00d4b4` | Accents, active selections |
| Primary text | `#e8edf5` | Body copy |

All modules are Black-formatted, fully type-hinted, and include data-source citations in every docstring.

---

## 🛣️ Roadmap

### Phase 2 — Remaining (all optional)

- [ ] **Hugging Face Spaces deployment** — Gradio forecast demo on the free tier
- [ ] **EM-DAT disaster bubbles** — animated time-lapse of disaster events on the global map
- [ ] **ERA5 CNN (Ham 2019 reproduction)** — spatial SST → 12-month ENSO lead time using PyTorch CNN
- [ ] **Surrogate significance** — phase-randomized null distribution for causation verdicts
- [ ] **climpred gridded skill verification** — ensemble skill maps for the CNN forecasts

---

## ❓ FAQ

<details>
<summary><strong>What is ENSO, and why does it matter for commodity markets?</strong></summary>

ENSO (El Niño–Southern Oscillation) is the dominant year-to-year driver of global climate variability. **El Niño** (warm phase, ONI ≥ +0.5 °C) suppresses rainfall in Southeast Asia and Australia while enhancing it along the West Coast of South America. **La Niña** (cool phase, ONI ≤ −0.5 °C) reverses those patterns. Because ENSO disrupts precipitation in the world's key agricultural zones, it is directly linked to price shocks in wheat, maize, rice, coffee, cocoa, and palm oil — typically with a 3–9 month lag from the SST anomaly peak.

</details>

<details>
<summary><strong>What is the difference between ONI and RONI?</strong></summary>

**ONI (Oceanic Niño Index)** is the 3-month running mean of sea-surface temperature (SST) anomalies in the Niño-3.4 region (5°N–5°S, 170°W–120°W), computed against a rolling 30-year climatological base. **RONI (Relative ONI)** subtracts the tropical-mean (20°S–20°N) SST anomaly from the Niño-3.4 anomaly, removing the long-term warming trend that increasingly inflates ONI. NOAA adopted RONI as the official ENSO classification index in February 2026. Under RONI the 2023–24 El Niño is approximately 0.6 °C weaker than under ONI.

</details>

<details>
<summary><strong>What is Convergent Cross Mapping (CCM)?</strong></summary>

Convergent Cross Mapping (CCM) is a nonlinear causal-inference method for dynamical systems (Sugihara et al., *Science*, 2012). It tests whether variable X causally drives variable Y by checking whether Y's attractor manifold can be used to recover the state of X — and whether that cross-map skill *converges* (increases) as the library of observations grows. Unlike Granger causality, CCM does not assume linear dynamics and is robust to the kind of low-dimensional, nonlinear coupling found in climate–economy interactions. This project implements CCM in-repo via simplex projection (NumPy/SciPy), without pyEDM, for Windows / Panel server compatibility.

</details>

<details>
<summary><strong>Why does SARIMA outperform the LSTM?</strong></summary>

SARIMA outperforms the small LSTM on the univariate ONI series because ONI is a short (~70 years / 916 monthly values) quasi-periodic signal that SARIMA can exploit directly through its seasonal AR structure. The LSTM, without ancillary climate indices (IOD, MJO, PDO) or spatial SST input (CNN track), has insufficient signal to overcome SARIMA's parsimony advantage at this data scale. This is an honest and common finding for short univariate climate series; the LSTM track becomes competitive only with richer multivariate input.

</details>

<details>
<summary><strong>Can I run this on macOS or Linux?</strong></summary>

Yes. Substitute `.venv\Scripts\activate` with `source .venv/bin/activate`. Everything else in the quickstart is cross-platform. The only Windows-specific workaround in the codebase is the avoidance of pyEDM (multiprocessing issues on Windows); the in-repo CCM implementation is fully cross-platform.

</details>

<details>
<summary><strong>How do I add my own commodity or climate index?</strong></summary>

1. Add a fetcher to `data/ingest/` that returns a tidy DataFrame with columns `date`, `value`, and `series_name`.
2. Register it in `data/process/lag_correlator.py` to compute lagged ONI correlations.
3. Optionally wire it into `data/process/granger_ccm.py` for causal testing.
4. The dashboard pages use the cache parquets — they will pick up the new series on the next `panel serve`.

</details>

---

## 📄 License & Attribution

Data © their respective providers: NOAA/NWS (ONI, advisory, ERSSTv5), World Bank (Pink Sheet), Copernicus/ECMWF (ERA5), USDA, FAO, CRED (EM-DAT).

Code and dashboard: research and educational use. Please cite the primary data sources when reusing outputs in any publication or report.

**Key reference:** Callahan, C. W. & Mankin, J. S. (2023). Persistent effect of El Niño on global economic growth. *Science*, 381, 789–793. DOI: 10.1126/science.adf0374

---

<div align="center">

Built with [HoloViz Panel](https://panel.holoviz.org/), [Plotly](https://plotly.com/), [PyTorch](https://pytorch.org/), [statsmodels](https://www.statsmodels.org/), and data from [NOAA CPC](https://www.cpc.ncep.noaa.gov/) and the [World Bank](https://www.worldbank.org/).

[Back to top](#top)

</div>
