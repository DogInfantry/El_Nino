---
title: ENSO Macro Risk Desk
emoji: 🌊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: ENSO commodity risk desk - causal-tested teleconnections
---

# ENSO Macro Risk Desk

A Bloomberg-style climate-intelligence terminal for **El Niño / Southern
Oscillation (ENSO)** macro & commodity risk. When the ENSO cycle shifts, it
tells you what commodity and sector exposure to reposition — and, crucially,
**which links are causally real vs. spurious** (Granger + a self-coded
Convergent Cross Mapping engine on detrended series).

The landing (the **Macro Risk Desk**) opens by default:
- live NOAA CPC Niño-3.4 / ONI gauge, 24-month trajectory, and an Ensemble
  (SARIMA + LSTM) 12-month forecast cone;
- a world **ENSO Exposure Index** choropleth (coral = dry-impact, blue = wet);
- a most-exposed-regions leaderboard (India & SE Asia link to live deep-dives);
- a **causation strip** — the honesty layer. Of six ONI→commodity-price links,
  none is strongly causal (max CCM ρ 0.32): most price trades the market makes
  don't survive causal testing. The clean ENSO signal lives on the
  climate/production side (the monsoon and Maritime-Continent drought proven in
  the region deep-dives), not in noisy monthly prices.

## Pages

`00` Macro Risk Desk · `01` ENSO Monitor · `02` Global SST Map · `03` Forecast
(SARIMA/LSTM/Ensemble) · `04` Sector Impact · `05` Causation Explorer (live
Granger + CCM) · `06` Historical Events · `07` India deep-dive (ENSO×IOD →
monsoon) · `08` SE Asia deep-dive (palm oil).

## Data

NOAA CPC ONI (live ASCII), ERSSTv5 anomaly grids, World Bank Pink Sheet
commodities, IMD monsoon. The app reads precomputed parquet caches; the offline
ingest/forecast pipeline (PyTorch / xarray / statsmodels) is not run at serve
time. Free CPU Basic; may cold-start after inactivity.

Auto-deployed from GitHub via Actions on every push to `master`.
Source & full methodology: https://github.com/DogInfantry/El_Nino
