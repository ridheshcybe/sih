import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

export default function Missions() {
  const [missions, setMissions] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .listMissions()
      .then(setMissions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <h2>Missions</h2>
      {error ? <p className="error-text">Backend unavailable: {error}</p> : null}
      {loading ? <p className="muted">Loading…</p> : null}
      {!loading && missions.length === 0 ? <p className="muted">No missions yet. Start one from the Dashboard.</p> : null}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Mission</th>
              <th>Name</th>
              <th>Profile</th>
              <th>Status</th>
              <th>Start</th>
              <th>End</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {missions.map((m) => (
              <tr key={m.mission_id}>
                <td>{m.mission_id}</td>
                <td>{m.mission_name}</td>
                <td>{m.profile_id}</td>
                <td>
                  <span className={`badge ${m.status === "running" ? "ok" : m.status === "completed" ? "warn" : "idle"}`}>
                    {m.status}
                  </span>
                </td>
                <td>{new Date(m.start_time).toLocaleString()}</td>
                <td>{m.end_time ? new Date(m.end_time).toLocaleString() : "—"}</td>
                <td>
                  <button className="btn small" onClick={() => navigate(`/reports?mission=${m.mission_id}`)}>
                    Report
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}