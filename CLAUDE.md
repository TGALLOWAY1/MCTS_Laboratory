# CLAUDE.md — Project Guidelines for Claude Code

## Agent Selection

- **Do NOT use `fast_mcts` (FastMCTSAgent / GameplayFastMCTSAgent). It has been archived.**
  A systematic audit determined that FastMCTS is NOT a valid tree search: nodes do not represent successor states and rollouts use heuristic scoring from the root state. The code has been moved to `archive/agents/` and the arena runner will reject `fast_mcts` agent types with an error. Always use `"type": "mcts"` (MCTSAgent) for arena runs and testing.

## Running Arena Tests

```bash
# Standard arena run
python scripts/arena.py --config scripts/arena_config.json

# Extended rollout test (4x rollout, fewer games)
python scripts/arena.py --config scripts/arena_config_extended_rollout.json

# Smoke test with reduced games
python scripts/arena.py --config scripts/arena_config_extended_rollout.json --num-games 4
```

## Key MCTS Parameters

- `max_rollout_moves`: Controls rollout simulation length (default: 50). The extended rollout config uses 200 (4x).
- `iterations`: Max MCTS iterations per move (default: 1000 for full MCTS).
- `iterations_per_ms`: Conversion rate for deterministic time budgets (10.0 for full MCTS).
- `exploration_constant`: UCB1 exploration parameter (default: 1.414).

### Layer 4: Simulation Strategy Parameters

- `rollout_policy`: Rollout move selection — `"heuristic"` (default), `"random"`, or `"two_ply"`.
- `two_ply_top_k`: Top-K filter for two-ply rollouts (None = evaluate all legal moves).
- `rollout_cutoff_depth`: Cut off rollout at this depth and evaluate statically (None = full rollout). Use 0 for pure static evaluation.
- `minimax_backup_alpha`: Blending weight for implicit minimax backups (0.0 = pure averaging, default).
- `state_eval_weights`: Custom weights dict for `BlokusStateEvaluator` features.

### Layer 5: History Heuristics & RAVE Parameters

- `rave_enabled`: Enable RAVE (Rapid Action Value Estimation) blending in UCB selection (default: `false`).
- `rave_k`: RAVE equivalence constant — controls how long RAVE influence persists. β = sqrt(k / (3×N + k)). Higher k = more RAVE influence. Sweep values: 100, 500, 1000, 5000.
- `nst_enabled`: Enable N-gram Selection Technique for rollout bias (default: `false`).
- `nst_weight`: Softmax temperature for NST scoring during rollouts (default: 0.5).

### Layer 6: Evaluation Function Refinement Parameters

- `state_eval_phase_weights`: Phase-dependent weight dicts `{"early": {...}, "mid": {...}, "late": {...}}` for `BlokusStateEvaluator`. Overrides `state_eval_weights` with phase-appropriate weights based on board occupancy.
- Phase thresholds: early < 0.25, mid < 0.55, late >= 0.55 (board occupancy fraction).
- Calibrated weights derived from regression on 13K+ self-play states are in `data/layer6_calibrated_weights.json`.

### Layer 7: Opponent Modeling Parameters

- `opponent_rollout_policy`: Rollout policy for opponents — `"same"` (default, backward compatible), `"random"`, or `"heuristic"`. When `"same"`, opponents use the same policy as `rollout_policy`.
- `opponent_modeling_enabled`: Master switch for opponent tracking, alliance detection, and king-maker awareness (default: `false`).
- `alliance_detection_enabled`: Track per-opponent blocking rates and flag targeting when rate > threshold × average (default: `false`).
- `alliance_threshold`: Blocking rate multiplier for targeting detection (default: `2.0`).
- `kingmaker_detection_enabled`: Detect late-game king-maker scenarios (occupancy >= 0.55, score gap > threshold) (default: `false`).
- `kingmaker_score_gap`: Score gap threshold for king-maker classification (default: `15`).
- `adaptive_opponent_enabled`: Build cross-game opponent profiles with EMA updates (default: `false`).
- `defensive_weight_shift`: Evaluation weight shift magnitude when under targeting threat (default: `0.15`).

### Layer 8: Parallelization Parameters

- `num_workers`: Number of parallel MCTS workers (default: `1`). When > 1, enables parallel search.
- `virtual_loss`: Virtual loss magnitude for tree parallelization (default: `1.0`). Controls how strongly nodes are penalized during concurrent selection.
- `parallel_strategy`: `"root"` (default, recommended) or `"tree"`. Root parallelization uses multiprocessing (real speedup in Python). Tree parallelization uses threading with virtual loss (GIL-limited but architecturally correct).

### Layer 9: Meta-Optimization Parameters

- `adaptive_exploration_enabled`: Enable branching-factor-adaptive exploration constant C (default: `false`).
- `adaptive_exploration_base`: Base exploration constant for adaptive C (default: `1.414`). Effective C = base * sqrt(bf / avg_bf).
- `adaptive_exploration_avg_bf`: Average branching factor for C normalisation (default: `80.0`).
- `adaptive_rollout_depth_enabled`: Enable branching-factor-adaptive rollout cutoff depth (default: `false`).
- `adaptive_rollout_depth_base`: Base rollout cutoff depth (default: `20`). Effective depth = base * (avg_bf / bf).
- `adaptive_rollout_depth_avg_bf`: Average branching factor for depth normalisation (default: `80.0`).
- `sufficiency_threshold_enabled`: Enable UCT sufficiency threshold — after 1/3 warmup, switch to C=0 when any child Q > mean + stddev (default: `false`).
- `loss_avoidance_enabled`: Enable loss avoidance — redirect selection away from catastrophic nodes (default: `false`).
- `loss_avoidance_threshold`: Reward threshold below which a result is catastrophic (default: `-50.0`).

## Project Structure

- `mcts/mcts_agent.py` — Full MCTSAgent with RAVE, progressive history, NST, configurable rollout policies, opponent modeling (Layer 7), parallelization (Layer 8), and adaptive meta-optimization (Layer 9)
- `mcts/parallel.py` — Root parallelization: worker spawning, config serialization, result merging (Layer 8)
- `mcts/opponent_model.py` — Opponent modeling: blocking tracker, alliance detection, king-maker awareness, adaptive profiles (Layer 7)
- `mcts/state_evaluator.py` — Lightweight state evaluation function with phase-dependent weights (Layers 4, 6)
- `archive/agents/fast_mcts_agent.py` — Archived FastMCTSAgent (NOT valid for competitive use)
- `scripts/arena.py` — Arena CLI entry point
- `scripts/arena_config*.json` — Arena configuration files
- `scripts/collect_layer6_data.py` — Self-play data collection for evaluation refinement
- `scripts/analyze_layer6_features.py` — Feature importance analysis (regression, SHAP, residuals)
- `scripts/self_improve.py` — Self-improvement loop: run tournaments, track metrics over time (Layer 9)
- `analytics/tournament/arena_runner.py` — Arena harness and agent construction
