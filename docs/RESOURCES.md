# Resources, and what is actually worth adopting

A working record of tools, references and data sources evaluated for this project. Each
entry carries a verdict, not just a link, so the same question does not get re-opened every
few months.

Nothing here is wired into the pipeline. Anything marked **candidate** is a decision made
ready, not a decision taken.

---

## 1. Visualization and dashboard frameworks

The honest summary: of the seven repositories gathered, one is already the stack, one is
genuinely adoptable, and the rest solve a different problem than this project has.

| Project | Verdict | Why |
|---|---|---|
| [holoviz/panel](https://github.com/holoviz/panel) | **In use** | Already the stack, pinned at 1.9.3. The whole app is `panel serve` behind `app.py`. |
| [perspective-dev/perspective](https://github.com/perspective-dev/perspective) | **Candidate, the only one** | WASM pivot grid built for streaming financial data. An `exposure_index` and `positioning` table a reader can sort, filter and pivot in place is the single upgrade that would most make this feel like a terminal rather than a report. Caveats below. |
| [apache/superset](https://github.com/apache/superset) | **Rejected** | A BI server with its own metadata database and auth. This deploys as one free-tier Docker Space serving parquet; adding Superset means adding infrastructure that dwarfs the app. |
| [getredash/redash](https://github.com/getredash/redash) | **Rejected** | Same shape as Superset. Query-against-a-warehouse is not the problem here; there is no warehouse, there are 25 parquet files. |
| [glue-viz/glue](https://github.com/glue-viz/glue) | **Rejected** | Desktop Qt application for linked-view exploration, aimed at astronomy workflows. Not deployable as a web page. |
| [mckinsey/vizro](https://github.com/mckinsey/vizro) | **Inspiration only** | A Plotly Dash framework, so adopting it means replacing Panel. Its layout grammar and KPI-card conventions are worth reading before the CSS consolidation noted below. |

### On Perspective specifically

Why it is a candidate and not a decision: this repo's verification is headless. Figures are
checked by importing the page and exporting through kaleido. A Perspective grid is a web
component and produces nothing kaleido can see, which is the same objection that got pydeck
rejected.

The difference is that Perspective is *verifiable by another route*. The live Space is
already checked by walking `shadowRoot`s through JavaScript evaluation, because Panel mounts
into shadow DOM. A grid can be asserted the same way. That makes it acceptable where WebGL
was not, provided the check is written at the same time as the grid, and provided the page
still renders a plain HTML table when the component fails to load.

Load it from a pinned CDN build. There is no bundler in the Space image, and
`requirements-space.txt` deliberately carries no JavaScript tooling.

---

## 2. Design references

For the `web/` front door, which is what a recruiter sees first and which currently
advertises four of the fourteen pages.

- **[21st.dev](https://21st.dev)**, React component gallery. `web/` is Next.js 15 with a
  static export, so these drop in directly.
- **awesome-design** and **impeccable.style**, general visual references. Useful for hero
  and section rhythm rather than for components.
- **gitdesign.md**, design-guideline conventions for repositories, relevant to how the
  README itself reads.

### WebGPU: recommended against

This project already rejected pydeck on the grounds that WebGL is unverifiable headless.
WebGPU inherits that objection and adds a narrower support matrix. The globe on page 02 is
a Plotly Scattergeo precisely so it can be asserted by a test. Changing that trades a
checkable claim for a prettier one, which is the opposite of this project's argument.

If the goal is a better globe, the cheaper win is the orthographic toggle page 02 already
has, plus better colour and graticule work inside Plotly.

---

## 3. Free data APIs evaluated

### The constraint that governs all of these

`data/cache/commodities.parquet` ends at **2024-12** by an explicit methodological decision
recorded in `data/ingest/source_registry.py`. Every causal verdict, every exposure index
value and every stance rests on that file. Splicing a second price source into it would
invalidate the lag, Granger and CCM work that is the whole moat.

So any new price source is a **parallel cache with its own registry row**, never a splice.
`positioning.VERDICT_KEY` already fails safe: a commodity with no verdict row is UNTESTED
and the causal gate caps it at WATCH. That is the property a new source must not break.

### FRED, for commodity prices after the cutoff

- Free API key, no rate limit worth worrying about at this volume.
- Serves the IMF Primary Commodity Price System monthly, covering the same commodities the
  Pink Sheet does.
- **Verified series:** `PCOCOUSDM`, global price of cocoa, US dollars per metric ton,
  monthly, not seasonally adjusted, from 1980, sourced from the IMF.
- Siblings for coffee, palm oil, wheat and sugar follow the same IMF naming pattern.
  **Confirm each identifier against FRED's own series search before wiring it** rather than
  trusting a guessed symbol. A wrong-but-valid series is worse than no series.
- **Use:** an overlay panel showing what prices did after the Pink Sheet cutoff, on its own
  axis and clearly labelled as a different source. Not an extension of the existing series.

### data.gov.in, for the India layer

- A key is held for this. See the secrets section below before using it.
- **Agmarknet daily mandi prices**, wholesale minimum, maximum and modal by commodity,
  variety and market, across roughly 300 commodities and 2000 varieties.
  Catalogue: `https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi`
  Resource: `https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity`
- **The catch, and it decides the sequencing:** the public resource is a *current snapshot*,
  not a history. A usable series means accumulating daily pulls over months before any panel
  can say anything. That is a project, not an afternoon.
- **What it would unlock:** ENSO to monsoon to actual Indian domestic crop prices, carrying
  the describe-to-prescribe thesis a step past what the Pink Sheet can reach.
- **It would also fix a provenance gap.** `monsoon_fetcher.py` reads a third-party GitHub
  CSV mirror of the IMD subdivision data. The registry now says so plainly, but a keyed
  data.gov.in fetcher would let that row become a live feed instead of a 1901–2017 static.

### Others worth knowing

| Source | Key | Good for | Note |
|---|---|---|---|
| World Bank Indicators API | none | Production and export shares behind the curated `E` factor in `exposure_index.py` | More stable than the XLSX `pink_sheet.py` already parses |
| EIA | free | US energy series, relevant to the energy transition angle | Not ENSO-linked; a separate story |
| Stooq | none | Daily OHLC for commodity futures and FX, plain CSV | Useful for a live price strip, not for causal work |
| **yfinance** | none | **Avoid** | Unofficial endpoint with unclear terms. The monthly refresh runs unattended in CI, and a silently changing source there would corrupt caches nobody is watching. |

### Sources already ruled out, recorded so they stay ruled out

The Bureau of Meteorology (RMM/MJO) serves a block page asking that scraping stop, which is
the data owner declining. IITM AISMR presents an incomplete TLS chain that Python rejects
and browsers silently repair; `verify=False` in a pipeline that commits unattended would
admit unauthenticated data into the caches the causal work rests on. ISRO, MOSDAC, Bhoonidhi
and IIRS are covered in `METHODOLOGY.md`; the short version is that INSAT-3D sits at 82°E
and physically cannot see Niño-3.4.

---

## 4. Secrets

No fetcher in `data/ingest/` currently uses a key. Every one is an anonymous GET with a
descriptive user agent, and `.env.example` says so.

What is already in place for when that changes:

- `python-dotenv` is a declared dependency in `requirements.txt` and is **never called**.
  Wiring a key starts with one `load_dotenv()`.
- `.gitignore` already covers `.env` and `.cdsapirc`.
- `data/ingest/_common.py` `get_session()` is the single choke point where an auth header
  belongs, so every fetcher keeps an identical shape.
- `data/ingest/source_registry.py` `REGISTRY` is the other choke point. A new source with no
  `Source(...)` row is invisible to the status page and to `/api/sources`.

**Rules for this repo specifically.** `data/cache/*.parquet` is deliberately tracked, so this
repository commits its data and pushes it to both GitHub and the Hugging Face Space. A key
placed in a source file ships to both. Keys live in `.env` locally, in a repository secret
for Actions, and in a Space secret for Hugging Face. This file records variable names only,
never values. A key that has been pasted into a chat window, an issue or a commit should be
treated as exposed and rotated before first use.

Variable names reserved and documented in `.env.example`, read by nothing today:
`DATA_GOV_IN_API_KEY`, `FRED_API_KEY`.

---

## 5. Known duplications, worth reading before editing

Places where one edit silently needs a second.

- **The tagline lives in two SVGs.** `assets/hero.svg` and `web/public/assets/hero.svg` both
  bake it into `<text>`. Change one and the rendered hero contradicts the prose beside it.
- **The palette lives twice.** `dashboard/theme.py` `COLORS` and `web/app/globals.css`
  `:root` custom properties carry the same values, unshared.
- **Ten stylesheet blocks.** Every page family builds its own f-string CSS and injects it
  through `pn.extension(raw_css=...)`. `.enso-card` is defined with three different paddings,
  and `.chip` means two different things in `region_template.py` and `06_historical.py`.
  Consolidating is worth a session where visual QA is the whole job, because the only
  verification is looking at it.
- **The About text lived in three files.** Now solved: `docs/ABOUT.md` is canonical and
  `tests/test_core.py::test_about_copy_is_single_sourced` fails on drift.

---

## 6. House style for user-facing copy

No em dashes. No hyphen standing in for one, which is worse than the dash it replaces.
Recast with a comma, a colon or a full stop. Keep hyphens that do real work, such as
area-weighted or walk-forward. En dashes in numeric ranges like 1950–2026 are correct.

`tests/test_core.py::test_user_facing_copy_has_no_em_dashes` enforces this over the published
prose files. Dashboard strings that reach the browser were cleared in the same pass. Module
docstrings were deliberately left alone, being internal and, in the causal core, not worth
opening a file for.
