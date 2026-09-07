from __future__ import annotations

from pathlib import Path

from simulator.dataset_generator import generate_mission_dataset
from simulator.mission_profiles import PROFILES, generate_mission_profile


def main() -> None:
    print("Generating simulation dataset...")
    for profile_id in PROFILES:
        profile = generate_mission_profile(profile_id, duration_seconds=1800)
        print(f"Profile: {profile_id} | phases={len(profile['phases'])} | timeline={len(profile['timeline'])}")
        print(f"  first phase: {profile['phases'][0]['phase']} | last phase: {profile['phases'][-1]['phase']}")

    dataset = generate_mission_dataset(num_missions=12, profiles=PROFILES)
    print("Dataset summary:")
    print(dataset["stats"])
    print(f"Files written to: {Path(__file__).resolve().parent.parent / 'data'}")


if __name__ == "__main__":
    main()
