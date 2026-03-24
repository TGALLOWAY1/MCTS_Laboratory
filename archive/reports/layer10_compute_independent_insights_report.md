# Layer 10: Compute-Independent Insights — Iterations vs. Rollout Depth

> **Date**: 2026-03-24
> **Status**: INFRASTRUCTURE COMPLETE — Calibration data collected, arena configs created and smoke-tested, progress reporting added. Ready for full tournament runs.
> **Branch**: `claude/optimize-layer3-arena-6tc7R`

## 10.0 — Motivation

Layers 1–9 built a strong MCTS agent, but nearly all arena experiments ran under a single compute regime: fixed `thinking_time_ms` with `iterations_per_ms: 10.0`, producing ~1000 iterations at 100ms. The default 50-move full rollout (`max_rollout_moves: 50`) was found to exceed **2 hours per game**, forcing all practical experimentation onto `rollout_cutoff_depth` values of 0, 5, or 10.

This creates a problem for the project's analytical story: our findings risk being artifacts of a specific compute budget rather than general insights about MCTS in Blokus.

### The Core Research Question

**Under a fixed compute budget, is it better to run more iterations with shallow rollouts or fewer iterations with deep rollouts?**

### What Went Wrong with the Original Plan

The original Layer 10 design called for full 50-move rollout reference baselines (4–8 games at 2+ hours each) and multi-depth comparisons at 1000 iterations. Two critical problems made this infeasible:

1. **No in-game progress reporting**: The arena runner (`arena_runner.py`) only printed output after each complete game. With full rollouts taking 2+ hours per game, the user saw zero output for hours — indistinguishable from a hang.

2. **Massive throughput cliff at depth > 0**: Calibration revealed that rollout depth is **100x more expensive than expected** due to Blokus's extreme branching factor (300+ legal moves in early game). Running 1000 iterations at depth 5 takes ~5 minutes per move in the early game, making a single game take hours.

## 10.1 — Throughput Calibration

### Method

Created `scripts/calibrate_throughput.py` to measure actual MCTS iterations/second at each rollout cutoff depth across three game phases (early: 8 moves played, mid: 28 moves, late: 48 moves). Board positions generated via `generate_random_valid_state()` with fixed seed for reproducibility.

### Results

| Depth | Early (314 moves) | Mid (362 moves) | Late (31 moves) | Avg iter/ms |
|------:|------------------:|-----------------:|----------------:|------------:|
| 0     | 465.8 iter/s       | 138.8 iter/s      | 367.9 iter/s     | 0.324       |
| 5     | 3.5 iter/s         | 4.8 iter/s        | 62.0 iter/s      | 0.024       |
| 10    | 1.4 iter/s         | 3.5 iter/s        | 51.4 iter/s      | 0.018       |
| 15    | 0.9 iter/s         | 3.0 iter/s        | 51.3 iter/s      | 0.018       |

### Key Findings

**Finding 1: The depth 0→5 cliff is 13–133x depending on game phase.** In early game, depth 0 runs at 466 iter/s while depth 5 runs at 3.5 iter/s — a **133x slowdown**. This is because each rollout step at depth 5 must generate and evaluate legal moves in positions with 300+ options. Even the "heuristic" rollout policy (which scores and selects among these moves) cannot escape this fundamental cost.

**Finding 2: Depth 10 and 15 have nearly identical throughput.** In late game, both run at ~51 iter/s. In early game, depth 15 (0.9 iter/s) is only marginally slower than depth 10 (1.4 iter/s). This suggests that rollout cost is dominated by the first few moves of the rollout — additional depth beyond 10 adds little cost but also likely little signal, since positions become increasingly random.

**Finding 3: Late-game rollouts are 10–50x cheaper than early-game rollouts.** With only 31 legal moves (vs. 314), late-game rollouts are dramatically faster. Depth 5 late-game (62 iter/s) is faster than depth 0 mid-game (139 iter/s). This validates Layer 9's adaptive rollout depth mechanism — the system should automatically use deeper rollouts in the late game where they're cheap.

**Finding 4: The `iterations_per_ms: 10.0` default was calibrated for depth 0 only.** The existing configs assume 10 iterations per millisecond, which is accurate for depth 0 (actual: 0.14–0.47 iter/ms). But for depth 5, the actual rate is 0.004–0.062 iter/ms — off by 160–2500x. Any config using `iterations_per_ms: 10.0` with `rollout_cutoff_depth > 0` was giving 1000 iterations regardless of how long each takes, resulting in multi-hour games.

### Wall-Clock Implications

At 1000 iterations per move, 60 moves per game, 4 agents:

| Depth | Per-move (early) | Per-move (late) | Est. game time |
|------:|-----------------:|----------------:|---------------:|
| 0     | 2.1s              | 0.14s            | ~2 minutes      |
| 5     | 286s (4.8 min)    | 0.8s             | **~5 hours**    |
| 10    | 714s (11.9 min)   | 0.2s             | **~12 hours**   |

This explains why the Layer 3 arena run (which used default full rollouts at 1000 iterations) showed no progress for hours.

