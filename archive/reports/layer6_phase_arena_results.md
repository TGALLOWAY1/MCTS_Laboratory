# Layer 6.2: Phase-Dependent Evaluation Arena Results

> **Status**: COMPLETE — Phase-dependent and RAVE variants decisively underperformed.

**Date:** 2026-03-25
**Branch:** `claude/update-arena-todo-Uo3SO`

## Tournament Setup

**Config:** `scripts/arena_config_layer6_phase.json`

| Agent | Eval Strategy | RAVE | Notes |
|-------|--------------|------|-------|
| `mcts_calibrated_d0` | Calibrated single weights | No | L6 regression-derived weights |
| `mcts_default_eval_d0` | Default hand-tuned weights | No | Baseline (includes `center_proximity: 0.25`) |
| `mcts_phase_eval_d0` | Phase-dependent weights | No | Early/mid/late weight vectors from per-phase regression |
| `mcts_phase_eval_rave_d0` | Phase-dependent weights | Yes (k=1000) | Phase weights + RAVE blending |

All agents: `rollout_cutoff_depth: 0` (pure static eval), `iterations: 1000`, `exploration_constant: 1.414`, deterministic time budget.

**Games:** 25, round-robin seating, seed `20260325`.

## Results

### Win Rates

| Agent | Win Rate | Wins | Mean Score | Median |
|-------|----------|------|------------|--------|
| `mcts_default_eval_d0` | **48.0%** | 12 | 95.7 | 94 |
| `mcts_calibrated_d0` | **52.0%** | 13 | 90.9 | 95 |
| `mcts_phase_eval_d0` | **0.0%** | 0 | 69.0 | 66 |
| `mcts_phase_eval_rave_d0` | **0.0%** | 0 | 60.8 | 61 |

### TrueSkill Rankings

| Rank | Agent | mu | sigma | Conservative |
|------|-------|----|-------|-------------|
| 1 | `mcts_default_eval_d0` | 45.97 | 7.72 | 22.80 |
| 2 | `mcts_calibrated_d0` | 41.19 | 7.68 | 18.16 |
| 3 | `mcts_phase_eval_d0` | 14.36 | 7.43 | -7.93 |
| 4 | `mcts_phase_eval_rave_d0` | -0.16 | 7.46 | -22.54 |

### Pairwise Head-to-Head

| Matchup | Score |
|---------|-------|
| calibrated vs default | 13-12 (near even) |
| calibrated vs phase | 19-6 |
| calibrated vs phase+RAVE | **25-0** |
| default vs phase | **25-0** |
| default vs phase+RAVE | **25-0** |
| phase vs phase+RAVE | 18-7 |

## Analysis: Why Phase-Dependent Eval Failed

### 1. Inverted Early-Game Weight Signs

The early-phase weights from per-phase regression have `squares_placed: -0.176` and `remaining_piece_area: +0.176`. This tells the agent that placing fewer squares and retaining more piece area is *desirable* in the opening — the opposite of correct Blokus strategy, where early expansion is critical.

The per-phase regression captured a **descriptive correlation** (players who have placed fewer squares early still have high remaining potential), not a **causal strategy** (placing fewer squares leads to winning). The calibrated single-weight agent has the correct sign (`squares_placed: +0.03`, `remaining_piece_area: -0.03`).

**Phase R² values confirm the problem:** Early R² = 0.006, meaning the early-phase regression explains virtually none of the outcome variance. The resulting weights are essentially noise.

### 2. Missing `center_proximity` Signal

The default evaluation assigns `center_proximity: 0.25` — one of its largest weights. Random Forest feature importance analysis (Layer 6.1) confirmed `center_proximity` as the **#1 most important feature** at 36.1% MDI importance.

All three phase weight vectors set `center_proximity: 0.0`. By zeroing out the single most predictive feature, the phase-dependent agents lost a major positional signal that the default agent retains throughout the entire game.

### 3. Phase Transition Discontinuities

Hard occupancy thresholds (early < 0.25, mid < 0.55, late >= 0.55) cause the evaluation function to switch weight vectors abruptly. A position evaluated under early weights may produce a very different score than the same position evaluated under mid weights — yet MCTS backpropagation averages Q-values across the tree without regard to which weight vector was active.

This creates **noisy, inconsistent value estimates** in the search tree. Nodes near phase boundaries accumulate statistics from evaluations using different weight vectors, undermining the convergence guarantees that make MCTS work.

### 4. RAVE Amplifies Noisy Evaluations

RAVE (Rapid Action Value Estimation) blends move-value statistics from all simulations where a move appeared *anywhere* in the subtree, not just at the node where it was played. When the underlying evaluation is already noisy (due to phase discontinuities and inverted weights), RAVE **spreads unreliable value estimates across the entire tree**.

Additionally, the RAVE agent runs ~12% slower (2737ms vs 2425ms avg per move), yielding fewer effective iterations per decision. This explains why phase+RAVE (mean score 61) performed even worse than phase-only (mean score 69).

### 5. Overfitting to Low-Variance Regression

The per-phase regressions had extremely low R² values:
- Early R² = 0.006
- Mid R² = 0.080
- Late R² = 0.435

Early and mid-game weights are derived from models that explain <1% and <8% of outcome variance respectively. These are not meaningful predictive models — they are curve-fitting to noise. Only the late-game regression has enough signal to produce useful weights, but by then the damage from poor early/mid play is irreversible.

## Conclusions

1. **Phase-dependent evaluation is theoretically sound but practically harmful** in its current form. The Guerrero-Romero insight ("change heuristic type during the game") is valid, but requires either (a) much better per-phase models or (b) smooth blending rather than hard phase switches.

2. **The calibrated single-weight agent and default agent are statistically tied** (13-12 wins). The calibrated weights correct `largest_remaining_piece_size` sign and re-balance `opponent_avg_mobility`, but lose the `center_proximity` signal — these effects roughly cancel.

3. **RAVE provides no benefit and actively harms performance** when combined with a noisy evaluation function. RAVE may still be useful with a stable, high-quality evaluator, but should not be paired with phase-dependent weights.

4. **Next steps for evaluation refinement should focus on:**
   - Adding `center_proximity` to the calibrated weight vector (it's the #1 RF feature)
   - Exploring smooth phase blending (e.g., linear interpolation between weight vectors based on occupancy) instead of hard switches
   - TD learning (Layer 6.3) to learn evaluation corrections from search experience
   - Requiring minimum R² thresholds before deploying per-phase weights

## Raw Data

Full tournament output: `arena_runs/20260325_033805_9b3944b6/`
