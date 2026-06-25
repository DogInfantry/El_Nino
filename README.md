# 🌊 ENSO Intelligence Platform

> A production-grade open-source platform for **monitoring, forecasting, and mapping the economic and agricultural impact of El Niño / ENSO events.** Built with real NOAA / ERA5 / IRI data, ML forecasting (CNN / LSTM + ARIMA), and world-class interactive visualization.

This is not a weather app. It is a **Bloomberg-meets-climate-science terminal**: live ENSO indices, model-spread forecasting, lag-resolved causation analysis, and sector-impact mapping across commodities, agriculture, and disasters.

---

## ✨ Status

**Phase 1 (MVP) + core Phase 2 (forecasting & causation) — complete and verified against live data.**

| Capability | Module | Status |
| :--- | :--- | :--- |
| ONI ingestion (1950–present) | `data/ingest/oni_fetcher.py` | ✅ live (916 seasons) |
| Commodity prices (1960–present) | `data/ingest/pink_sheet.py` | ✅ live (71 commodities) |
| Live ENSO advisory (runtime) | `data/ingest/advisory_fetcher.py` | ✅ live PDF parse |
| ENSO phase / event labeling | `data/process/enso_phase_labeler.py` | ✅ 42 events detected |
| Lagged cross-correlation engine | `data/process/lag_correlator.py` | ✅ |
| **SARIMA baseline + backtest** | `forecasting/baselines/arima_model.py` | ✅ beats persistence 12/12 leads |
| **LSTM forecaster** | `forecasting/ml_models/lstm_enso.py` | ✅ PyTorch, same harness |
| **Skill verification (ACC/RMSE/MSSS)** | `forecasting/verification/skill_metrics.py` | ✅ vs persistence |
| **Ensemble** | `forecasting/ensemble.py` | ✅ model averaging |
| **Granger + CCM causation engine** | `data/process/granger_ccm.py` | ✅ self-contained CCM |
| **ERSSTv5 SST-anomaly grids** | `data/ingest/ersst_fetcher.py` | ✅ live (2°×2°, 1854–present) |
| **ENSO Monitor** dashboard | `dashboard/pages/01_enso_monitor.py` | ✅ |
| **Global Map** dashboard (SST + teleconnections) | `dashboard/pages/02_global_map.py` | ✅ flat + globe |
| **Forecast** dashboard (fan chart) | `dashboard/pages/03_forecast.py` | ✅ |
| **Sector Impact** dashboard | `dashboard/pages/04_sector_impact.py` | ✅ |
| **Causation Explorer** dashboard | `dashboard/pages/05_causation.py` | ✅ |

