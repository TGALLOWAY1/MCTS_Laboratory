# Features

## Game Engine

- Bitboard board representation (20x20, 4 players, 21 pieces each) — `engine/board.py`, `engine/bitboard.py`
- Frontier-based move generation with bitboard optimization — `engine/move_generator.py`
- Advanced metrics: mobility, territory, blocking, corner proximity, center distance — `engine/advanced_metrics.py`, `engine/mobility_metrics.py`
- Per-state telemetry and diagnostics — `engine/telemetry.py`
- Pydantic game schemas (config, state, moves, updates) — `schemas/`

## MCTS Search Engine

- Full UCB1 tree search with configurable exploration constant — `mcts/mcts.py`, `mcts/mcts_agent.py`
- Transposition tables via Zobrist hashing — `mcts/zobrist.py`
- Progressive widening for action-space reduction (Layer 3) — `mcts/mcts_agent.py`
- Progressive history for move ordering (Layer 3) — `mcts/mcts_agent.py`
- Configurable rollout policies: random, heuristic, two-ply (Layer 4) — `mcts/mcts_agent.py`
- Rollout cutoff depth with static evaluation fallback (Layer 4) — `mcts/mcts_agent.py`
- Minimax backup blending (Layer 4) — `mcts/mcts_agent.py`
- RAVE (Rapid Action Value Estimation) with tunable equivalence constant (Layer 5) — `mcts/mcts_agent.py`
- N-gram Selection Technique (NST) for rollout bias (Layer 5) — `mcts/mcts_agent.py`
- Phase-dependent evaluation weights (early/mid/late) (Layer 6) — `mcts/state_evaluator.py`
- Regression-calibrated weights from 13K+ self-play states (Layer 6) — `data/layer6_calibrated_weights.json`
- Opponent modeling: alliance detection, king-maker awareness, adaptive profiles (Layer 7) — `mcts/opponent_model.py`
- Asymmetric rollout policies for opponents (Layer 7) — `mcts/mcts_agent.py`
- Root parallelization via multiprocessing (Layer 8) — `mcts/parallel.py`
- Tree parallelization with virtual loss (Layer 8) — `mcts/parallel.py`
- Adaptive exploration constant based on branching factor (Layer 9) — `mcts/mcts_agent.py`
- Adaptive rollout cutoff depth based on branching factor (Layer 9) — `mcts/mcts_agent.py`
- UCT sufficiency threshold (Layer 9) — `mcts/mcts_agent.py`
- Loss avoidance for catastrophic nodes (Layer 9) — `mcts/mcts_agent.py`
- Learned evaluator (GBT model) for state scoring (Layer 2) — `mcts/learned_evaluator.py`
- Move heuristic scoring — `mcts/move_heuristic.py`
- Search trace diagnostics (per-node Q-values, visits, depths) — `mcts/search_trace.py`

## Agents

- Random agent — `agents/random_agent.py`
- Heuristic agent — `agents/heuristic_agent.py`
- Full MCTS agent (Layers 1-9) — `mcts/mcts_agent.py`
- Agent registry for dynamic construction — `agents/registry.py`
- Gameplay protocol for human play — `agents/gameplay_protocol.py`, `agents/gameplay_human.py`

## Arena & Tournament System

- Round-robin tournament scheduling with deterministic seeding — `analytics/tournament/scheduler.py`
- Arena CLI with configurable JSON experiments — `scripts/arena.py`
- 35+ arena configuration presets for layer experiments — `scripts/arena_config*.json`
- TrueSkill multi-player rating — `analytics/tournament/trueskill_rating.py`
- ELO rating — `analytics/tournament/elo.py`
- Bootstrap confidence intervals and permutation tests — `analytics/tournament/statistics.py`
- Seat-position bias analysis — `analytics/baseline/seat_bias.py`
- Arena statistics and aggregation — `analytics/tournament/arena_stats.py`, `analytics/tournament/aggregate.py`
- Self-improvement loop with metric tracking — `scripts/self_improve.py`
- Throughput calibration — `scripts/calibrate_throughput.py`, `data/throughput_calibration.json`

## Analytics & Metrics

