# Layer 4 Arena — Final Results

## Config Calibration Notes

All L4 configs recalibrated from original design:
- Original configs used `iterations_per_ms=10.0` (1000 iter) for ALL agents
- Measured actual speeds: cutoff_0=91ms/move, cutoff_5=11s, cutoff_10=44s, cutoff_20=109s at 100 iter
- Recalibrated: cutoff_0 agents at 1000 iter (fast), deeper agents at 25 iter
- Minimax agents all use cutoff_0 + 1000 iter (fast pure-eval comparison)
- Dropped cutoff_20 (impractical at any iteration count)

## L4.2 Cutoff Depth Sweep (25 games) — run `20260325_164035_0a7ca009`

| Agent | Win Rate | Mean Score | TrueSkill mu |
|-------|----------|-----------|-------------|
| cutoff_5_25iter | **54%** | **75.2** | 29.43 |
| cutoff_10_25iter | 28% | 73.4 | 13.46 |
| cutoff_0_25iter | 18% | 70.8 | 29.72 |
| cutoff_0_1000iter | **0%** | 70.8 | 27.20 |

**Key finding**: Rollout quality > iteration quantity. cutoff_5 at 25 iter dominates. cutoff_0 at 1000 iter has ZERO wins despite 40× more tree-search iterations. A 5-move heuristic rollout per iteration provides more useful information than pure static evaluation with massive tree exploration.

Pairwise: cutoff_5 beats cutoff_10 18:7, cutoff_5 beats cutoff_0@1000iter 16:7.

## L4.3 Minimax Alpha Sweep (25 games) — run `20260325_164033_3b30eeb2`

| Agent | Win Rate | Mean Score |
|-------|----------|-----------|
| alpha_0.0 | 24% | 69.32 |
| alpha_0.1 | 28% | 69.40 |
| alpha_0.25 | 24% | 69.20 |
| alpha_0.5 | 24% | 69.08 |

**Key finding**: Minimax backup alpha has ZERO effect at cutoff_depth=0. All agents produce identical scores at every seat position (std=0.0). Score margins are constant 8.0±0.0. The MCTS tree search is fully deterministic with pure static evaluation — alpha only matters when rollouts provide variance.

## L4.1 Two-Ply Rollout Policy (25 games) — run `20260325_165028_feca38f3`

| Agent | Win Rate | Mean Score | TrueSkill mu | ms/move |
|-------|----------|-----------|-------------|---------|
| random_cutoff8 | **36%** | 73.4 | **27.16** | **604ms** |
| two_ply_all_cutoff8 | 34% | **74.9** | 26.67 | 6075ms |
| two_ply_k10_cutoff8 | 16% | 73.0 | 23.62 | 1816ms |
| heuristic_cutoff8 | **14%** | 71.6 | 22.24 | 5355ms |

**Key finding**: Heuristic rollout is the weakest policy (14% win rate). Random and two_ply_all are competitive leaders, but random is **10× faster** per move (604ms vs 6075ms). Top-K=10 filtering hurts two-ply performance (16% vs 34%).

Pairwise: random beats two_ply_all 15:10. two_ply_all beats k10 19:6.

## L4 Combined (25 games) — run `20260325_182815_f28a2209`

| Agent | Win Rate | Mean Score | TrueSkill mu | ms/move |
|-------|----------|-----------|-------------|---------|
| random_d5 + alpha=0.25 | **36%** | 70.9 | 26.89 | **441ms** |
| two_ply_all_d8 | **36%** | 72.8 | 16.98 | 6295ms |
| random_d5 | 24% | 72.2 | 24.63 | 433ms |
| baseline_d0 @1000iter | 4% | 70.9 | 31.22* | 3504ms |

*Baseline TrueSkill is high because it consistently places mid-table (std=1.47) but rarely wins outright.

**Key finding**: Minimax alpha DOES help with rollouts — random_d5+alpha0.25 beats vanilla random_d5 15:10 pairwise. Combined, random_d5+alpha0.25 is the best practical strategy: tied for highest win rate (36%) and 14× faster per move than two_ply_all.

---

## Layer 4 Conclusions

### Recommended Settings
- **Rollout cutoff depth**: 5 (massive improvement over depth 0)
- **Rollout policy**: `"random"` (fastest, competitive quality) or `"two_ply"` without K filtering (highest raw quality but 10× slower)
- **Minimax backup alpha**: 0.25 (helps when rollouts are enabled, no effect without)
- **Best overall**: random rollout + cutoff 5 + alpha 0.25

### Key Insights
1. **Rollout quality > iteration quantity**: 25 iterations with 5-move rollout beats 1000 iterations with pure static eval
2. **Heuristic rollout is harmful**: The default heuristic policy is the worst. Random is better, likely because it avoids systematic biases
3. **Top-K filtering hurts**: Restricting two-ply to K=10 loses important information
4. **Minimax backup needs variance**: Has zero effect with deterministic evaluation, but helps when rollouts provide stochastic signals
5. **Time efficiency matters**: random_d5 + alpha0.25 achieves the same win rate as two_ply_all_d8 at 14× lower compute cost
