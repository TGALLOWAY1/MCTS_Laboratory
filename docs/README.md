# Project Documentation Index

Last verified: March 2026.

Welcome to the Blokus RL documentation directory. This folder aggregates all technical documentation, architecture notes, and guides for the project.

## Directory Structure

- **/architecture/**: Architectural decisions, performance optimizations, and audit reports.
- **/config/**: Agent configurations and environment variable setups.
- **/deployment/**: Notes and manifests for deploying the frontend/backend to Vercel/etc.
- **/engine/**: Move generation logic, win detection, and game engine internals.
- **/frontend/**: Setup instructions and design notes for the React UI.
- **/training/**: Documentation covering SB3 / PettingZoo reinforcement learning pipelines, RL agent evaluation, and metrics.
- **/webapi/**: Documentation for FastAPI gameplay and research endpoints.
- **/metrics/**: Notes on advanced mobility metrics, frontier calculations, etc.
- **arena.md**: Reproducible arena experiment runner, output artifacts, summary interpretation, win-probability training commands, and learned-evaluator MCTS integration.
- **datasets.md**: Arena dataset schemas (`games.jsonl`, snapshots parquet/csv), pairwise transformation, and loading examples.
- **profiler_baseline.md**: MCTS profiler baseline results — time breakdown by phase (selection, expansion, simulation, backpropagation), memory footprint, and optimization recommendations.

## Measurement Infrastructure (Layer 0)

The project includes a comprehensive measurement infrastructure for evaluating agent performance:

- **Game Logger** (`analytics/logging/`): Per-move MCTS diagnostics (iterations, tree depth, visit entropy, Q-values, regret gap, score deltas). See `URGENT_TODO.md` at project root for verification instructions.
- **TrueSkill Ratings** (`analytics/tournament/trueskill_rating.py`): Multiplayer skill rating using Plackett-Luce model with convergence detection.
- **Statistical Testing** (`analytics/tournament/statistics.py`): Bootstrap CIs, permutation tests, seat-position analysis, score margins.
- **Profiler** (`scripts/profile_mcts.py`): Structured per-phase MCTS timing breakdown.
- **Tournament Runner** (`scripts/run_tournament.py`): Single command to run a tournament and produce a full report.

*To start running or developing the project, please see the root [README.md](../README.md).*
