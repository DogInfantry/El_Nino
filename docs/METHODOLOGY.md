# Methodology — ENSO Macro Risk Desk

`exposure-v1 (2026-08-07)` · `stance-v1 (2026-08-07)`

Every number this desk shows is either **computed** from a public source or **curated** by
hand. This page says which is which, publishes the weights, and states the limits. If a
figure is not derived here, it is not on the desk.

---

## What this desk is, and is not

**It is** a triage tool for one question: when the ENSO cycle shifts, which commodity and
regional exposures are worth re-examining, and which apparent links do not survive causal
testing.

**It is not** a trade recommendation, a price forecast, a backtested signal, or investment
advice. The stances are formula outputs over one correlation and one causal test. Nothing
here has been validated against realised P&L, and no claim of predictive skill is made for
the positioning layer.

The honest headline from our own data: **most ENSO → commodity-*price* links do not survive
causal testing.** Of six tested links, none is CAUSAL; two are MODERATE and the rest are
WEAK · confounded. The clean, strong ENSO signal lives on the climate and production side
(monsoon rainfall, Maritime Continent drought), not in noisy monthly prices. Any page that
implied otherwise would be selling a story the data does not support.

---

## Computed vs curated

| Layer | Status | Source |
|---|---|---|
| ONI, weekly Niño-3.4, ERSSTv5 grids, commodity prices | computed | NOAA CPC / NOAA PSL / World Bank |
| RONI | computed, **approximate** | in-repo from ERSSTv5, fixed 1991–2020 base |
| ENSO phases, event tiers | computed | in-repo from the ONI |
| SARIMA / LSTM / ensemble forecasts | computed | in-repo |
| Granger + CCM verdicts | computed | in-repo |
| Exposure Index — factor `C` | computed | peak lagged correlation |
| Exposure Index — factor `E` | **curated** | public production/export shares |
| Positioning badge, conviction, horizon | computed | this page's rules |
| Catalyst / key-risk text, hotspot annotations | **curated** | editorial |

---

## Exposure Index (`exposure-v1`)

A **constructed** score ranking ENSO-exposed agricultural exporters. Labelled as
constructed everywhere it appears; it is not an observed quantity.

```
index = 100 * (0.5 * C + 0.5 * E)
```

- **`C` — link strength (computed).** Peak `|r|` between the ONI and the country's dominant
  Pink Sheet commodity over lags 0–24 months, both series linearly detrended, scaled so
  `|r| = 0.45` maps to `C = 1.0` and clipped there. `|r| ≈ 0.45` is strong for a detrended
  ENSO–price link; the cap stops one outlier dominating the ranking.
- **`E` — structural exposure (curated).** The country's reliance on that commodity —
  global market share × agricultural weight, 0–1, from public FAO/USDA production shares.
  **These are editorial judgements**, reviewed by hand, not fitted to anything.

`sign` (`dry` / `wet` / `mixed`) is the climate direction, used for the choropleth's
diverging palette. It is **not** a price direction.

| iso3 | Country | Commodity | C (computed) | E (curated) | Index | sign |
|---|---|---|---|---|---|---|
| IDN | Indonesia | Palm oil | 0.58 | 0.85 | 71.3 | dry |
| CIV | Côte d'Ivoire | Cocoa | 0.42 | 0.90 | 66.1 | dry |
| MYS | Malaysia | Palm oil | 0.58 | 0.70 | 63.8 | dry |
| AUS | Australia | Wheat, US HRW | 0.60 | 0.65 | 62.5 | dry |
| GHA | Ghana | Cocoa | 0.42 | 0.80 | 61.1 | dry |
| IND | India | Sugar, world | 0.31 | 0.80 | 55.3 | dry |
| ARG | Argentina | Soybeans | 0.38 | 0.70 | 54.2 | mixed |
| THA | Thailand | Sugar, world | 0.31 | 0.60 | 45.3 | dry |
| BRA | Brazil | Coffee, Arabica | 0.15 | 0.75 | 44.8 | mixed |
| USA | United States | Soybeans | 0.38 | 0.45 | 41.7 | mixed |
| VNM | Vietnam | Coffee, Robusta | 0.08 | 0.70 | 39.2 | dry |

