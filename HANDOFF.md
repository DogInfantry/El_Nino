# HANDOFF — 2026-06-27

Session handoff for the **ENSO Intelligence Platform** (`El_Nino`). The user is starting
a fresh chat to begin implementation. Read `CLAUDE.md` (repo root) first for the full
project memory — this file is the *session-specific* resume note.

---

## Exact task we were doing

**Brainstorming/designing the dashboard's landing page and region deep-dive pages** using
the superpowers **brainstorming** skill + Visual Companion (HTML mockups served from a
local server, files in the gitignored `.superpowers/brainstorm/`).

This session did NOT write any Python. It was pure design iteration. Two designs were
driven to "locked" status with the user reacting to live HTML mockups:

1. **Landing page — "ENSO Macro Risk Desk" — LOCKED at v4.**
   The big pivot: the original flat SST-anomaly map read as a generic "high-school"
   visualization. We reframed the front door as a **finance-style macro risk desk** that
   *blends climate-science and Bloomberg-terminal idioms* — the project's actual thesis.
   Final layout (`.superpowers/brainstorm/1954-1782430142/landing-risk-desk-v4.html`):
   - `ENSO<GO>` command bar + function tabs (MAP / FCST / IMPACT / CAUSAL / HIST)
   - scrolling impact ticker
   - **left rail** = three instruments: Niño-3.4 gauge, ONI 24-mo trajectory sparkline,
     12-mo forecast cone (with skeptic model dashed)
   - **center** = world **ENSO Exposure Index choropleth** (computed score per country,
     NOT raw SST), Pacific-centered, clickable countries → region deep-dive
   - **right** = ranked "most-exposed regions" leaderboard (bars)
   - **bottom** = **causation strip**: 6 `ONI→commodity` cards, each with a verdict badge
     (CAUSAL / MODERATE / WEAK / NONE) + Granger/CCM stats + a convergence mini-chart.
     **Cocoa and wheat deliberately FAIL** — this is the misattribution guard, built into
     the UI (cocoa's 2023-24 spike was disease, not El Niño).

2. **India region deep-dive — "research-note" layout — LOCKED (user chose Option A).**
   `.superpowers/brainstorm/363-1782522811/region-india-research-note.html`.
   India **tear-sheet pinned on the RIGHT** (sticky: flag, India silhouette, at-a-glance
   key-values, "house view"); main body **tabbed Climate / Agriculture / Economics /
   History**. This is the **template for all region deep-dives** — build India first,
   then clone.

**Final action of the session:** user said "I'll go with Option A" and asked for this
handoff before moving to a new chat. Design phase is DONE; next chat is BUILD.

---

## What worked

- **Reframing the map as a "risk desk," not a heatmap.** The user's "looks like a high
  school project" critique was the turning point. The winning idea: show a *derived
  decision metric* (exposure index) instead of the raw physical SST field — the
  finance inversion. User picked "A's bones + D's skin" (map-hero structure + terminal
  chrome) over a pure six-panel cockpit.
- **Turning vague panels into instruments.** User wanted "striking, accurate, not texty."
  Rebuilding each panel as a real data-viz (gauge / sparkline / forecast cone / ranked
  bars / heat→causation strip) landed well.
- **The causation strip** (user's pick for the bottom panel) — showing that some
  ONI→commodity links FAIL the Granger/CCM test is the most-praised idea; it doubles as
  the rigor/honesty signal.
- **Self-contained full-HTML mockups** (d3 from CDN) rendered the real world map
  convincingly and let the user click pins/countries.
- **Honest sanity-checking of every placeholder number** built trust (the user is
  equity-research-minded and explicitly asked for it).

## What didn't work / friction

- **The brainstorm Visual Companion frame squeezed fragment-style content into a narrow
  left column.** Fix: write mockups as **full `<!DOCTYPE html>` documents** (the server
  serves those as-is, only injecting its helper script) — see `landing-risk-desk-v2.html`
  onward. Do this for any future mockups.
- **Companion servers die between sessions.** Each `/` (session restart) spawns a NEW
  server on a NEW port and a NEW `screen_dir`; old browser tabs point at dead ports.
  Mockup *files* persist; the server does not. Restart via
  `~/.claude/plugins/cache/claude-plugins-official/superpowers/<ver>/skills/brainstorming/scripts/start-server.sh --project-dir <repo>`
  (run in background on Windows), then copy the newest `.html` into the new `screen_dir`.
- **`jq` is not installed** — JSON one-liners silently no-op; use PowerShell
  `ConvertFrom-Json` or grep/sed.
- **Early mis-sequencing:** I mocked the region detail before the map; user corrected
  "the start should be the MAP." Lesson: design the landing first, then drill-downs.

---

## Files modified / created this session

### Repo (git-tracked or trackable)
- `CLAUDE.md` — **updated** this handoff (India flipped to LOCKED/Option A; Active Task
  and Next Steps now point at building `07_india.py`). Still **untracked** in git — commit it.
- `.gitignore` — earlier modified to add `.superpowers/` (shows as modified in `git status`).
- `HANDOFF.md` — **this file (new)**.

### Mockups (gitignored `.superpowers/brainstorm/` — design reference, NOT source)
- `1954-1782430142/landing-risk-desk-v4.html` — **LOCKED landing design**
- `1954-1782430142/landing-risk-desk-v2.html`, `-v3.html` — earlier landing iterations
- `1954-1782430142/landing-directions.html` — the 4 concept wireframes (A/B/C/D)
- `1954-1782430142/map-scientific-2d.html` — 2D scientific instrument map exploration
- `1954-1782430142/impact-explorer-map-v2.html` — early d3 pin map
- `1954-1782430142/region-detail-india.html` — first (single-scroll) India deep-dive
- `363-1782522811/region-india-research-note.html` — **LOCKED India design (Option A)**

### NOT changed
- No Python files were touched. The 6 existing dashboard pages, all engines, all caches,
  and `requirements.txt` are exactly as committed at `ddd4b0f`.

---

## Next steps (in order)

1. **Build `dashboard/pages/07_india.py`** from the locked research-note mockup.
   Tear-sheet pinned right; tabs Climate / Agriculture / Economics / History. Use
   `dashboard/theme.py` color tokens (already match the mockups). Wire real engines:
   Climate = monsoon/rainfall composites; Agriculture = crop tiles; Economics =
   `lag_correlator` + `granger_ccm` verdict; History = `enso_phase_labeler` events.
2. **Refactor `07_india.py` into a parameterised region template** so other regions are cheap.
3. **Build the landing** ("ENSO Macro Risk Desk" v4) as the Panel entry page; country
   click → region deep-dive.
4. **Define + document the ENSO Exposure Index** formula (constructed score; label as such).
5. **Resolve d3-vs-Plotly per component** (see CLAUDE.md "Active Task"): prefer Plotly
   where an equivalent exists (CI-verifiable); custom HTML/JS pane only where needed; NO pydeck.
6. **Commit** the new pages + the untracked `CLAUDE.md` + `.gitignore` change.
7. **Push to GitHub** — no remote configured yet (`git remote add origin …`).
8. Optional backlog: HF Spaces deploy, EM-DAT bubbles (page 02), surrogate significance (page 05).

---

## Commands to run first (new chat)

```bash
# 1. From repo root, activate the Python 3.12 venv (NOT system 3.14 — see Gotchas)
cd "C:/Users/Anklesh/Documents/Claude_Code/El_Nino"
.venv/Scripts/activate          # Windows (PowerShell/Git-Bash)

# 2. Confirm the existing dashboard still runs
panel serve dashboard/pages/01_enso_monitor.py --show

# 3. Re-open the LOCKED design mockups in a browser to work against them
#    (open the files directly — no server needed):
#    .superpowers/brainstorm/1954-1782430142/landing-risk-desk-v4.html
#    .superpowers/brainstorm/363-1782522811/region-india-research-note.html

# 4. Sanity-check git state
git status            # expect: modified .gitignore, untracked CLAUDE.md + HANDOFF.md
git log --oneline -3  # latest should be ddd4b0f
```

**Then start with Next Step #1: build `dashboard/pages/07_india.py`.**
