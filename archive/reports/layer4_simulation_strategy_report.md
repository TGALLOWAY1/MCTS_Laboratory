# Layer 4: Simulation Strategy Report

> **Status**: IMPLEMENTED — Two-ply search-based playouts, early rollout termination, and implicit minimax backups fully integrated. Arena experiment configs ready for benchmarking.

**Branch:** `claude/layer-4-simulation-strategy-NKpzu`

## 4.0 — Motivation

The Layer 1 simulation quality audit revealed a critical gap: the heuristic-only agent scored 83.4 while the full MCTS agent scored only 75.4 — a negative 8-point penalty from tree search. This indicates random/heuristic rollouts produce low-quality game continuations in 4-player Blokus, making MCTS iterations work with noisy, weakly informative evaluations.

**Layer 4 addresses rollout quality directly.** Improving simulation quality has a multiplicative effect — every iteration becomes more valuable, even if fewer iterations are possible.

### Dependencies
- **Layer 3** (action reduction): Progressive widening and history are available for combination
- **Layer 1** (simulation quality audit): Baseline characterization provides comparison targets

## 4.1 — Two-Ply Search-Based Playouts

### Technique (Nijssen's Thesis, Chapter 6)

> "Two-ply searches in the playout phase of multi-player MCTS may increase the playing strength significantly, even at the cost of less playouts."

During the rollout simulation, instead of selecting moves by heuristic/random at each step, perform a shallow lookahead: evaluate candidate moves using a lightweight state evaluation function and select the best.

### Implementation

**New method: `MCTSAgent._two_ply_select(board, player, legal_moves)`**

For each candidate move:
1. Apply move to a board copy
2. Evaluate resulting state with `BlokusStateEvaluator`
3. Return the move with highest evaluation for current player

**Top-K filtering**: When `two_ply_top_k` is set, only the top-K moves (by move heuristic score from Layer 3) are evaluated. This bounds the per-step cost.

**Rollout policy dispatch** (`rollout_policy` parameter):
| Policy | Description | Throughput |
|--------|-------------|------------|
| `"heuristic"` | Default — softmax over piece size, corners, center | Baseline |
| `"random"` | Uniform random legal move selection | ~10x faster |
| `"two_ply"` | One-ply lookahead with state evaluation | ~K× slower per step |

### Configurations to Test

| Config | `rollout_policy` | `two_ply_top_k` | `rollout_cutoff_depth` | Expected Tradeoff |
|--------|-----------------|-----------------|----------------------|-------------------|
| Heuristic baseline | `heuristic` | — | — | Max iterations, moderate quality |
| Random baseline | `random` | — | — | Max iterations, min quality |
| Two-ply full + cutoff 8 | `two_ply` | — (all) | 8 | Highest quality, fewest iterations |
| Two-ply K=10 + cutoff 8 | `two_ply` | 10 | 8 | Balanced quality vs throughput |

**Arena config:** `scripts/arena_config_layer4_two_ply.json`

## 4.2 — Early Termination with State Evaluation Function

### State Evaluation Function

**New module: `mcts/state_evaluator.py`** — `BlokusStateEvaluator` class

Lightweight board-state evaluation normalised to [0, 1]:

```
V(state, player) = w1 * squares_placed
                 + w2 * remaining_piece_area
                 + w3 * accessible_corners
                 + w4 * reachable_empty_squares
                 + w5 * largest_remaining_piece_size
                 + w6 * opponent_avg_mobility
                 + w7 * territory_enclosure_area
```

**Feature details:**

| # | Feature | Normalisation | Source | Weight |
|---|---------|--------------|--------|--------|
| 1 | squares_placed | / 89 (total piece area) | `np.sum(grid == player.value)` | +0.30 |
| 2 | remaining_piece_area | / 89 | `sum(unused piece sizes)` | −0.15 |
| 3 | accessible_corners | / 40 (frontier upper bound) | `board.get_frontier(player)` | +0.25 |
| 4 | reachable_empty_squares | / 60 (BFS limit) | Bounded BFS from frontier | +0.10 |
| 5 | largest_remaining_piece_size | / 5 | `max(unused piece sizes)` | +0.10 |
| 6 | opponent_avg_mobility | / 40 | Mean opponent frontier size | −0.10 |
| 7 | territory_enclosure_area | — | Placeholder (weight=0) | 0.00 |

