#!/usr/bin/env bash
# Launch the full demo: trains models if missing, starts the backend, then the
# frontend, and prints the URLs. Ctrl+C stops both.
set -e
cd "$(dirname "$0")/.."

if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
else
  PYTHON=".venv/bin/python"
fi

# 1. Models
if [ ! -f "models/anomaly_model.joblib" ] || [ ! -f "models/fault_classifier.joblib" ]; then
  echo "==> Models missing - training first"
  bash scripts/train_all.sh
fi

# 2. Backend
echo "==> Starting backend on http://localhost:8000"
"$PYTHON" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for the backend to come up
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/api/system/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# 3. Frontend
echo "==> Starting frontend on http://localhost:3000"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

trap 'echo "==> Stopping demo"; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' INT TERM

echo ""
echo "------------------------------------------------------------"
echo "  Dashboard:  http://localhost:3000"
echo "  API docs:   http://localhost:8000/docs"
echo "  Press Ctrl+C to stop."
echo "------------------------------------------------------------"

wait