Half the score is data, half is a documented opinion. Treat the ranking as opinionated.

---

## Causal verdicts

Granger causality (linear **detrend**, never first-differencing — differencing monthly data
is a high-pass filter that kills the low-frequency ENSO band and makes everything look
null) plus self-coded Convergent Cross Mapping, both at `maxlag = 24`, `α = 0.05`.
`sig` = the count of lags with `p < α`; `converges` = forward CCM skill rising with library
size; `rho_end` = forward `ρ` at the largest library.

| Verdict | Rule |
|---|---|
| `CAUSAL` | `sig ≥ 3` **and** converges **and** `rho_end ≥ 0.30` |
| `MODERATE` | `sig ≥ 3` **and** converges |
| `WEAK · confounded` | `sig ≥ 2` **or** converges |
| `NONE` | otherwise |

Current results: Palm oil MODERATE, Wheat MODERATE, Sugar / Soybeans / Cocoa / Robusta
WEAK · confounded, none CAUSAL. Granger over-detects (palm fires on 13 of 24 lags) and CCM
declines to confirm it — which is the whole reason both tests are run.

---

## Positioning stances (`stance-v1`)

Recomputed every month by `data/process/positioning.py`, after the verdicts it depends on.

1. **`r_peak`, `L`** — signed Pearson r at the peak-`|r|` lag over 0–24 months, detrended.
   The Exposure Index deliberately discards this sign; the stance needs it, because it says
   whether a warm ENSO pushes that price up or down.
2. **`state`** — the forcing the lagged price will respond to, in ONI standard deviations:
   the mean of the latest observed ONI and the ensemble path over the next `L` months. A
   stance therefore inherits the forecast's decay instead of freezing today's reading.
3. **`impact = r_peak × state`**.
4. **Causal gate.** Only `CAUSAL` and `MODERATE` links may carry a direction. `WEAK`,
   `NONE` and untested links are capped at **WATCH** however large `impact` is. This is the
   misattribution guard applied to the prescription, not just to the description.
5. **Noise floor.** `|impact| < 0.25` ⇒ WATCH.
6. **Direction.** `impact > 0` ⇒ CONSTRUCTIVE, `impact < 0` ⇒ CAUTIOUS.
7. **Conviction (1–4).** Seeded by verdict class (`causal` 4, `mod` 3, `weak` 2, `none` /
   untested 1); `+1` if `|impact| ≥ 0.60`; `−1` if observed-minus-forecast exceeds `1.0 °C`;
   clamped to 1–4.
8. **Overrides.** `positioning.OVERRIDES` lets a human pin a badge. An override renders
   *as* an override with its written reason — a formula cannot see an export-policy
   catalyst, but it should not pretend the pin was computed either.

### Current output

Regime: **WEAK EL NIÑO · 2026 · STRENGTHENING**. Observed-minus-forecast is **+1.01 °C**,
past the 1.0 tolerance, so the conviction haircut is **active on every row** — the ensemble
decays toward neutral while the observed weekly reads +2.15, and the desk does not get to
ignore that disagreement.

| iso3 | Commodity | r_peak | Lag | Impact | Verdict | Stance | Conv. |
|---|---|---|---|---|---|---|---|
| AUS | Wheat, US HRW | −0.270 | 4 mo | −0.397 | MODERATE | ▼ CAUTIOUS | 2/4 |
| MYS | Palm oil | −0.259 | contemp. | −0.306 | MODERATE | ▼ CAUTIOUS | 2/4 |
| IDN | Palm oil | −0.259 | contemp. | −0.306 | MODERATE | ▼ CAUTIOUS | 2/4 |
| ARG | Soybeans | −0.173 | contemp. | −0.204 | WEAK | ● WATCH | 1/4 |
| USA | Soybeans | −0.173 | contemp. | −0.204 | WEAK | ● WATCH | 1/4 |
| GHA | Cocoa | −0.190 | 24 mo † | −0.188 | WEAK | ● WATCH | 1/4 |
| CIV | Cocoa | −0.190 | 24 mo † | −0.188 | WEAK | ● WATCH | 1/4 |
| IND | Sugar, world | −0.138 | 12 mo | −0.136 | WEAK | ● WATCH | 1/4 |
| THA | Sugar, world | −0.138 | 12 mo | −0.136 | WEAK | ● WATCH | 1/4 |
| BRA | Coffee, Arabica | −0.066 | 24 mo † | −0.065 | UNTESTED | ● WATCH | 1/4 |
| VNM | Coffee, Robusta | +0.038 | 12 mo | +0.037 | WEAK | ● WATCH | 1/4 |

