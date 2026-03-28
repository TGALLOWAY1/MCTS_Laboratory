# MCTS / Blokus Codebase Audit (2026-03-28)

## Audit checklist (short)
- [x] Verify MCTS loop semantics (selection/expansion/simulation/backprop/root choice).
- [x] Verify multiplayer reward perspective consistency.
- [x] Verify pass/no-move handling vs true Blokus terminal rules.
- [x] Verify legality/move generation and frontier/bitboard consistency surfaces.
- [x] Verify score semantics and winner/tie handling.
- [x] Verify benchmark harness fairness/reproducibility/time-budget semantics.
- [x] Verify diagnostic/analytics metric definitions for misleading semantics.
- [x] Verify major performance bottlenecks and architecture constraints.

## Key findings

### Confirmed critical issues

1) **FastMCTSAgent is not a valid tree search over successor states (critical correctness bug).**
- Evidence:
  - `FastMCTSNode` stores no board/player state; only move/stats.
  - `_fast_mcts_iteration` always calls `_get_cached_legal_moves(board, player)` and `_fast_rollout(board, player)` with the original root board/player rather than the selected node state.
  - Expansion uses `node.expand(legal_moves)` but those legal moves are from the root state, so deeper nodes are not conditioned on prior moves.
- Impact:
  - Search statistics look plausible but are not evaluating a game tree.
  - Reported diagnostics (`maxDepthReached`, `rootPolicy`, etc.) can be deeply misleading.

2) **FastMCTS legal-move cache key is unsafe and can return moves from a different board state.**
- Evidence:
  - Cache key is `f"{player.name}_{board.move_count}"` only; board occupancy/pieces/frontier are ignored.
  - Cache persists on the agent instance across calls.
  - Reproduction script in this audit found mismatched cached vs true legal move sets for two different states with same `(player, move_count)`.
- Impact:
  - Can produce stale/illegal move candidates and distorted evaluations.
  - Causes hidden cross-position contamination that appears deterministic and “fast”.

3) **Main MCTS rollout and backup semantics are perspective-inconsistent in multiplayer.**
- Evidence:
  - `_simulation(node)` calls `_rollout(node.board, node.player)`.
  - `_rollout` computes reward from `player` argument (`initial_score`/`final_score`)—i.e., current node player perspective.
  - `_backpropagation` propagates the same scalar reward unchanged to all ancestors.
  - Selection uses `child.total_reward / child.visits` directly at all depths.
- Impact:
  - Ancestor decisions are optimized using mixed player perspectives.
  - Root action choice is not consistently “best for root player”; trustworthiness of strength results is compromised.

4) **Pass/no-move handling in MCTS search is incorrect (premature terminal behavior).**
- Evidence:
  - Node terminal check: `len(untried_moves)==0 and len(children)==0`.
  - Rollout loop breaks immediately when current player has no legal moves, instead of passing to next player and continuing until all players blocked/end condition.
- Impact:
  - Overestimates terminality, truncates playouts, and biases rewards.
  - Especially harmful in late game and multi-player blocking phases.

### Likely issues / suspicious behaviors

1) **Transposition cache semantics are unsafe for policy/value changes and perspective fixes.**
- Current cache stores only `{reward}` for board hash. If reward semantics are changed to root-relative (recommended), cache key must include perspective context (at least root player or canonical value vector).
- Confidence: high.

2) **Board-level winner API is tie-unsafe.**
- `Board.get_winner()` returns `max(scores)` without tie handling. This can silently convert ties to a single winner.
- Confidence: high.

3) **Metric naming/semantics drift in diagnostics.**
- `branching_factor` is reported as root legal count after search, not empirical average branching.
- `avg_branching` in trace uses `tree_size / root_children_count`, which is not branching factor.
- Confidence: high.

4) **Game scoring semantics are non-standard but described as “standard”.**
- Engine adds corner and center bonuses on top of coverage (+ all-pieces bonus). This is valid as a house variant, but the wording suggests canonical Blokus scoring.
- Confidence: high.

### Possible concerns / hypotheses

1) **Tree parallel mode race conditions may inflate/deflate stats non-deterministically.**
- Code explicitly tolerates races on visits/rewards. Algorithmically acceptable in some MCTS implementations, but metrics comparability may suffer.
- Confidence: medium.

2) **Progressive-history and RAVE use coarse action keys (`piece_id`) rather than full move identity.**
- Could smear value across strategically different placements.
- Confidence: medium.

## Performance bottlenecks (ranked)

1) **Full board copies per node/rollout step** in main MCTS (`board.copy()`) are dominant overhead.
2) **Repeated full legal move generation** in rollouts (especially with heuristic/two-ply) remains expensive.
3) **Search-trace/tree-diagnostic traversal** can be heavy for large trees if always enabled.
4) **Python object-heavy move/position representations** likely limit throughput vs bit-packed move encoding.

## Highest-leverage improvements

### Immediate (correctness first)
1. Fix FastMCTSAgent or mark experimental-only and remove from competitive comparisons.
2. Refactor reward/backup to a consistent root-relative value (or vector-valued multiplayer backup).
3. Implement proper pass handling in tree and rollout (advance player when no legal move; terminal only when all players cannot move).
4. Fix tie semantics in winner APIs used by rollouts/evals.

### Short term
1. Add invariant checks:
   - reward perspective invariant at root,
   - rollout pass progression invariant,
   - cached move legality spot-checks.
2. Add deterministic replay harness and seed-stable regression tests.
3. Clarify metric definitions and rename misleading fields.

### Medium term (research platform)
1. Add vector-valued backups for multiplayer (per-player returns).
2. Add calibrated evaluation at rollout cutoffs and confidence-aware root policy diagnostics.
3. Add transposition entries with richer payloads (visits/value vectors) + policy-consistent keys.

## Suggested validation experiments
- Differential test: MCTS with/without pass-correct rollout on identical seeds and budgets.
- Shadow evaluator: recompute root move ranking using root-relative value vector and compare disagreement rate.
- Cache poisoning test: random states with same move_count/player to detect stale-cache hits.
- Budget fairness test: per-move wall-clock distribution by agent/seat with identical configuration.
