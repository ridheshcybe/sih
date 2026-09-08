"""SIH26054 inference CLI.

Runs the trained ML stack (PyTorch preferred, scikit-learn fallback, safe
defaults otherwise) outside the backend:

  # model status + a demo prediction on a zero feature vector
  python -m ml.predict --status

  # score a telemetry CSV (train/val/test or a mission export)
  python -m ml.predict --csv data/test.csv --out data/predictions.csv

  # score one simulated mission (same flags as simulator.run_simulation)
  python -m ml.predict --simulate --profile hot_weather --fault-type overheating \
      --severity 0.7 --fault-start 60 --duration 300

  # live-watch mode: print a score line every second
  python -m ml.predict --live --interval 1.0

The CLI is read-only over the dataset: it never writes back to data/ unless
--out is given.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ml.data_utils import DEFAULT_WINDOW, MODELS_DIR
from ml.feature_extractor import FeatureExtractor
from ml.inference import get_predictor
from simulator.simulate import simulate_mission

logger = logging.getLogger("sih26054.predict")

_WINDOW = DEFAULT_WINDOW  # matches training (10 rows @ 10 Hz = 1 s)


def _print_status(predictor) -> int:
    print("Model status (models/ directory):")
    for name, loaded in predictor.status.items():
        print(f"  {name:<18} {'LOADED' if loaded else 'MISSING (fallbacks in use)'}")
    print(f"  torch available    {'yes' if predictor.torch else 'no'}")
    print(f"  feature vector     {FeatureExtractor().n_features} dims (window={_WINDOW})")
    print("")
    print("Demo prediction on a zero feature vector (healthy-ish baseline):")
    result = predictor.predict_all(np.zeros(FeatureExtractor().n_features))
    print(f"  anomaly_score    {result['anomaly_score']}")
    print(f"  degradation      {result['degradation_level']}")
    print(f"  rul_estimate     {result['rul_estimate']} h ({result['rul_confidence']} confidence)")
    print(f"  top fault        {max(result['fault_probs'], key=result['fault_probs'].get)}")
    return 0


def _score_frame(df: pd.DataFrame, predictor, extractor: FeatureExtractor) -> pd.DataFrame:
    """Score every window (stride=window, non-overlapping) of a telemetry frame."""
    sensors = extractor.sensor_names
    missing = [c for c in sensors + ["mission_id"] if c not in df.columns]
    if missing:
        raise SystemExit(f"CSV is missing required columns: {missing}\n"
                         "Generate telemetry with: python -m simulator.run_simulation")

    out_rows = []
    for mission_id, mission in df.groupby("mission_id", sort=False):
        mission = mission.reset_index(drop=True)
        if len(mission) < _WINDOW:
            continue
        arr = mission[sensors].to_numpy(dtype=float)
        for start in range(0, len(mission) - _WINDOW + 1, _WINDOW):
            end = start + _WINDOW
            context = {
                k: float(mission.iloc[end - 1][k])
                for k in ("throttle", "altitude", "ambient_temperature")
                if k in mission.columns
            }
            # Prefer simulator-recorded healthy-model values when present.
            context.update({
                f"expected_{s}": float(mission.iloc[end - 1][f"expected_{s}"])
                for s in ("cht", "egt", "oil_pressure", "oil_temperature", "fuel_flow", "vibration_rms")
                if f"expected_{s}" in mission.columns
            })
            x = extractor.extract_array(arr[start:end], context)
            result = predictor.predict_all(x)
            top = max(result["fault_probs"], key=result["fault_probs"].get)
            out_rows.append({
                "mission_id": mission_id,
                "timestamp": mission.iloc[end - 1]["timestamp"],
                "phase": mission.iloc[end - 1].get("phase", ""),
                "anomaly_score": result["anomaly_score"],
                "degradation_level": result["degradation_level"],
                "rul_estimate": result["rul_estimate"],
                "rul_confidence": result["rul_confidence"],
                "top_fault": top,
                "top_probability": result["fault_probs"][top],
                "true_fault_label": mission.iloc[end - 1].get("fault_label", ""),
            })

    if not out_rows:
        raise SystemExit("No complete windows found (need at least "
                         f"{_WINDOW} rows per mission).")
    return pd.DataFrame(out_rows)


def _print_csv_summary(pred: pd.DataFrame) -> None:
    n = len(pred)
    hits = int((pred["top_fault"] == pred["true_fault_label"]).sum())
    print(f"Windows scored : {n}")
    print(f"Anomaly mean   : {pred['anomaly_score'].mean():.3f}  "
          f"max {pred['anomaly_score'].max():.3f}")
    print(f"Degradation    : mean {pred['degradation_level'].mean():.3f}  "
          f"max {pred['degradation_level'].max():.3f}")
    print(f"RUL            : mean {pred['rul_estimate'].mean():.1f} h  "
          f"min {pred['rul_estimate'].min():.1f} h")
    print(f"Top-fault match with simulator ground truth: {hits}/{n} "
          f"({100.0 * hits / n:.1f}%)  [no-model runs score ~0]")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ml.predict",
        description="Run the SIH26054 ML inference stack outside the backend.",
    )
    parser.add_argument("--models-dir", default=str(MODELS_DIR),
                        help="directory containing model artifacts (default: models/)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output where supported")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--status", action="store_true",
                      help="show which models are loaded + one demo prediction")
    mode.add_argument("--csv", metavar="FILE",
                      help="score a telemetry CSV (e.g. data/test.csv)")
    mode.add_argument("--simulate", action="store_true",
                      help="simulate one mission and score it")
    mode.add_argument("--live", action="store_true",
                      help="score simulated telemetry continuously (Ctrl+C to stop)")
    parser.add_argument("--out", metavar="FILE",
                        help="write per-window predictions to this CSV (with --csv/--simulate)")

    sim = parser.add_argument_group("simulation options (--simulate / --live)")
    sim.add_argument("--profile", default="standard_isr",
                     help="mission profile id (default: standard_isr)")
    sim.add_argument("--fault-type", default=None, help="fault to inject")
    sim.add_argument("--severity", type=float, default=0.6)
    sim.add_argument("--fault-start", type=float, default=300.0,
                     help="mission-relative fault start (s)")
    sim.add_argument("--duration", type=float, default=None,
                     help="mission duration (s); default = full profile")
    sim.add_argument("--seed", type=int, default=42)
    sim.add_argument("--interval", type=float, default=1.0,
                     help="seconds between --live score lines")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    predictor = get_predictor(Path(args.models_dir))
    extractor = FeatureExtractor()

    if args.status:
        return _print_status(predictor)

    if args.csv:
        path = Path(args.csv)
        if not path.exists():
            raise SystemExit(f"CSV not found: {path}\n"
                             "Generate it with: python -m simulator.generate_dataset")
        print(f"Scoring {path} ...")
        pred = _score_frame(pd.read_csv(path), predictor, extractor)
        _print_csv_summary(pred)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            pred.to_csv(args.out, index=False)
            print(f"Predictions written to {args.out}")
        elif args.json:
            print(pred.tail(10).to_json(orient="records", indent=2))
        return 0

    if args.simulate:
        print(f"Simulating mission (profile={args.profile}, fault={args.fault_type or 'none'}, "
              f"severity={args.severity}) ...")
        df = simulate_mission(
            profile_id=args.profile,
            duration_s=args.duration,
            fault_type=args.fault_type,
            severity=args.severity,
            fault_start_s=args.fault_start,
            seed=args.seed,
        )
        pred = _score_frame(df, predictor, extractor)
        _print_csv_summary(pred)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            pred.to_csv(args.out, index=False)
            print(f"Predictions written to {args.out}")
        elif args.json:
            print(json.dumps(pred.tail(10).to_dict(orient="records"), indent=2))
        return 0

    if args.live:
        print("Live-watch mode: simulating telemetry in real time. Ctrl+C to stop.")
        print(f"{'timestamp':<24} {'anomaly':>8} {'degrad':>7} {'rul_h':>6}  top_fault")
        try:
            while True:
                df = simulate_mission(
                    profile_id=args.profile,
                    duration_s=_WINDOW * 0.1,
                    fault_type=args.fault_type,
                    severity=args.severity,
                    fault_start_s=0.0,
                    seed=args.seed,
                )
                arr = df[extractor.sensor_names].to_numpy(dtype=float)
                context = {k: float(df.iloc[-1][k]) for k in
                           ("throttle", "altitude", "ambient_temperature")}
                x = extractor.extract_array(arr, context)
                result = predictor.predict_all(x)
                top = max(result["fault_probs"], key=result["fault_probs"].get)
                print(f"{df.iloc[-1]['timestamp']:<24} "
                      f"{result['anomaly_score']:>8.3f} "
                      f"{result['degradation_level']:>7.3f} "
                      f"{result['rul_estimate']:>6.1f}  {top}")
                import time
                time.sleep(max(args.interval, 0.1))
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
