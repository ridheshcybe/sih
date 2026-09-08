"""PyTorch model architectures for the SIH26054 pipeline.

Shared by the GPU training script (ml/train_gpu.py) and the inference service
(ml/inference.py) so the architecture used at train time is identical at
inference time.
"""

from __future__ import annotations

from typing import List

import torch
from torch import nn


def _mlp(n_features: int, hidden: tuple, out_dim: int, activation: nn.Module = nn.ReLU(),
         final: nn.Module | None = None) -> nn.Sequential:
    layers: List[nn.Module] = []
    prev = n_features
    for h in hidden:
        layers += [nn.Linear(prev, h), activation()]
        prev = h
    layers.append(nn.Linear(prev, out_dim))
    if final is not None:
        layers.append(final)
    return nn.Sequential(*layers)


class AnomalyAutoencoder(nn.Module):
    """Undercomplete autoencoder: reconstruction error = anomaly score."""

    def __init__(self, n_features: int, hidden: tuple = (64, 32)):
        super().__init__()
        self.net = _mlp(n_features, hidden, n_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class FaultMLP(nn.Module):
    """Multiclass fault classifier."""

    def __init__(self, n_features: int, n_classes: int, hidden: tuple = (128, 64)):
        super().__init__()
        self.net = _mlp(n_features, hidden, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class RegressionMLP(nn.Module):
    """Degradation (sigmoid out) and RUL (relu out) share this shape."""

    def __init__(self, n_features: int, hidden: tuple = (128, 64),
                 out_activation: str = "sigmoid"):
        super().__init__()
        final = nn.Sigmoid() if out_activation == "sigmoid" else (nn.ReLU() if out_activation == "relu" else None)
        self.net = _mlp(n_features, hidden, 1, final=final)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).reshape(-1)


def build_model(kind: str, n_features: int, n_classes: int | None = None) -> nn.Module:
    if kind == "anomaly":
        return AnomalyAutoencoder(n_features)
    if kind == "fault":
        if n_classes is None:
            raise ValueError("n_classes is required for the fault model")
        return FaultMLP(n_features, n_classes)
    if kind == "degradation":
        return RegressionMLP(n_features, out_activation="sigmoid")
    if kind == "rul":
        return RegressionMLP(n_features, out_activation="relu")
    raise ValueError(f"Unknown model kind '{kind}'")