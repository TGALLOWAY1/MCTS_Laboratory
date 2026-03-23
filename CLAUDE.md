# CLAUDE.md — Project Guidelines for Claude Code

## Agent Selection

- **Do NOT use `fast_mcts` (FastMCTSAgent / GameplayFastMCTSAgent) unless the user explicitly asks for it.**
  The fast_mcts agent uses a simplified rollout policy and lightweight node structure that trades accuracy for speed. Layer 2 analysis found that the evaluation function underperforms under the constrained search time of fast_mcts. Default to the full `mcts` agent type (MCTSAgent) for arena runs and testing.

- When creating new arena configs, prefer `"type": "mcts"` over `"type": "gameplay_fast_mcts"` or `"type": "fast_mcts"`.

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
- `iterations_per_ms`: Conversion rate for deterministic time budgets (10.0 for full MCTS, 20.0 for fast_mcts).
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

## Project Structure

- `mcts/mcts_agent.py` — Full MCTSAgent with RAVE, progressive history, NST, configurable rollout policies, and opponent modeling (Layer 7)
- `mcts/opponent_model.py` — Opponent modeling: blocking tracker, alliance detection, king-maker awareness, adaptive profiles (Layer 7)
- `mcts/state_evaluator.py` — Lightweight state evaluation function with phase-dependent weights (Layers 4, 6)
- `agents/fast_mcts_agent.py` — Lightweight FastMCTSAgent (use only when explicitly requested)
- `scripts/arena.py` — Arena CLI entry point
- `scripts/arena_config*.json` — Arena configuration files
- `scripts/collect_layer6_data.py` — Self-play data collection for evaluation refinement
- `scripts/analyze_layer6_features.py` — Feature importance analysis (regression, SHAP, residuals)
- `analytics/tournament/arena_runner.py` — Arena harness and agent construction
