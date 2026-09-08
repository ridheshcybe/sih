#!/usr/bin/env python3
"""GPU (CUDA) training for all four SIH26054 models with PyTorch.

Usage:
  python -m ml.train_gpu --device auto              # train all four (auto picks cuda/mps/cpu)
  python -m ml.train_gpu --task fault --device cuda:0 --epochs 30
  python -m ml.train_gpu --task all --device auto --epochs 20 --batch-size 256

Artifacts (saved to models/):
  anomaly_autoencoder.pt + torch_anomaly_meta.json     (reconstruction-error anomaly)
  fault_mlp.pt            + torch_fault_meta.json      (multiclass MLP)
  degradation_mlp.pt      + torch_degradation_meta.json(sigmoid regressor)
  rul_mlp.pt              + torch_rul_meta.json        (relu regressor, features + degradation)

The dataset is auto-generated on first run if data/train.csv is missing, so the
script works standalone on a GPU server that only has the repo checked out.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
except ImportError as exc:  # noqa: BLE001
    print("torch is not installed. On the GPU server run:\n"
          "  pip install -r requirements-gpu.txt\n"
          "  # or: pip install torch --index-url https://download.pytorch.org/whl/cu124")
    sys.exit(1)

from ml.data_utils import load_splits
from ml.feature_extractor import FeatureExtractor, build_window_dataset
from ml.torch_models import build_model

WINDOW, STRIDE = 10, 2
BATCH = 256
LR = 1e-3
PATIENCE = 6


# ----------------------------------------------------------------------------- data
def _windows(df, extractor):
    return build_window_dataset(df, extractor, WINDOW, STRIDE)


def task_data(task: str):
    """Return (X_train, y_train, X_val, y_val, X_test, y_test, meta_extra)."""
    train, val, test = load_splits()
    ex = FeatureExtractor()

    if task == "anomaly":
        # Train only on healthy windows (normal operating envelope).
        t = train[train["fault_label"] == "none"]
        v = val[val["fault_label"] == "none"]
        X_train, *_ = _windows(t, ex)
        X_val, *_ = _windows(v, ex)
        X_test, y_fault, _, _, _ = _windows(test, ex)
        return X_train, None, X_val, None, X_test, y_fault, {"extractor": ex}

    X_train, y_fault, y_deg, y_rul, _ = _windows(train, ex)
    X_val, v_fault, v_deg, v_rul, _ = _windows(val, ex)
    X_test, t_fault, t_deg, t_rul, _ = _windows(test, ex)

    if task == "fault":
        classes = sorted(set(y_fault) | set(v_fault) | set(t_fault))
        idx = {c: i for i, c in enumerate(classes)}
        return (X_train, np.array([idx[l] for l in y_fault]),
                X_val, np.array([idx[l] for l in v_fault]),
                X_test, np.array([idx[l] for l in t_fault]),
                {"extractor": ex, "classes": classes})
    if task == "degradation":
        return X_train, y_deg.astype(np.float32), X_val, v_deg.astype(np.float32), X_test, t_deg.astype(np.float32), {"extractor": ex}
    if task == "rul":
        # RUL input = features + degradation level (appended after scaling).
        return (X_train, y_rul.astype(np.float32), X_val, v_rul.astype(np.float32),
                X_test, t_rul.astype(np.float32),
                {"extractor": ex, "deg_train": y_deg, "deg_val": v_deg, "deg_test": t_deg})
    raise ValueError(f"Unknown task '{task}'")


def scale(X_train, X_val, X_test):
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std[std < 1e-8] = 1.0
    return (X_train - mean) / std, (X_val - mean) / std, (X_test - mean) / std, mean, std


def make_loader(X, y, batch):
    t = torch.tensor(X, dtype=torch.float32)
    if y is not None:
        t = (t, torch.tensor(y, dtype=torch.float32 if y.dtype == np.float32 else torch.long))
    ds = TensorDataset(*t)
    return DataLoader(ds, batch_size=batch, shuffle=True)


# ------------------------------------------------------------------------ training
def train_loop(model, train_loader, X_val, y_val, criterion, epochs, lr, device):
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    best_loss, best_state, bad = float("inf"), None, 0
    for epoch in range(1, epochs + 1):
        model.train()
        total, n = 0.0, 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            opt.step()
            total += loss.item() * len(xb)
            n += len(xb)
        train_loss = total / max(n, 1)

        model.eval()
        with torch.no_grad():
            vx = torch.tensor(X_val, dtype=torch.float32).to(device)
            out = model(vx)
            if y_val is not None:
                vy = torch.tensor(y_val, dtype=torch.float32).to(device)
                val_loss = criterion(out, vy).item()
            else:  # anomaly: reconstruction MSE
                val_loss = float(((vx - out) ** 2).mean().item())
        if val_loss < best_loss - 1e-5:
            best_loss, bad = val_loss, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                print(f"  early stop at epoch {epoch} (val loss {val_loss:.5f})")
                break
        if epoch == 1 or epoch % 5 == 0:
            print(f"  epoch {epoch:3d}  train={train_loss:.5f}  val={val_loss:.5f}")
    if best_state is None:
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    return best_loss


def save(kind, model, meta: dict):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    fname = {"anomaly": "anomaly_autoencoder.pt", "fault": "fault_mlp.pt",
             "degradation": "degradation_mlp.pt", "rul": "rul_mlp.pt"}[kind]
    mname = {"anomaly": "torch_anomaly_meta.json", "fault": "torch_fault_meta.json",
             "degradation": "torch_degradation_meta.json", "rul": "torch_rul_meta.json"}[kind]
    torch.save(model.state_dict(), MODELS_DIR / fname)
    meta["device"] = str(device)
    meta["torch_version"] = torch.__version__
    meta["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    (MODELS_DIR / mname).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  saved {MODELS_DIR / fname} + {mname}")


def report_anomaly(model, X_test, y_fault, err_mean, err_std):
    ex = FeatureExtractor()
    idx = np.array([i for i, n in enumerate(ex.feature_names) if n.endswith("_residual")])
    with torch.no_grad():
        mse = ((torch.tensor(X_test) - model(torch.tensor(X_test))) ** 2).mean(dim=1).numpy()
    z = (mse - err_mean) / max(err_std, 1e-6)
    score = np.clip((z - 1.0) / 4.0, 0.0, 1.0)
    healthy = y_fault == "none"
    print(f"  healthy segments: score mean={score[healthy].mean():.3f} p95={np.percentile(score[healthy], 95):.3f}")
    print(f"  faulty segments:  score mean={score[~healthy].mean():.3f} p95={np.percentile(score[~healthy], 95):.3f}")


# ------------------------------------------------------------------------------ main
def train_task(task, epochs, lr, batch, device):
    print(f"\n=== Training: {task} ===")
    X_train, y_train, X_val, y_val, X_test, y_test, extra = task_data(task)
    X_train, X_val, X_test, mean, std = scale(X_train, X_val, X_test)
    n_features = X_train.shape[1]
    ex: FeatureExtractor = extra["extractor"]

    meta = {"feature_names": ex.feature_names, "scaler_mean": mean.tolist(), "scaler_std": std.tolist(),
            "window": WINDOW, "stride": STRIDE, "epochs": epochs}

    if task == "anomaly":
        model = build_model("anomaly", n_features).to(device)
        train_loader = make_loader(X_train, None, batch)
        train_loop(model, train_loader, X_val, None, nn.MSELoss(), epochs, lr, device)
        # Normalize reconstruction error using healthy training windows.
        with torch.no_grad():
            err = ((torch.tensor(X_train) - model(torch.tensor(X_train))) ** 2).mean(dim=1).numpy()
        meta["train_err_mean"] = float(err.mean())
        meta["train_err_std"] = float(err.std())
        save("anomaly", model, meta)
        report_anomaly(model, X_test, y_test, err.mean(), err.std())

    elif task == "fault":
        classes = extra["classes"]
        meta["classes"] = classes
        model = build_model("fault", n_features, n_classes=len(classes)).to(device)
        train_loader = make_loader(X_train, y_train, batch)
        train_loop(model, train_loader, X_val, y_val, nn.CrossEntropyLoss(), epochs, lr, device)
        save("fault", model, meta)
        model.eval()
        with torch.no_grad():
            probs = torch.softmax(model(torch.tensor(X_test)), dim=1).numpy()
        pred = probs.argmax(1)
        acc = (pred == y_test).mean()
        print(f"  test accuracy: {acc:.3f}")
        try:
            from sklearn.metrics import classification_report
            print(classification_report(y_test, pred, target_names=classes,
                                        labels=list(range(len(classes))), zero_division=0))
        except Exception:  # noqa: BLE001 - report is optional
            pass

    else:  # degradation / rul
        model = build_model(task, n_features).to(device)
        if task == "rul":
            # RUL input = scaled features + raw degradation level.
            X_train = np.hstack([X_train, extra["deg_train"].reshape(-1, 1)])
            X_val = np.hstack([X_val, extra["deg_val"].reshape(-1, 1)])
            X_test = np.hstack([X_test, extra["deg_test"].reshape(-1, 1)])
        train_loader = make_loader(X_train, y_train, batch)
        train_loop(model, train_loader, X_val, y_val, nn.MSELoss(), epochs, lr, device)
        save(task, model, meta)
        model.eval()
        with torch.no_grad():
            pred = model(torch.tensor(X_test)).numpy()
        mae = float(np.abs(pred - y_test).mean())
        ss_res = float(((y_test - pred) ** 2).sum())
        ss_tot = float(((y_test - y_test.mean()) ** 2).sum())
        r2 = 1.0 - ss_res / max(ss_tot, 1e-9)
        print(f"  test MAE={mae:.4f}  R2={r2:.3f}")

    print(f"=== {task} done ===")


def resolve_device(arg: str):
    if arg == "auto":
        if torch.cuda.is_available():
            return f"cuda:{torch.cuda.current_device()}"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    return arg


def main() -> int:
    parser = argparse.ArgumentParser(description="GPU/CPU training for SIH26054 models")
    parser.add_argument("--task", choices=["anomaly", "fault", "degradation", "rul", "all"], default="all")
    parser.add_argument("--device", default="auto", help="auto | cpu | cuda | cuda:0 | mps")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=BATCH)
    parser.add_argument("--lr", type=float, default=LR)
    args = parser.parse_args()

    if not (DATA_DIR / "train.csv").exists():
        print("Dataset missing - generating it first (this runs on the GPU server too).")
        from simulator.generate_dataset import build_dataset, split_by_mission, write_dataset_csvs
        df = build_dataset(40, 4000, seed=7)
        write_dataset_csvs(*split_by_mission(df))

    global device
    device = torch.device(resolve_device(args.device))
    print(f"torch {torch.__version__} | device: {device}")
    if device.type == "cuda":
        print(f"  GPU: {torch.cuda.get_device_name(device)} | "
              f"{torch.cuda.get_device_count()} device(s) | "
              f"mem {torch.cuda.get_device_properties(device).total_memory / 1e9:.1f} GB")
    elif device.type == "cpu":
        print("  WARNING: running on CPU - for real speed use --device cuda on the GPU farm")

    torch.manual_seed(0)
    np.random.seed(0)

    tasks = ["anomaly", "fault", "degradation", "rul"] if args.task == "all" else [args.task]
    for task in tasks:
        train_task(task, args.epochs, args.lr, args.batch_size, device)

    print("\nAll done. Copy models/*.pt and models/torch_*_meta.json to the laptop's "
          "models/ directory (or un-ignore models/ in .git and commit them).")
    return 0


if __name__ == "__main__":
    sys.exit(main())