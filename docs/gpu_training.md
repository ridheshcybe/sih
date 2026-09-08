# GPU Training Guide — SIH26054

Train the four ML models on your GPU server farm, then copy the artifacts back
to the laptop. The backend runs fine **without** any models (it uses safe
rule-based fallbacks so the demo still works), but training makes the anomaly
detection, fault classification, degradation, and RUL numbers real.

## What gets trained

| Model | File (models/) | Input | Output |
|---|---|---|---|
| Anomaly (autoencoder) | `anomaly_autoencoder.pt` | 78-dim features | reconstruction error → 0–1 score |
| Fault classifier (MLP) | `fault_mlp.pt` | 78-dim features | 8-class probabilities |
| Degradation (MLP) | `degradation_mlp.pt` | 78-dim features | 0–1 degradation |
| RUL (MLP) | `rul_mlp.pt` | 78-dim features + degradation | hours remaining |

Each model also writes a `torch_*_meta.json` with the feature names, class list,
and standardization stats — **copy the .pt and .json files together**.

## Steps on the GPU server

```bash
# 1. Get the repo (data/ is gitignored; generate it on the server - ~30 s)
git clone <your-repo-url> && cd <repo>

# 2. Python env + PyTorch with CUDA (pick the wheel matching your driver)
python -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu124   # or cu121/cu126/cu128
pip install -r requirements-gpu.txt

# 3. Train everything (auto-detects CUDA; generates the dataset first if needed)
bash scripts/train_gpu.sh --device auto --epochs 25

# Or per-task, e.g. only the fault classifier on GPU 0:
bash scripts/train_gpu.sh --task fault --device cuda:0 --epochs 40

# 4. Sanity-check the printed metrics
#    - anomaly: healthy segments score ~0, faulty segments clearly higher
#    - fault: test accuracy + per-class precision/recall/F1
#    - degradation / RUL: test MAE and R²
```

## Getting artifacts back to the laptop

The `models/` directory is gitignored (artifacts can be large), so use one of:

```bash
# Option A - copy directly (replace host/path)
scp -r models/ user@laptop:~/<repo>/models/

# Option B - commit them for this repo
git add -f models/ && git commit -m "trained models" && git push
```

Then on the laptop: restart the backend (it loads `models/*.pt` + `torch_*_meta.json`
at startup; check `http://localhost:8000/api/system/info` → `models` status).

## Running on CPU for a quick check

`bash scripts/train_gpu.sh --device cpu --epochs 5` — small epochs give a quick
smoke test of the pipeline, but for real quality use the GPU.

## Optional: scikit-learn baselines (CPU, laptop-friendly)

The original baseline trainers still exist if you ever want them:
`python -m ml.train_anomaly` / `ml.train_fault_classifier` / `ml.train_degradation_rul`
(save `models/*.joblib`). Inference prefers the PyTorch models when both exist.

## Notes

- Deterministic seeds are set (`torch.manual_seed(0)`) so runs are reproducible.
- Early stopping on validation loss is on (patience 6) — you don't need to tune.
- The dataset (`data/train.csv`) uses a fixed mission epoch, so the same seed
  produces byte-identical data on every machine.