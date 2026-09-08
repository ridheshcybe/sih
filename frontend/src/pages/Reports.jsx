import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";

export default function Reports() {
  const [params, setParams] = useSearchParams();
  const selected = params.get("mission") || "";
  const [missions, setMissions] = useState([]);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .listMissions()
      .then(setMissions)
      .catch((e) => setError(e.message));
  }, []);

  const loadReport = useCallback(
    (missionId) => {
      if (!missionId) {
        setReport(null);
        return;
      }
      api
        .getReport(missionId)
        .then((r) => {
          setReport(r);
          setError(null);
        })
        .catch((e) => setError(e.message));
    },
    []
  );

  useEffect(() => {
    if (selected) loadReport(selected);
  }, [selected, loadReport]);

  const select = (missionId) => setParams({ mission: missionId });

  return (
    <div className="page">
      <h2>Mission Reports</h2>
      <label>
        Mission
        <select value={selected} onChange={(e) => select(e.target.value)}>
          <option value="">— select a mission —</option>
          {missions.map((m) => (
            <option key={m.mission_id} value={m.mission_id}>
              {m.mission_id} · {m.profile_id} · {m.status}
            </option>
          ))}
        </select>
      </label>

      {error ? <p className="error-text">{error}</p> : null}
      {!report && !error ? <p className="muted">Select a mission to view its diagnostic summary.</p> : null}

      {report ? (
        <div className="report">
          <div className="grid-main">
            <Stat label="Mission" value={report.mission_id} />
            <Stat label="Profile" value={report.profile_id} />
            <Stat label="Status" value={report.status} />
            <Stat label="Duration" value={report.duration_sec != null ? `${report.duration_sec}s` : "—"} />
            <Stat label="Telemetry rows" value={report.telemetry_rows} />
            <Stat label="Avg Health Index" value={report.health_index?.average ?? "—"} />
            <Stat label="Min Health Index" value={report.health_index?.minimum ?? "—"} />
            <Stat label="Final Health Index" value={report.health_index?.final ?? "—"} />
            <Stat label="Final RUL" value={report.rul_estimate_final != null ? `${report.rul_estimate_final} h` : "—"} />
            <Stat label="Final Degradation" value={report.degradation_final != null ? `${(report.degradation_final * 100).toFixed(0)}%` : "—"} />
          </div>

          <h3>Fault Predictions</h3>
          {Object.keys(report.fault_predictions || {}).length === 0 ? (
            <p className="muted">No faults predicted during this mission.</p>
          ) : (
            <ul className="alerts">
              {Object.entries(report.fault_predictions).map(([f, n]) => (
                <li key={f} className="alert-fault">
                  {f} — {n} detection{n > 1 ? "s" : ""}
                </li>
              ))}
            </ul>
          )}

          <h3>Advisories</h3>
          {(report.advisories || []).length === 0 ? (
            <p className="muted">No advisories recorded.</p>
          ) : (
            <ul className="alerts">
              {report.advisories.map((a, i) => (
                <li key={i} className={`alert-${a.priority === "HIGH" ? "error" : "advisory"}`}>
                  <span className="alert-time">{new Date(a.timestamp).toLocaleString()}</span>
                  [{a.priority}] {a.text}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value ?? "—"}</div>
    </div>
  );
}