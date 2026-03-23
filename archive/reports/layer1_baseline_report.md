# Layer 1: Baseline Characterization Report

> **Status**: DIAGNOSTIC — data collected with the current agent, no algorithm changes.
>
> This report documents the current MCTS agent's behaviour across 500+ self-play games and identifies the highest-impact areas for subsequent optimisation layers.

**Data source:** `baseline_runs/layer1_20260322_154726` (571 self-play, 119 heuristic games)

## 1.1 — Branching Factor Curve

Measured across **81** distinct turn indices.

- **Peak branching factor**: 534 legal moves at turn 17
- **Implied visits/child** at 2000 iterations: **3.7**
- This is where search budget is most strained.

![Branching Factor Curve](baseline_runs/layer1_20260322_154726/plots/branching_factor_curve.png)

## 1.2 — Iteration Efficiency

- **Overall mean utilization**: 11.0%
- Turns below 50% (search spreading thin): **78** / 80
- Turns above 90% (over-exploiting): **0** / 80

![Utilization Curve](baseline_runs/layer1_20260322_154726/plots/utilization_curve.png)

## 1.3 — Simulation Quality Audit

| Metric | Heuristic-only | Full MCTS | Delta |
|--------|---------------|-----------|-------|
| Avg Score | 83.4 | 75.4 | -8.0 |
| Games | 119 | 571 | — |

**Heuristic rank distribution**: Rank 1: 129 | Rank 2: 124 | Rank 3: 119 | Rank 4: 104

The tree search adds **-8.0 points** of value over raw rollout policy decisions.

## 1.4 — Q-Value Convergence Check

Tested across **47** sampled states.

### Move Identity Stability

| Budget Transition | States | Moves Changed | Change Rate |
|-------------------|--------|---------------|-------------|
| 1K → 5K | 47 | 28 | 59.6% |
| 5K → 10K | 47 | 32 | 68.1% |
| 10K → 50K | 47 | 41 | 87.2% |
| 50K → 100K | 47 | 27 | 57.4% |

### Q-Value Statistics by Budget

| Budget | Mean Q | Std Q | Mean Regret Gap | States |
|--------|--------|-------|-----------------|--------|
| 1K | 1.8751 | 0.5300 | 0.0041 | 45 |
| 5K | 1.8721 | 0.5303 | 0.0029 | 45 |
| 10K | 1.8712 | 0.5301 | 0.0011 | 45 |
| 50K | 1.8701 | 0.5301 | 0.0006 | 45 |
| 100K | 1.8693 | 0.5293 | 0.0004 | 45 |

![Q-Value Convergence Heatmap](baseline_runs/layer1_20260322_154726/plots/qvalue_convergence_heatmap.png)

![Q-Value Convergence Per State](baseline_runs/layer1_20260322_154726/plots/qvalue_convergence_per_state.png)

## 1.5 — Seat-Position Bias

| Seat | Mean Score | Std | 95% CI | N |
|------|-----------|-----|--------|---|
| P1 | 78.0 | 10.2 | [77.2, 78.8] | 571 |
| P2 | 77.4 | 10.8 | [76.5, 78.3] | 571 |
| P3 | 73.4 | 10.5 | [72.5, 74.2] | 571 |
| P4 | 72.7 | 11.1 | [71.8, 73.6] | 571 |

**ANOVA**: F=37.2439, p=0.000000 (scipy.stats.f_oneway)

> **Significant seat-position bias detected** (p < 0.05). Seat assignments should be rotated in all future comparisons.

### Pairwise KS Tests

| Pair | KS Stat | p-value |
|------|---------|---------|
| P1 vs P2 | 0.0578 | 0.296215 |
| P1 vs P3 | 0.1926 | 0.000000 |
| P1 vs P4 | 0.2382 | 0.000000 |
| P2 vs P3 | 0.1839 | 0.000000 |
| P2 vs P4 | 0.2119 | 0.000000 |
| P3 vs P4 | 0.0701 | 0.121358 |

![Seat Bias](baseline_runs/layer1_20260322_154726/plots/seat_bias.png)

## Key Decisions This Data Informs

| Measurement | Decision It Informs | Layer Affected |
|-------------|--------------------|-----------------|
| Branching factor peak location | Where to focus action reduction | Layer 3 |
| Branching factor peak magnitude | How aggressive to prune | Layer 3 |
| Utilization ratio shape | Action reduction vs exploration tuning priority | Layer 3, 9 |
| Simulation quality gap | Whether to replace rollouts with evaluation | Layer 4 |
| Q-value convergence budget | Whether parallelisation helps | Layer 8 |
| Convergence-slow turn numbers | Where to focus action reduction | Layer 3 |
| Seat-position bias magnitude | Tournament design correction | Layer 0.2 |

## Checklist: Layer 1 Complete When...

- [x] 500+ self-play games completed with full logging
- [x] Branching factor curve plotted and peak identified
- [x] Iteration efficiency curve plotted with threshold annotations
- [x] Simulation quality audit completed (119 rollout-only games)
- [ ] Q-value convergence check completed across 47 states
- [x] Seat-position bias quantified with significance testing
- [x] All results documented in baseline report
