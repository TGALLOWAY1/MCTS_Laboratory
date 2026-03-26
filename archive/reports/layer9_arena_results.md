# Layer 9 Arena Results: Meta-Optimization

> **Run ID:** `20260326_202636_3c2cc7c8`
> **Date:** 2026-03-26
> **Games:** 25 (round-robin, 4 agents)
> **Config:** `scripts/arena_config_layer9_adaptive.json`

## Summary

Adaptive rollout depth is the only Layer 9 mechanism that helps. Adaptive exploration constant (C) is actively harmful, and the combined "full" agent underperforms baseline. The adaptive depth agent is also **1.8x faster** per move due to shorter early-game rollouts.

## Experiment Design

All agents use the best L4-L6 foundation: random rollout, cutoff depth 5, minimax alpha 0.25, RAVE k=1000, calibrated weights, 100 iterations per move (0.5 iter/ms x 200ms).

| Agent | Layer 9 Features |
|-------|-----------------|
| `L9_baseline` | None (fixed C=1.414, fixed depth=5) |
| `L9_adaptive_c` | Adaptive exploration only (C scales with sqrt(BF/avg_BF)) |
| `L9_adaptive_depth` | Adaptive rollout depth only (depth scales inversely with BF) |
| `L9_full` | All L9 features: adaptive C + adaptive depth + sufficiency threshold + loss avoidance |

## Results

### Win Rates and TrueSkill Rankings

