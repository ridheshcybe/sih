import { useState } from "react";
import { startMission, stopMission } from "../api/client";

export default function MissionControls({ engineId, mission, onMissionChange, notify }) {
  const [busy, setBusy] = useState(false);
  const running = mission?.status === "running";

  const handleStart = async () => {
    setBusy(true);
    const result = await startMission(engineId, "normal_cruise");
    setBusy(false);
    if (!result) return notify("Failed to start mission", "error");
      if (!result || result.error) return notify(result?.error || "Failed to start mission", "error");
    onMissionChange(result);
    notify("Mission started successfully", "success");
  };

  const handleStop = async () => {
    setBusy(true);
    const result = await stopMission(mission.mission_id);
    setBusy(false);
    if (!result) return notify("Failed to stop mission", "error");
      if (!result || result.error) return notify(result?.error || "Failed to stop mission", "error");
    onMissionChange(result);
    notify("Mission stopped", "success");
  };

  return <section className="control-card">
    <div><p className="eyebrow">Mission control</p><h2>{running ? "Mission Running" : "Mission Stopped"}</h2></div>
    <div className="control-actions">
      <button className="button button-primary" onClick={handleStart} disabled={busy || running}>{busy && !running ? "Starting..." : "Start Mission"}</button>
      <button className="button button-muted" onClick={handleStop} disabled={busy || !running}>{busy && running ? "Stopping..." : "Stop Mission"}</button>
    </div>
  </section>;
}