Remaining Phase 2 (HF Spaces deployment, EM-DAT bubbles, surrogate significance) — see [Roadmap](#-roadmap).

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — DATA INGESTION & PROCESSING                           │
│                                                                  │
│   data/ingest/        →   data/process/        →   data/cache/   │
│   oni_fetcher          enso_phase_labeler          *.parquet     │
│   pink_sheet           lag_correlator                            │
│   advisory_fetcher     (granger_ccm, teleconn. — Phase 2)        │
└───────────────────────────────┬─────────────────────────────────┘
                                 │  parquet
┌───────────────────────────────▼─────────────────────────────────┐
│  LAYER 2 — FORECASTING ENGINE  (Phase 2)                         │
│   baselines/ (ARIMA, Prophet) · ml_models/ (LSTM, CNN, XGB)      │
│   verification/ (climpred: ACC, RMSE, MSSS) · ensemble.py        │
└───────────────────────────────┬─────────────────────────────────┘
                                 │
┌───────────────────────────────▼─────────────────────────────────┐
│  LAYER 3 — VISUALIZATION DASHBOARD  (HoloViz Panel)              │
│   01 ENSO Monitor ✅   02 Global Map    03 Forecast              │
│   04 Sector Impact ✅  05 Causation     06 Historical            │
│   components/ — oni_gauge ✅, timeseries ✅, globe, waterfall     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

**Requires Python 3.12** (matches Hugging Face Spaces; the Phase 2 ML/geo stack
lacks wheels on very new Python builds).

```bash
# 1. Environment
py -3.12 -m venv .venv
.venv\Scripts\activate              # Windows  (source .venv/bin/activate on *nix)
pip install -r requirements.txt

# 2. Pull live data → data/cache/*.parquet
python data/ingest/oni_fetcher.py -v
python data/ingest/pink_sheet.py -v
python data/process/enso_phase_labeler.py -v

# 3. Launch a dashboard page
panel serve dashboard/pages/01_enso_monitor.py --show
panel serve dashboard/pages/04_sector_impact.py --show
```

No API keys are needed for Phase 1 — every source is free and public.

---

## 📚 Data Sources

| Source | Provider | Use | Auth |
| :--- | :--- | :--- | :--- |
| [ONI ASCII feed](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt) | NOAA CPC | Core ENSO index (Niño-3.4, 3-mo mean) | None |
| [ONI HTML table](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php) | NOAA CPC | ONI fallback | None |
| [ENSO Diagnostic Discussion (PDF)](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.pdf) | NOAA CPC / IRI | Live advisory status | None |
| [Pink Sheet (historical monthly)](https://www.worldbank.org/en/research/commodity-markets) | World Bank | Commodity prices (1960–) | None |
| [RONI + probabilities](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/) | NOAA CPC | Official index (Phase 1.5) | None |
| [ERA5](https://cds.climate.copernicus.eu/) | Copernicus CDS | SST anomaly grids (Phase 2) | Free key |
| [USDA NASS](https://quickstats.nass.usda.gov) · [FAOSTAT](https://www.fao.org/faostat/) | USDA / FAO | Crop yields (Phase 2) | Free key / none |
| [EM-DAT](https://www.emdat.be/) | CRED / UCLouvain | Disaster events (Phase 2) | Account |

---

## ⚠️ Data Disclaimer

This platform reports observational and model data with known limitations. **Read this before drawing conclusions.**

1. **ONI vs RONI.** Charts here use **ONI** (3-month running mean of Niño-3.4 SST anomaly, rolling 30-yr base). On **16 Feb 2026 NOAA adopted RONI (Relative ONI)** — which subtracts tropical-mean SST to remove background warming — as the *official* index. Under RONI the 2023–24 El Niño registers ~0.6 °C cooler and some "neutral" periods reclassify. **Every index-based chart is labeled; do not compare ONI- and RONI-classified events directly.**
2. **The 3-month mean lags the raw weekly Niño-3.4.** A weekly spike (e.g. +1.7 °C) can precede the smoothed ONI crossing +0.5 °C by ~2 months. The monitor shows both views and never hardcodes the current phase — advisory status is fetched live at runtime.
3. **Forecast spread is real.** Never trust a single forecast. CPC and independent models can disagree sharply (e.g. ~65% strong-El-Niño odds vs ~37.5% onset in arXiv:2602.14773). Phase 2 shows the full ensemble range.
4. **Correlation ≠ causation.** Sector correlations are detrended Pearson coefficients, not causal effects. Shared seasonality, IOD, and MJO can drive spurious co-movement. Causal direction requires Granger / CCM testing (Phase 2).
5. **Teleconnections are probabilistic tendencies, not guarantees**, and are modulated by the Indian Ocean Dipole (IOD) and Madden–Julian Oscillation (MJO).
6. **Source freshness / sunset risks:**
   - The World Bank historical Pink Sheet workbook currently resolves to a snapshot ending **2024-12**; recent months should be supplemented with the latest dated bulletin. Fetchers degrade gracefully to cached data.
   - **CHIRPS v2** precipitation ends **Dec 2026** → migrate to CHIRPS v3.
   - The **IRI Data Library (IRIDL)** is being sunset (~Apr 2026); NOAA PSL is the fallback.

---

## 🗂️ Project Structure

```
enso-intelligence-platform/
├── data/
│   ├── ingest/        oni_fetcher · pink_sheet · advisory_fetcher · ersst_fetcher · _common
│   ├── process/       enso_phase_labeler · lag_correlator · granger_ccm
│   ├── raw/           ERSSTv5 netCDF (gitignored, ~150 MB)
│   └── cache/         oni · commodities · enso_phases · sst_anomaly_grids · *_backtest/forecast
├── dashboard/
│   ├── theme.py       palette + Plotly template + cache loaders
│   ├── components/    oni_gauge · timeseries · globe_layer
│   └── pages/         01_monitor · 02_global_map · 03_forecast · 04_sector_impact · 05_causation
├── forecasting/
│   ├── baselines/     arima_model
│   ├── ml_models/     lstm_enso
│   ├── verification/  skill_metrics
│   └── ensemble.py
├── tests/
├── requirements.txt · .env.example · .gitignore · README.md
```

---

## 🔬 Forecasting & causation methodology

**Forecasting.** SARIMA and a PyTorch LSTM both forecast the ONI to 12 months and
are verified *pseudo-out-of-sample* on identical walk-forward origins, scored by
ACC / RMSE / MSSS against a persistence reference. Headline findings: both beat
persistence at all 12 leads; **SARIMA actually outperforms the small LSTM** on
this short univariate series (an honest result — the LSTM needs ancillary indices
or spatial SST fields to win); ACC falls below the 0.5 useful-skill line around
6–8 months (the ENSO spring predictability barrier). The forecast page shows the
ensemble *and* external operational forecasts (CPC ~strong vs a skeptical
published estimate) so model disagreement is visible, never hidden.

**Causation.** Two complementary tests on detrended ONI vs commodity series:
Granger causality across lags 0–24 (linear), and Convergent Cross Mapping
(nonlinear, implemented in-repo via simplex projection — no pyEDM). CCM is the
more discriminating test: genuine causation shows cross-map skill that rises and
converges with library size in one direction only (e.g. ONI → wheat converges
while wheat → ONI collapses). Surrogate (phase-randomized) significance is a
planned addition; verdicts are exploratory.

## 🛣️ Roadmap

**Phase 1.5** — `roni_fetcher.py` (official RONI index) → ONI/RONI dual time series on the monitor.

**Phase 2 — remaining**
- Hugging Face Spaces deployment (Gradio forecast demo)
- EM-DAT disaster-event bubbles + time animation on the global map
- ERA5 CNN (Ham 2019 reproduction) + `climpred` gridded skill verification
- Phase-randomized **surrogate** significance for the causation explorer
- Historical event cards (peak ONI/RONI, duration, Callahan & Mankin 2023 economic cost)

---

## 🎨 Design

Dark "terminal" theme — background `#0a0e1a`, surface `#141929`, El Niño `#f4623a`,
La Niña `#3a9af4`, neutral `#8a94a6`, highlight teal `#00d4b4`, text `#e8edf5`.
Card-based layout, per-chart PNG/CSV export, Black-formatted code with type hints
and data-source citations in every module docstring.

## 📄 License & Attribution

Data © their respective providers (NOAA, World Bank, Copernicus, USDA, FAO, CRED).
This project is for research and educational use. Cite sources when reusing.
