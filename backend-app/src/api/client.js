export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!response.ok) throw new Error(`API request failed: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error(error);
    return null;
  }
}

export const getEngineState = (engineId) => request(`/engines/${encodeURIComponent(engineId)}/state`);
export const getEngineTelemetry = (engineId) => request(`/engines/${encodeURIComponent(engineId)}/telemetry`);
export const startMission = (engineId, profileId) => request("/missions/start", { method: "POST", body: JSON.stringify({ engine_id: engineId, profile_id: profileId }) });
export const stopMission = (missionId) => request("/missions/stop", { method: "POST", body: JSON.stringify({ mission_id: missionId }) });
export const injectFault = (engineId, faultType, severity, startTime = null) => request("/faults/inject", { method: "POST", body: JSON.stringify({ engine_id: engineId, fault_type: faultType, severity: Number(severity), start_time: startTime || new Date().toISOString() }) });