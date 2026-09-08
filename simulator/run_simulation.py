#!/usr/bin/env python3
"""Run a single simulated mission.

Usage:
  python -m simulator.run_simulation --profile standard_isr --duration 120 \
      --fault-type injector_degradation --severity 0.6 --fault-start 300 \
      --output data/mission.csv
  python -m simulator.run_simulation --profile standard_isr --stream   # push to backend
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

import pandas as pd

from simulator.simulate import simulate_mission


def stream_to_backend(df: pd.DataFrame, base_url: str) -> None:
    """POST each row to the backend telemetry ingest endpoint."""
    url = base_url.rstrip("/") + "/api/v1/telemetry/ingest"
    payload_cols = [c for c in df.columns if c != "rul_label"]
    print(f"Streaming {len(df)} rows to {url} at ~10 Hz ...")
    for _, row in df.iterrows():
        data = {k: (None if pd.isna(v) else v) for k, v in row[payload_cols].items()}
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception as exc:  # noqa: BLE001 - report and continue is fine for a streamer
            print(f"[stream] row failed: {exc}")
        time.sleep(0.1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an SIH26054 engine mission simulation")
    parser.add_argument("--profile", default="standard_isr", help="mission profile id")
    parser.add_argument("--duration", type=float, default=None, help="override duration (s)")
    parser.add_argument("--fault-type", default=None, help="fault to inject (see fault_injection.FAULT_TYPES)")
    parser.add_argument("--severity", type=float, default=0.6, help="fault severity 0..1")
    parser.add_argument("--fault-start", type=float, default=300.0, help="fault start time (s)")
    parser.add_argument("--fault-duration", type=float, default=240.0, help="fault duration (s)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--output", default=None, help="write CSV to this path")
    parser.add_argument("--stream", action="store_true", help="push rows to the backend live")
    parser.add_argument("--base-url", default="http://localhost:8000", help="backend base URL for --stream")
    args = parser.parse_args()

    df = simulate_mission(
        profile_id=args.profile,
        duration_s=args.duration,
        fault_type=args.fault_type,
        severity=args.severity,
        fault_start_s=args.fault_start,
        fault_duration_s=args.fault_duration,
        dt=args.dt,
        seed=args.seed,
    )

    if args.stream:
        stream_to_backend(df, args.base_url)
        return
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"Wrote {len(df)} rows to {args.output}")
        return
    print(df.head(20).to_string(index=False))
    print(f"\nSimulated {len(df)} rows.")


if __name__ == "__main__":
    sys.exit(main())