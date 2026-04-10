# MCTS Laboratory

**A Blokus AI experimentation platform where a 25-iteration MCTS agent with calibrated evaluation beats a 1,000-iteration agent using defaults — because tuning the evaluation function beats brute-force search.**

<img width="1795" height="865" alt="MCTS Laboratory hero" src="https://github.com/user-attachments/assets/751e771f-ce00-45b8-8289-6086f760cd7d" />

> **TODO:** Replace the static hero image with an animated GIF of an AI-vs-AI demo game, ideally showing the "Explain This Move" panel updating in real time.

## Why this project exists

Most published MCTS work tunes one knob at a time and reports win rates without controlling for compute. I wanted to know whether a systematically-tuned evaluation function could outperform brute-force search in a high-branching-factor game, and whether the full nine layers of MCTS enhancements (RAVE, progressive history, phase weights, parallelization, adaptive exploration) actually compose the way the literature implies. So I built a full-stack lab — engine, agents, arena, analytics, and browser UI — and ran the experiments end-to-end on 4-player Blokus.

## What it does

- Plays 4-player Blokus at thousands of simulations per second with a bitboard + frontier move generator.
- Runs configurable MCTS agents through **nine layers** of enhancements: UCB1, RAVE, progressive history, NST, phase-dependent evaluation, opponent modeling, root/tree parallelization, adaptive meta-optimization.
- Executes reproducible round-robin tournaments via a JSON-config arena runner with deterministic seeding and TrueSkill scoring.
- Runs MCTS in the browser via Pyodide WebWorkers — zero backend compute for the public demo.
- Exposes a React SPA with live move explanations, a scoreboard matrix, and an analysis mode for introspecting the search tree.

## Why it is technically interesting

- **Calibrated weights from 13,332 self-play states** flipped a wrong-sign feature and 3x-underweighted opponent denial. Result: **76% win rate vs. the hand-tuned default**, and an agent at 25 iterations beats one at 1,000 iterations with old weights.
- **Rollout quality > iteration quantity.** Random rollouts with cutoff depth 5 + minimax backup α=0.25 dominate every "smarter" rollout policy. Heuristic rollouts were *the worst* option.
- **Root parallelization (multiprocessing) beats tree parallelization (threads + virtual loss).** The GIL makes the architecturally-correct option slower than single-threaded. Root-2w wins 46% of games in a 4-way round robin.
- **Less is more.** Phase-dependent weights (0% WR), adaptive exploration constant (8% WR), and the combined "full" agent all *lost* to simpler baselines. Negative results are reported as loudly as positive ones.
- Full experimental details: **[KEY_FINDINGS.md](KEY_FINDINGS.md)**.

## Architecture overview

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  React / Vite   │────▶│  FastAPI webapi  │────▶│  Python engine   │
│  SPA frontend   │     │  (optional)      │     │  (bitboard)      │
└────────┬────────┘     └──────────────────┘     └──────────────────┘
         │                                                 ▲
         │  Pyodide WebWorker                              │
         ▼                                                 │
┌─────────────────┐                              ┌──────────────────┐
│ Browser-side    │                              │  MCTS agents     │
│ engine + MCTS   │                              │  (Layers 1–9)    │
└─────────────────┘                              └──────────────────┘
                                                          ▲
                                                          │
                                                 ┌──────────────────┐
                                                 │  Arena runner    │
                                                 │  (round-robin)   │
                                                 └──────────────────┘
```

- **Engine** (`engine/`) — 20×20 bitboard + frontier move generation, Board.copy() fast path.
- **MCTS** (`mcts/`) — `mcts_agent.py` is the full-featured agent; `parallel.py`, `opponent_model.py`, `state_evaluator.py` house Layers 7–9.
- **Arena** (`scripts/arena.py`, `analytics/tournament/`) — reproducible tournaments with JSON/Markdown artifacts.
- **Frontend** (`frontend/`) — React/TypeScript SPA; MCTS runs in a Pyodide WebWorker so the public demo needs no server.
- **Browser mirror** (`browser_python/`) — Pyodide-compatible copy of the engine and MCTS.
- **Web API** (`webapi/`, `api-runtime/`) — FastAPI; optional for local two-process dev and Vercel deployment.

## Key features

- Full MCTS with UCB1, RAVE (k=1000 default), progressive history, NST, opponent modeling, and multi-process root parallelization.
- Phase-aware state evaluator with weights calibrated from regression on 13K+ self-play states (`data/layer6_calibrated_weights.json`).
- Deterministic arena harness with per-layer experiment configs under `scripts/arena_config_layer*.json`.
- In-browser AI via Pyodide — the scoreboard and demo game run entirely client-side.
- MCTS analysis mode: pause, step, and inspect candidate moves, simulation counts, and Q-values.
- 81 preserved arena runs and nine layer reports in `archive/reports/` for reproducibility.

## Demo / live link

> **TODO:** Paste the live Vercel URL here once the current deployment is public.

Local demo walkthrough:

1. Start the frontend (`cd frontend && npm run dev`) or open the live deployment.
2. Click **Run Demo Game** on the home page — an AI-vs-AI match starts automatically.
3. Use **Pause / Step** to freeze the game and inspect state.
4. Open **Explain This Move** to see MCTS candidates, visit counts, and Q-values.
5. Open **AI Scoreboard** for the multi-game evaluation matrix.

## Local setup

Requirements: **Python 3.9+**, **Node 16+**.

```bash
# Clone and install Python deps
pip install -e .

