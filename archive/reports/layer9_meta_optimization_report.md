# Layer 9: Game-Feature-Informed Meta-Optimization

> **Status**: IMPLEMENTED — Adaptive exploration constant, adaptive rollout depth, UCT sufficiency threshold, loss avoidance, and self-improvement loop. Arena experiment config ready for benchmarking.

**Branch:** `claude/layer-9-meta-optimization-ZhFdZ`

## 9.0 — Motivation

Layers 1-8 built a powerful MCTS agent with structured simulations, calibrated evaluation, opponent modeling, and parallelization. However, all hyperparameters — exploration constant C, rollout depth, exploitation vs. exploration balance — remain **fixed** throughout the game.

Blokus has dramatically different characteristics across phases: early-game branching factors exceed 100+ legal moves, while late-game positions may have fewer than 10. A fixed C that explores well in the early game over-explores in the late game; a fixed rollout depth that's efficient early is wastefully short when the game tree narrows.

Layer 9 makes these parameters **adaptive**, driven by game-state features computed at each move. It also adds loss avoidance (from Soemers et al.) to reduce catastrophic blunders.

### Research Foundations

- **Soemers et al., "Towards a Characterisation of MCTS Performance in Different Games"** — Random Forest regressors predict which MCTS configurations work best in which game contexts. Applied internally: treat different Blokus game states as different "games."
- **AutoMCTS (MCTS survey §3.2)** — Self-adaptation mechanisms that adjust hyperparameters during search based on the search landscape.
- **Gudmundsson and Bjornsson (2013)** — Sufficiency threshold: when a child Q-value is clearly dominant, switch to pure exploitation.
- **Soemers et al. (2016), MCTS survey §4.5** — Loss avoidance: re-search away from catastrophic nodes.

## 9.1 — Adaptive Exploration Constant

### Design

Instead of a fixed C = 1.414, the exploration constant scales with the square root of the current branching factor relative to an average:

```
C_effective = C_base * sqrt(branching_factor / avg_branching_factor)
```

- **High branching factor (early game):** C increases, driving more exploration when the tree is wide and the search can't afford to commit early.
- **Low branching factor (late game):** C decreases, favoring exploitation when few moves remain and the position is more deterministic.

The branching factor is simply `len(legal_moves)` at the root, computed once per move in `select_action()`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `adaptive_exploration_enabled` | `false` | Enable branching-factor-adaptive C |
| `adaptive_exploration_base` | `1.414` | Base exploration constant (scales from here) |
| `adaptive_exploration_avg_bf` | `80.0` | Average branching factor for normalisation |

### Implementation

In `select_action()`, before the MCTS loop:
1. Compute `bf = len(legal_moves)`
2. Set `self._effective_exploration_constant = C_base * sqrt(bf / avg_bf)`
3. All `_selection()` and `_selection_with_virtual_loss()` calls use `self._effective_exploration_constant`

When disabled, `_effective_exploration_constant` equals the fixed `exploration_constant`.

## 9.2 — Adaptive Rollout Depth

### Design

Rollout cutoff depth varies inversely with branching factor:

```
cutoff_depth = base_depth * (avg_branching_factor / branching_factor)
```

- **High branching factor:** Shorter rollouts — cheap iterations matter more when the tree is wide.
- **Low branching factor:** Deeper rollouts — each rollout is cheaper and more informative when the tree is narrow.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `adaptive_rollout_depth_enabled` | `false` | Enable branching-factor-adaptive depth |
| `adaptive_rollout_depth_base` | `20` | Base cutoff depth |
| `adaptive_rollout_depth_avg_bf` | `80.0` | Average branching factor for normalisation |

### Implementation

In `select_action()`, compute `self._effective_rollout_cutoff_depth`. In `_rollout()`, use the effective value instead of the fixed `rollout_cutoff_depth`.

## 9.3 — Sufficiency Threshold

### Design

From Gudmundsson and Bjornsson (2013): when any child's Q-value exceeds a threshold α, replace the exploration constant with 0 — pure exploitation. This prevents MCTS from wasting iterations re-exploring clearly inferior moves.

**Auto-calibrating α:** Set α = mean(Q_children) + stddev(Q_children). This adapts to the current game state automatically.