**Performance**: Features 1–3, 5–6 use pre-computed data on `Board` (O(1) or O(21)). Feature 4 uses bounded BFS limited to 60 cells. Target: <0.5ms per call.

### Early Termination Mechanism

**New parameter: `rollout_cutoff_depth`** (default: `None` = full rollout)

When `moves_made >= rollout_cutoff_depth`, the rollout terminates and the state evaluator provides the reward:
```python
reward = state_evaluator.evaluate(sim_board, player) * eval_reward_scale
```

The `eval_reward_scale` (100.0) matches the magnitude of existing rewards (score deltas + win bonus).

### Cutoff Depth Sweep

| Depth | Description | Expected Throughput |
|-------|-------------|-------------------|
| 0 | Pure static evaluation — no rollout at all | Maximum |
| 4 | Short rollout + evaluation | High |
| 8 | Moderate rollout + evaluation | Moderate |
| 16 | Long rollout + evaluation | Lower |
| None | Full rollout to terminal or max_rollout_moves | Baseline |

**Arena config:** `scripts/arena_config_layer4_cutoff.json`

### Interpreting Results

- **Depth 0 wins**: Evaluation function is strong enough to skip rollouts. Invest heavily in evaluation refinement (Layer 6).
- **Depth 4–8 wins**: Partial rollouts add information the static eval misses. Use adaptive depth by game phase.
- **Full rollout wins**: Evaluation function is too weak for early termination. Improve features.

## 4.3 — Implicit Minimax Backups

### Technique (Lanctot et al., 2014)

Standard MCTS averaging can be misleading in multiplayer games. If a move leads to a state where one opponent has a devastating response, random rollouts will rarely simulate that targeted play. The minimax component catches worst-case scenarios.

**Blended Q-value:**
```
Q_hat(s, a) = (1 - alpha) * (r / n) + alpha * v_minimax
```

where `v_minimax` is maintained implicitly alongside standard MCTS updates.

### Implementation

**New fields on `MCTSNode`:**
- `minimax_value: float` — best/worst child Q-value from root player's perspective
- `blended_q(alpha)` — returns blended exploitation value

**Backpropagation update:**
After each `node.update(reward)`, if `minimax_backup_alpha > 0`:
- If `node.player == root_player`: `minimax_value = max(child Q-values)` (maximise)
- If `node.player != root_player`: `minimax_value = min(child Q-values)` (opponents minimise)

**UCB1 integration:**
The exploitation term in UCB1 uses `blended_q(alpha)` instead of raw `total_reward / visits`.

### Alpha Sweep

| Alpha | Description |
|-------|-------------|
| 0.0 | Pure averaging (baseline — current behavior) |
| 0.1 | Light minimax influence |
| 0.25 | Moderate blending |
| 0.5 | Heavy minimax influence |

**Key diagnostic**: Blunder frequency — how often does the agent finish last or lose 10+ points vs. a "safe" alternative? If implicit minimax reduces blunders, it's catching tactical oversights.

**Arena config:** `scripts/arena_config_layer4_minimax.json`

## 4.4 — Combined Experiment

After individual experiments, the best settings from each sub-task are combined:

| Agent | Settings |
|-------|----------|
| Baseline | Default heuristic rollout, full rollout, alpha=0 |
| Two-ply K=10 + cutoff 8 | Best from 4.1 |
| Cutoff 4 + minimax 0.1 | Best from 4.2 + 4.3 |
| All combined | Two-ply K=10 + cutoff 8 + minimax 0.1 |

**Arena config:** `scripts/arena_config_layer4_combined.json`

## Implementation Summary

### New Files
| File | Description |
|------|-------------|
| `mcts/state_evaluator.py` | `BlokusStateEvaluator` — 7-feature state evaluation, normalised [0,1] |
| `scripts/arena_config_layer4_two_ply.json` | 4.1 experiment config |
| `scripts/arena_config_layer4_cutoff.json` | 4.2 experiment config |
| `scripts/arena_config_layer4_minimax.json` | 4.3 experiment config |
| `scripts/arena_config_layer4_combined.json` | Combined experiment config |