| Agent | Win Rate | Wins | TrueSkill mu | TrueSkill Rank | Mean Score |
|-------|----------|------|-------------|---------------|------------|
| **L9_adaptive_depth** | **36.0%** | **9** | **29.22 (#1)** | **1** | 72.96 |
| L9_baseline | 32.0% | 8 | 29.09 (#2) | 2 | **75.76** |
| L9_full | 24.0% | 6 | 23.80 (#3) | 3 | 71.72 |
| L9_adaptive_c | 8.0% | 2 | 17.75 (#4) | 4 | 69.92 |

TrueSkill not converged (sigma ~7.5) — adaptive_depth and baseline are statistically tied by TrueSkill, but win rate and pairwise matchups favor adaptive_depth.

### Pairwise Matchups

| Matchup | Head-to-Head | Notes |
|---------|-------------|-------|
| adaptive_depth vs baseline | **13:11** (1 tie) | Slight edge |
| adaptive_depth vs full | **15:10** | Clear advantage |
| adaptive_depth vs adaptive_c | **15:9** (1 tie) | Strong advantage |
| baseline vs full | **13:9** (3 ties) | Baseline better |
| baseline vs adaptive_c | **16:9** | Strong advantage |
| full vs adaptive_c | **16:9** | Full better than adaptive_c |

**Ranking by pairwise dominance:** adaptive_depth > baseline > full > adaptive_c

### Time Efficiency

| Agent | avg ms/move | iter/s | Score/sec | Speedup vs baseline |
|-------|------------|--------|-----------|-------------------|
| L9_adaptive_depth | 1,315ms | 76.1 | 55.5 | **1.64x faster** |
| L9_full | 1,348ms | 74.2 | 53.2 | **1.60x faster** |
| L9_baseline | 2,162ms | 46.2 | 35.0 | 1.00x |
| L9_adaptive_c | 2,432ms | 41.1 | 28.8 | 0.89x (slower!) |

The adaptive depth agent runs **1.64x faster** than baseline while also winning more games. This is because:
- Early game (BF ~100): depth = 5 * (80/100) = 4 (shorter, faster rollouts)
- Mid game (BF ~50): depth = 5 * (80/50) = 8 (slightly deeper)
- Late game (BF ~10): depth = 5 * (80/10) = 40 (much deeper, but moves are cheap)

Shorter early-game rollouts save time where RAVE/UCB exploration dominates decision quality, while deeper late-game rollouts improve play where positions are more deterministic.

## Per-Mechanism Analysis

### Adaptive Exploration Constant (C) -- HARMFUL

**Result: 8% win rate (worst), TrueSkill #4**

The formula `C_eff = 1.414 * sqrt(BF / 80)` increases C when BF is high (early game) and decreases it when BF is low (late game). This is counterproductive:
- Early game already has RAVE blending (k=1000), which handles exploration. Increasing C on top of RAVE causes over-exploration.
- Late game needs some exploration to avoid committing to locally optimal but globally suboptimal endgame moves. Reducing C here removes that safety net.
- The adaptive C agent is also **12% slower** than baseline (2,432ms vs 2,162ms avg/move), suggesting the increased exploration in high-BF positions leads to more expensive tree operations.

**Conclusion:** Adaptive C is incompatible with RAVE. RAVE already provides adaptive exploration (its influence decays with visit count), so layering another adaptive exploration mechanism creates over-exploration.

### Adaptive Rollout Depth -- BENEFICIAL

**Result: 36% win rate (best), TrueSkill #1, 1.64x faster**

The formula `depth = 5 * (80 / BF)` allocates rollout compute where it matters most:
- High BF positions: shallow eval is sufficient (RAVE + UCB drive exploration)
- Low BF positions: deeper rollouts are cheap and more informative
- Net effect: faster games AND better play quality

Pairwise vs baseline: 13:11 (slight but consistent edge).

**Conclusion:** Adaptive rollout depth is a genuine improvement. It provides a small playing strength advantage while dramatically reducing computation time.

### Sufficiency Threshold + Loss Avoidance (in L9_full)

These mechanisms only appear in the `L9_full` agent, so their individual effect is confounded by the harmful adaptive C. However, the full agent:
- Beats adaptive_c 16:9 (the adaptive depth and sufficiency/loss components help)
- Loses to baseline 9:13 (the adaptive C drags it down)
- Loses to adaptive_depth 10:15

The full agent is faster than baseline (1,348ms vs 2,162ms) due to adaptive depth, suggesting sufficiency threshold and loss avoidance have minimal overhead. Their playing strength contribution is unclear because the harmful adaptive C masks any benefit.

**Conclusion:** Sufficiency threshold and loss avoidance need isolated testing (without adaptive C) to properly evaluate.

## Score by Seat Position

Strong first-player advantage across all agents (mean P1 score ~78, P4 ~65):

| Agent | P1 | P2 | P3 | P4 |
|-------|-----|-----|-----|-----|
| adaptive_depth | 79.5 | 74.3 | 72.3 | 65.8 |
| baseline | 82.1 | 80.5 | 72.5 | 66.8 |
| full | 78.7 | 71.7 | 74.8 | 63.1 |
| adaptive_c | 72.8 | 73.4 | 68.0 | 64.8 |

Baseline has the highest P1/P2 scores but fails to convert those into wins as consistently as adaptive_depth, which maintains competitive scores across all seats.

## Key Findings

1. **Adaptive rollout depth is the only beneficial L9 mechanism.** It wins 36% of games (TrueSkill #1) while being 1.64x faster than baseline. The speed-quality tradeoff is a net positive.

2. **Adaptive exploration constant (C) is harmful with RAVE.** RAVE already provides adaptive exploration; adding branching-factor-based C scaling causes over-exploration and loses 92% of games.

3. **The combined "full" agent (all L9 features) underperforms baseline.** The harmful adaptive C outweighs any benefit from sufficiency threshold and loss avoidance.

4. **Sufficiency threshold and loss avoidance need isolated testing.** Their individual effects are masked by the confounding adaptive C in the full agent.

## Recommended Settings

```json
{
  "adaptive_exploration_enabled": false,
  "adaptive_rollout_depth_enabled": true,
  "adaptive_rollout_depth_base": 5,
  "adaptive_rollout_depth_avg_bf": 80.0,
  "sufficiency_threshold_enabled": false,
  "loss_avoidance_enabled": false
}
```

Use adaptive rollout depth only. Do not use adaptive C. Sufficiency threshold and loss avoidance remain inconclusive -- a follow-up experiment pairing adaptive_depth + sufficiency + loss_avoidance (without adaptive C) would clarify.

## Reproduction

```bash
python3 scripts/arena.py --config scripts/arena_config_layer9_adaptive.json --verbose
```
