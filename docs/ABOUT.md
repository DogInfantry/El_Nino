# About the ENSO Macro Risk Desk

This file is the canonical description of the project. `README.md` and the
Hugging Face Space card (`deploy/hf/README.md`) both embed the blocks below
between `about:start` and `about:end` markers, and `web/app/layout.tsx` carries
the one-line pitch as its meta description.

`tests/test_core.py::test_about_copy_is_single_sourced` fails if any of them
drift. Edit here, then paste into the marked blocks. Do not edit the copies.

House style for everything below, and for user-facing copy generally: no em
dashes, and no hyphen standing in for one. Recast the sentence with a comma, a
colon, or a full stop instead. Keep hyphens only where they do real work, as in
area-weighted or walk-forward. En dashes in numeric ranges such as 1950–2026 are
correct and stay.

---

## One line

<!-- oneline:start -->
When the ENSO cycle shifts, which commodity and sector exposures to reposition, and which of those links are causally real rather than spurious.
<!-- oneline:end -->

## Summary

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
**[`docs/METHODOLOGY.md`](METHODOLOGY.md)**, rendered in-app as page 09 and
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

---

## Why the canonical block stops where it does

The marked block covers what the project *is* and what it *runs on*. That is
exactly the part that drifted: the page count went stale in three places at once,
and the causal claim went stale in two.

What is deliberately **not** in the shared block:

- **This month's stances.** The README used to state that India read WATCH and
  SE Asia CAUTIOUS. One refresh later every region reads WATCH, because the
  surrogate null moved all seven links to *weak* and the causal gate caps a weak
  link at WATCH. Copy that quotes a current stance is copy that rots on a
  schedule. Describe the mechanism; let the page render the number.
- **Per-page detail and screenshots.** Local to the README.
- **The Space landing walk-through.** Local to the Space card.
- **Scope and limits.** `docs/METHODOLOGY.md` opens with "What this desk is, and
  is not", which answers a different question and is rendered verbatim by page
  09. It points here rather than repeating this.
