# Layer 3 Validation Report: Progressive Widening & Progressive History

**Run ID:** `20260325_201856_32cf0875`
**Date:** 2026-03-25
**Games:** 25 (round-robin seating, seed `20260323`)
**Config:** `scripts/arena_config_layer3.json`

## Executive Summary

Progressive widening (PW) is the strongest Layer 3 mechanism, winning 64% of games with a mean score of 92.4 (+16.4 over baseline). Progressive history (PH) provides zero measurable benefit. Combining PW+PH is worse than PW alone. PH should not be used.

## Agents Tested

All agents share the same base configuration (L4 best settings):
- `rollout_policy: "random"`, `rollout_cutoff_depth: 5`, `minimax_backup_alpha: 0.25`
- `thinking_time_ms: 100`, `iterations_per_ms: 0.25` (25 iterations/move)
- `exploration_constant: 1.414`

| Agent | L3 Mechanism | Parameters |
|-------|-------------|------------|
| `mcts_baseline` | None | — |
| `mcts_progressive_widening` | PW only | `pw_c=2.0, pw_alpha=0.5` |
| `mcts_progressive_history` | PH only | `progressive_history_weight=1.0` |
| `mcts_pw_plus_ph` | PW + PH | Both sets combined |

## Results

### Win Rates and TrueSkill Rankings

| Rank | Agent | Win Rate | Wins | Mean Score | Median | Std | TrueSkill mu | Conservative |
|------|-------|----------|------|------------|--------|-----|-------------|-------------|
| 1 | **progressive_widening** | **64.0%** | 16/25 | **92.4** | 94.0 | 6.0 | 47.51 | **24.25** |
| 2 | pw_plus_ph | 32.0% | 8/25 | 87.2 | 88.0 | 8.6 | 32.70 | 9.90 |
| 3 | baseline | 4.0% | 1/25 | 76.0 | 73.0 | 9.9 | 10.88 | -11.41 |
| 4 | progressive_history | 0.0% | 0/25 | 76.6 | 77.0 | 6.4 | 10.09 | -12.21 |

### Pairwise Matchups (row agent > column agent)

| | baseline | PH | PW | PW+PH |
|---|---------|-----|-----|-------|
| **baseline** | — | 10-14 | 3-22 | 3-21 |
| **PH** | 14-10 | — | 0-25 | 6-19 |
| **PW** | **22-3** | **25-0** | — | **17-8** |
| **PW+PH** | **21-3** | **19-6** | 8-17 | — |

### Score Distributions

| Agent | Min | P25 | Median | P75 | Max |
|-------|-----|-----|--------|-----|-----|
| progressive_widening | 79 | 89 | 94 | 96 | 103 |
| pw_plus_ph | 72 | 81 | 88 | 94 | 102 |
| progressive_history | 64 | 73 | 77 | 80 | 89 |
| baseline | 61 | 71 | 73 | 77 | 112 |

Note: Baseline's max of 112 is a single outlier (game 19); the P75 is only 77.

## Key Findings

### 1. Progressive Widening is the clear winner

PW alone produces the highest win rate (64%), the highest mean score (92.4), and the tightest score distribution (std=6.0). It dominates every other agent pairwise — most strikingly, it beats progressive history 25-0 across all 25 games.

The +16.4 mean score improvement over baseline is the largest single-mechanism gain observed in the MCTS Laboratory to date, comparable in magnitude to the L4 simulation strategy improvements.

### 2. Progressive History provides no benefit

PH's mean score (76.6) is statistically indistinguishable from baseline (76.0). Its 0% win rate over 25 games and near-identical TrueSkill rating (10.09 vs 10.88) confirm it adds no value at the current iteration budget of 25 iterations/move.

This is likely because progressive history needs many more visits to accumulate meaningful action statistics. At only 25 iterations, the history table remains too sparse to guide selection effectively.

### 3. Combining PW+PH hurts compared to PW alone

PW+PH wins 32% vs PW's 64%, and PW beats PW+PH 17-8 pairwise. The progressive history component introduces noise into the selection policy that counteracts the benefit of progressive widening.

This is an important anti-result: more mechanisms are not always better. PH's noisy action history estimates at low iteration counts actively degrade PW's selection quality.

### 4. Seat position matters

All agents show a seat 4 (last-mover) disadvantage:

| Agent | Seat 1 | Seat 2 | Seat 3 | Seat 4 |
|-------|--------|--------|--------|--------|
| PW | 95.3 | 92.1 | 96.7 | 85.5 |
| PW+PH | 92.2 | 90.2 | 89.8 | 78.3 |
| baseline | 72.4 | 73.8 | 87.3 | 70.8 |
| PH | 74.3 | 76.7 | 82.0 | 72.3 |

Seat 3 tends to score highest (possibly due to round-robin positioning effects). This is consistent across all agents and likely reflects a game-structural advantage rather than an agent property.

## Efficiency

| Agent | Avg ms/move | Sims/sec | Score/sec |
|-------|-------------|----------|-----------|
| progressive_widening | 553.5 | 45.2 | 166.9 |
| pw_plus_ph | 587.5 | 42.6 | 148.5 |
| progressive_history | 564.0 | 44.3 | 135.7 |
| baseline | 574.9 | 43.5 | 132.1 |

PW is not only the strongest but also slightly the fastest agent (553ms avg vs 587ms for PW+PH), meaning the widening mechanism may be reducing branching factor overhead.

## Recommendations

1. **Use progressive widening** (`pw_c=2.0, pw_alpha=0.5`) as a standard MCTS enhancement going forward.
2. **Do not use progressive history** at the current iteration budget. It may warrant re-evaluation at higher iteration counts (100+) where the history table can accumulate meaningful statistics.
3. **Do not combine PW+PH** — the combination is strictly worse than PW alone.
4. **Best known MCTS configuration** after L3+L4:
   ```json
   {
     "rollout_policy": "random",
     "rollout_cutoff_depth": 5,
     "minimax_backup_alpha": 0.25,
     "progressive_widening_enabled": true,
     "pw_c": 2.0,
     "pw_alpha": 0.5
   }
   ```

## Methodology Notes

- All agents use deterministic time budgets (`iterations_per_ms: 0.25` = 25 iterations per 100ms) for reproducibility.
- The L4 best settings (random rollout, cutoff depth 5, minimax alpha 0.25) were applied uniformly to isolate the L3 mechanisms.
- Games were run in batches (5, 10, 5, 5) with intermediate commits to enable progress tracking and resume capability.
- The `--resume` flag was added to `arena.py` during this validation to support incremental runs.
