"""
ml/generate_dataset.py -- Generate the synthetic training/eval dataset (SIH26054).

Produces a JSONL file of samples, one JSON object per line:

    {"features": [54 floats], "label": "none", "degradation": 0.12, "rul": 118.0}

- Healthy samples: label "none", degradation 0, rul = full life.
- Faulty samples: one of the FAULT_TYPES, degradation ramping 0->1,
  rul shrinking as degradation grows.
- Split into data/train.jsonl and data/test.jsonl (stratified by label).

All data is SYNTHETIC for a hackathon demonstrator only.
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.features import extract_features, WINDOW_SIZE  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

FAULT_TYPES = [
    "injector_degradation",
    "overheating",
    "lubrication_issue",
    "sensor_drift",
    "abnormal_vibration",
]

# Nominal cruise telemetry (1 Hz), realistic for an aero piston engine.
NOMINAL = {
    "rpm": 2450.0, "cht": 180.0, "egt": 780.0, "oil_pressure": 62.0,
    "oil_temperature": 85.0, "fuel_flow": 38.0, "vibration_rms": 1.2,
    "battery_voltage": 27.2, "alternator_current": 32.0,
}
NOISE = {k: v * 0.03 for k, v in NOMINAL.items()}
RUL_FULL_LIFE = 120.0  # missions


def _base_window() -> list:
    return [{k: v + random.gauss(0, NOISE[k]) for k, v in NOMINAL.items()}
            for _ in range(WINDOW_SIZE)]


def apply_fault(window: list, fault: str, severity: float) -> None:
    """Mutate a healthy window in-place with a fault at given severity (0..1)."""
    ramp = [severity * (i + 1) / len(window) for i in range(len(window))]
    for i, row in enumerate(window):
        s = ramp[i]
        if fault == "injector_degradation":
            row["egt"] += 90.0 * s
            row["fuel_flow"] += 6.0 * s
        elif fault == "overheating":
            row["cht"] += 45.0 * s
            row["oil_temperature"] += 18.0 * s
        elif fault == "lubrication_issue":
            row["oil_pressure"] -= 22.0 * s
            row["oil_temperature"] += 12.0 * s
        elif fault == "sensor_drift":
            row["cht"] += 30.0 * s * (1 if i % 2 == 0 else 0.4)
            row["oil_pressure"] += 8.0 * s
        elif fault == "abnormal_vibration":
            row["vibration_rms"] += 1.4 * s
            row["oil_temperature"] += 5.0 * s


def healthy_sample() -> dict:
    win = _base_window()
    return {
        "features": extract_features(win).tolist(),
        "label": "none",
        "degradation": round(random.uniform(0.0, 0.05), 4),
        "rul": RUL_FULL_LIFE,
    }


def faulty_sample(label: str) -> dict:
    severity = random.uniform(0.15, 1.0)
    win = _base_window()
    apply_fault(win, label, severity)
    degradation = round(severity, 4)
    return {
        "features": extract_features(win).tolist(),
        "label": label,
        "degradation": degradation,
        "rul": round(RUL_FULL_LIFE * (1.0 - degradation), 2),
    }


def main(n_healthy=3000, per_fault=500, test_frac=0.2, seed=42):
    random.seed(seed)
    healthy = [healthy_sample() for _ in range(n_healthy)]
    faulty = [faulty_sample(ft) for ft in FAULT_TYPES for _ in range(per_fault)]
    samples = healthy + faulty
    random.shuffle(samples)

    n_test = int(len(samples) * test_frac)
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, part in (("train", samples[n_test:]), ("test", samples[:n_test])):
        path = os.path.join(OUT_DIR, f"{name}.jsonl")
        with open(path, "w") as f:
            for s in part:
                f.write(json.dumps(s) + "\n")
        labels = {}
        for s in part:
            labels[s["label"]] = labels.get(s["label"], 0) + 1
        print(f"{path}: {len(part)} samples | {labels}")


if __name__ == "__main__":
    main()
