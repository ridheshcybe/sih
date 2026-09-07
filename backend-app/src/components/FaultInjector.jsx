import { useState } from "react";
import { injectFault } from "../api/client";

const FAULTS = ["injector_degradation", "lubrication_issue", "overheating", "sensor_drift", "abnormal_vibration", "battery_alternator_degradation"];

export default function FaultInjector({ engineId, notify }) {
  const [faultType, setFaultType] = useState(FAULTS[0]);
  const [severity, setSeverity] = useState(0.7);
  const [busy, setBusy] = useState(false);

  const handleInject = async () => {
    setBusy(true);
    const result = await injectFault(engineId, faultType, severity);
    setBusy(false);
    notify(result ? "Fault injected successfully" : "Failed to inject fault", result ? "success" : "error");
  };

  return <section className="control-card fault-card">
    <div><p className="eyebrow">Scenario lab</p><h2>Fault injection</h2></div>
    <label>Fault type<select value={faultType} onChange={(event) => setFaultType(event.target.value)}>{FAULTS.map((fault) => <option key={fault}>{fault}</option>)}</select></label>
    <label>Severity <strong>{Math.round(severity * 100)}%</strong><input type="range" min="0" max="1" step="0.05" value={severity} onChange={(event) => setSeverity(event.target.value)} /></label>
    <button className="button button-danger" onClick={handleInject} disabled={busy}>{busy ? "Injecting..." : "Inject Fault"}</button>
  </section>;
}