# MCTS Profiler Baseline Results

**Date:** 2026-03-22
**Agent:** MCTSAgent (standard, heuristic rollouts)
**Configuration:** Default exploration_constant=1.414, transposition_table=True, max_rollout_moves=50

## Key Finding

> **Simulation (rollout) dominates at 99%+ of total time across all game phases.**
> Move generation, selection, expansion, and backpropagation are negligible.
> The primary optimization target is the rollout/simulation phase.

## Phase Breakdown by Game Phase

### Early Game (8 moves played, ~314 legal moves)

| Phase           | Time (s) | %     | Per-iter (μs) |
|-----------------|----------|-------|---------------|
| Selection       | 0.0001   | 0.0%  | 2.5           |
| Expansion       | 0.078    | 0.1%  | 1,557         |
| **Simulation**  | **79.6** | **99.9%** | **1,592,810** |
| Backpropagation | 0.0005   | 0.0%  | 9.6           |

- **Throughput:** ~0.6 iterations/second
- **Move generation:** 2.5ms avg (314 moves)

### Mid Game (25 moves played, ~412 legal moves)

| Phase           | Time (s) | %     | Per-iter (μs) |
|-----------------|----------|-------|---------------|
| Selection       | 0.0002   | 0.0%  | 2.3           |
| Expansion       | 0.393    | 0.7%  | 3,925         |
| **Simulation**  | **55.9** | **99.3%** | **558,986** |
| Backpropagation | 0.001    | 0.0%  | 10.2          |

- **Throughput:** ~1.8 iterations/second
- **Move generation:** 6.1ms avg (412 moves)

## Memory Footprint

| Component               | Size     |
|-------------------------|----------|
| MCTSNode (shallow)      | 56 bytes |
| Board grid (numpy 20×20)| 3,200 bytes |
| Estimated per-node total| ~6-7 KB  |
| Untried moves list      | Varies (314-412 moves in early/mid game) |

## Board.copy() Cost

- **~3 μs** per copy (negligible)
- Uses `object.__new__()` optimization to skip `__init__`
- Includes numpy array copy + dict/set copies

## Implications for Optimization

1. **Rollout is the bottleneck.** At ~560ms-1.6s per rollout, the agent can only complete 1-2 iterations per second. This means:
   - With a 1-second time budget, you get ~1-2 MCTS iterations — far too few for meaningful search.
   - Learned leaf evaluation (replacing rollout with model prediction) would be transformative.

2. **Move generation is cheap** at 2-6ms. Not a significant optimization target.

3. **Board copying is negligible** at ~3μs. No need for make/unmake optimization.

4. **Tree operations (selection + backprop) are trivial** at <15μs combined.

5. **Expansion cost** is moderate at 1.5-4ms (dominated by move generation in the child node's `_initialize_untried_moves()`).

## Recommendation

The immediate priority should be:
- **Replace heuristic rollouts with learned leaf evaluation** (this would reduce simulation time from ~1s to ~1ms per iteration, enabling 100-1000× more iterations per time budget)
- Alternatively, **truncate rollouts aggressively** or use **faster rollout policies**

## How to Reproduce

```bash
# Full profile (all phases, 500 iterations each)
python scripts/profile_mcts.py --iterations 500 --game-phase all

# Quick profile (single phase)
python scripts/profile_mcts.py --iterations 50 --game-phase mid

# Save JSON report
python scripts/profile_mcts.py --iterations 100 --output reports/profile.json
```