These figures move every month. They are regenerated by the cron, not typed — the table is
a snapshot of the committed cache, and the live values are on the desk itself.

### Known limitations

- **† Boundary lags.** Cocoa and Arabica peak at lag 24 — the edge of the search window —
  so the true peak may lie outside it and the number must not be read as a horizon. The UI
  renders these as `24 mo (window edge)`. Lag 0 renders as `contemporaneous`.
- **`r_peak` is negative for 10 of 11 rows.** A warm ENSO maps to *lower* prices at the peak
  lag across almost the whole registry. Given that 9 of those links are WEAK or untested,
  the honest reading is that the price channel is mostly confounded — not that El Niño is
  broadly deflationary for softs.
- Selecting the peak lag from 25 candidates inflates `|r|`; no multiple-comparison
  correction is applied, which is another reason the causal gate, not the correlation, sets
  the stance.
- Prices end **2024-12** (below), so the correlation is fitted on history while the state is
  current. A stance is a conditional expectation, not an observed relationship holding today.

---

## Data cutoffs and label conventions

- **The ONI is labelled by its centre month.** It is a 3-month running mean, so CPC's newest
  row is a *season* (AMJ 2026) stored under `2026-05-01`. A perfectly current value looks
  ~2.5 months old. Freshness is therefore measured against a per-source structural label lag
  (`expected_lag_days`, 75 for the ONI), never raw age. Getting this wrong is what caused a
  false staleness alarm on 2026-07-30.
- **Weekly Niño-3.4 is a different quantity from the ONI** — different product, different
  cadence. It is never compared against the ONI's ±0.5 °C event thresholds. Only
  `wksst9120.for` is live; `wksst8110.for` is frozen at 27 Jan 2021 yet still returns HTTP
  200, so fetching it would silently ship years-old data.
- **World Bank Pink Sheet ends 2024-12**, by decision. Splicing a second live price source
  risks corrupting the lag / Granger / CCM work that is this project's moat, in exchange for
  recency the analysis does not need. Disclosed on the Sector Impact page.
- **India monsoon rainfall now comes from IMD's 0.25° gridded daily product**, 1950–2024,
  area-weighted by cos(lat) over valid cells — see the validation note below. The old
  36-subdivision set (frozen 1901–2017, all-India as an *unweighted* subdivision mean) is
  retained only for the pre-1950 record.

### India monsoon: how well the gridded series validates

| Check | Result |
|---|---|
| 1971–2020 all-India normal | **858.9 mm** vs IMD's published ~868 mm (within 1.1%) |
| Old unweighted subdivision mean | ~1045 mm — about 20% too high |
| Year-to-year agreement with the subdivision series | **r = 0.945** (n = 68, 1950–2017) |
| 1972 drought | −22.5% here vs ~−24% cited |
| 2009 drought | −15.0% here vs ~−22% cited |

Averaging 36 subdivisions equally over-weights small very wet ones (the north-east, the
Konkan coast); cos(lat) area weighting removes that bias, which is what the old r = 0.77
caveat was really measuring. Departures use a **fixed 1971–2020 baseline**, IMD's current
normal period — against a series' own mean they would not be comparable with any published
figure.

**These values are internally consistent and close to the official series, but they do not
reproduce it.** IMD's headline "country as a whole" number uses subdivision-area weights
over its own subdivision set, which is a different estimator from a cos(lat) mean over every
valid grid cell; 2009 is where the two diverge most. Do not quote these as IMD's published
departures.

The IITM official AISMR series would have been the independent cross-check. Its host
(`mol.tropmet.res.in`) serves an incomplete certificate chain that Python rejects and
browsers silently repair by fetching the missing intermediate. Disabling verification in a
pipeline that commits unattended would admit unauthenticated data into the caches the causal
work depends on, so the series is dropped rather than worked around.
- **RONI approximates** NOAA's official index: fixed 1991–2020 base where NOAA uses rolling
  30-year bases. Values are close, not identical.
