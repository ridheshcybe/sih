from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from simulator.config import DATA_DIR, README_PATH, TEST_PATH, TRAIN_PATH, VAL_PATH
from simulator.fault_injection import generate_faulty_mission
from simulator.mission_profiles import PROFILES, generate_mission_profile


def _build_fault_plan(profile_id: str, fault_type: str, severity: float, start_time: int = 180, end_time: int = 900) -> Dict[str, float | str]:
    return {
        "fault_type": fault_type,
        "severity": severity,
        "start_time": start_time,
        "end_time": end_time,
        "profile_id": profile_id,
    }


def generate_mission_dataset(num_missions: int = 12, profiles: Iterable[str] | None = None, fault_configs: Iterable[Dict[str, object]] | None = None, output_dir: str | Path | None = None) -> Dict[str, pd.DataFrame]:
    output_dir = Path(output_dir) if output_dir else DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    profiles = list(profiles) if profiles is not None else PROFILES
    if fault_configs is None:
        fault_configs = [
            _build_fault_plan("injector_degradation", "injector_degradation", 0.65, 200, 950),
            _build_fault_plan("lubrication_issue", "lubrication_issue", 0.7, 250, 900),
            _build_fault_plan("overheating", "overheating", 0.6, 300, 1200),
            _build_fault_plan("battery_alternator_degradation", "battery_alternator_degradation", 0.5, 150, 700),
        ]

    mission_frames: List[pd.DataFrame] = []
    healthy_missions = int(num_missions * 0.6)
    faulty_missions = num_missions - healthy_missions

    for mission_index in range(num_missions):
        profile_id = profiles[mission_index % len(profiles)]
        if mission_index < healthy_missions:
            fault_list = []
        else:
            choices = [
                [
                    _build_fault_plan(profile_id, "injector_degradation", round(random.uniform(0.5, 0.9), 2), 200, 980),
                ],
                [
                    _build_fault_plan(profile_id, "lubrication_issue", round(random.uniform(0.5, 0.8), 2), 250, 900),
                ],
                [
                    _build_fault_plan(profile_id, "overheating", round(random.uniform(0.5, 0.85), 2), 300, 1200),
                ],
                [
                    _build_fault_plan(profile_id, "battery_alternator_degradation", round(random.uniform(0.4, 0.7), 2), 180, 750),
                ],
            ]
            fault_list = random.choice(choices)

        frames = generate_faulty_mission(profile_id, fault_list)
        df = pd.DataFrame(frames)
        df["mission_id"] = mission_index + 1
        df["profile_id"] = profile_id
        mission_frames.append(df)

    combined = pd.concat(mission_frames, ignore_index=True)
    combined = combined.sort_values(["mission_id", "timestamp"]).reset_index(drop=True)

    train_missions, val_missions, test_missions = _split_by_mission(combined["mission_id"].unique(), ratios=(0.6, 0.2, 0.2))
    train_df = combined[combined["mission_id"].isin(train_missions)].copy()
    val_df = combined[combined["mission_id"].isin(val_missions)].copy()
    test_df = combined[combined["mission_id"].isin(test_missions)].copy()

    train_df.to_csv(TRAIN_PATH, index=False)
    val_df.to_csv(VAL_PATH, index=False)
    test_df.to_csv(TEST_PATH, index=False)

    stats = {
        "num_missions": int(num_missions),
        "train_missions": len(train_missions),
        "val_missions": len(val_missions),
        "test_missions": len(test_missions),
        "rows": len(combined),
        "healthy_rows": int((combined["fault_type"] == "healthy").sum()),
        "faulty_rows": int((combined["fault_type"] != "healthy").sum()),
        "profiles": dict(combined["profile_id"].value_counts().to_dict()),
        "fault_distribution": dict(combined["fault_type"].value_counts().to_dict()),
    }

    readme_path = generate_readme(output_dir / "README.md", stats)
    return {
        "train": train_df,
        "val": val_df,
        "test": test_df,
        "readme": readme_path,
        "stats": stats,
    }


def _split_by_mission(mission_ids: List[int], ratios: Tuple[float, float, float]) -> Tuple[List[int], List[int], List[int]]:
    shuffled = sorted(list(mission_ids))
    train_count = int(len(shuffled) * ratios[0])
    val_count = int(len(shuffled) * ratios[1])
    test_count = len(shuffled) - train_count - val_count
    total = train_count + val_count + test_count
    if total != len(shuffled):
        test_count = max(1, len(shuffled) - train_count - val_count)
    return shuffled[:train_count], shuffled[train_count:train_count + val_count], shuffled[train_count + val_count:train_count + val_count + test_count]


def generate_readme(path: str | Path, stats: Dict[str, object]) -> Path:
    path = Path(path)
    lines = [
        "# Synthetic Engine Fault Dataset",
        "",
        "This dataset contains synthetic telemetry generated to model aero-piston engine operation in MALE UAV missions.",
        "",
        "## Dataset summary",
        f"- Number of missions: {stats['num_missions']}",
        f"- Total rows: {stats['rows']}",
        f"- Healthy rows: {stats['healthy_rows']}",
        f"- Faulty rows: {stats['faulty_rows']}",
        f"- Train missions: {stats['train_missions']}",
        f"- Validation missions: {stats['val_missions']}",
        f"- Test missions: {stats['test_missions']}",
        "",
        "## Profiles used",
        "- standard_isr",
        "- high_altitude",
        "- hot_weather",
        "- aggressive",
        "",
        "## Fault labels",
        "- healthy: normal operation",
        "- misfire: transient RPM loss with EGT spike and vibration rise",
        "- injector_degradation: rising EGT and CHT with fuel-flow drift",
        "- lubrication_issue: fall in oil pressure and increase in oil temperature/vibration",
        "- overheating: CHT/EGT exceed normal thermal envelope",
        "- sensor_drift: sensor bias begins to diverge from true value",
        "- sensor_dropout: a sensor returns NaN or unrealistic values",
        "- abnormal_vibration: vibration RMS rises beyond expected runtime levels",
        "- battery_alternator_degradation: voltage drop and alternator current anomalies",
        "",
        "## Label descriptions",
        "- fault_type: string label for the active fault condition",
        "- fault_severity: scalar severity in the range [0, 1]",
        "- degradation_level: scalar degradation estimate in [0, 1]",
        "- rul_label: nominal or degraded life-remaining state",
        "",
        "## Split policy",
        "The dataset is split by mission ID: 60% train, 20% validation, 20% test. There is no overlap between splits.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


__all__ = ["generate_mission_dataset", "generate_readme"]
