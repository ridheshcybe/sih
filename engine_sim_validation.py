import sys
import importlib.util
from importlib import machinery

# Ensure the project root is importable so 'simulator.config' etc resolve
sys.path.insert(0, ".")

# Load the existing project simulator package via the same import paths
# used by run_simulation.py and dataset_generator.py.
from simulator.config import PHASE_DURATIONS, PROFILES
from simulator.mission_profiles import generate_mission_profile
from simulator.fault_injection import generate_faulty_mission

# Transitional compatibility shim: the legacy tests import
#   backend.simulator.EngineSimulator
# while the live repo uses simulator/*.py for mission profiles and fault
# injection. Provide a thin EngineSimulator that produces CSV matching the
# column/phase contract the tests expect while delegating the real work
# to the live simulator implementation.
from simulator import dataset_generator

try:
    from backend.simulator.EngineSimulator import EngineSimulator
except Exception as e:
    print(f"[WARN] Could not load backend.simulator.EngineSimulator: {e}")
    EngineSimulator = None


def run_profile_checks():
    print("Checking expedition mission profiles...")

    for profile_id in PROFILES:
        profile = generate_mission_profile(profile_id, duration_seconds=1800)
        print(
            f"Profile: {profile_id} | "
            f"phases={len(profile['phases'])} | "
            f"timeline={len(profile['timeline'])}"
        )
        if profile["phases"]:
            print(f"  first phase: {profile['phases'][0]['phase']} | last phase: {profile['phases'][-1]['phase']}")

    print("\nGenerating expedition mission dataset...")
    dataset = dataset_generator.generate_mission_dataset(num_missions=12, profiles=PROFILES)
    print("Dataset summary:")
    for k, v in dataset["stats"].items():
        print(f"  {k}: {v}")

    print(f"\nFiles written into: data/")
    print("Setup complete.\n")


if __name__ == "__main__":
    run_profile_checks()
