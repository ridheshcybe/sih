// Thin fetch wrapper around the SIH26054 backend.
// All endpoints live under /api/v1 except /api/system/health.

const API_V1 = "/api/v1";

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    let detail = body.detail || body.message || `HTTP ${res.status}`;
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; ");
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

const get = (path) => request(path);
const post = (path, data) => request(path, { method: "POST", body: JSON.stringify(data ?? {}) });

export const api = {
  // system
  systemHealth: () => request("/api/system/health"),
  systemInfo: () => request("/api/system/info"),

  // engines
  getEngineState: (engineId) => get(`${API_V1}/engines/${engineId}/state`),
  getEngineTelemetry: (engineId, limit = 50) => get(`${API_V1}/engines/${engineId}/telemetry?limit=${limit}`),
  getEngineHealth: (engineId) => get(`${API_V1}/engines/${engineId}/health`),
  getEngineFaults: (engineId) => get(`${API_V1}/engines/${engineId}/faults`),
  getEngineRul: (engineId) => get(`${API_V1}/engines/${engineId}/rul`),

  // missions
  startMission: (payload) => post(`${API_V1}/missions`, payload),
  stopMission: (missionId) => post(`${API_V1}/missions/${missionId}/stop`),
  listMissions: () => get(`${API_V1}/missions/list`),
  getMission: (missionId) => get(`${API_V1}/missions/${missionId}`),

  // simulation
  simulationStatus: () => get(`${API_V1}/simulation/status`),

  // faults
  injectFault: (payload) => post(`${API_V1}/faults/inject`, payload),

  // replay
  startReplay: (payload) => post(`${API_V1}/replay/start`, payload),
  stopReplay: () => post(`${API_V1}/replay/stop`),
  replayStatus: () => get(`${API_V1}/replay/status`),

  // reports
  getReport: (missionId) => get(`${API_V1}/reports/${missionId}`),
  generateReport: (missionId) => post(`${API_V1}/reports/${missionId}/generate`),
};

export const FAULT_TYPES = [
  "misfire",
  "injector_degradation",
  "lubrication_issue",
  "overheating",
  "sensor_drift",
  "abnormal_vibration",
  "battery_alternator_degradation",
];

export const PROFILES = ["standard_isr", "high_altitude", "hot_weather", "aggressive"];