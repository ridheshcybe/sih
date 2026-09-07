import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { getEngineState, getEngineTelemetry } from "../api/client";
import { connectWebSocket, disconnectWebSocket } from "../api/websocket";
import MissionControls from "../components/MissionControls";
import FaultInjector from "../components/FaultInjector";

const ENGINE_ID = "ENG-001";
const SENSOR_COLUMNS = ["timestamp", "rpm", "cht", "egt", "oil_pressure", "oil_temperature", "fuel_flow", "vibration_rms", "altitude"];

function healthLabel(value) { return value < 55 ? "Critical" : value < 80 ? "Warning" : "Healthy"; }

export default function EngineMonitor() {
  const [state, setState] = useState(null);
  const [telemetry, setTelemetry] = useState([]);
  const [mission, setMission] = useState(null);
  const [connection, setConnection] = useState("connecting");
  const [error, setError] = useState("");
  const [lastUpdate, setLastUpdate] = useState(null);

  const notify = (message, type) => toast[type](message);
  const chartData = useMemo(() => telemetry.slice(-60).map((row) => ({ ...row, time: new Date(row.timestamp).toLocaleTimeString([], { minute: "2-digit", second: "2-digit" }) })), [telemetry]);

  useEffect(() => {
    let active = true;
    Promise.all([getEngineState(ENGINE_ID), getEngineTelemetry(ENGINE_ID)]).then(([nextState, nextTelemetry]) => {
      if (!active) return;
      if (!nextState || nextState.error || !nextTelemetry || nextTelemetry.error) return setError(nextState?.error || nextTelemetry?.error || "Backend unavailable - check connection");
      setState(nextState);
      setTelemetry(nextTelemetry.data || nextTelemetry.data_points || []);
      setError("");
    });
    connectWebSocket(ENGINE_ID, {
      onConnect: () => { setConnection("live"); setError(""); },
      onDisconnect: () => setConnection("reconnecting"),
      onError: () => { setConnection("offline"); setError("Backend unavailable - check connection"); },
      onMessage: (event, payload) => {
        if (event === "twin_state_update") { setState((previous) => ({ ...previous, ...payload })); setLastUpdate(payload.timestamp); }
        if (event === "telemetry_update") setTelemetry((previous) => [...previous, payload].slice(-120));
      },
    });
    return () => { active = false; disconnectWebSocket(); };
  }, []);

  if (error && !state) return <main className="app-shell"><header className="topbar"><div><p className="eyebrow">SIH26054 / DIGITAL TWIN</p><h1>Engine monitor</h1></div></header><div className="error-panel">{error}</div><ToastContainer theme="dark" /></main>;
  const health = state?.health_index ?? 0;
  const sensors = state?.sensors || {};

  return <main className="app-shell">
    <header className="topbar"><div><p className="eyebrow">SIH26054 / DIGITAL TWIN</p><h1>Engine monitor</h1><p className="subtle">Synthetic telemetry demonstrator · {ENGINE_ID}</p></div><div className={`connection connection-${connection}`}><span />{connection}</div></header>
    {error && <div className="notice">{error}</div>}
    <div className="controls-grid"><MissionControls engineId={ENGINE_ID} mission={mission} onMissionChange={setMission} notify={notify} /><FaultInjector engineId={ENGINE_ID} notify={notify} /></div>
    <section className="overview-grid">
      <article className="health-card"><div className="card-heading"><div><p className="eyebrow">Twin state</p><h2>Health index</h2></div><span className={`status status-${healthLabel(health).toLowerCase()}`}>{healthLabel(health)}</span></div><div className="health-number">{health.toFixed(1)}<small>/100</small></div><div className="health-track"><span style={{ width: `${health}%` }} /></div><p className="subtle">Anomaly score <strong>{(state?.anomaly_score ?? 0).toFixed(3)}</strong>{lastUpdate && ` · updated ${new Date(lastUpdate).toLocaleTimeString()}`}</p></article>
      <article className="sensor-card"><div className="card-heading"><div><p className="eyebrow">Live parameters</p><h2>Key sensors</h2></div><span className="live-dot">LIVE</span></div><div className="sensor-grid">{[["RPM", sensors.rpm, "rpm"], ["CHT", sensors.cht, "°C"], ["EGT", sensors.egt, "°C"], ["Oil pressure", sensors.oil_pressure, "psi"]].map(([label, value, unit]) => <div className="sensor" key={label}><span>{label}</span><strong>{value == null ? "--" : Number(value).toFixed(1)} <small>{unit}</small></strong></div>)}</div></article>
    </section>
    <section className="chart-panel"><div className="card-heading"><div><p className="eyebrow">Streaming signal</p><h2>Exhaust gas temperature</h2></div><span className="unit-label">°C / last 60 samples</span></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}><defs><linearGradient id="egtFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ff7b45" stopOpacity={0.45} /><stop offset="100%" stopColor="#ff7b45" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#263443" strokeDasharray="3 3" vertical={false} /><XAxis dataKey="time" tick={{ fill: "#8293a3", fontSize: 11 }} minTickGap={36} /><YAxis tick={{ fill: "#8293a3", fontSize: 11 }} domain={["dataMin - 20", "dataMax + 20"]} /><Tooltip contentStyle={{ background: "#111c27", border: "1px solid #304354" }} /><Area type="monotone" dataKey="egt" stroke="#ff7b45" fill="url(#egtFill)" strokeWidth={2} isAnimationActive={false} /></AreaChart></ResponsiveContainer></div></section>
    <section className="table-panel"><div className="card-heading"><div><p className="eyebrow">Raw stream</p><h2>Telemetry history</h2></div><span className="unit-label">{telemetry.length} rows buffered</span></div><div className="table-scroll"><table><thead><tr>{SENSOR_COLUMNS.map((column) => <th key={column}>{column.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{telemetry.slice(-20).reverse().map((row, index) => <tr key={`${row.timestamp}-${index}`}>{SENSOR_COLUMNS.map((column) => <td key={column}>{column === "timestamp" ? new Date(row[column]).toLocaleTimeString() : Number(row[column] ?? 0).toFixed(2)}</td>)}</tr>)}</tbody></table></div></section>
    <p className="disclaimer">Synthetic telemetry for software demonstration only. This prototype is not flight-certified and has not been validated against real engine data.</p>
    <ToastContainer position="top-right" autoClose={3500} theme="dark" />
  </main>;
}