### Modified Files
| File | Changes |
|------|---------|
| `mcts/mcts_agent.py` | 5 new constructor params, `_rollout()` with cutoff + policy dispatch, `_two_ply_select()`, `MCTSNode.blended_q()` + `minimax_value`, minimax in `_backpropagation()`, minimax in `_selection()` UCB |
| `analytics/tournament/arena_runner.py` | `build_agent()` wires Layer 4 params |

### New MCTSAgent Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rollout_policy` | str | `"heuristic"` | Rollout move selection strategy |
| `two_ply_top_k` | Optional[int] | None | Top-K filter for two-ply (None = all) |
| `rollout_cutoff_depth` | Optional[int] | None | Early termination depth (None = full) |
| `state_eval_weights` | Optional[Dict] | None | Custom evaluator weights |
| `minimax_backup_alpha` | float | 0.0 | Minimax blending (0 = off) |

### New Stats Tracked
| Stat | Description |
|------|-------------|
| `two_ply_evals` | Number of state evaluations in two-ply rollout |
| `cutoff_evals` | Number of early termination evaluations |
| `minimax_updates` | Number of minimax backup updates in backprop |

### Backward Compatibility
All default parameters reproduce existing behavior exactly. No existing tests or configs are affected.

## Smoke Test Results

Functional verification with 5 configurations (5–10 iterations each):

| Config | Result | Key Stats |
|--------|--------|-----------|
| Heuristic baseline | Pass | 8.8s/5 iter |
| Random rollout | Pass | 0.75s/5 iter (~10x faster) |
| Cutoff depth 0 | Pass | cutoff_evals=5 (one per iteration) |
| Two-ply K=5 cutoff=4 | Pass | two_ply_evals=100, cutoff_evals=5 |
| Minimax alpha=0.25 | Pass | minimax_updates=10 |

## Running the Experiments

```bash
# 4.1: Two-ply playout comparison
python scripts/arena.py --config scripts/arena_config_layer4_two_ply.json

# 4.2: Cutoff depth sweep
python scripts/arena.py --config scripts/arena_config_layer4_cutoff.json

# 4.3: Minimax alpha sweep
python scripts/arena.py --config scripts/arena_config_layer4_minimax.json

# 4.4: Combined best settings
python scripts/arena.py --config scripts/arena_config_layer4_combined.json

# Smoke test (reduced games)
python scripts/arena.py --config scripts/arena_config_layer4_two_ply.json --num-games 4
```

## Checklist

- [x] Two-ply search-based playouts implemented with configurable K (top-K filtering)
- [x] State evaluation function implemented and normalised to [0, 1]
- [x] Three playout configurations testable (random, heuristic, two-ply)
- [x] Cutoff depth sweep configs ready (depth 0, 4, 8, full)
- [x] Implicit minimax backups implemented with configurable alpha
- [x] Arena configs created for all experiments
- [x] Smoke tests passed for all configurations
- [ ] Full arena runs with TrueSkill ratings (pending — ~25 games per config)
- [ ] Blunder frequency analysis (pending — requires arena results)
- [ ] Optimal simulation strategy documented with TrueSkill evidence (pending)

## Key Decisions This Layer Informs

| Finding | Decision | Layer Affected |
|---------|----------|----------------|
| Two-ply playouts win | Progressive History (Layer 5) applies to structured rollouts | Layer 5 |
| Depth 0 wins (no rollout) | Maximise evaluation function investment | Layer 6 |
| Depth 4–8 wins | Use adaptive depth by game phase | Layer 9.2 |
| Blunders reduced by minimax | Keep minimax backups; tune alpha per phase | Layer 9.2 |
| Blunders NOT reduced | Problem is in evaluation quality, not backup method | Layer 6 |

## Next Steps

1. Run full 25-game arena sweeps for each experiment config
2. Analyse TrueSkill ratings and throughput (iterations/second)
3. Compute quality × throughput product to find net-positive sweet spot
4. Run blunder frequency analysis on minimax results
5. Select optimal simulation strategy and create combined config
6. Feed results into Layer 5 (Progressive History) and Layer 6 (evaluation refinement)
