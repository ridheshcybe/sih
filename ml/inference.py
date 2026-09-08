"""Inference service for the SIH26054 ML pipeline.

Model priority at inference time:
  1. GPU-trained PyTorch models (models/*.pt + torch_*_meta.json)
  2. scikit-learn baselines (models/*.joblib)
  3. safe fallback defaults

Any missing/corrupt model logs a warning and degrades gracefully, so the
backend never crashes because a model file is absent (e.g. before training).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ml.data_utils import MODELS_DIR, load_meta

logger = logging.getLogger("sih26054.ml")

RUL_MAX_HOURS = 500.0
_DEFAULT_CLASSES = ["none", "misfire", "injector_degradation", "lubrication_issue",
                    "overheating", "sensor_drift", "abnormal_vibration",
                    "battery_alternator_degradation"]

_EMA_ALPHA = 0.35  # smoothing for anomaly / degradation to avoid score jumps

# Fallback residual scales (used when the anomaly meta file is missing).
_FALLBACK_RESID_STD = {
    "cht": 15.0, "egt": 15.0, "oil_pressure": 0.25, "oil_temperature": 3.0,
    "vibration_rms": 0.12, "fuel_flow": 0.6,
}

try:  # torch is optional at runtime (backend runs without it)
    import torch  # noqa: F401
    from ml.torch_models import build_model

    TORCH_AVAILABLE = True
except Exception:  # noqa: BLE001
    TORCH_AVAILABLE = False

_TORCH_FILES = {
    "anomaly": ("anomaly_autoencoder.pt", "torch_anomaly_meta.json", "anomaly"),
    "fault": ("fault_mlp.pt", "torch_fault_meta.json", "fault"),
    "degradation": ("degradation_mlp.pt", "torch_degradation_meta.json", "degradation"),
    "rul": ("rul_mlp.pt", "torch_rul_meta.json", "rul"),
}


def _anomaly_score_from_raw(raw: float) -> float:
    """Map -decision_function (higher = more anomalous) to 0..1."""
    return float(1.0 - np.exp(-max(raw, 0.0)))


class Predictor:
    """Thin wrapper around the ML models with graceful degradation."""

    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = Path(models_dir)
        self.torch = TORCH_AVAILABLE

        # --- PyTorch models (GPU-trained, CPU inference) ---------------------
        self.ae_model = None
        self.fault_torch = None
        self.deg_torch = None
        self.rul_torch = None
        self._scaler = {}          # kind -> (mean, std)
        self._ae_stats = None      # (train_err_mean, train_err_std) for AE
        self._torch_classes: List[str] = _DEFAULT_CLASSES
        if self.torch:
            self._load_torch_models()

        # --- scikit-learn baselines ------------------------------------------
        self.anomaly_model = self._load("anomaly_model.joblib", "anomaly (sklearn)")
        self.fault_model = self._load("fault_classifier.joblib", "fault classifier (sklearn)")
        self.degradation_model = self._load("degradation_model.joblib", "degradation (sklearn)")
        self.rul_model = self._load("rul_model.joblib", "RUL (sklearn)")

        self.classes: List[str] = _DEFAULT_CLASSES
        meta = load_meta(self.models_dir / "fault_classifier_meta.json")
        if meta.get("classes"):
            self.classes = list(meta["classes"])

        # Residual statistics for the residual z-score anomaly signal.
        ameta = load_meta(self.models_dir / "anomaly_meta.json")
        self._residual_means: Optional[np.ndarray] = None
        self._residual_stds: Optional[np.ndarray] = None
        self._residual_idx = np.array([], dtype=int)
        self._residual_names: List[str] = []
        if ameta.get("residual_means") and ameta.get("residual_stds"):
            self._residual_means = np.asarray(ameta["residual_means"], dtype=float)
            self._residual_stds = np.asarray(ameta["residual_stds"], dtype=float)
            fnames = ameta.get("feature_names", [])
            self._residual_idx = np.array([i for i, n in enumerate(fnames)
                                           if n.endswith("_residual")], dtype=int)
            self._residual_names = [str(fnames[i]).replace("_residual", "") for i in self._residual_idx]

        self._ema_anomaly = 0.0
        self._ema_degradation = 0.0
        self._ema_set = False

    # --- loading helpers -------------------------------------------------------
    def _load(self, filename: str, label: str):
        path = self.models_dir / filename
        if not path.exists():
            logger.warning("ML model '%s' not found at %s - using fallback defaults", label, path)
            return None
        try:
            return joblib_load(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load ML model '%s': %s - using fallback defaults", label, exc)
            return None

    def _load_torch_models(self) -> None:
        for kind, (fname, mname, label) in _TORCH_FILES.items():
            path = self.models_dir / fname
            if not path.exists():
                logger.info("Torch model '%s' not present (%s) - falling back", label, path)
                continue
            meta = load_meta(self.models_dir / mname)
            try:
                n_features = len(meta.get("feature_names", []))
                if kind == "anomaly":
                    model = build_model("anomaly", n_features)
                    self._ae_stats = (float(meta.get("train_err_mean", 0.0)),
                                      float(meta.get("train_err_std", 1.0)))
                elif kind == "fault":
                    classes = meta.get("classes") or _DEFAULT_CLASSES
                    self._torch_classes = list(classes)
                    model = build_model("fault", n_features, n_classes=len(classes))
                elif kind == "degradation":
                    model = build_model("degradation", n_features)
                else:  # rul
                    model = build_model("rul", n_features)
                model.load_state_dict(torch_load(path))
                model.eval()
                setattr(self, {"anomaly": "ae_model", "fault": "fault_torch",
                               "degradation": "deg_torch", "rul": "rul_torch"}[kind], model)
                mean = np.asarray(meta.get("scaler_mean", []), dtype=float)
                std = np.asarray(meta.get("scaler_std", []), dtype=float)
                if mean.size and std.size:
                    self._scaler[kind] = (mean, std)
                logger.info("Loaded torch model %s from %s", label, path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load torch model '%s': %s - falling back", label, exc)

    # --- status -----------------------------------------------------------------
    @property
    def status(self) -> Dict[str, bool]:
        return {
            "anomaly": self.ae_model is not None or self.anomaly_model is not None,
            "fault_classifier": self.fault_torch is not None or self.fault_model is not None,
            "degradation": self.deg_torch is not None or self.degradation_model is not None,
            "rul": self.rul_torch is not None or self.rul_model is not None,
        }

    def _standardize(self, x: np.ndarray, kind: str) -> np.ndarray:
        scaler = self._scaler.get(kind)
        if scaler is None:
            return x.astype(np.float32)
        mean, std = scaler
        return ((x - mean) / np.maximum(std, 1e-6)).astype(np.float32)

    # --- individual predictors -----------------------------------------------------
    def _residual_anomaly(self, x: np.ndarray) -> float:
        """0..1 anomaly signal from residual z-scores (max over monitored sensors)."""
        if self._residual_idx is None or len(self._residual_idx) == 0:
            return 0.0
        names = self._residual_names
        means = self._residual_means[self._residual_idx]
        stds = self._residual_stds[self._residual_idx]
        floor = np.array([_FALLBACK_RESID_STD.get(n, 0.1) for n in names])
        stds = np.maximum(stds, floor)
        z = np.abs((x[self._residual_idx] - means) / stds)
        contrib = np.clip((z - 1.0) / 4.0, 0.0, 1.0)  # 0 below 1 sigma, 1 at 5 sigma
        return float(np.max(contrib)) if contrib.size else 0.0

    def predict_anomaly(self, x: np.ndarray) -> float:
        if self.ae_model is not None and self._ae_stats is not None:
            xz = self._standardize(x, "anomaly")
            with torch_no_grad():
                mse = float(torch_mse(self.ae_model, torch_tensor(xz)))
            err_mean, err_std = self._ae_stats
            z = (mse - err_mean) / max(err_std, 1e-6)
            ml_score = float(np.clip((z - 1.0) / 4.0, 0.0, 1.0))
        elif self.anomaly_model is not None:
            raw = float(-self.anomaly_model.decision_function(x.reshape(1, -1))[0])
            ml_score = _anomaly_score_from_raw(raw)
        else:
            ml_score = 0.0
        score = max(ml_score, self._residual_anomaly(x))
        if not self._ema_set:
            self._ema_anomaly = score
            self._ema_set = True
        else:
            self._ema_anomaly = _EMA_ALPHA * score + (1 - _EMA_ALPHA) * self._ema_anomaly
        return round(self._ema_anomaly, 4)

    def predict_fault(self, x: np.ndarray) -> Dict[str, float]:
        if self.fault_torch is not None:
            xz = self._standardize(x, "fault")
            with torch_no_grad():
                logits = torch_logits(self.fault_torch, torch_tensor(xz))
            probs = torch_softmax(logits)
            out = {c: round(float(p), 4) for c, p in zip(self._torch_classes, probs)}
        elif self.fault_model is not None:
            probs = self.fault_model.predict_proba(x.reshape(1, -1))[0]
            out = {c: round(float(p), 4) for c, p in zip(self.classes, probs)}
        else:
            out = {c: (1.0 if c == "none" else 0.0) for c in self.classes}
        for c in _DEFAULT_CLASSES:
            out.setdefault(c, 0.0)
        return out

    def predict_degradation(self, x: np.ndarray) -> float:
        if self.deg_torch is not None:
            xz = self._standardize(x, "degradation")
            with torch_no_grad():
                value = float(torch_forward(self.deg_torch, torch_tensor(xz)))
        elif self.degradation_model is not None:
            value = float(self.degradation_model.predict(x.reshape(1, -1))[0])
        else:
            value = 0.0
        value = float(np.clip(value, 0.0, 1.0))
        self._ema_degradation = _EMA_ALPHA * value + (1 - _EMA_ALPHA) * self._ema_degradation
        return round(self._ema_degradation, 4)

    def predict_rul(self, x: np.ndarray, degradation: float) -> tuple:
        """Return (rul_estimate_hours, confidence)."""
        if self.rul_torch is not None:
            xz = self._standardize(x, "rul")
            x_in = np.concatenate([xz, [degradation]]).astype(np.float32)
            with torch_no_grad():
                rul = float(torch_forward(self.rul_torch, torch_tensor(x_in)))
        elif self.rul_model is not None:
            x_rul = np.hstack([x.reshape(1, -1), [[degradation]]])
            rul = float(self.rul_model.predict(x_rul)[0])
        else:
            rul = RUL_MAX_HOURS * (1.0 - degradation)
        rul = max(0.0, rul)
        confidence = "high" if degradation >= 0.6 else ("medium" if degradation >= 0.3 else "low")
        return round(rul, 1), confidence

    # --- combined -------------------------------------------------------------------
    def predict_all(self, x: np.ndarray, twin_state: Optional[dict] = None) -> Dict:
        """Run the full ML stack on one feature vector."""
        anomaly = self.predict_anomaly(x)
        fault_probs = self.predict_fault(x)
        degradation = self.predict_degradation(x)
        rul, rul_conf = self.predict_rul(x, degradation)
        return {
            "anomaly_score": anomaly,
            "fault_probs": fault_probs,
            "degradation_level": degradation,
            "rul_estimate": rul,
            "rul_confidence": rul_conf,
            "model_status": self.status,
        }


# --- torch call helpers (imports kept lazy so torch is optional) --------------------
def torch_tensor(x):
    import torch
    return torch.from_numpy(np.asarray(x, dtype=np.float32)).unsqueeze(0)


def torch_no_grad():
    import torch
    return torch.no_grad()


def torch_load(path):
    import torch
    return torch.load(path, map_location="cpu", weights_only=True)


def joblib_load(path):
    import joblib
    return joblib.load(path)


def torch_mse(model, x):
    import torch
    return float(((x - model(x)) ** 2).mean().item())


def torch_logits(model, x):
    return model(x)


def torch_softmax(logits):
    import torch
    return torch.softmax(logits, dim=1)[0].detach().numpy()


def torch_forward(model, x):
    return model(x).detach().numpy().reshape(-1)[0]


_predictor: Optional[Predictor] = None


def get_predictor(models_dir: Path = MODELS_DIR) -> Predictor:
    """Module-level singleton so model files are loaded once per process."""
    global _predictor
    if _predictor is None:
        _predictor = Predictor(models_dir)
    return _predictor


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = get_predictor()
    x = np.zeros(78)
    print("Torch available:", p.torch)
    print("Model status:", p.status)
    print("Fallback prediction:", {k: v for k, v in p.predict_all(x).items() if k != "fault_probs"})