# Install frontend deps
cd frontend && npm install && cd ..

# Run backend (http://localhost:8000)
python run_server.py

# Run frontend in a second terminal (http://localhost:5173)
cd frontend && npm run dev

# Run an arena tournament
python scripts/arena.py --config scripts/arena_config.json

# Run the test suite
pytest tests/
```

Per `CLAUDE.md`: always use `"type": "mcts"` (the full MCTSAgent). The archived `fast_mcts` agent will be rejected by the arena runner.

## Environment variables

**Backend** (`.env` — see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `MONGODB_URI` | MongoDB connection string for league / tournament persistence |
| `MONGODB_DB_NAME` | Database name (default: `blokusdb`) |
| `ENGINE_URL` | Optional URL of an external long-running engine service (e.g. `http://localhost:8100`) |

**Frontend** (`frontend/.env` — see `frontend/.env.example`):

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Base URL of the webapi deployment |
| `VITE_APP_PROFILE` | Set to `deploy` for the simplified 4-player Human-vs-MCTS UI |
| `VITE_ENABLE_DEBUG_UI` | Set to `true` to expose the in-game telemetry / logs tab |

## Deployment overview

Deployed as a three-piece split (see `docs/deployment/DEPLOYMENT_NOTES.md`):

- **Frontend** — Vite static build deployed to Vercel (`frontend/` as project root).
- **Web API** — FastAPI via `@vercel/python` (`api-runtime/app.py`, routed in `vercel.json`).
- **Engine service** — `engine-service/app.py` on a long-running host (Vercel functions are too short-lived for arena workloads); the API proxies to it via `ENGINE_URL`.

Local two-process run for validating the deployment topology:

```bash
uvicorn engine-service.app:app --host 0.0.0.0 --port 8100
ENGINE_URL=http://localhost:8100 python run_server.py
cd frontend && npm run dev
```

## Screenshots

<img width="2816" height="1536" alt="BlokusRL scoreboard" src="https://github.com/user-attachments/assets/93e85cd8-c5fe-4785-ae13-810327a1aa07" />

> **TODO:** Add current screenshots of (a) the Explain-This-Move panel, (b) the AI Scoreboard matrix, and (c) the MCTS analysis mode tree view. Replace the BlokusRL image above if the UI has shifted since.

## Limitations

- **Opponent modeling (Layer 7) is not yet competitive.** Activation thresholds are too strict and the defensive weight shift is dead code. See the Layer 7 note in `CLAUDE.md`. Needs re-implementation.
- **Phase-dependent weights fail in practice** (0% WR) despite looking sound on paper — global calibration is more robust.
- **Tree parallelization is GIL-bound** and slower than single-threaded in Python. Root parallelization is the only option that actually helps.
- **Default 50-move full rollouts** exceed two hours per game; all current configs use `rollout_cutoff_depth` (5 is optimal).
- **Arena tournaments use single-seed 25-game runs.** Statistical confidence would improve with multi-seed 100+ game runs.
- **Original GBT learned evaluator** had 26 ms inference cost, which blew the 200 ms move budget. Currently shelved in favour of the calibrated linear evaluator.

## Future work

1. **TD-UCT learning** — bootstrap evaluation corrections during search; R²=0.136 is low enough that temporal-difference updates should help.
2. **Expand the feature set** — `center_proximity` is the #1 Random Forest feature (36.1% importance) but currently carries zero weight in the evaluator.
3. **Multi-seed validation** — rerun headline experiments at 100+ games across multiple seeds.
4. **Distilled / quantized learned evaluator** — bring the GBT model back within the move budget.
5. **Fix and re-run Layer 7** — loosen activation thresholds, wire up the defensive weight shift, re-test alliance and king-maker detection.

---

### Project history

The full narrative (RL origins → MCTS reframing → nine layers of optimization) is preserved in:

- [`KEY_FINDINGS.md`](KEY_FINDINGS.md) — the headline result, calibrated weights, and layer-by-layer outcomes.
- [`docs/project-history.md`](docs/project-history.md) — full development timeline.
- [`archive/reports/`](archive/reports/) — one report per optimization layer.
- [`archive/rl-agents`](#) branch — the original PyTorch / Stable-Baselines3 / PettingZoo training pipeline, archived March 2026.

**Python** 3.9+ · **Node** 16+ · **License:** see repository
