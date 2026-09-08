# Demo Script — SIH26054 (5 minutes)

Setup before the judges arrive: backend + frontend running
(`bash scripts/start_demo.sh`), models trained, mission stopped.

| # | Time | Presenter action | On screen | Key trends | System response | Narration (1 line) |
|---|---|---|---|---|---|---|
| 1 | 0:00–0:30 | Click **Start Mission** (profile `standard_isr`) | Health gauge ≈ 95+, status OPERATIONAL, charts begin streaming | RPM climbs to ~2500, EGT ~450 °C | Twin state streaming live at 10 Hz | "This is a healthy engine flying a standard ISR profile — digital twin is live." |
| 2 | 0:30–1:00 | Point at telemetry table + charts | Live telemetry rows, EGT/CHT/RPM charts | Stable within envelopes | Health Index steady | "Every sensor is compared against the physics-based twin model in real time." |
| 3 | 1:00–1:30 | Pick `injector_degradation`, severity 0.6, click **Inject Fault** | Toast confirms injection | Fuel flow dips, EGT/CHT creep up | Anomaly score starts rising | "Now we inject a realistic fuel-injector degradation." |
| 4 | 1:30–2:15 | Point at alerts + health chart | Anomaly badge, fault alert `injector_degradation` | EGT +50 °C over baseline | Anomaly detection fires; fault classifier identifies injector degradation | "The model flags the anomaly and classifies the fault before it becomes critical." |
| 5 | 2:15–3:00 | Point at RUL + degradation | RUL counting down, Health Index falling | HI drops 95 → ~70 | RUL estimate falls from ~500 h | "Health Index and Remaining Useful Life are degrading together — this is the prognosis." |
| 6 | 3:00–3:30 | Point at advisory panel | MEDIUM advisory: injector service within 25 h | — | Actionable maintenance advice generated | "The twin doesn't just warn — it tells the maintenance engineer what to do." |
| 7 | 3:30–4:00 | Click **Stop Mission** | Mission ends, toast confirms | — | Mission report generated | "Mission complete — the whole event has been recorded." |
| 8 | 4:00–4:30 | Click **Replay (5x)** | Mission replays at 5x, charts scroll | — | Replay broadcasts stored data | "And we can replay the entire mission post-flight for analysis." |
| 9 | 4:30–5:00 | Open **Reports** → mission | Diagnostic summary: avg/min HI, fault counts, advisories, final RUL | — | Report served | "Finally, a full diagnostic report — event, root cause, and required maintenance." |

Closing line: "Synthetic data today, but the architecture is ready to ingest real
telemetry and retrain — that's our path to test-rig validation."

## 2-minute backup demo

1. **Start Mission** (`standard_isr`). *(0:00–0:15)*
2. Show healthy twin: gauge ≥ 95, stable charts. *(0:15–0:30)*
3. **Inject Fault** — `lubrication_issue`, severity 0.8. *(0:30–0:45)*
4. Watch oil pressure drop, anomaly fire, HI fall, RUL drop, HIGH advisory
   ("reduce load by 20%"). *(0:45–1:30)*
5. **Stop Mission** → open **Reports**, show summary. *(1:30–2:00)*

Fallback if the live sim misbehaves: restart mission (Stop → Start) or skip
replay; the Reports page always has the last completed mission.