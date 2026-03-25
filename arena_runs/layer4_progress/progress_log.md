# Layer 4 Arena Progress Log

## Config Calibration Notes

All L4 configs recalibrated from original design:
- Original configs used `iterations_per_ms=10.0` (1000 iter) for ALL agents
- Measured actual speeds: cutoff_0=91ms/move, cutoff_5=11s, cutoff_10=44s, cutoff_20=109s at 100 iter
- Recalibrated: cutoff_0 agents at 1000 iter (fast), deeper agents at 25 iter
- Minimax agents all use cutoff_0 + 1000 iter (fast pure-eval comparison)
- Dropped cutoff_20 (impractical at any iteration count)

## Intermediate Results (after ~5 games each)

### L4.2 Cutoff Depth Sweep (5/25 games)

| Agent | Wins | Notable |
|-------|------|---------|
| cutoff_5_25iter | 3 (incl ties) | Dominant — scored 94 in game 3 |
| cutoff_0_25iter | 2 (incl ties) | Competitive |
| cutoff_10_25iter | 1 | Won game 4 with 94 score |
| cutoff_0_1000iter | 0 | Surprising — 40× more iterations, zero wins |

**Key finding**: Depth_5 rollouts at 25 iterations outperform depth_0 at 1000 iterations. Rollout quality > iteration quantity.

### L4.3 Minimax Alpha Sweep (4/25 games)

| Game | Winner | Scores |
|------|--------|--------|
| 1 | alpha_0.1 | 73,71,68,65 |
| 2 | alpha_0.25 | 73,71,68,65 |
| 3 | alpha_0.5 | 73,71,68,65 |
| 4 | alpha_0.0 | 73,71,68,65 |

**Key finding**: Identical score distributions — seat position determines outcome, not alpha value. Minimax backup has NO effect with cutoff_depth=0 (pure static eval).

### L4.1 Two-Ply Rollout Policy (2/25 games)

| Agent | Wins | Scores |
|-------|------|--------|
| random_cutoff8_25iter | 1 | 76 in game 1 |
| two_ply_all_cutoff8_25iter | 1 | 76 in game 2 |
| heuristic_cutoff8_25iter | 0 | 73, 62 |
| two_ply_k10_cutoff8_25iter | 0 | 66, 73 |

Too early to draw conclusions.
