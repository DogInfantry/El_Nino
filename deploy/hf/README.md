---
title: ENSO Macro Risk Desk
emoji: 🌊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: ENSO commodity risk desk, causal-tested teleconnections
---

# ENSO Macro Risk Desk

<!-- about:start -->
The **ENSO Macro Risk Desk** is a production-grade, open source Python dashboard
that answers one question for a commodity or macro analyst and for a climate
aware portfolio manager: **when the El Niño–Southern Oscillation (ENSO) cycle
shifts, what commodity and sector exposure should you reposition, and which of
those links survive causal testing?**

It ingests canonical ENSO data directly from **NOAA CPC** (the Oceanic Niño
Index), **ERSSTv5 sea surface temperature grids**, the **World Bank Pink Sheet**
commodity database, and **IMD 0.25° gridded rainfall** area-weighted across
1901–2024. It then runs a **dual model forecasting engine** (SARIMA plus a
PyTorch LSTM) and a **causal inference engine** (Granger causality, Convergent
Cross Mapping, and phase-randomized surrogate significance) across **fourteen
interactive pages**, in a dark, data-dense terminal UI. **No API keys are
required to start.**

Every weight, threshold and known limit is written down in
**[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)**, rendered in-app as page 09 and
enforced against the code by a test, so the published document cannot drift from
what actually runs. The same caches are served as JSON at **`/api`**, so a claim
on a page can be checked rather than screenshotted.

The product philosophy is **describe → prescribe**: every region and commodity
ends in a positioning view (constructive, cautious or watch, plus a swing
catalyst and a risk), not just a chart. Those stances are **computed, not
typed**, and gated by the causal verdict, which is why the desk will say *no
trade* when that is what the evidence supports.

> **Who it's for:** commodity and macro research analysts, climate risk and
> energy transition desks, agricultural economists, and data science portfolio
> reviewers.
<!-- about:end -->

## The landing page

The **Macro Risk Desk** opens by default:

- live NOAA CPC Niño-3.4 and ONI gauge, 24-month trajectory, and an Ensemble
  (SARIMA plus LSTM) 12-month forecast cone;
- a **weekly Niño-3.4 nowcast** fetched live on every page load, about one week
  behind. The ONI is a 3-month mean labelled by its *centre* month, so a fully
  current value reads about two months old, and the nowcast shows where SST
  actually is. It is a different quantity from the ONI, one week rather than a
  3-month mean, so it is never scored against ONI's ±0.5 °C thresholds, and a
  4-week mean sits beside it;
- a world **ENSO Exposure Index** choropleth (coral for dry impact, blue for wet);
- a most-exposed-regions leaderboard, where every region with a deep-dive page
  links straight to it;
- a **causation strip**, the honesty layer. Seven ONI→commodity-price links are
  tested against a phase-randomized surrogate null, and **not one survives**. All
  seven read *weak, confounded*. The sharpest case is Robusta, which carries the
  highest raw cross-map ρ on the board at 0.32 and the worst p-value at 0.976,
  meaning a null built from the ONI's own power spectrum beats it almost every
  time. The clean ENSO signal lives on the climate and production side, the
  monsoon and Maritime Continent drought proven in the region deep-dives, not in
  noisy monthly prices.

## Pages

`00` Macro Risk Desk · `01` ENSO Monitor · `02` Global SST Map · `03` Forecast
(SARIMA, LSTM, Ensemble) · `04` Sector Impact · `05` Causation Explorer (live
Granger and CCM) · `06` Historical Events · `07` India deep-dive (ENSO×IOD →
monsoon) · `08` SE Asia deep-dive (palm oil) · `09` Methodology · `10` Source
Status · `11` Brazil deep-dive (Arabica) · `12` Australia deep-dive (wheat) ·
`13` Peru deep-dive (fishmeal).

## API

Eight read-only JSON endpoints serve the same caches the pages read, so a claim
can be checked rather than screenshotted: `/api/state`, `/api/positioning`,
`/api/exposure`, `/api/verdicts`, `/api/analogs`, `/api/sources`, `/api/skill`
and `/api/skill_variants`. `/api` itself returns the index.

## Data

NOAA CPC ONI (live ASCII), CPC weekly Niño-3.4 (live), ERSSTv5 anomaly grids,
World Bank Pink Sheet commodities, IMD gridded rainfall. The app reads
precomputed parquet caches, with the advisory and the weekly nowcast as the two
live reads, and the offline ingest and forecast pipeline (PyTorch, xarray,
statsmodels) is not run at serve time. Free CPU Basic, so it may cold-start after
inactivity.

Commodity prices end **2024-12**: the World Bank's historical workbook is a
periodic snapshot, not a live feed. That cutoff is deliberate, because the lag
and causality work needs decades of history rather than the current month.
Splicing a second price source to gain recency would put the causal verdicts at
risk for no analytical gain. The ENSO indices are current.

Auto-deployed from GitHub via Actions on every push to `master`. The parquet
caches are refreshed by a monthly scheduled workflow.
Source and full methodology: https://github.com/DogInfantry/El_Nino
