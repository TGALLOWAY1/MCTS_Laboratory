# MCTS Laboratory — Blokus AI Experimentation Platform

A Blokus AI experimentation platform centered on fast simulation, Monte Carlo Tree Search, analytics, benchmarking, and comparative strategy evaluation.

<img width="1795" height="865" alt="image" src="https://github.com/user-attachments/assets/751e771f-ce00-45b8-8289-6086f760cd7d" />

---

## Contribution: GA-Evolved Heuristic Agent (feat/ga-weight-evolution)

We added an **Island-Model Genetic Algorithm** that evolves heuristic evaluation weights for Blokus — and the resulting agent **beats MCTS 8-to-1**.

### The Problem

The existing `HeuristicAgent` has 4 hand-tuned feature weights. They were never optimized. Meanwhile, MCTS struggles in Blokus due to the enormous branching factor (~80-500 legal moves per turn) and uninformative random rollouts.

### What We Built

1. **`EnhancedHeuristicAgent`** — 10 strategic features (the original 4 + 6 new ones covering opponent awareness, frontier management, and piece economy)
2. **Island-Model GA** — 7 islands in a ring topology, evolving weights via BLX-alpha crossover, tournament selection, and Gaussian mutation with parallel fitness evaluation across 8 CPU cores

### Results

| Agent | Win Rate | Avg Score |
|-------|----------|-----------|
| **GA-Evolved Enhanced Heuristic** | **60.0%** | **96.6** |
| Default Heuristic (4 features) | 32.5% | 88.1 |
| FastMCTS (500 iterations) | 7.5% | 75.9 |
| Random | 0.0% | 60.5 |

The evolved agent uses **zero lookahead** — it evaluates moves instantly using a weighted sum of 10 features. It beats MCTS because the GA discovered a counterintuitive aggressive strategy: play big pieces, rush the center, create outpost corners near opponents, and save flexible pieces for the endgame. Three of the 10 weights flipped sign from their hand-tuned defaults.

### Why MCTS Struggles Here

This isn't unique to Blokus. We independently discovered the same thing that [Nonaga](https://github.com/RaggedR/nonaga) research found — AlphaZero-style MCTS with random rollouts fails in games where the branching factor is too high for shallow search to be meaningful and random play produces uninformative value estimates. In both Blokus and Nonaga, a well-tuned evaluation function with zero lookahead outperforms tree search. The insight: **features matter more than search when search quality is poor.**

### Quick Start

```bash
# Run the GA (full evolution, ~1 hour with 8 cores)
python scripts/ga_evolve_weights.py --islands 7 --population 6 --generations 200 \
    --games-per-eval 6 --workers 8 --sigma-start 1.0 --verbose

# Quick arena comparison (2 minutes)
python scripts/quick_arena.py 40

# Run tests
pytest tests/test_ga_evolve.py -v
```

### New Files

| File | Purpose |
|------|---------|
| `agents/enhanced_heuristic_agent.py` | 10-feature heuristic agent |
| `scripts/ga_evolve_weights.py` | Island-model GA with multiprocessing |
| `scripts/quick_arena.py` | Lightweight game runner for fast benchmarking |
| `scripts/arena_config_ga_evolved.json` | Arena config with evolved weights |
| `tests/test_ga_evolve.py` | 20 unit tests |
| `docs/ga_weight_evolution.md` | Documentation |
| `DESIGN_DECISIONS.md` | Full design rationale, training runs, and results |

