import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from "recharts";
import { api, FAULT_TYPES, PROFILES } from "../api/client.js";
import { useEngineSocket, useSeries } from "../ws/useEngineSocket.js";
import HealthGauge from "../components/HealthGauge.jsx";
import StatCard from "../components/StatCard.jsx";
import { useToast } from "../components/Toasts.jsx";

const ENGINE_ID = "ENG-001";
const timeLabel = (iso) =>
  iso ? new Date(iso).toLocaleTimeString("en-GB", { hour12: false }) : "";

function chartPoint(row, label) {
  return {
    t: label,
    egt: row.egt,
    cht: row.cht,
    rpm: row.rpm,
    oil_pressure: row.oil_pressure,
    vibration: row.vibration_rms,
  };
}

function twinPoint(twin, label) {
  return {
    t: label,
    health_index: twin.health_index,
    // scale 0-1 to the chart's 0-100 domain
    anomaly_score: twin.anomaly_score == null ? null : twin.anomaly_score * 100,
    degradation: twin.degradation_level,
  };
}

const chartTheme = (color) => ({
  stroke: color,
  strokeWidth: 2,
  dot: false,
  isAnimationActive: false,
  type: "monotone",
});

export default function Dashboard() {
  const toast = useToast();
  const [backendOk, setBackendOk] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [missionId, setMissionId] = useState(null);
  const [twin, setTwin] = useState(null);
  const [telemetryRows, setTelemetryRows] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [missions, setMissions] = useState([]);
  const [phase, setPhase] = useState("—");

  // controls
  const [profileId, setProfileId] = useState(PROFILES[0]);
  const [duration, setDuration] = useState(600);
  const [faultType, setFaultType] = useState(FAULT_TYPES[1]);
  const [severity, setSeverity] = useState(0.6);
  const [faultDuration, setFaultDuration] = useState(240);
  const [replayMission, setReplayMission] = useState("");
  const [busy, setBusy] = useState(false);

  const sensorSeries = useSeries(600);
  const healthSeries = useSeries(600);
  const rowCount = useRef(0);

  const refreshMissions = useCallback(async () => {
    try {
      const list = await api.listMissions();
      setMissions(list);
      setReplayMission((prev) => prev || (list[0]?.mission_id ?? ""));
    } catch {
      /* backend down - ignore */
    }
  }, []);

  const hydrate = useCallback(async () => {
    try {
      await api.systemHealth();
      setBackendOk(true);
      const state = await api.getEngineState(ENGINE_ID);
      if (state.running) setRunning(true);
      if (state.mission) {
        setMissionId(state.mission.mission_id);
        if (state.mission.status !== "running") setRunning(false);
      }
      if (state.twin_state) setTwin(state.twin_state);
    } catch {
      setBackendOk(false);
    }
  }, []);

  const onWsMessage = useCallback(
    (msg) => {
      if (!msg?.event) return;
      const p = msg.payload;
      switch (msg.event) {
        case "telemetry_update": {
          if (p.phase) setPhase(p.phase);
          const point = chartPoint(p, timeLabel(p.timestamp));
          sensorSeries.push(point);
          setTelemetryRows((prev) => [...prev.slice(-19), p]);
          break;
        }
        case "twin_state_update": {
          setTwin(p);
          healthSeries.push(twinPoint(p, timeLabel(p.timestamp)));
          if (p.top_fault && p.top_fault !== "none") {
            setAlerts((prev) =>
              [
                { kind: "fault", time: timeLabel(p.timestamp), text: `${p.top_fault} (${(p.top_probability * 100).toFixed(0)}%)` },
                ...prev,
              ].slice(0, 8)
            );
          }
          if (p.advisory && p.advisory.text && !p.advisory.text.startsWith("No active")) {
            setAlerts((prev) =>
              [
                { kind: "advisory", time: timeLabel(p.timestamp), text: `${p.advisory.priority}: ${p.advisory.text}` },
                ...prev,
              ].slice(0, 8)
            );
          }
          break;
        }
        case "fault_prediction": {
          setAlerts((prev) =>
            [
              { kind: "fault", time: timeLabel(p.timestamp), text: `${p.fault_type} (${(p.probability * 100).toFixed(0)}%)` },
              ...prev,
            ].slice(0, 8)
          );
          break;
        }
        case "simulation_status": {
          if (p.running === false) {
            setRunning(false);
            toast("Mission ended", "info");
            refreshMissions();
          }
          break;
        }
        case "replay_status": {
          setReplaying(!!p.replaying);
          break;
        }
        case "system_error":
          setAlerts((prev) => [{ kind: "error", time: timeLabel(p.timestamp), text: p.message }, ...prev].slice(0, 8));
          break;
        default:
          break;
      }
    },
    [sensorSeries, healthSeries, toast, refreshMissions]
  );

  const { connected } = useEngineSocket(ENGINE_ID, onWsMessage);
  useEffect(() => setWsConnected(connected), [connected]);

  // hydrate + polling fallback
  useEffect(() => {
    hydrate();
    refreshMissions();
    const id = setInterval(() => {
      api
        .getEngineState(ENGINE_ID)
        .then((state) => {
          setBackendOk(true);
          if (state.running) setRunning(true);
          if (state.mission && state.mission.status !== "running") setRunning(false);
        })
        .catch(() => setBackendOk(false));
    }, 5000);
    return () => clearInterval(id);
  }, [hydrate, refreshMissions]);

  const startMission = async () => {
    setBusy(true);
    try {
      const res = await api.startMission({
        mission_name: `Demo ${profileId}`,
        profile_id: profileId,
        engine_id: ENGINE_ID,
        duration_s: Number(duration) || null,
      });
      setMissionId(res.mission_id);
      setRunning(true);
      setAlerts([]);
      rowCount.current = 0;
      sensorSeries.clear();
      healthSeries.clear();
      toast(`Mission ${res.mission_id} started (${profileId})`, "success");
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const stopMission = async () => {
    if (!missionId) return;
    setBusy(true);
    try {
      await api.stopMission(missionId);
      setRunning(false);
      toast(`Mission ${missionId} stopped — report generated`, "success");
      refreshMissions();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const injectFault = async () => {
    setBusy(true);
    try {
      const res = await api.injectFault({
        engine_id: ENGINE_ID,
        fault_type: faultType,
        severity: Number(severity),
        duration_sec: Number(faultDuration),
      });
      toast(res.message, "success");
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const startReplay = async () => {
    if (!replayMission) return;
    setBusy(true);
    try {
      await api.startReplay({ mission_id: replayMission, speed: 5 });
      setReplaying(true);
      toast(`Replaying mission ${replayMission} at 5x`, "success");
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const stopReplay = async () => {
    try {
      await api.stopReplay();
      setReplaying(false);
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const status = twin?.status ?? "—";
  const statusTone = status === "OPERATIONAL" ? "ok" : status === "DEGRADED" ? "warn" : "crit";

  return (
    <div className="dashboard">
      <div className="status-strip">
        <HealthGauge value={twin?.health_index ?? 0} />
        <div className="status-block">
          <div className="status-badge-row">
            <span className={`badge ${statusTone}`}>{status}</span>
            <span className={`badge ${running ? "ok" : "idle"}`}>{running ? "MISSION ACTIVE" : "IDLE"}</span>
            <span className={`badge ${wsConnected ? "ok" : "idle"}`}>{wsConnected ? "LIVE" : "WS OFFLINE"}</span>
            <span className={`badge ${backendOk ? "ok" : "crit"}`}>{backendOk ? "BACKEND OK" : "BACKEND DOWN"}</span>
          </div>
          <div className="twin-meta">
            <StatCard label="Remaining Useful Life" value={twin?.rul_estimate ?? "—"} unit="h" />
            <StatCard label="Confidence" value={twin?.rul_confidence?.toUpperCase() ?? "—"} />
            <StatCard label="Anomaly Score" value={twin?.anomaly_score?.toFixed(3) ?? "—"} />
            <StatCard label="Degradation" value={twin?.degradation_level ? `${(twin.degradation_level * 100).toFixed(0)}%` : "0%"} />
            <StatCard label="Phase" value={phase} />
            <StatCard label="Mission" value={missionId ?? "—"} />
          </div>
        </div>
      </div>

      <div className="grid-main">
        <div className="panel controls-panel">
          <h3>Mission Control</h3>
          <label>
            Profile
            <select value={profileId} onChange={(e) => setProfileId(e.target.value)}>
              {PROFILES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label>
            Duration (s, 0 = until stopped)
            <input type="number" min="0" step="30" value={duration} onChange={(e) => setDuration(e.target.value)} />
          </label>
          <div className="btn-row">
            <button className="btn primary" disabled={busy || running} onClick={startMission}>
              Start Mission
            </button>
            <button className="btn danger" disabled={busy || !running} onClick={stopMission}>
              Stop Mission
            </button>
          </div>

          <h3>Fault Injection</h3>
          <label>
            Fault type
            <select value={faultType} onChange={(e) => setFaultType(e.target.value)}>
              {FAULT_TYPES.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </label>
          <label>
            Severity: <b>{severity.toFixed(2)}</b>
            <input type="range" min="0.05" max="1" step="0.05" value={severity} onChange={(e) => setSeverity(Number(e.target.value))} />
          </label>
          <label>
            Duration (s)
            <input type="number" min="10" step="10" value={faultDuration} onChange={(e) => setFaultDuration(e.target.value)} />
          </label>
          <button className="btn warn" disabled={busy || !running} onClick={injectFault}>
            Inject Fault
          </button>

          <h3>Mission Replay</h3>
          <label>
            Mission
            <select value={replayMission} onChange={(e) => setReplayMission(e.target.value)}>
              {missions.map((m) => (
                <option key={m.mission_id} value={m.mission_id}>
                  {m.mission_id} · {m.profile_id} · {m.status}
                </option>
              ))}
            </select>
          </label>
          <div className="btn-row">
            <button className="btn" disabled={busy || replaying || !replayMission} onClick={startReplay}>
              Replay (5x)
            </button>
            <button className="btn" disabled={!replaying} onClick={stopReplay}>
              Stop
            </button>
          </div>
        </div>

        <div className="charts-col">
          <div className="panel">
            <h3>Health Index & Anomaly Score</h3>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={healthSeries.data}>
                <CartesianGrid stroke="#1f2a44" strokeDasharray="3 3" />
                <XAxis dataKey="t" stroke="#64748b" fontSize={10} minTickGap={40} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line name="Health Index" dataKey="health_index" {...chartTheme("#38bdf8")} />
                <Line name="Anomaly (0-100)" dataKey="anomaly_score" {...chartTheme("#f87171")} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="panel">
            <h3>EGT / CHT (°C)</h3>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={sensorSeries.data}>
                <CartesianGrid stroke="#1f2a44" strokeDasharray="3 3" />
                <XAxis dataKey="t" stroke="#64748b" fontSize={10} minTickGap={40} />
                <YAxis stroke="#64748b" fontSize={10} domain={["auto", "auto"]} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line name="EGT" dataKey="egt" {...chartTheme("#fb923c")} />
                <Line name="CHT" dataKey="cht" {...chartTheme("#a78bfa")} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="panel">
            <h3>RPM / Oil Pressure</h3>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={sensorSeries.data}>
                <CartesianGrid stroke="#1f2a44" strokeDasharray="3 3" />
                <XAxis dataKey="t" stroke="#64748b" fontSize={10} minTickGap={40} />
                <YAxis yAxisId="rpm" stroke="#64748b" fontSize={10} />
                <YAxis yAxisId="op" orientation="right" stroke="#64748b" fontSize={10} domain={[0, 6]} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line yAxisId="rpm" name="RPM" dataKey="rpm" {...chartTheme("#34d399")} />
                <Line yAxisId="op" name="Oil Pressure (bar)" dataKey="oil_pressure" {...chartTheme("#facc15")} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="panel">
            <h3>Vibration (g)</h3>
            <ResponsiveContainer width="100%" height={140}>
              <LineChart data={sensorSeries.data}>
                <CartesianGrid stroke="#1f2a44" strokeDasharray="3 3" />
                <XAxis dataKey="t" stroke="#64748b" fontSize={10} minTickGap={40} />
                <YAxis stroke="#64748b" fontSize={10} domain={[0, "auto"]} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line name="Vibration RMS" dataKey="vibration" {...chartTheme("#f472b6")} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid-bottom">
        <div className="panel">
          <h3>Alerts & Advisories</h3>
          {alerts.length === 0 ? (
            <p className="muted">No alerts yet. Start a mission and inject a fault to see detection in action.</p>
          ) : (
            <ul className="alerts">
              {alerts.map((a, i) => (
                <li key={i} className={`alert-${a.kind}`}>
                  <span className="alert-time">{a.time}</span>
                  {a.text}
                </li>
              ))}
            </ul>
          )}
          {twin?.advisory ? (
            <div className="advisory">
              <b>{twin.advisory.priority}</b> — {twin.advisory.text}
            </div>
          ) : null}
        </div>

        <div className="panel">
          <h3>Latest Telemetry</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Phase</th>
                  <th>RPM</th>
                  <th>CHT °C</th>
                  <th>EGT °C</th>
                  <th>Oil P bar</th>
                  <th>Oil T °C</th>
                  <th>Fuel L/h</th>
                  <th>Vib g</th>
                </tr>
              </thead>
              <tbody>
                {telemetryRows.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="muted">
                      Waiting for telemetry…
                    </td>
                  </tr>
                ) : (
                  telemetryRows.map((r, i) => (
                    <tr key={i}>
                      <td>{timeLabel(r.timestamp)}</td>
                      <td>{r.phase}</td>
                      <td>{r.rpm}</td>
                      <td>{r.cht}</td>
                      <td>{r.egt}</td>
                      <td>{r.oil_pressure}</td>
                      <td>{r.oil_temperature}</td>
                      <td>{r.fuel_flow}</td>
                      <td>{r.vibration_rms}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

const tooltipStyle = {
  backgroundColor: "#0f172a",
  border: "1px solid #1f2a44",
  borderRadius: 8,
  fontSize: 12,
  color: "#e2e8f0",
};