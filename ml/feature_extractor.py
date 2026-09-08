"""Feature extraction for the SIH26054 ML pipeline.

Turns a window of telemetry rows (plus operating context) into a fixed-length
numpy feature vector:

  - last observed value per sensor
  - rolling stats (mean, std, min, max, slope) per sensor over the window
  - physics residuals (observed - expected) for key sensors

The output ordering is deterministic and identical at train and inference time
so models trained on it can be applied directly to live windows. The hot path
is vectorized with numpy so building ~100k windows takes seconds, not minutes.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from simulator.engine_model import expected_sensors

# Sensors used for residual features (must be in SENSOR_COLUMNS)
RESIDUAL_SENSORS = [
    "cht",
    "egt",
    "oil_pressure",
    "oil_temperature",
    "vibration_rms",
    "fuel_flow",
]

# Control inputs used to compute expected sensor values (steady-state fallback).
# Deliberately excludes observed sensors so residuals stay meaningful during faults.
_CONTEXT_KEYS = ["throttle", "altitude", "ambient_temperature"]

# Healthy-model expected values recorded per row by the simulator (preferred
# over the steady-state fallback because transients cancel exactly).
_EXPECTED_CONTEXT_KEYS = [f"expected_{s}" for s in RESIDUAL_SENSORS]
_ALL_CONTEXT_KEYS = _CONTEXT_KEYS + _EXPECTED_CONTEXT_KEYS


def _build_context(row: pd.Series) -> Dict[str, float]:
    return {k: float(row[k]) for k in _ALL_CONTEXT_KEYS if k in row.index}


class FeatureExtractor:
    """Fixed-length feature extraction from a window of telemetry rows."""

    def __init__(self, sensor_names: Optional[List[str]] = None):
        from simulator import SENSOR_COLUMNS

        self.sensor_names = sensor_names or list(SENSOR_COLUMNS)
        self.feature_names: List[str] = []
        for s in self.sensor_names:
            self.feature_names += [f"{s}_last", f"{s}_mean", f"{s}_std", f"{s}_min", f"{s}_max", f"{s}_slope"]
        for s in RESIDUAL_SENSORS:
            self.feature_names.append(f"{s}_residual")
        self._index = {name: i for i, name in enumerate(self.feature_names)}
        self._sensor_idx = {s: i for i, s in enumerate(self.sensor_names)}

    @property
    def n_features(self) -> int:
        return len(self.feature_names)

    # --- numpy core ----------------------------------------------------------
    def extract_array(self, arr: np.ndarray, context: Optional[Dict[str, float]] = None) -> np.ndarray:
        """Feature vector from a (W, S) float array of sensor values.

        arr columns must match self.sensor_names ordering. Missing values are
        forward-filled, then backward-filled, then zeroed.
        """
        W, S = arr.shape
        if W == 0:
            raise ValueError("Feature extraction requires a non-empty telemetry window")

        arr = np.asarray(arr, dtype=float).copy()
        # fill missing values along the time axis (interpolate over valid points)
        filled = arr
        for j in range(S):
            col = filled[:, j]
            nan = np.isnan(col)
            if nan.any():
                if nan.all():
                    col[:] = 0.0
                else:
                    idx = np.where(~nan)[0]
                    filled[:, j] = np.interp(np.arange(W), idx, col[idx])

        last = filled[-1]
        x = np.arange(W, dtype=float)
        sx = x.sum()
        sxx = (x * x).sum()

        vec = np.zeros(self.n_features, dtype=float)
        for s in self.sensor_names:
            j = self._sensor_idx[s]
            base = j * 6
            col = filled[:, j]
            mean = col.mean()
            vec[base + 0] = last[j]
            vec[base + 1] = mean
            vec[base + 2] = col.std() if W > 1 else 0.0
            vec[base + 3] = col.min()
            vec[base + 4] = col.max()
            # closed-form linear slope
            sy = col.sum()
            sxy = float(x @ col)
            denom = W * sxx - sx * sx
            vec[base + 5] = (W * sxy - sx * sy) / denom if denom != 0 else 0.0

        # Residuals: observed (last) minus expected value. Preferred: the
        # healthy-model value recorded with the row (transients cancel).
        # Fallback: steady-state physics from control inputs.
        if context is None:
            context = {}
        try:
            offset = S * 6
            for j2, sensor in enumerate(RESIDUAL_SENSORS):
                observed = last[self._sensor_idx[sensor]]
                exp = context.get(f"expected_{sensor}")
                if exp is None:
                    exp = float(expected_sensors(context).get(sensor, observed))
                vec[offset + j2] = observed - float(exp)
        except Exception:  # noqa: BLE001 - residuals are auxiliary; never crash on them
            pass
        return vec

    # --- pandas/df API ---------------------------------------------------------
    def extract(self, window: pd.DataFrame) -> np.ndarray:
        """Return a 1-D float feature vector for a telemetry window DataFrame."""
        if window is None or len(window) == 0:
            raise ValueError("Feature extraction requires a non-empty telemetry window")
        missing = [c for c in self.sensor_names if c not in window.columns]
        if missing:
            raise ValueError(f"Window is missing sensor columns: {missing}")
        arr = window[self.sensor_names].to_numpy(dtype=float)
        context = _build_context(window.iloc[-1])
        return self.extract_array(arr, context)


def build_window_dataset(
    df: pd.DataFrame,
    extractor: FeatureExtractor,
    window: int = 10,
    stride: int = 2,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """Build X + labels (fault_label, degradation_level, rul_label) from a full telemetry frame.

    Windows never cross mission boundaries. Returns (X, y_fault_labels,
    y_degradation, y_rul, feature_names).
    """
    xs: List[np.ndarray] = []
    faults: List[str] = []
    degs: List[float] = []
    ruls: List[float] = []
    sensors = extractor.sensor_names

    for _, mission in df.groupby("mission_id", sort=False):
        mission = mission.reset_index(drop=True)
        if len(mission) < window:
            continue
        arr = mission[sensors].to_numpy(dtype=float)
        n = len(mission)
        starts = range(0, n - window + 1, stride)
        for start in starts:
            end = start + window
            context = _build_context(mission.iloc[end - 1])
            xs.append(extractor.extract_array(arr[start:end], context))
            last_row = mission.iloc[end - 1]
            faults.append(str(last_row.get("fault_label", "none")))
            degs.append(float(last_row.get("degradation_level", 0.0)))
            ruls.append(float(last_row.get("rul_label", 0.0)))
    X = np.vstack(xs) if xs else np.zeros((0, extractor.n_features))
    return X, np.array(faults), np.array(degs), np.array(ruls), extractor.feature_names


if __name__ == "__main__":
    from simulator.simulate import simulate_mission

    ex = FeatureExtractor()
    df = simulate_mission(duration_s=30, seed=3)
    X, faults, degs, ruls, names = build_window_dataset(df, ex, window=10, stride=2)
    print(f"Feature vector length: {ex.n_features}")
    print(f"Windows: {X.shape}")
    print("Sample feature names:", names[:6], "...", names[-6:])