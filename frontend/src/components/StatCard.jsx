import React from "react";

export default function StatCard({ label, value, unit, tone = "default" }) {
  return (
    <div className={`stat-card tone-${tone}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {value ?? "—"}
        {unit ? <span className="stat-unit">{unit}</span> : null}
      </div>
    </div>
  );
}