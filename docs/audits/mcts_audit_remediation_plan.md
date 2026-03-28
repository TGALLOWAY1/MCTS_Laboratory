# MCTS Audit Remediation Plan

## Background

A systematic audit of the MCTS/Blokus codebase identified several correctness
and research-integrity issues. This plan documents the remediation steps.

## Issues Identified

1. **FastMCTS is not a valid tree search.** Nodes do not represent successor
   states; rollouts use heuristic scoring from root state. Results are misleading.
2. **Reward perspective is mixed.** Rollout reward is computed from the
   *node player's* perspective but backpropagated unchanged to all ancestors,
   corrupting root decision-making in multiplayer.
3. **Pass handling is incorrect.** Rollout terminates when *any* player has no
   legal moves instead of passing to the next player.
4. **Tie bonuses never apply.** `sim_board.is_game_over()` is always False
   during rollout because the flag is only set by the game engine, not during
   MCTS simulation. Win/tie bonuses are dead code.
5. **No arena result validity tracking.** No way to distinguish pre-fix results
   from post-fix results.

## Phases

### Phase 0 — Commit This Plan
File: `docs/audits/mcts_audit_remediation_plan.md`

### Phase 1 — Remove FastMCTS from Competitive Use
- Archive `agents/fast_mcts_agent.py` and `agents/gameplay_fast_mcts.py`
- Block FastMCTS agent types in arena runner with ValueError
- Remove adapter classes from `analytics/tournament/arena_runner.py`
- Move tests to archive
- Add deprecation warnings to browser_python copies

### Phase 2 — Fix Reward Perspective
- Change `_rollout()` to compute reward from `self._root_player` perspective
- Fix cutoff evaluation and potential shaping to use root player
- Backpropagation already propagates unchanged — correct once reward is root-relative
- Add regression tests

### Phase 3 — Fix Pass / No-Move Handling
- Replace `if not legal_moves: break` with pass-to-next-player logic
- Track consecutive passes; end rollout only when all players pass
- Handle pass nodes in tree expansion
- Add regression tests

### Phase 4 — Fix Tie Handling
- Compute game result at end of rollout (scores for all players)
- Apply win/tie bonuses based on actual scores, not `sim_board.is_game_over()`
- Add tests for tie scenarios

### Phase 5 — Arena Result Validity Tracking
- Add `is_valid_result`, `invalid_reason`, `audit_version` fields to game records
- Add `audit_version` to index.csv
- Update summary output

### Phase 6 — Invariant Tests
- Reward perspective: root Q-values are root-relative
- Pass handling: single pass doesn't end rollout
- Tie handling: GameResult handles ties correctly
- Arena validity: records include validity fields
- FastMCTS rejection: arena rejects fast_mcts type

### Phase 7 — Clean Up Misleading Metrics
- Clarify `branching_factor` naming where misleading
- Update scoring docstrings to note variant bonuses

### Final — Summary Document
File: `docs/audits/mcts_audit_remediation_summary.md`

## Files Affected

| File | Phases |
|------|--------|
| `mcts/mcts_agent.py` | 2, 3, 4, 7 |
| `agents/fast_mcts_agent.py` | 1 (archived) |
| `agents/gameplay_fast_mcts.py` | 1 (archived) |
| `agents/registry.py` | 1 |
| `analytics/tournament/arena_runner.py` | 1, 5, 7 |
| `analytics/tournament/arena_stats.py` | 5 |
| `engine/game.py` | 7 |
| `tests/test_audit_invariants.py` | 6 (new) |
| `tests/test_reward_perspective.py` | 2, 4 (new) |
| `tests/test_rollout_pass_handling.py` | 3 (new) |
| `tests/test_arena_validity.py` | 5 (new) |

## Verification

```bash
python -m pytest tests/ -v
python scripts/arena.py --config scripts/arena_config.json --num-games 4
```