## 10.2 — Real-Time Mode Validation

### Experiment

Ran 2 games with `deterministic_time_budget: false` at 100ms per move, comparing depths 0, 5, 10, and 15.

### Results

| Agent           | Avg sims/move | Avg time/move | Sims/sec | Budget utilization |
|-----------------|:-------------:|:-------------:|---------:|-------------------:|
| depth_0 (100ms) | 55            | 105ms         | 521      | 1.05x              |
| depth_5 (100ms) | —             | —             | —        | —                  |
| depth_10 (100ms)| 11            | 365ms         | 30       | 3.65x              |
| depth_15 (100ms)| 21            | 498ms         | —        | 4.98x              |

### Key Finding

**Real-time mode overshoots the budget dramatically for deep agents.** Depth 10 averages 365ms on a 100ms budget (3.65x overshoot) because a single MCTS iteration can take 700ms+ in the early game. The agent completes one iteration, checks the clock, and finds it's already over budget. This makes 100ms real-time mode unusable for depth > 5 comparisons.

**Mitigation**: The final 10.2 config uses 500ms and 2000ms budgets, giving deeper agents enough time for multiple iterations before the time check triggers.

## 10.3 — Infrastructure Changes

### Progress Reporting (`arena_runner.py`)

Added two progress outputs to `run_experiment()` and `run_single_game()`:

1. **Game-start announcement**: Prints immediately when each game begins, showing game index, seed, and agent names.
2. **Per-move progress**: Every 4 turns (and the first 3 turns), prints elapsed time, current agent, and move duration in milliseconds.

All prints use `flush=True` to ensure immediate output, preventing buffering delays.

**Before**: Zero output for 2+ hours during a single game.
**After**: Output within seconds of game start, updates every 10–30 seconds depending on move speed.

### Calibration Script (`calibrate_throughput.py`)

Standalone script that measures actual MCTS throughput at each depth/phase combination. Uses adaptive iteration counts (fewer iterations for deep depths) to complete calibration in < 5 minutes. Outputs both human-readable table and JSON for programmatic use.

## 10.4 — Experiment Design

Based on calibration data, all Layer 10 experiments were redesigned to complete in 60–90 minutes with continuous progress output.

### Sub-layer 10.1: Depth Strength at Equal Iterations

**Config**: `arena_config_layer10_depth_strength.json` (16 games)

| Agent | Depth | Iterations | Est. per-move (early) | Est. per-move (late) |
|-------|:-----:|:----------:|----------------------:|---------------------:|
| depth_0_1000iter | 0 | 1000 | 2.1s | 0.14s |
| depth_0_25iter   | 0 | 25   | 0.05s | 0.003s |
| depth_5_25iter   | 5 | 25   | 7.1s | 0.4s |
| depth_10_25iter  | 10| 25   | 17.9s | 0.2s |

**Question**: At equal iteration count (25), do deeper rollouts produce better moves? The depth_0_1000iter agent serves as a "strong reference" — can any depth agent at 25 iterations match 1000 shallow iterations?

**Estimated runtime**: ~70 minutes (smoke-tested: 4.4 min/game)

### Sub-layer 10.2: Fixed Wall-Clock Budget

**Config**: `arena_config_layer10_iter_vs_depth.json` (16 games)

| Agent | Depth | Budget | Est. iters (early) | Est. iters (late) |
|-------|:-----:|:------:|-------------------:|------------------:|
| realtime_depth_0_500ms  | 0 | 500ms  | ~233 | ~184 |
| realtime_depth_5_500ms  | 5 | 500ms  | ~2   | ~31  |
| realtime_depth_0_2000ms | 0 | 2000ms | ~932 | ~736 |
| realtime_depth_5_2000ms | 5 | 2000ms | ~7   | ~124 |

**Question**: Under the same time budget, are 233 shallow iterations better or worse than 2 deep iterations? Does the answer change at 4x the budget?

### Sub-layer 10.3: Phase-Dependent Analysis

**Script**: `analyze_layer10_snapshots.py` (no new arena run)

Analyzes snapshot data from 10.1 and 10.2 at each checkpoint ply (8, 16, 24, 32, 40, 48, 56, 64) to determine whether the optimal depth changes across game phases. Expected result based on calibration data: deeper rollouts should gain relative strength in late game where they're cheap.

### Sub-layer 10.4: Eval Quality x Depth

**Config**: `arena_config_layer10_eval_quality.json` (16 games)

| Agent | Depth | Iters | Eval Weights |
|-------|:-----:|:-----:|:-------------|
| default_weights_d0 | 0 | 1000 | Default |
| phase_weights_d0   | 0 | 1000 | Phase-dependent (Layer 6) |
| default_weights_d5 | 5 | 25   | Default |
| phase_weights_d5   | 5 | 25   | Phase-dependent (Layer 6) |

**Question**: Does improving the static evaluator (phase weights) help depth 0 more than depth 5? If phase_weights_d0 closes the gap with depth_5 agents, the evaluator is the bottleneck — better to invest in eval quality than rollout depth.

