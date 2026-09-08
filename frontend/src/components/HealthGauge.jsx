import React from "react";

function colorFor(value) {
  if (value >= 85) return "#34d399";
  if (value >= 60) return "#fbbf24";
  return "#f87171";
}

/** Radial 0-100 gauge for the Health Index. */
export default function HealthGauge({ value = 0 }) {
  const v = Math.max(0, Math.min(100, value));
  const r = 42;
  const circ = 2 * Math.PI * r;
  const filled = (v / 100) * circ;
  const color = colorFor(v);
  return (
    <div className="gauge">
      <svg viewBox="0 0 100 100" width="110" height="110">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#1f2a44" strokeWidth="9" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circ - filled}`}
          transform="rotate(-90 50 50)"
        />
        <text x="50" y="54" textAnchor="middle" dominantBaseline="middle" fontSize="22" fontWeight="700" fill="#e2e8f0">
          {Math.round(v)}
        </text>
        <text x="50" y="76" textAnchor="middle" fontSize="8" fill="#64748b" letterSpacing="1">
          HEALTH INDEX
        </text>
      </svg>
    </div>
  );
}