- **SARIMA beats the LSTM** on this short univariate series. Both beat persistence at all 12
  leads. The result is reported as-is rather than tuned until deep learning wins.
- **Ancillary indices update on ragged schedules.** SOI, PNA and WP run about a month ahead
  of the Niño regions, which run ahead of TNI and the DMI. Any model consuming them must
  handle a ragged right edge rather than assume a rectangular matrix.

### Frozen upstreams

Some public index files stop updating while still returning HTTP 200, so a naive fetch
ships years-old data as if it were current. Two are known:

| File | Status | Handling |
|---|---|---|
| CPC `wksst8110.for` | frozen at 2021-01-27 | never fetched; only `wksst9120.for` is used |
| PSL `amon.us.data` (AMO) | frozen at 2023-01 | fetched and flagged, excluded from model input |

`climate_indices.coverage()` computes each index's lag behind the freshest one and marks
anything more than 400 days behind as frozen; `model_features()` drops those columns before
any model sees them, so the exclusion happens once at the source rather than being
remembered at each call site.

### Sources deliberately not used

- **Bureau of Meteorology (RMM / MJO index).** Requesting the RMM file returns a block page
  stating the Bureau "does not support web scraping: if you are trying to access Bureau data
  through automated means, you should stop." That is the data owner declining automated
  access, so the index is out of scope rather than worked around. MJO is a daily
  sub-seasonal index and adds little to a monthly desk.
- **ISRO / IIRS satellite archives** — see the section below.

---

## ISRO, IIRS and Indian satellite data — why they are not in the pipeline

A deliberate exclusion, recorded so it reads as a decision rather than an oversight.

- **INSAT-3D / 3DR / 3DS are geostationary at 82°E.** A geostationary platform sees roughly
  ±81° of longitude, giving a disk of about 1°E–163°E. **Niño-3.4 spans 170°W–120°W — over
  the horizon.** India's meteorological satellites physically cannot observe the ENSO index
  region. They are impact-side instruments (Indian monsoon convection, Bay of Bengal, the
  western edge of the Maritime Continent), not ENSO-monitoring ones.
- **MOSDAC** (ISRO/SAC) requires account signup and approval, credentials in a plain
  `config.json`, and caps downloads at 5 000 files/day. Products are scene-level.
- **Bhoonidhi** (ISRO/NRSC) offers a cleaner STAC catalogue with JWT auth (20-minute tokens,
  20 auth requests/hour/IP) over ResourceSat-2/2A, EOS-04, EOS-06 and Cartosat-1 — still
  scene-level imagery, not time series.
- **IIRS Dehradun is a training and capacity-building institute.** It publishes courses and
  outreach material, not machine-readable feeds. The actual ISRO data doors are MOSDAC,
  Bhuvan/Bhoonidhi and VEDAS.
- **Used instead for India:** IMD gauge-based gridded rainfall and the IITM area-weighted
  AISMR series — longer records, no authentication, no CI secret.
- **What would justify revisiting:** an INSAT-3D OLR / Hydro-Estimator monsoon-convection
  panel, or Oceansat-3 OCM chlorophyll for the Peru upwelling collapse. Both need a MOSDAC
  account and a CI secret, and both are impact-side — exactly where ISRO data is strong.

---

## Versioning policy

Every stance row carries `stance_version`. **Any change to the weights, thresholds, registry
rows, gate rules, or conviction arithmetic must bump the version constant in the same
commit** — `EXPOSURE_VERSION` in `data/process/exposure_index.py`, `STANCE_VERSION` in
`data/process/positioning.py` — and add a changelog entry below.

`tests/test_core.py` enforces that this document names every `iso3` in the registry and
quotes both current version constants, so the doc cannot silently drift from the code.

## Changelog

- **`exposure-v1` / `stance-v1` (2026-08-07)** — first published methodology. Positioning
  engine replaces hand-typed desk stances; freshness is measured net of structural label
  lag. Fixed at introduction: the causal gate tested for a class literal (`strong`) that
  `landing_causation` never emits, which would have muzzled any genuinely `CAUSAL` link.
