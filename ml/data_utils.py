"""Shared helpers for loading the synthetic dataset and model metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ml.feature_extractor import FeatureExtractor, build_window_dataset

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
DEFAULT_WINDOW = 10
DEFAULT_STRIDE = 2


def load_split(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Generate it first with: "
            "python -m simulator.generate_dataset"
        )
    return pd.read_csv(path)


def load_splits() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return load_split("train"), load_split("val"), load_split("test")


def build_features(
    df: pd.DataFrame,
    window: int = DEFAULT_WINDOW,
    stride: int = DEFAULT_STRIDE,
    extractor: Optional[FeatureExtractor] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """Window features + labels for a telemetry frame (per-mission windows)."""
    ex = extractor or FeatureExtractor()
    return build_window_dataset(df, ex, window, stride)


def encode_faults(labels: np.ndarray, classes: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]:
    """Map fault label strings to integer codes."""
    unique = sorted(set(str(l) for l in labels))
    classes = classes or unique
    mapping = {c: i for i, c in enumerate(classes)}
    y = np.array([mapping.get(str(l), mapping.get("none", 0)) for l in labels])
    return y, classes


def save_meta(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_meta(path: Path) -> Dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def healthy_only(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["fault_label"] == "none"].copy()