import React from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { ToastProvider } from "./components/Toasts.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Missions from "./pages/Missions.jsx";
import Reports from "./pages/Reports.jsx";

export default function App() {
  return (
    <ToastProvider>
      <div className="app">
        <header className="topbar">
          <div className="brand">
            <span className="brand-mark">⚙</span>
            <div>
              <h1>Aero Engine Digital Twin</h1>
              <p>SIH26054 · AI-Enabled Health Monitoring &amp; Fault Prediction · MALE UAV</p>
            </div>
          </div>
          <nav>
            <NavLink to="/" end>
              Dashboard
            </NavLink>
            <NavLink to="/missions">Missions</NavLink>
            <NavLink to="/reports">Reports</NavLink>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/missions" element={<Missions />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </main>
      </div>
    </ToastProvider>
  );
}