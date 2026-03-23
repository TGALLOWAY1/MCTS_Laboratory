# Documentation Index

Last updated: March 2026.

## Active Documentation

- **/architecture/**: Engine optimization reports and performance results.
- **/config/**: Agent configurations and environment variable setups.
- **/deployment/**: Deployment notes and manifests (Vercel, etc.).
- **/engine/**: Move generation logic, win detection, and game engine internals.
- **/frontend/**: Setup instructions and design notes for the React UI.
- **/mcts-analysis-mode/**: MCTS diagnostics, analysis panel usage, metrics explained.
- **/metrics/**: Advanced mobility metrics, frontier calculations, endgame analysis.
- **/telemetry/**: Move-delta dashboards, move-vs-round semantics, verification.
- **/webapi/**: FastAPI gameplay and research endpoint documentation.
- **arena.md**: Arena experiment runner, output artifacts, win-probability training, learned-evaluator integration.
- **datasets.md**: Arena dataset schemas (`games.jsonl`, snapshots parquet/csv), pairwise transformation.
- **evaluation.md**: State evaluation design and feature descriptions.
- **profiler_baseline.md**: MCTS profiler baseline — time breakdown by phase, memory footprint, optimization notes.
- **project-history.md**: Full narrative of the project's evolution from RL environment to MCTS platform.

## Archived Documentation

Outdated, RL-specific, and historical documentation has been moved to `archive/docs/` and `archive/rl/training-docs/`. This includes:
- RL training architecture, VecEnv compatibility, checkpoint docs
- Cleanup plans, audit notes, verification checklists
- MongoDB setup, tournament planning docs

## Measurement Infrastructure

- **Game Logger** (`analytics/logging/`): Per-move MCTS diagnostics (iterations, tree depth, visit entropy, Q-values, regret gap, score deltas).
- **TrueSkill Ratings** (`analytics/tournament/trueskill_rating.py`): Multiplayer skill rating with convergence detection.
- **Statistical Testing** (`analytics/tournament/statistics.py`): Bootstrap CIs, permutation tests, seat-position analysis.
- **Profiler** (`scripts/profile_mcts.py`): Structured per-phase MCTS timing breakdown.
- **Tournament Runner** (`scripts/run_tournament.py`): Single command for tournament + full report.

*To start running the project, see the root [README.md](../README.md).*