**Timing:** The check fires once, after 1/3 of iterations (warmup period) to allow Q-values to stabilise.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sufficiency_threshold_enabled` | `false` | Enable UCT sufficiency threshold |

### Implementation

`_check_sufficiency_threshold(root)` is called at the warmup point in both `_run_mcts_with_iterations()` and `_run_mcts_with_time_limit()`. If triggered, sets `_effective_exploration_constant = 0.0` for the remainder of the search.

## 9.4 — Loss Avoidance

### Design

From Soemers et al. (2016): when MCTS finds a simulation resulting in a catastrophic outcome (reward below threshold), mark the leaf node's ancestors. On subsequent iterations, selection prefers siblings of flagged nodes, steering the search away from catastrophic paths.

### Mechanism

1. **Flagging (backpropagation):** When `reward < loss_avoidance_threshold`, set `node.loss_detected = True` on each node in the backprop path (excluding root).
2. **Redirection (selection):** `select_child()` with `loss_avoidance=True` filters out flagged children when safe alternatives exist. If all children are flagged, flags are cleared and normal UCB selection proceeds.
3. **One-shot:** The `loss_detected` flag is cleared after it causes one redirection, preventing permanent penalization.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `loss_avoidance_enabled` | `false` | Enable loss avoidance |
| `loss_avoidance_threshold` | `-50.0` | Reward below which a result is catastrophic |

### Impact Evidence

The MCTS survey reports that enhancements including loss avoidance increased average win rate from 31.0% to 48.4% across 60+ video games compared to vanilla MCTS.

## 9.5 — Self-Improvement Loop

### Design

`scripts/self_improve.py` automates the continuous improvement cycle:
1. Run an arena tournament with a specified config
2. Parse `summary.json` for win rates, scores, and TrueSkill ratings
3. Append metrics to `data/self_improve_log.json`
4. Print improvement trends (first run → latest)

### Usage

```bash
# Run a tournament and log results
python scripts/self_improve.py --config scripts/arena_config_layer9_adaptive.json

# Quick smoke test
python scripts/self_improve.py --config scripts/arena_config_layer9_adaptive.json --num-games 4

# View history without running
python scripts/self_improve.py --show
```

## New Files

| File | Purpose |
|------|---------|
| `tests/test_layer9_meta_optimization.py` | 16 unit tests for all Layer 9 features |
| `scripts/arena_config_layer9_adaptive.json` | 4-agent arena config (baseline vs. adaptive variants) |
| `scripts/self_improve.py` | Self-improvement loop orchestration |

## Modified Files

| File | Changes |
|------|---------|
| `mcts/mcts_agent.py` | Layer 9 parameters, adaptive C/depth, sufficiency threshold, loss avoidance |
| `mcts/parallel.py` | Serialize Layer 9 params for root-parallel workers |
| `analytics/tournament/arena_runner.py` | Wire Layer 9 params in `build_agent()` |

## Arena Experiment

The `arena_config_layer9_adaptive.json` config runs 100 round-robin games comparing:

| Agent | Features |
|-------|----------|
| `mcts_baseline` | Fixed C=1.414, fixed depth=20 |
| `mcts_adaptive_c` | Adaptive C only |
| `mcts_adaptive_depth` | Adaptive rollout depth only |
| `mcts_adaptive_full` | All Layer 9 features enabled |

```bash
# Full experiment
python scripts/arena.py --config scripts/arena_config_layer9_adaptive.json

# Smoke test
python scripts/arena.py --config scripts/arena_config_layer9_adaptive.json --num-games 4
```

## Diagnostics

Layer 9 adds four stats keys to `agent.stats`:

| Key | Type | Description |
|-----|------|-------------|
| `adaptive_c_value` | `float` | Effective C used this move (0.0 when disabled) |
| `adaptive_rollout_depth` | `int` | Effective cutoff depth this move (0 when disabled) |
| `sufficiency_activations` | `int` | 1 if sufficiency threshold fired, else 0 |
| `loss_avoidance_triggers` | `int` | Number of nodes flagged for loss avoidance |

## Checklist

- [x] Adaptive C implemented and tested (varies with branching factor)
- [x] Adaptive rollout depth implemented and tested
- [x] Sufficiency threshold implemented with auto-calibrating α
- [x] Loss avoidance implemented and blunder rate measurable via stats
- [x] Self-improvement loop automated and producing tracked results
- [x] All features gated by boolean flags (backward compatible)
- [x] Arena experiment config ready
- [x] 16 unit tests passing
