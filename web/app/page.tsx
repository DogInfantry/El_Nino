"use client";

import { useEffect, useState } from "react";

const APP = "https://doginfantry-enso-macro-risk-desk.hf.space/";
const API =
  "https://huggingface.co/api/spaces/DogInfantry/enso-macro-risk-desk/runtime";

type DeskState = {
  cls: string;
  label: string;
  note: string;
};

const STATES: Record<string, DeskState> = {
  live: { cls: "pill live", label: "LIVE", note: "desk is warm — opens instantly" },
  warming: { cls: "pill", label: "WARMING…", note: "free-tier host waking up — ~30s" },
  offline: { cls: "pill", label: "OFFLINE", note: "host is down — the launch button may not respond" },
};

/**
 * Prewarm + honest status.
 * - The hidden iframe GET is what actually wakes a sleeping Space, so it's
 *   warm by the time the visitor clicks LAUNCH.
 * - The pill is driven by the HF runtime API (CORS-enabled), NOT the iframe
 *   load event — cross-origin `load` fires even on a 503 error page, so it
 *   cannot distinguish LIVE from down.
 */
function useDeskStatus(): DeskState {
  const [state, setState] = useState<DeskState>(STATES.warming);

  useEffect(() => {
    let tries = 0;
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;

    const retry = () => {
      // ponytail: 36 x 5s = 3 min cap, then leave the last honest state up.
      if (!cancelled && ++tries < 36) timer = setTimeout(poll, 5000);
    };
    const poll = () => {
      fetch(API)
        .then((r) => r.json())
        .then((j: { stage?: string }) => {
          if (cancelled) return;
          if (j.stage === "RUNNING") setState(STATES.live);
          else if (j.stage === "RUNTIME_ERROR" || j.stage === "PAUSED") setState(STATES.offline);
          else {
            // SLEEPING / BUILDING / RESTARTING etc.: our iframe hit is waking it.
            setState(STATES.warming);
            retry();
          }
        })
        .catch(retry);
    };
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return state;
}

export default function Home() {
  const status = useDeskStatus();

  return (
    <div className="wrap">
      <div className="topbar">
        <span className="cmd">
          ENSO<span className="go">&lt;GO&gt;</span>
        </span>
        <span style={{ color: "var(--muted)" }}>Macro Risk Desk</span>
        <span className="spacer" />
        <span className={status.cls}>
          <span className="dot" />
          <span>{status.label}</span>
        </span>
      </div>

      <section className="hero">
        <div className="backdrop" />
        <h1>
          ENSO <span className="accent">Macro Risk Desk</span>
        </h1>
        <p className="thesis">
          When the ENSO cycle shifts: which commodity &amp; sector exposures to
          reposition &mdash; and which ENSO&rarr;price links are causally real
          vs. spurious. ONI/RONI monitoring &middot; SARIMA+LSTM forecasts
          &middot; Granger + CCM causal testing.
        </p>
        <div className="cta-row">
          <a className="btn btn-primary" href={APP}>
            LAUNCH DESK &rarr;
          </a>
          <a className="btn btn-ghost" href="https://github.com/DogInfantry/El_Nino">
            SOURCE ON GITHUB
          </a>
          <span className="coldstart">{status.note}</span>
        </div>
        <a className="shot" href={APP} aria-label="Open the live desk">
          <img
            src="/assets/desk-landing.png"
            alt="ENSO Macro Risk Desk — landing: ONI gauge, forecast cone, exposure choropleth, causation strip"
          />
        </a>
      </section>

      <h2 className="section">Desk pages</h2>
      <div className="grid">
        <a className="card" href={`${APP}03_forecast`}>
          <img src="/assets/forecast.png" alt="Forecast fan chart" loading="lazy" />
          <div className="label">
            <b>Forecast</b>
            <span>SARIMA / LSTM / ensemble cone + skill-by-lead</span>
          </div>
        </a>
        <a className="card" href={`${APP}02_global_map`}>
          <img src="/assets/global-map.png" alt="Global SST anomaly map" loading="lazy" />
          <div className="label">
            <b>Global Map</b>
            <span>ERSSTv5 anomalies, Ni&ntilde;o-3.4 box, teleconnections</span>
          </div>
        </a>
        <a className="card" href={`${APP}05_causation`}>
          <img src="/assets/causation.png" alt="Causation explorer" loading="lazy" />
          <div className="label">
            <b>Causation Explorer</b>
            <span>Granger + CCM &mdash; the misattribution guard</span>
          </div>
        </a>
        <a className="card" href={`${APP}07_india`}>
          <img src="/assets/india.png" alt="India deep dive" loading="lazy" />
          <div className="label">
            <b>India Deep Dive</b>
            <span>ENSO &times; IOD monsoon engine, desk view</span>
          </div>
        </a>
      </div>

      <footer>
        <span>
          ENSO Macro Risk Desk &mdash; portfolio project by{" "}
          <a href="https://github.com/DogInfantry">Anklesh Rawat</a>
        </span>
        <span>
          Served live from{" "}
          <a href="https://huggingface.co/spaces/DogInfantry/enso-macro-risk-desk">
            Hugging&nbsp;Face Spaces
          </a>
        </span>
        <span>Not investment advice.</span>
      </footer>

      {/* Prewarm iframe: waking the Space is its only job. */}
      <iframe id="prewarm" title="prewarm" aria-hidden="true" tabIndex={-1} src={APP} />
    </div>
  );
}