- Per-move MCTS diagnostics logging (iterations, tree depth, visit entropy, Q-values) — `analytics/logging/`
- 7 feature extraction modules: territory, blocking, proximity, mobility, pieces, corners, center — `analytics/metrics/`
- Baseline analysis: branching factor, iteration efficiency, Q-value convergence, simulation quality — `analytics/baseline/`
- Heatmap visualization and spatial analysis — `analytics/heatmap/`
- Win probability modeling — `analytics/winprob/`
- Game aggregation and phase splitting — `analytics/aggregate/`
- Arena visualization generation (layer progression charts) — `scripts/generate_arena_visuals.py`, `arena_visuals/`

## Frontend

- React 18 + TypeScript SPA with Zustand state management — `frontend/`
- Interactive Blokus board with piece selection and placement — `frontend/src/components/Board.tsx`
- MCTS visualization suite: rollout histograms, UCT breakdown, exploration/exploitation charts — `frontend/src/components/mcts-viz/`
- Move impact panels: waterfall charts, strategy-mix radar, move-delta diverging bars — `frontend/src/components/telemetry/`
- Advanced MCTS configuration UI with Layer 3-9 parameter controls and layer presets — `frontend/src/components/GameConfigModal.tsx`
- Arena Results page with live pairwise win rate matrix, TrueSkill ratings, and agent config display — `frontend/src/pages/Benchmark.tsx`
- Layer Progression dashboard grouping arena experiments by MCTS layer with expandable result cards — `frontend/src/pages/TrainEval.tsx`
- Analysis page with MCTS diagnostics — `frontend/src/pages/Analysis.tsx`
- ExplainMove panel — `frontend/src/components/ExplainMovePanel.tsx`
- Game history browser with agent config badges and active layer indicators — `frontend/src/pages/History.tsx`
- Recruiter-facing scrolling story page with architecture narrative, animation specs, and impact framing — `frontend/src/pages/RecruiterStoryPage.tsx`, `docs/frontend/recruiter_scrolling_story_page.md`

## Web API

- FastAPI REST backend — `webapi/app.py`
- Gameplay routes: game creation, moves, state management — `webapi/routes_gameplay.py`
- Research routes: training runs, analysis, history, trends, arena results — `webapi/routes_research.py`
- Arena results API: list and detail endpoints for tournament data (`/api/arena-runs`) — `webapi/app.py`, `webapi/routes_research.py`
- Game orchestration with full MCTSAgent (Layers 3-9) — `webapi/app.py`
- Agent factory using MCTSAgent with gameplay adapter — `webapi/gameplay_agent_factory.py`
- MongoDB integration — `webapi/db/`
- Research and deploy profiles — `webapi/profile.py`

## Browser-Side Execution

- Pyodide mirror of engine, MCTS, and agents — `browser_python/`
- WebWorker bridge for background computation — `browser_python/worker_bridge.py`
- Zero-backend Blokus gameplay in the browser

## League Infrastructure

- Self-play league management — `league/league.py`
- ELO tracking — `league/elo.py`
- Plackett-Luce ranking model — `league/pdl.py`
- League database — `league/db.py`

## Scripts & Tools

- Self-play data collection for evaluation refinement — `scripts/collect_layer6_data.py`
- Feature importance analysis (regression, SHAP) — `scripts/analyze_layer6_features.py`
- Eval model training and validation — `scripts/train_eval_model.py`, `scripts/validate_eval_model.py`
- MCTS profiler (time breakdown by phase) — `scripts/profile_mcts.py`
- TrueSkill computation from JSONL logs — `scripts/compute_trueskill_from_jsonl.py`
- Training data generation — `scripts/generate_training_data.py`
- Tournament runner (single-command) — `scripts/run_tournament.py`

## Testing

- Layer-specific test suites (Layers 3, 5, 6, 7, 8, 9) — `tests/test_layer*.py`
- Core engine tests: legality, game over, pass, piece shapes, bitboard — `tests/`
- Integration tests: audit invariants, agent timeout, telemetry — `tests/`
- TrueSkill convergence testing — `tests/test_trueskill_rating.py`
- Analytics metrics tests — `analytics/metrics/tests/`
- Performance benchmarks — `tests/performance_test.py`

## Benchmarking

- Move generation benchmarks — `benchmarks/benchmark_move_generation.py`
- MCTS settings sweep benchmarks — `benchmarks/benchmark_mcts_settings.py`
- Self-play league benchmarks — `benchmarks/bench_selfplay_league.py`

## Data & Calibration

- Regression-calibrated evaluation weights — `data/layer6_calibrated_weights.json`
- Throughput calibration (iterations/ms by phase and depth) — `data/throughput_calibration.json`
- Sample search trace for diagnostics — `data/sample_search_trace.json`