See [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for the complete story — including why 3 weights flipped sign and how the island model works.

### Neural Network Experiments

We also trained a ResNet (317k params) on 337k board states from GA self-play, then attempted self-play RL to surpass the GA agent. **The NN did not beat the GA.** Supervised pre-training hit a ceiling (the NN can't beat its teacher), and self-play training plateaued at 33% win rate vs the GA — insufficient data per iteration and value-head-only training couldn't close the gap. Full results and analysis in [NN.md](NN.md).

---

## Architecture at a Glance

- **Game Engine (Python)**: High-performance bitboard and frontier-based move generation, capable of thousands of simulations per second.
- **MCTS Agent**: Full Monte Carlo Tree Search with UCB1, transposition tables, RAVE, progressive history, NST, phase-dependent evaluation, opponent modeling, parallelization, and adaptive meta-optimization (9 layers of iterative improvement).
- **Frontend (React/TypeScript)**: Responsive, color-blind friendly SPA with in-browser Pyodide execution — MCTS runs locally via WebWorkers with zero backend scaling required.
- **Arena System**: Reproducible tournament framework with deterministic seeding, round-robin scheduling, and structured output artifacts.

## Quick Start

```bash
# Install
pip install -e .
cd frontend && npm install && cd ..

# Run backend
python run_server.py            # http://localhost:8000

# Run frontend (separate terminal)
cd frontend && npm run dev      # http://localhost:5173

# Run an arena tournament
python scripts/arena.py --config scripts/arena_config.json
```

## How to Run the Demo

1. Open the live deployment (or run frontend locally via `npm run dev`).
2. Click **Run Demo Game** on the home page.
3. The game will automatically start an AI vs. AI match.
4. Use the **Pause/Step** controls to freeze the game.
5. Watch the **Explain This Move** panel to see the MCTS agent's thought process — top candidates, simulation counts, and Q-values.
6. Click **AI Scoreboard** to view the statistically significant evaluation matrix mapping agent strength hierarchy.

---

## Project History & Development Milestones

This project began as a Blokus reinforcement learning environment and evolved into an MCTS-centered AI experimentation platform. The shift happened in stages: engine speed became the real bottleneck, then league/tournament infrastructure broadened the focus from training to evaluation, and finally the RL components were archived to clarify the project's identity.

For the full narrative, see [docs/project-history.md](docs/project-history.md) and [archive/reports/blokus_project_history_and_milestones.md](archive/reports/blokus_project_history_and_milestones.md).

### Phase 1: RL Foundation (Nov–Dec 2025)

| Date | Milestone | What Changed |
|------|-----------|-------------|
| Nov 30, 2025 | **Initial full-stack RL scaffold** | Engine, agents, frontend, PettingZoo/Gymnasium wrappers, MaskablePPO training in one buildout. |
| Dec 1, 2025 | **VecEnv compatibility** | Stabilized vectorized env support and training throughput benchmarks. |
| Dec 4, 2025 | **Frontier + bitboard move generation (M6)** | Frontier tracking, bitboard legality, equivalence tests. Made simulation throughput a first-class concern — the turning point that made everything else possible. |
| Dec 4, 2025 | **Game-result semantics** | Canonical GameResult, win detection, dead-agent handling, benchmark scripts. |

### Phase 2: From Training to Evaluation (Jan–Feb 2026)

| Date | Milestone | What Changed |
|------|-----------|-------------|
| Jan 19, 2026 | **Self-play league & Elo training** | Self-play pipeline, league modules, agent registry. Shifted from "train one policy" to "compare agents in an ecosystem." |
| Feb 18, 2026 | **Stage 3 analytics platform** | Analytics/logging, metrics packages, tournament utilities, Analysis/History frontend pages. The repo became a research platform. |
| Feb 24, 2026 | **Browser-side MCTS via Pyodide** | Engine + MCTS mirrored into Pyodide WebWorker. Zero-backend-cost gameplay. Changed the project's public identity. |

### Phase 3: MCTS Research Tooling (Mar 2026)

| Date | Milestone | What Changed |
|------|-----------|-------------|
| Mar 2, 2026 | **Arena runner + learned evaluator** | Reproducible arena harness, snapshot datasets, feature extraction, learned evaluator integration. MCTS games became benchmarkable and ML-ready. |
| Mar 2, 2026 | **Fair-time tuning & multiseed benchmarks** | Equal-time tournaments, fairness validation, adaptive-bias benchmarks. Ad hoc experiments became statistically defensible. |
| Mar 5, 2026 | **Metrics v2 & move-delta telemetry** | Telemetry engine, move-delta charts, strategy-mix analysis. |
| Mar 6, 2026 | **RL archival** | Removed RL training code from active branch → `archive/rl-agents`. Made the MCTS-first reframing explicit. |
| Mar 7, 2026 | **MCTS analysis mode** | MCTS diagnostics UI, analysis panel, search introspection as a first-class feature. |
| Mar 21, 2026 | **Performance re-audit** | Found bitboard-path regression, added fast mask shifting, BIT_TABLE lookup, Board.copy() optimization. Re-centered optimization on measurement. |
| Mar 22, 2026 | **End-to-end eval-model pipeline** | Training-data generation, eval-model training, and validation scripts connected in a single workflow. |
| Mar 22, 2026 | **Layer 1 baseline characterization** | Profiler, TrueSkill utilities, tournament runner, baseline report. Began treating MCTS improvement as a staged research program. |

### Phase 4: Layered MCTS Optimization (Mar 2026)

Nine layers of systematic MCTS improvement, each with arena experiments and written reports:

| Layer | Focus | Key Technique |
|-------|-------|--------------|
| **Layer 1** | Baseline characterization | Profiling, TrueSkill evaluation, rollout cost analysis |
| **Layer 2** | Evaluation model | Learned state evaluator with regression on self-play data |
| **Layer 3** | Action reduction | Move filtering and pruning to reduce branching factor |
| **Layer 4** | Simulation strategy | Rollout cutoff depth, random/two-ply/heuristic policies, minimax backups. **Finding:** random rollout + cutoff depth 5 + minimax alpha 0.25 is optimal; default heuristic rollout is the *worst* policy; cutoff_5 at 25 iter beats cutoff_0 at 1000 iter (rollout quality > iteration quantity). See [`archive/reports/layer4_arena_results.md`](archive/reports/layer4_arena_results.md). |
| **Layer 5** | History heuristics & RAVE | RAVE with k=1000 provides 4x convergence speedup; progressive history hurts when combined with RAVE. **Finding:** RAVE-only dominates (44.7% win rate vs 14.7% baseline) and outperforms 4x higher-budget vanilla MCTS (50ms RAVE > 200ms baseline, 15:6 pairwise). See [`archive/reports/layer5_arena_results.md`](archive/reports/layer5_arena_results.md). |
| **Layer 6** | Evaluation refinement | Phase-dependent weights calibrated from 13K+ self-play states. **Finding:** phase-dependent eval (0% win rate) and RAVE variant both decisively lost to calibrated single-weight and default agents in 25-game arena — inverted early-game weight signs, missing `center_proximity`, and hard phase-transition discontinuities made the tree statistics noisy and unreliable. See [`archive/reports/layer6_phase_arena_results.md`](archive/reports/layer6_phase_arena_results.md). |
| **Layer 7** | Opponent modeling | Asymmetric rollout policies, alliance detection, king-maker awareness. **Status: needs re-implementation.** Initial arena testing showed zero effect — all agents produced identical play. Investigation revealed: activation thresholds too strict (alliance needs 3+ moves, kingmaker needs 55% occupancy), defensive weight shift is dead code (never called), and opponent rollout differentiation too weak at low iteration counts. The Blokus research literature models all opponents as a single combined adversary for alliance/kingmaker triggers; current implementation tracks opponents individually with overly conservative thresholds. Requires debugging before re-testing. |
| **Layer 8** | Parallelization | Root-parallel multiprocessing, tree-parallel virtual loss. **Finding:** Root parallelization is the clear winner — root_2w wins 46% of games (TrueSkill #1), root_4w wins 40% (#2), while baseline_1w and tree_2w each win <10%. Tree parallelization is *slower* than single-threaded (GIL contention) and provides zero strength benefit. Throughput scales near-linearly: 1.84x at 2 workers, 3.13x at 4 workers on 4 cores; 8 workers oversubscribes. **Best setting:** `num_workers: 2, parallel_strategy: "root"`. |
| **Layer 9** | Meta-optimization | Adaptive exploration/depth, UCT sufficiency threshold, loss avoidance. **Finding:** Adaptive rollout depth is the only beneficial mechanism -- wins 36% (TrueSkill #1) and is 1.64x faster than baseline by allocating shallow rollouts to high-BF early game and deep rollouts to low-BF late game. Adaptive exploration constant is harmful (8% wins) because it over-explores on top of RAVE. Combined "full" agent loses to baseline. See [`archive/reports/layer9_arena_results.md`](archive/reports/layer9_arena_results.md). |

All layer reports are preserved in [`archive/reports/`](archive/reports/).

---

## Project Structure

```
MCTS_Laboratory/
├── engine/              # Core Blokus engine (bitboard, frontier move gen)
├── mcts/                # MCTS implementation (Layers 1-9)
│   ├── mcts_agent.py    # Full MCTS with RAVE, NST, opponent modeling, parallelization
│   ├── parallel.py      # Root parallelization (Layer 8)
│   ├── opponent_model.py # Alliance detection, king-maker (Layer 7)
│   └── state_evaluator.py # Phase-dependent evaluation (Layers 4, 6)
├── agents/              # Agent implementations (random, heuristic, fast_mcts)
├── analytics/           # Logging, metrics, tournament, win-probability
├── scripts/             # Arena CLI, analysis scripts, utilities
├── frontend/            # React/TypeScript SPA
├── browser_python/      # Pyodide mirror of engine + MCTS
├── webapi/              # FastAPI REST API
├── benchmarks/          # Performance benchmarks
├── schemas/             # Pydantic data models
├── tests/               # Test suite
├── data/                # Calibrated weights and active data
├── config/              # Agent configuration
├── docs/                # Active documentation
│   ├── arena.md         # Arena run schema and outputs
│   ├── datasets.md      # Dataset generation docs
│   ├── engine/          # Move generation, optimization notes
│   ├── mcts-analysis-mode/ # MCTS diagnostics docs
│   ├── deployment/      # Deployment guides
│   └── project-history.md  # Full project narrative
└── archive/             # Historical artifacts
    ├── rl/              # RL configs, logs, models, training docs
    ├── arena_runs/      # 81 timestamped arena run results
    ├── data/            # Parquet datasets, analysis plots
    ├── databases/       # League databases
    ├── reports/         # Layer 1-9 optimization reports
    ├── docs/            # Archived documentation
    ├── logs/            # Historical logs
    └── misc/            # Legacy scripts and plans
```

## Key Components

### Game Engine (`engine/`)
- 20x20 board, 4 players, 21 pieces per player
- Frontier-based move generation with bitboard legality checks
- Optimized caching, Board.copy(), and early-exit `has_legal_moves()`

### MCTS Agent (`mcts/`)
- UCB1 selection with RAVE blending and progressive history
- Configurable rollout policies: random (recommended), heuristic, two-ply
- Phase-dependent state evaluation with calibrated weights
- Minimax backup blending (alpha=0.25 recommended with rollout depth ≥ 5)
- RAVE blending (k=1000 recommended; provides 4x convergence speedup over vanilla MCTS)
- Opponent modeling: asymmetric rollouts, alliance/targeting detection, king-maker awareness
- Parallelization: root-parallel (multiprocessing) or tree-parallel (virtual loss)
- Adaptive meta-optimization: branching-factor-adaptive rollout depth (1.64x speedup, recommended), sufficiency threshold, loss avoidance

### Arena System (`scripts/arena.py`)
- Round-robin tournaments with deterministic seeding
- Structured JSON/Markdown output artifacts
- TrueSkill and win-rate statistics
- See [docs/arena.md](docs/arena.md) for full schema

### Web Interface (`frontend/`)
- In-browser MCTS via Pyodide WebWorkers
- Real-time game visualization, piece placement, move explanation
- AI Scoreboard with multi-game evaluation matrices

## Running Arena Experiments

```bash
# Standard arena run
python scripts/arena.py --config scripts/arena_config.json

# Layer 4 experiments (simulation strategy)
python scripts/arena.py --config scripts/arena_config_layer4_cutoff.json --verbose
python scripts/arena.py --config scripts/arena_config_layer4_two_ply.json --verbose
python scripts/arena.py --config scripts/arena_config_layer4_minimax.json --verbose
python scripts/arena.py --config scripts/arena_config_layer4_combined.json --verbose

# Layer 6 experiments (evaluation weights)
python scripts/arena.py --config scripts/arena_config_layer6_weights.json --verbose
python scripts/arena.py --config scripts/arena_config_layer6_phase.json --verbose

# Layer 5 experiments (RAVE & history heuristics)
python scripts/arena.py --config scripts/arena_config_layer5_rave_k_sweep.json --verbose
python scripts/arena.py --config scripts/arena_config_layer5_head_to_head.json --verbose
python scripts/arena.py --config scripts/arena_config_layer5_convergence.json --verbose

# Layer 9 experiments (meta-optimization)
python scripts/arena.py --config scripts/arena_config_layer9_adaptive.json --verbose

# Smoke test (reduced game count)
python scripts/arena.py --config scripts/arena_config_layer4_cutoff.json --num-games 4 --verbose
```

> **Note on rollout depth**: The default 50-move full rollout (`max_rollout_moves: 50`) was found to exceed 2 hours per game. Arena configs now use `rollout_cutoff_depth` (0, 5, or 10) instead. Layer 4 experiments showed cutoff depth 5 is optimal — deeper rollouts have diminishing returns, and depth 0 (pure static eval) underperforms even with 40× more MCTS iterations.

## Testing

```bash
pytest tests/
```

## Archived RL Code

The original reinforcement learning agents and training pipeline (PyTorch, Stable-Baselines3, PettingZoo environments) were archived on March 6, 2026. To access:

```bash
git fetch && git checkout archive/rl-agents
```

RL training configs, logs, models, and documentation are also preserved in `archive/rl/`.

---

**Python**: 3.9+ | **Node.js**: 16+

<img width="2816" height="1536" alt="BlokusRL" src="https://github.com/user-attachments/assets/93e85cd8-c5fe-4785-ae13-810327a1aa07" />
