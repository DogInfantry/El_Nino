<a name="top"></a>

<div align="center">

<img src="assets/hero.svg" alt="ENSO Macro Risk Desk — a Bloomberg-style terminal for causal-tested El Niño commodity and sector risk, showing the real 1950–2026 Oceanic Niño Index record" width="100%">

# 🌊 ENSO Macro Risk Desk

**A Bloomberg-style climate-intelligence terminal that turns the El Niño / La Niña (ENSO) cycle into actionable commodity & sector positioning — with the causal rigor to tell which links are real and which are spurious.**

[![🤗 Live Demo](https://img.shields.io/badge/🤗%20Live%20Demo-Hugging%20Face%20Spaces-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co/spaces/DogInfantry/enso-macro-risk-desk)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3120/)
[![Panel](https://img.shields.io/badge/Dashboard-HoloViz%20Panel-purple)](https://panel.holoviz.org/)
[![Plotly](https://img.shields.io/badge/Viz-Plotly%206-3F4F75?logo=plotly)](https://plotly.com/)
[![Causal Inference](https://img.shields.io/badge/Causal-Granger%20%2B%20CCM-00d4b4)](#-the-moat-causal-rigor)
[![Data: NOAA](https://img.shields.io/badge/Data-NOAA%20CPC-00559B)](https://www.cpc.ncep.noaa.gov/)
[![License: Research](https://img.shields.io/badge/License-Research%20%26%20Educational-green)](#-license--attribution)

### **▶ [Open the live dashboard →](https://huggingface.co/spaces/DogInfantry/enso-macro-risk-desk)**

**[Live Demo](https://huggingface.co/spaces/DogInfantry/enso-macro-risk-desk) · [The Moat](#-the-moat-causal-rigor) · [Screenshots](#-screenshots) · [14 Pages](#-the-fourteen-pages) · [Methodology](docs/METHODOLOGY.md) · [Run It](#-run-it-locally) · [Deploy](#-deployment) · [FAQ](#-faq)**

</div>

---

## What is the ENSO Macro Risk Desk?

The **ENSO Macro Risk Desk** is a production-grade, open-source Python dashboard that answers one question for a commodity / macro analyst or climate-aware portfolio manager: **when the El Niño–Southern Oscillation (ENSO) cycle shifts, what commodity and sector exposure should you reposition — and which of those links survive causal testing?**

It ingests canonical ENSO data directly from **NOAA CPC** (the Oceanic Niño Index), **ERSSTv5 sea-surface-temperature grids**, the **World Bank Pink Sheet** commodity database, and **IMD monsoon** records. It then runs a **dual-model forecasting engine** (SARIMA + PyTorch LSTM) and a **causal-inference engine** (Granger causality + Convergent Cross Mapping) across **fourteen interactive pages** — a dark, data-dense terminal UI, **no API keys required to start.**

Every weight, threshold and known limit is written down in **[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)** — rendered in-app as page 09 and enforced against the code by a test, so the published document cannot drift from what actually runs.

The product philosophy is **describe → prescribe**: every region and commodity ends in a positioning view (constructive / cautious / watch + swing catalyst + risk), not just a chart.

> **Who it's for:** commodity & macro research analysts, climate-risk and energy-transition desks, agricultural economists, and data-science portfolio reviewers.

**TL;DR**
- 🌍 **ENSO Exposure Index** — a world choropleth + leaderboard ranking where an ENSO swing reprices commodity & sector risk.
- 🔬 **Causal rigor as the moat** — Granger + Convergent Cross Mapping (CCM) separate *real* ENSO→price links from spurious ones. Most don't survive — and that's the honest headline.
- 📈 **12-month forecasts** — SARIMA + LSTM ensemble, walk-forward backtested, beating persistence at all 12 leads.
- 🛰️ **Live data** — NOAA CPC ONI + ENSO advisory fetched at runtime; ERSSTv5 SST grids; 71 World Bank commodities.
- 🇮🇳 **Five region deep-dives** — India (ENSO × Indian Ocean Dipole → monsoon → food CPI), SE Asia (palm oil), Brazil (coffee), Australia (wheat) and Peru (fishmeal), each ending in a computed desk view — including the ones where the honest view is *no trade*.
- 🚀 **Live & auto-deployed** — running on Hugging Face Spaces, CI/CD from GitHub.

---

## 🖥️ Screenshots

> The **Macro Risk Desk** landing — left rail (Niño-3.4 gauge, ONI trajectory, 12-month forecast cone), the world **ENSO Exposure Index** choropleth, a most-exposed-regions leaderboard, and the **causation strip** (the honesty layer):

<div align="center">
<img src="assets/desk-landing.png" alt="ENSO Macro Risk Desk dashboard landing page showing the Niño-3.4 gauge, 12-month ENSO forecast cone, a world commodity exposure choropleth, a leaderboard of most-exposed regions, and a Granger plus CCM causal-test strip" width="100%">
</div>

<table>
<tr>
<td width="50%">

**🇮🇳 India deep-dive** — ENSO × IOD → monsoon → food CPI, with a computed desk view and the real OLS regression heatmap.

<img src="assets/india.png" alt="India ENSO deep-dive showing a computed desk view, monsoon rainfall deficit map, and an ENSO by Indian Ocean Dipole probability-of-deficient-monsoon heatmap with OLS regression" width="100%">

</td>
<td width="50%">

**🛰️ Global SST Map** — ERSSTv5 sea-surface-temperature anomalies with the classic El Niño equatorial-Pacific warm tongue + teleconnection zones.

<img src="assets/global-map.png" alt="Global sea surface temperature anomaly map from ERSSTv5 showing the El Niño warm tongue across the equatorial Pacific with teleconnection overlay boxes" width="100%">

</td>
</tr>
<tr>
<td width="50%">

**🔬 Causation Explorer** — live Granger + Convergent Cross Mapping on ONI vs. any commodity, with a plain-language verdict.

<img src="assets/causation.png" alt="Causation Explorer page running Granger causality and Convergent Cross Mapping on the Oceanic Niño Index versus a commodity price series" width="100%">

</td>
<td width="50%">

**📈 Forecast** — SARIMA + LSTM + ensemble fan chart with confidence bands and ACC-vs-lead skill.

<img src="assets/forecast.png" alt="ENSO 12-month forecast page with a SARIMA, LSTM, and ensemble fan chart, confidence bands, and anomaly correlation skill versus lead time" width="100%">

</td>
</tr>
</table>

---

## 🎯 The Moat: Causal Rigor

Anyone can plot a correlation between El Niño and cocoa prices. The hard — and honest — part is asking **does it survive a causal test?** This desk runs two complementary engines on every ONI→commodity link:

- **Granger causality** (linear): does lagged ONI add predictive power over the commodity's own history?
- **Convergent Cross Mapping / CCM** (nonlinear, Sugihara et al. *Science* 2012): does cross-map skill *rise and converge* with library size in **one direction only**? Self-coded via simplex projection — no `pyEDM` dependency.
- **Phase-randomized surrogate significance** (Ebisuzaki): does that skill beat a null built from the ONI's *own power spectrum* with the phases scrambled? This is the test that matters, because cross-map skill runs high between **any** two smooth seasonal series — two *independent* sine-plus-noise series score ρ ≈ 0.83 in this engine.

**The result is deliberately humbling, and got more so.** Of the seven ONI→commodity-**price** links tested, **not one survives** — all are *weak / confounded*. Palm oil and wheat read *moderate* until they were tested against the null (p = 0.15 and p = 0.47). The sharpest lesson is Robusta: it has the **highest** raw ρ on the board at 0.32 and the **worst** p-value at 0.976, against a null that averages ρ 0.23 on its own. That ρ 0.32 was previously quoted here as the desk's strongest causal evidence; it is indistinguishable from chance. The best link is Peru/fishmeal — 21 of 24 Granger lags, ρ 0.29 against a 0.10 null — and at **p = 0.078** it still misses the bar and stays *weak*. So the takeaway the desk leads with is:

> **Most ENSO→commodity-price trades the market makes don't survive causal testing.** The clean ENSO signal lives on the **climate & production** side — the monsoon and Maritime-Continent drought we *prove* in the region deep-dives — not in noisy monthly prices.

That "misattribution guard" — showing the *computed* verdict instead of an asserted one, even when it undercuts a tidy narrative — is the whole point. Cocoa and wheat were *expected* to fail; the data said wheat is actually one of the stronger ones, and the desk reports that, not the assumption.

---

## 🗂️ The Fourteen Pages

| # | Page | What it does |
|:-:|------|------|
| **00** | **Macro Risk Desk** (landing) | Command-bar terminal: Niño-3.4 gauge · ONI trajectory · forecast cone · **ENSO Exposure Index** choropleth · most-exposed leaderboard · **causal-test strip** |
| **01** | ENSO Monitor | Live ONI **+ RONI** dual series (1950–present), gauge, live NOAA advisory badge, **weekly Niño-3.4 nowcast** (~1-week lag), CSV export |
| **02** | Global SST Map | ERSSTv5 2°×2° anomaly grids, flat + orthographic globe, teleconnection zones |
| **03** | Forecast | SARIMA + LSTM + ensemble fan chart, CI bands, ACC-vs-lead skill, **observed-vs-forecast check** (live weekly SST beside the ensemble's nearest month), **analog panel** — nearest historical ENSO states by z-scored state vector, with their forward ONI paths |
| **04** | Sector Impact | Detrended lag-correlation heatmap, ONI × 71 commodities, lags 0–24 mo |
| **05** | Causation Explorer | Live **Granger + CCM**, both directions, plain-language verdict |
| **06** | Historical Events | Per-event cards since 1950: peak ONI/RONI, Callahan & Mankin 2023 GDP losses |
| **07** | 🇮🇳 India deep-dive | **ENSO × IOD → monsoon → food CPI** on **IMD 0.25° gridded rainfall, area-weighted, 1901–2024**; real OLS regression (n=124); desk view |
| **08** | 🌴 SE Asia deep-dive | Palm oil; the ENSO-premium story fails its own composite |
| **09** | 📐 Methodology | Renders [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) directly — one source of truth, no second copy to drift |
| **10** | 🩺 Source Status | Per-feed freshness, measured **net of structural label lag** — leads with "Behind", not "Age" |
| **11** | 🇧🇷 Brazil deep-dive | Arabica; the honest **no-trade** region — the phase composite hints at an El Niño premium, the lag profile finds nothing (peak r ≈ −0.07, on the window edge) |
| **12** | 🇦🇺 Australia deep-dive | Wheat; the drought is real and the **price sign is inverted** (r = −0.27 at 4 mo) — correct physics, wrong instrument |
| **13** | 🇵🇪 Peru deep-dive | Fishmeal; the original El Niño and the desk's **best near-miss** — 21/24 Granger lags, ρ 0.29 vs a 0.10 null, surrogate p = 0.078 |

**916 ENSO months · 42 events detected · 71 commodities · 2°×2° global SST grids from 1854 · 124 years of gridded Indian monsoon · 12-month forecast horizon · zero API keys required.**

Positioning stances are **computed, not typed** — signed peak-lag correlation × current ENSO state, gated by the causal verdict and haircut when the live observation diverges from the forecast. They move when the data moves: on the current run India reads **WATCH** and SE Asia **CAUTIOUS**, both flipped from the earlier hand-written calls.

---

## 🔬 Forecasting & Causation Methodology

> Summary below. The full published spec — every weight, threshold, sample window, and the sources deliberately *not* used and why — is **[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)**, served in-app as page 09 and checked against the code by `tests/test_core.py`.

### Forecasting
Two models share an identical walk-forward verification harness, scored against a **persistence reference** (last observed ONI held constant):

| Model | Type | Architecture | Result |
|-------|------|-------------|--------|
| **SARIMA** | Statistical | statsmodels SARIMAX(2,0,1)(1,0,0,12) | Beats persistence at all 12 leads ✅ |
| **LSTM** | Deep Learning | PyTorch, 2-layer, 64 hidden | Beats persistence at all 12 leads ✅ |

**Honest result:** SARIMA outperforms the LSTM on this short univariate ONI series. The LSTM needs ancillary indices (IOD/MJO/PDO) or spatial SST fields (CNN track) to close the gap — framing it otherwise would misrepresent the evidence. Both models' skill (ACC) drops below the 0.5 useful-skill threshold at **6–8 months**, consistent with the ENSO spring predictability barrier.

### Causation
Both tests run on **linearly detrended** (not differenced — differencing kills the low-frequency ENSO band) ONI vs. commodity series:

- **Granger causality** (linear): F-test across lags 0–24.
- **Convergent Cross Mapping** (nonlinear): in-repo simplex projection (NumPy/SciPy), no pyEDM (its multiprocessing is incompatible with the Panel server on Windows). Genuine causation → cross-map skill rises and converges with library size in *one direction only*.

- **Surrogate significance** (Ebisuzaki phase randomization, 500 draws per link): the observed ρ is scored against surrogates that keep the ONI's amplitude spectrum — its annual cycle, persistence and smoothness — and randomize only the Fourier phases. `CAUSAL` and `MODERATE` now additionally require `p < 0.05`; a link that can't beat its own seasonal null is capped at `WEAK` whatever its ρ, and an untested link (`p = NaN`) fails the gate rather than passing it.

The live explorer on page 05 does **not** run surrogates — 500 extra cross-map passes per commodity is a precompute cost, not a page-load cost — so its verdicts use the pre-surrogate rules and are exploratory. The landing strip carries the gated ones.

---

## 🏗️ Architecture

```
NOAA CPC · ERSSTv5 · World Bank · IMD          data/ingest/  ──►  data/cache/*.parquet
                                                data/process/ ──►  (phases · RONI · Granger+CCM · exposure index)
                                                      │
              forecasting/ (SARIMA · LSTM · ensemble · skill) ──►  forecasts/skill caches
                                                      │
                                                      ▼
   app.py  ──►  HoloViz Panel + Plotly  ──►  00 Desk · 01 Monitor · 02 Map · 03 Forecast
                                              04 Impact · 05 Causation · 06 History · 07 India · 08 SE Asia
                                              09 Methodology · 10 Source Status
                                                      │
                                      Dockerfile  ──►  🤗 Hugging Face Space  (CI/CD from GitHub)
```

The dashboard reads **parquet caches only** — the heavy ingest/forecast pipeline (PyTorch, xarray, netCDF4) runs offline, so the deployed image is lean and serves instantly.

---

## 🚀 Run It Locally

**Requires Python 3.12** (Hugging Face Spaces parity; the ML/geo stack lacks wheels on newer builds).

```bash
# 1 — environment
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows  ·  source .venv/bin/activate on macOS/Linux

# 2 — dependencies
pip install -r requirements.txt

# 3 — (optional) refresh live data into data/cache/*.parquet
python data/ingest/oni_fetcher.py -v
python data/ingest/pink_sheet.py -v

# 4a — serve the whole site (landing at / + all 13 sub-pages) via the unified entry point
python app.py                   # → http://localhost:5006

# 4b — or serve a single page
panel serve dashboard/pages/00_landing.py --show
```

**No API keys required** for any module — every data source is free and public.

---

## ☁️ Deployment

**Live now:** **[el-nino-green.vercel.app](https://el-nino-green.vercel.app/)** (Next.js front-door on Vercel — prewarms the app host on visit) → **[huggingface.co/spaces/DogInfantry/enso-macro-risk-desk](https://huggingface.co/spaces/DogInfantry/enso-macro-risk-desk)** (the app — Docker SDK, free CPU Basic).

Panel/Bokeh is a long-running WebSocket server, so the app ships as a **Docker Space** (not Gradio/Static, and not Vercel without WASM conversion) running real `panel serve` via [`app.py`](app.py). The [`web/`](web/) directory is a static-exported **Next.js 15** landing page deployed on Vercel; it deep-links into the Space and polls the HF runtime API for live status. Data caches are refreshed monthly with one command: `python scripts/refresh_data.py`. A **GitHub Action** ([`.github/workflows/deploy-hf.yml`](.github/workflows/deploy-hf.yml)) auto-syncs the Space on every push to `master` — **push to GitHub → the Space redeploys itself**, and each run is recorded under the repo's **Deployments** tab. The serve-only dependency set ([`requirements-space.txt`](requirements-space.txt)) excludes torch/xarray/kaleido, keeping the image small.

---

## 📚 Data Sources

| Source | Provider | Module | Auth |
|:-------|:---------|:-------|:----:|
| [ONI ASCII feed](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt) | NOAA CPC | `oni_fetcher.py` | None |
| [Weekly Niño-3.4 SST anomaly](https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for) | NOAA CPC | `weekly_nino34.py` — read **live at page load**; parquet snapshot is only the offline fallback | None |
| [ENSO Diagnostic Discussion (PDF)](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.pdf) | NOAA CPC / IRI | `advisory_fetcher.py` | None |
| [Pink Sheet — monthly commodities](https://www.worldbank.org/en/research/commodity-markets) | World Bank | `pink_sheet.py` | None |
| [ERSSTv5 netCDF grids](https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/netcdf/) | NOAA NCEI | `ersst_fetcher.py` | None |
| IMD **0.25° daily gridded rainfall, 1901–2024** → cos(lat) area-weighted all-India JJAS | India Met. Dept. | `imd_gridded.py` — **manual, ~3 GB of raw year-binaries**; the parquet is committed | None |
| IMD 36-subdivision monthly rainfall (1901–2017) | India Met. Dept. | `monsoon_fetcher.py` — superseded for all-India, kept for provenance | None |
| [SOI · Niño 1+2/3/4 · TNI · PDO · AMO · PNA · WP · DMI](https://psl.noaa.gov/data/climateindices/list/) | NOAA PSL | `climate_indices.py` — `coverage()` flags frozen upstreams, `model_features()` drops them before any model sees them | None |
| [ERA5 reanalysis](https://cds.climate.copernicus.eu/) · [USDA NASS](https://quickstats.nass.usda.gov) · [EM-DAT](https://www.emdat.be/) | Copernicus / USDA / CRED | *(roadmap)* | Free |

---

## ⚠️ Data Caveats & Known Limitations

Rigorous analysis means disclosing limits. Read before drawing conclusions.

1. **ONI vs RONI.** Charts label every index. On **16 Feb 2026 NOAA adopted RONI** (subtracts tropical-mean SST to remove background warming) as the *official* ENSO index; under RONI the 2023–24 El Niño is ~0.6 °C cooler. Don't compare ONI- and RONI-classified events directly. This repo's RONI is computed from ERSSTv5 on a fixed 1991–2020 base — it *approximates* the official value.
2. **The 3-month mean lags raw Niño-3.4 — and is labelled by its *centre* month.** A weekly spike can precede the smoothed ONI crossing ±0.5 °C by ~2 months. CPC's newest ONI row is a *season*: AMJ 2026 is stored under `2026-05-01`, so a fully current reading legitimately displays as "May". Pages therefore name the season (`AMJ 2026 · 3-mo mean, ctr. May`) and pair it with the **live weekly Niño-3.4 nowcast** (~1-week lag) so freshness is visible. The weekly value is a **different quantity** — a single week of OISST, not a 3-month mean — so it must never be read against ONI's ±0.5 °C event thresholds; the 4-week mean is shown beside it to damp noise. Current phase is fetched live, never hardcoded.
3. **Correlation ≠ causation.** Sector links are detrended Pearson r; the IOD and MJO can drive spurious co-movement. Causal direction needs Granger / CCM (Page 05) — and most price links *fail* it (see [The Moat](#-the-moat-causal-rigor)).
4. **Exposure Index is a research construct** — 50% computed peak lagged ONI–commodity correlation + 50% curated structural exposure. Not an official product.
5. **Source freshness.** The World Bank Pink Sheet workbook currently ends **2024-12**; fetchers degrade gracefully to cache. India crop/CPI tabs are illustrative pending USDA/FAOSTAT ingestion. Page **10 (Source Status)** publishes per-feed lateness live — measured *net of each feed's structural label lag*, because the ONI is stamped with its **centre** month and a perfectly current value therefore looks ~2.5 months old.
6. **The gridded all-India series approximates, not reproduces, IMD's published AISMR.** The 1971–2020 normal comes out at 858.9 mm against IMD's ~868 (within 1.1%), and the departures track the old subdivision series at r=0.945 — but IMD weights its own subdivisions rather than cos(lat) grid cells, so 2009 reads −15.0% here against a commonly cited ~−22%. Use these as this repo's series, never as IMD's official departures.

---

## ❓ FAQ

<details>
<summary><strong>What is the ENSO Macro Risk Desk?</strong></summary>

It's an interactive Python dashboard that maps the El Niño–Southern Oscillation (ENSO) cycle to commodity and sector risk, and stress-tests each link with causal inference (Granger + Convergent Cross Mapping). It's built for commodity/macro analysts and climate-risk desks, and it's [live on Hugging Face Spaces](https://huggingface.co/spaces/DogInfantry/enso-macro-risk-desk).
</details>

<details>
<summary><strong>What is ENSO, and why does it matter for commodity markets?</strong></summary>

ENSO is the dominant year-to-year driver of global climate variability. **El Niño** (ONI ≥ +0.5 °C) suppresses rainfall in Southeast Asia and Australia and enhances it on South America's west coast; **La Niña** (ONI ≤ −0.5 °C) reverses it. Because ENSO disrupts rainfall in the world's key agricultural zones, it is linked to price shocks in wheat, maize, rice, coffee, cocoa, and palm oil — typically 3–9 months after the SST anomaly peak.
</details>

<details>
<summary><strong>What is the difference between ONI and RONI?</strong></summary>

**ONI** is the 3-month running mean of Niño-3.4 SST anomalies against a rolling 30-year base. **RONI (Relative ONI)** subtracts the tropical-mean (20°S–20°N) anomaly, removing the warming trend that increasingly inflates ONI. NOAA adopted RONI as the official ENSO index in February 2026; under it the 2023–24 El Niño is ~0.6 °C weaker.
</details>

<details>
<summary><strong>What is Convergent Cross Mapping (CCM)?</strong></summary>

CCM (Sugihara et al., *Science*, 2012) is a nonlinear causal-inference method for dynamical systems. It tests whether X drives Y by checking whether Y's reconstructed attractor can recover X's states — and whether that cross-map skill *converges* as the observation library grows. Unlike Granger causality it doesn't assume linearity. This project implements CCM in-repo via simplex projection (NumPy/SciPy), without pyEDM, for Windows/Panel compatibility.
</details>

<details>
<summary><strong>Is it really live? How is it deployed?</strong></summary>

Yes — [running on Hugging Face Spaces](https://huggingface.co/spaces/DogInfantry/enso-macro-risk-desk) as a Docker Space serving `panel serve` via `app.py`, on the free CPU tier (it may cold-start after inactivity). A GitHub Action auto-redeploys on every push to `master`.
</details>

<details>
<summary><strong>Why does SARIMA outperform the LSTM?</strong></summary>

ONI is a short (~70-year) quasi-periodic univariate signal that SARIMA exploits directly through its seasonal AR structure. Without ancillary indices (IOD/MJO/PDO) or spatial SST input (CNN track), the LSTM lacks the signal to overcome SARIMA's parsimony at this data scale — an honest, common finding for short univariate climate series.
</details>

<details>
<summary><strong>Can I run it on macOS or Linux?</strong></summary>

Yes. Swap `.venv\Scripts\activate` for `source .venv/bin/activate`; the rest is cross-platform. The only Windows-specific choice is avoiding pyEDM — the in-repo CCM is fully portable.
</details>

---

## 📄 License & Attribution

Data © respective providers: NOAA/NWS (ONI, advisory, ERSSTv5), World Bank (Pink Sheet), India Meteorological Department (monsoon), Copernicus/ECMWF, USDA, FAO, CRED (EM-DAT). Code & dashboard: research and educational use — cite the primary data sources when reusing outputs.

**Key reference:** Callahan, C. W. & Mankin, J. S. (2023). Persistent effect of El Niño on global economic growth. *Science*, 381, 789–793. DOI: [10.1126/science.adf0374](https://doi.org/10.1126/science.adf0374)

---

<div align="center">

Built with [HoloViz Panel](https://panel.holoviz.org/), [Plotly](https://plotly.com/), [PyTorch](https://pytorch.org/), [statsmodels](https://www.statsmodels.org/), and data from [NOAA CPC](https://www.cpc.ncep.noaa.gov/) and the [World Bank](https://www.worldbank.org/).

<sub><b>Topics:</b> el-nino · la-nina · enso · enso-forecast · climate-risk · commodity-markets · macro-research · teleconnections · oceanic-nino-index · oni · roni · nino-3.4 · granger-causality · convergent-cross-mapping · ccm · sarima · lstm · time-series-forecasting · climate-finance · indian-ocean-dipole · monsoon · palm-oil · sea-surface-temperature · python-dashboard · holoviz-panel · plotly · data-visualization</sub>

**[▲ Back to top](#top)**

</div>
