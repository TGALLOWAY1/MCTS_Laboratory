# Layer 4 Arena Progress Log

## Config Calibration Notes

All L4 configs recalibrated from original design:
- Original configs used `iterations_per_ms=10.0` (1000 iter) for ALL agents
- Measured actual speeds: cutoff_0=91ms/move, cutoff_5=11s, cutoff_10=44s, cutoff_20=109s at 100 iter
- Recalibrated: cutoff_0 agents at 1000 iter (fast), deeper agents at 25 iter
- Minimax agents all use cutoff_0 + 1000 iter (fast pure-eval comparison)
- Dropped cutoff_20 (impractical at any iteration count)

## Mid-Tournament Results

### L4.2 Cutoff Depth Sweep (14/25 games)

| Agent | Solo Wins | Tie Wins | Total | Win Rate |
|-------|-----------|----------|-------|----------|
| cutoff_5_25iter | 6 | 3 | 9 | 64% |
| cutoff_10_25iter | 4 | 0 | 4 | 29% |
| cutoff_0_25iter | 1 | 3 | 4 | 29% |
| cutoff_0_1000iter | 0 | 0 | 0 | 0% |

**Key finding**: Rollout quality > iteration quantity. cutoff_5 at 25 iter dominates; cutoff_0 at 1000 iter has ZERO wins despite 40× more tree-search iterations. A 5-move heuristic rollout per iteration provides more useful information than pure static evaluation with 40× more tree exploration.

**Note**: Results repeat on a 4-game cycle (round_robin × 4 seats). With deterministic time budget and seeded agents, MCTS behavior is reproducible. Games 1-4 ≈ games 5-8 ≈ games 9-12 (minor variation in some games). Effective unique games ≈ 4.

### L4.3 Minimax Alpha Sweep (13/25 games — essentially complete)

All alpha values produce **identical results**. Score distribution is always {73, 71, 68, 65} with winner determined solely by seat position. Games repeat on a perfect 4-game cycle.

**Key finding**: Minimax backup alpha has ZERO effect with cutoff_depth=0 (pure static eval). With no rollout stochasticity, the MCTS tree search is fully deterministic regardless of alpha. The backup strategy only matters when rollouts introduce variance.

**Implication**: To test minimax backup properly, need cutoff_depth ≥ 5 (with rollouts). The current config is conclusive but shows a methodological gap.

### L4.1 Two-Ply Rollout Policy (11/25 games)

| Agent | Wins | Mean Score | Notable |
|-------|------|-----------|---------|
| random_cutoff8_25iter | 4.5 | ~74 | Surprising leader — random rollouts beat heuristic |
| two_ply_all_cutoff8_25iter | 4 | ~76 | Strong, highest peak scores (86) |
| two_ply_k10_cutoff8_25iter | 1.5 | ~72 | K=10 filtering hurts vs full enumeration |
| heuristic_cutoff8_25iter | 1 | ~69 | Weakest — heuristic rollout policy is the worst |

**Key finding**: Heuristic rollout is the worst policy at cutoff_depth=8. Random and two-ply full enumeration are competitive leaders. The heuristic may introduce systematic biases that hurt evaluation quality.

**Top-K filtering hurts**: two_ply_k10 significantly underperforms two_ply_all, suggesting that limiting the move set to top-10 during two-ply evaluation loses important information.

## Emerging Conclusions

1. **Rollout depth matters**: Even 5 moves of rollout at 25 iterations beats 1000 iterations of pure static eval
2. **Heuristic rollout is the worst policy**: At equal depth and iterations, random and two-ply beat heuristic
3. **Minimax backup is irrelevant with static eval**: Needs rollout variance to have any effect
4. **Top-K filtering hurts two-ply**: Full move enumeration > K=10 filtering
