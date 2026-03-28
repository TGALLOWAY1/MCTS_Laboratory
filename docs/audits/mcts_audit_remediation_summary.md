# MCTS Audit Remediation Summary

**Date:** 2026-03-28
**Audit version:** `v1_2026-03-28`

## What Was Fixed

### 1. FastMCTS Removed from Competitive Use
FastMCTS (`FastMCTSAgent`, `GameplayFastMCTSAgent`) was determined to be an
invalid tree search: nodes did not represent successor states and rollouts used
heuristic scoring from the root state. All competitive code was archived to
`archive/agents/`. The arena runner now rejects `fast_mcts` and
`gameplay_fast_mcts` agent types with a clear error.

### 2. Reward Perspective Fixed
Previously, rollout reward was computed from the *expanding node's player
perspective* and backpropagated unchanged to all ancestors. In multiplayer
Blokus this mixed perspectives and corrupted root decisions.

**Fix:** All reward computation (score delta, win/tie bonus, cutoff evaluation,
potential shaping, leaf evaluation) now uses `self._root_player` consistently.
Backpropagation of a single root-relative value is correct.

### 3. Pass Handling Fixed
Previously, the rollout terminated immediately when any player had no legal
moves (`if not legal_moves: break`). In Blokus, a player with no moves passes
and play continues to the next player.

**Fix (rollout):** Track `consecutive_passes` counter. When a player has no
moves, pass to next player and increment counter. End rollout only when all 4
players pass consecutively. Reset counter after each successful move.

**Fix (tree):** `_initialize_untried_moves()` now detects pass nodes (player
has no moves but others do) and stores a `[None]` sentinel. `expand()` handles
pass nodes by creating a child with the same board and next player.

### 4. Tie Handling Fixed
Previously, `sim_board.is_game_over()` was always `False` during rollout
because the flag is only set by the game engine. Win and tie bonuses were dead
code.

**Fix:** After rollout ends naturally (all players passed), compute actual
scores for all players and apply: +100 for outright win, +10 for shared win
(tie), no bonus for loss or truncated rollouts.

### 5. Arena Validity Tracking Added
Each game record now includes:
- `is_valid_result`: `true` for all post-audit runs
- `invalid_reason`: empty string for valid runs
- `audit_version`: `"v1_2026-03-28"`

Historical results without `audit_version` are pre-audit.

### 6. Invariant Tests Added
16 new tests in `tests/test_audit_invariants.py` covering:
- Reward perspective correctness
- Pass handling in rollout and tree
- Tie detection in GameResult
- Arena validity fields and FastMCTS rejection
- Game-over detection

### 7. Metric Naming Clarified
- `stats["branching_factor"]` renamed to `stats["root_legal_moves"]` (it
  measured legal moves at root, not average tree branching)
- Scoring docstring clarified to note corner/center bonuses are custom
  additions beyond standard Blokus rules

## What Was Removed
- `agents/fast_mcts_agent.py` -> `archive/agents/fast_mcts_agent.py`
- `agents/gameplay_fast_mcts.py` -> `archive/agents/gameplay_fast_mcts.py`
- `tests/test_fast_mcts_think.py` -> `archive/tests/test_fast_mcts_think.py`
- `tests/test_mcts_diagnostics.py` -> `archive/tests/test_mcts_diagnostics.py`
- FastMCTS adapter classes and helper functions from arena_runner.py

## Historical Results Considered Invalid

All arena results produced **before** audit version `v1_2026-03-28` should be
treated with caution due to:
1. Mixed reward perspective in multiplayer
2. Incorrect pass handling (premature rollout termination)
3. Dead win/tie bonus code in rollouts
4. Any results involving FastMCTS agents

Results with `audit_version: "v1_2026-03-28"` or later are produced with
corrected MCTS logic.

## Trusted Configuration for Future Experiments

Use `"type": "mcts"` agents with default parameters. Example:

```json
{
  "agents": [
    {"name": "mcts_100ms", "type": "mcts", "thinking_time_ms": 100},
    {"name": "mcts_200ms", "type": "mcts", "thinking_time_ms": 200},
    {"name": "mcts_500ms", "type": "mcts", "thinking_time_ms": 500},
    {"name": "heuristic",  "type": "heuristic"}
  ],
  "num_games": 100,
  "seed": 20260328,
  "seat_policy": "round_robin"
}
```

Do **not** use `fast_mcts`, `gameplay_fast_mcts`, or `gameplay_mcts` agent
types. The arena runner will reject them with an error.
