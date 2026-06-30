# Contributing to the ENSO Macro Risk Desk

Thanks for being here. 🌊 This project is a climate-intelligence terminal whose
whole value is **causal honesty** — so contributions are welcome as long as they
keep that bar. This guide gets you from clone to PR.

New here? Start with a [`good first issue`](https://github.com/DogInfantry/El_Nino/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) —
most are ~60-line region clones with no framework changes.

---

## 1. Setup

**Python 3.12 is required** (not 3.13/3.14 — the ML/geo stack lacks wheels there, and Hugging Face Spaces runs 3.12).

```bash
git clone https://github.com/DogInfantry/El_Nino.git
cd El_Nino

py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

The dashboard reads the **parquet caches in `data/cache/`** (tracked in git) — so you can run everything immediately, no data fetching or API keys needed.

```bash
python app.py                   # whole site at http://localhost:5006
# or a single page:
panel serve dashboard/pages/00_landing.py --show
```

> `data/raw/` (ERSSTv5 netCDF, ~150 MB) is gitignored. You only need it if you're
> re-running the offline pipeline (`data/ingest/ersst_fetcher.py`, RONI, etc.).

---

## 2. Project layout (where things live)

```
data/ingest/     fetchers  → data/cache/*.parquet      (offline; run manually)
data/process/    phases · RONI · Granger+CCM · exposure index
forecasting/     SARIMA · LSTM · ensemble · skill metrics (offline)
dashboard/
  theme.py       palette · Plotly dark template · cache loaders
  components/     oni_gauge · timeseries · globe_layer
  region_template.py   the generic region deep-dive shell
  pages/         00_landing … 08_seasia   (each calls build_app()/build_region().servable())
app.py           single entry point: landing at / + all pages at route slugs
```

`CLAUDE.md` is the full working-memory doc — read it for the design decisions and gotchas before touching anything non-trivial.

---

## 3. How to add a region deep-dive (the most common contribution)

Five steps, ~60 lines, no framework code:

1. **Copy** `dashboard/pages/08_seasia.py` → e.g. `dashboard/pages/09_brazil.py`.
2. **Fill a `RegionConfig`** (the dataclass is documented in `dashboard/region_template.py`): identity, thesis, **desk view** (CONSTRUCTIVE / WATCH / CAUTIOUS + swing catalyst + risk), KPIs, hotspots (lat/lon), `commodity`, `geo_scope`, `history_rows`, `econ_takeaway`, `footer`.
3. **Provide a climate exhibit** — a simple ENSO-phase composite is fine (see `seasia_climate()` / `causal_chain` in page 08). India (page 07) shows a richer ENSO×IOD version.
4. **Register the route:** add the country to `DEEP_DIVES` in `dashboard/pages/00_landing.py` (so the leaderboard row links out) and to `_ROUTE` in `app.py`.
5. **Verify** (see §4) and open a PR.

There are ready-to-claim region issues: [Brazil #1](https://github.com/DogInfantry/El_Nino/issues/1), [Australia #2](https://github.com/DogInfantry/El_Nino/issues/2), [Peru #3](https://github.com/DogInfantry/El_Nino/issues/3), [cocoa belt #4](https://github.com/DogInfantry/El_Nino/issues/4).

---

## 4. Verifying your change

You **cannot** screenshot the live Bokeh server by waiting on `networkidle` (the WebSocket never idles). Use these instead:

- **Page builds without error** — import the module (which runs `build_app()` / `build_region()`):
  ```bash
  python -c "import importlib.util,sys; sys.path.insert(0,'dashboard'); \
    s=importlib.util.spec_from_file_location('p','dashboard/pages/09_brazil.py'); \
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print('OK')"
  ```
  …or just `python app.py` and open the route in a browser.
- **Charts** — export Plotly figures to PNG via `kaleido` (see the verification pattern used across the pages). On Windows, set `PYTHONIOENCODING=utf-8` (the console can't print `−`/`ñ`).
- **Unit tests** — `python tests/test_core.py` (pure logic, no network).

---

## 5. The honesty bar (please read — this is the point of the project)

This desk's credibility rests on **not over-claiming**. PRs that fake a clean result will be asked to change:

- **Report the *computed* causal verdict, not a convenient one.** If Granger/CCM says a link is weak or confounded, say so — that's a feature (the "misattribution guard"), not a failure. Cocoa and wheat were *expected* to fail; the data said wheat is actually one of the stronger links, and the desk reports *that*.
- **Granger uses linear detrend, not first-differencing** (differencing kills the low-frequency ENSO band). See `data/process/granger_ccm.py` and the note in `CLAUDE.md`.
- **Label ONI vs RONI** on every index chart (they're not interchangeable — NOAA adopted RONI as official on 16 Feb 2026).
- **Flag illustrative / placeholder data** explicitly in the page footer (e.g. India's crop KPIs are placeholders pending real ingestion — see issue #7).
- **Correlation ≠ causation** — sector correlations belong on Page 04; causal claims need Page 05's Granger/CCM.

If a result is unflattering, that's usually the *interesting* result here. Keep it.

---

## 6. Code style

- **Black-formatted**, **fully type-hinted**, and every module/function has a docstring.
- **Cite the data source** in docstrings when you add a fetcher or a derived series.
- Match the surrounding code's idiom (the theme palette is in `dashboard/theme.py` — use `COLORS`, don't hardcode hex).
- Keep new caches **small** if you commit them to `data/cache/` (they're tracked so the app runs offline); large raw inputs stay gitignored.

---

## 7. Pull request workflow

```bash
git checkout -b feat/brazil-region
# ...make your change, verify (§4)...
git add dashboard/pages/09_brazil.py app.py dashboard/pages/00_landing.py
git commit -m "feat: add Brazil / coffee region deep-dive"
git push -u origin feat/brazil-region
gh pr create   # or open a PR on GitHub
```

In the PR description: link the issue (`Closes #1`), say how you verified, and — for any causal/data claim — note the source and any caveat. Pushing to `master` auto-deploys to the live Space via GitHub Actions, so PRs are reviewed before merge.

Questions? Open a [discussion or issue](https://github.com/DogInfantry/El_Nino/issues). Thanks for contributing. 🙌
