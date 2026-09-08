# Task Board & Risks — SIH26054

Status: **code-complete and verified** — backend + frontend + simulator + ML
pipeline all built; 21/21 tests pass; live end-to-end demo works in no-model
fallback mode. ML training is deferred to the team's GPU server farm.

## Next 24 h ⏳

| Task | Owner | Priority |
|---|---|---|
| Run `bash scripts/train_gpu.sh --device auto` on the GPU farm | ML | P0 |
| Copy `models/*.pt` + `models/torch_*_meta.json` back to laptop, restart backend | ML | P0 |
| UI polish pass (tooltips explaining each metric) | Frontend | P2 |
| Docker-compose for one-command demo | Tech Lead | P2 |

## Done ✅

| Task | Owner | Notes |
|---|---|---|
| MVP scope & architecture summary | Tech Lead | `docs/architecture.md`, `PROJECT_PLAN.md` |
| Repo structure + README | Tech Lead | `README.md` |
| API contract | Tech Lead | `docs/api_contract.md` |
| Task board & risk tracker | Tech Lead | this file |
| FastAPI skeleton + health endpoint | Backend | `backend/main.py`, `/api/system/health` |
| DB models + init | Backend | `backend/models.py`, `database.py` |
| Telemetry ingest + twin update stub | Backend | `services/telemetry_ingest.py`, `services/digital_twin.py` |
| WebSocket server + broadcast (throttled) | Backend | `services/ws_manager.py`, `/ws/telemetry/{engine_id}` |
| Mission control + fault injection + replay + reports REST | Backend | routers under `backend/routers/` |
| Simulator: engine model, profiles, fault injection, dataset gen | Simulation | `simulator/` |
| Feature extraction module | ML | `ml/feature_extractor.py` (78-dim) |
| Anomaly / fault / degradation / RUL training scripts | ML | `ml/train_*.py` |
| Inference integration with fallbacks | ML | `ml/inference.py` + `backend/services/ml_inference.py` |
| React skeleton + routing | Frontend | `frontend/src/App.jsx` |
| API client + telemetry display | Frontend | `frontend/src/api/client.js`, telemetry table |
| WebSocket live charts + reconnection | Frontend | `frontend/src/ws/useEngineSocket.js`, Recharts |
| Mission controls + fault injection UI | Frontend | Dashboard page |
| Docs: architecture, API, model card, demo script | Demo | `docs/` |
| Smoke tests (simulator + backend) | Tech Lead | `tests/` |
| Automated E2E browser demo + screenshots | Buffy (Codebuff) | `data/e2e/demo_flow.mjs`, `docs/screenshots/demo/` |

## To Do / Next 24 h ⏳

| Task | Owner | Priority |
|---|---|---|
| Train models on a bigger dataset (e.g., 120 missions) for better metrics | ML | P1 |
| UI polish pass (mobile layout, tooltips explaining each metric) | Frontend | P2 |
| Docker-compose for one-command demo | Tech Lead | P2 |
| Multi-engine support (schema already has engine_id) | Backend | P2 |

## Blocked 🚧

| Task | Blocker |
|---|---|
| Real-engine validation | No hardware access; synthetic-only by design |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| ML inference latency > demo budget | High | Tree models (<5 ms); fallbacks if slow; WS throttling |
| WebSocket disconnects during demo | High | Auto-reconnect + 5 s REST polling fallback |
| Fault simulator bugs / non-determinism | High | Seeded RNG, unit tests on ranges + fault effects |
| Synthetic data unrealistic (credibility) | Medium | Ranges checked against published engine data; honest disclaimers |
| Time pressure / feature creep | High | P0 flow fixed: telemetry → twin → anomaly/fault → RUL → UI |