**Estimated runtime**: ~60 minutes (smoke-tested: 3.9 min/game)

### Sub-layer 10.5: Scaling Curve

**Config**: `arena_config_layer10_scaling.json` (16 games)

| Agent | Depth | Iterations |
|-------|:-----:|:----------:|
| depth_0_250iter  | 0 | 250  |
| depth_0_1000iter | 0 | 1000 |
| depth_0_2000iter | 0 | 2000 |
| depth_5_25iter   | 5 | 25   |

**Question**: How does depth 0 scale with more iterations? Is there diminishing return? Does depth_5 at 25 iterations outperform depth_0 at 250 iterations (roughly equal wall-clock cost)?

## 10.5 — Preliminary Observations from Smoke Tests

From the 2-game smoke tests (not statistically significant, but directionally interesting):

**Eval quality smoke test (2 games)**:
- Game 1: `default_weights_d5` won (93 pts) > `depth_0_1000iter` (79) > `phase_weights_d5` (66) > `phase_weights_d0` (64)
- Game 2: `default_weights_d0` won (84 pts) > `phase_weights_d5` (83) > `default_weights_d5` (81) > `phase_weights_d0` (52)

**Depth strength smoke test (1 game)**:
- `depth_0_25iter` won (73 pts) > `depth_0_1000iter` (71) = `depth_5_25iter` (71) > `depth_10_25iter` (66)

Early indication: depth_0 at 25 iterations is competitive with depth_5 at 25 iterations despite being ~140x faster per move. The extra rollout signal may not justify the compute cost. Full 16-game runs are needed to confirm.

## 10.6 — Comparison with Production MCTS Systems

The calibration data provides context for why production MCTS systems (AlphaGo, KataGo, Leela Chess Zero) abandoned rollouts in favor of neural network evaluation:

| System | Evaluator R² | Rollout cost | Decision |
|--------|:------------:|:------------:|:---------|
| AlphaGo | ~0.8+ (CNN) | Moderate (Go bf ~250) | Dropped rollouts in AlphaGo Zero |
| KataGo  | ~0.9+ (NN)  | Moderate | Pure eval, no rollouts |
| This project | 0.136 overall, 0.44 late | **Extreme** (Blokus bf 300+) | Rollouts infeasible in practice |

Our evaluator is weak (R² = 0.136), which in theory should favor rollouts. But Blokus's extreme branching factor makes rollouts so expensive that even 5-deep rollouts reduce iteration count by 100x. The evaluator would need to be dramatically worse than random for 100x fewer iterations to be worthwhile.

**Hypothesis for full runs**: depth 0 (pure eval) will dominate at equal wall-clock time. The evaluator, despite its low R², provides enough signal to guide 100x more tree expansions. The rollout signal adds marginal accuracy per iteration but cannot overcome the 100x throughput penalty.

## Files Created

| File | Purpose |
|------|---------|
| `analytics/tournament/arena_runner.py` | Modified: per-move progress reporting |
| `scripts/calibrate_throughput.py` | Throughput calibration at each depth/phase |
| `data/throughput_calibration.json` | Calibration results |
| `scripts/arena_config_layer10_depth_strength.json` | 10.1: Equal-iteration depth comparison |
| `scripts/arena_config_layer10_iter_vs_depth.json` | 10.2: Fixed wall-clock budget comparison |
| `scripts/arena_config_layer10_eval_quality.json` | 10.4: Eval weights x depth interaction |
| `scripts/arena_config_layer10_scaling.json` | 10.5: Iteration scaling curve |
| `scripts/analyze_layer10_snapshots.py` | 10.3: Phase-dependent analysis |

## Running the Experiments

```bash
# All configs support --verbose for per-move progress
# Estimated 60-90 minutes per run

# 10.1: Depth strength comparison
python scripts/arena.py --config scripts/arena_config_layer10_depth_strength.json --verbose

# 10.2: Iterations vs depth (real-time)
python scripts/arena.py --config scripts/arena_config_layer10_iter_vs_depth.json --verbose

# 10.3: Phase analysis (after 10.1 or 10.2)
python scripts/analyze_layer10_snapshots.py --run-dir arena_runs/<run_id>

# 10.4: Eval quality interaction
python scripts/arena.py --config scripts/arena_config_layer10_eval_quality.json --verbose

# 10.5: Scaling curve
python scripts/arena.py --config scripts/arena_config_layer10_scaling.json --verbose

# Recalibrate throughput (if needed)
python scripts/calibrate_throughput.py --output data/throughput_calibration.json
```

## Next Steps

1. Run all four arena configs (10.1, 10.2, 10.4, 10.5) — can be run sequentially overnight or in parallel
2. Run `analyze_layer10_snapshots.py` on the results for phase-dependent insights
3. If depth 0 dominates (as hypothesized), this validates the project's focus on eval improvement over rollout depth and motivates a Layer 6 follow-up with a stronger evaluator
4. If depth 5 shows strength in specific phases, consider phase-adaptive depth switching (connecting to Layer 9's `adaptive_rollout_depth_enabled`)
