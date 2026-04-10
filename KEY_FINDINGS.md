# Key Findings — MCTS Laboratory

A systematic, 9-layer optimization program for Monte Carlo Tree Search in 4-player Blokus. Over 700 self-play games and 13,000+ labeled game states were used to train and validate evaluation functions, rollout strategies, and search enhancements — each tested in reproducible arena tournaments.

---

## The Headline Result

**Rollout quality dominates iteration quantity.** An MCTS agent with calibrated evaluation weights and shallow rollouts (depth 5, 25 iterations) beats an agent using 1,000 iterations of pure static evaluation — winning 54% of games versus 0%. Getting the evaluation right matters far more than searching deeper.

---

## ML Pipeline

```
700 self-play games
    → 13,332 labeled game states (features + final score)
        → Linear regression (R² = 0.136, 7 features)
        → Random Forest (R² = 0.535, 34 features)
            → Calibrated weight vector
                → 76% arena win rate vs. hand-tuned baseline
```

### Feature Importance (Random Forest, 34 features)

| Rank | Feature | Importance |
|------|---------|-----------|
| 1 | `center_proximity` | 36.1% |
| 2 | `utility_frontier_plus_mobility` | 17.0% |
| 3 | `corner_differential` | 6.1% |
| 4 | `remaining_squares` | 5.9% |
| 5 | `opponent_adjacency` | 5.7% |

### Calibrated vs. Default Weights

The regression revealed three critical miscalibrations in the hand-tuned defaults:

| Feature | Default | Calibrated | Issue |
|---------|---------|-----------|-------|
| `largest_remaining_piece_size` | +0.10 | **-0.23** | Wrong sign — large remaining pieces are bad |
| `opponent_avg_mobility` | -0.10 | **-0.30** | 3x underweighted — opponent denial is critical |
| `squares_placed` | +0.30 | **+0.03** | 10x overweighted — raw score is a weak signal |

### What the ML Showed About Game Phases

Evaluation accuracy varies dramatically by phase:

| Phase | Board Occupancy | R² | Interpretation |
|-------|----------------|-----|---------------|
| Early | < 25% | 0.006 | Essentially random — positional features can't predict outcomes |
| Mid | 25–55% | 0.080 | Weak signal emerges |
| Late | ≥ 55% | 0.435 | Evaluation becomes meaningfully predictive |

Phase-dependent weight vectors were trained but **failed in practice** (0% win rate) due to inverted early-game signs and hard transition discontinuities. Global calibration proved more robust.

---

## Layer-by-Layer Results

### Layer 3 — Action Reduction
Progressive widening reduces the branching factor without losing move quality.
- **+64% win rate**, mean score 92.4 vs. 76.0 baseline

### Layer 4 — Simulation Strategy
The most impactful layer. Random rollouts with shallow cutoff depth beat every alternative.
- **Random rollout is 10x faster** than two-ply and **higher win rate** than heuristic
- **Cutoff depth 5** is the sweet spot (depth 10 has diminishing returns, depth 0 is too shallow)
- **Minimax backup (α=0.25)** improves pairwise record 15–10 when rollouts are present

### Layer 5 — RAVE Blending
RAVE (Rapid Action Value Estimation) with k=1000 provides a 4x convergence speedup.
- 50ms RAVE budget beats 200ms vanilla budget (pairwise 15–6)
- **44.7% win rate** vs. 14.7% for baseline in 4-way tournaments
- Progressive history hurts when combined with RAVE (redundant exploration)

### Layer 6 — Evaluation Refinement
ML-calibrated weights from regression on 13,332 game states.
- **76% win rate** for calibrated weights vs. 12% for defaults
- Phase-dependent weights: **0% win rate** — global calibration is more robust
- Key insight: `largest_remaining_piece_size` had the **wrong sign** in defaults

### Layer 7 — Opponent Modeling
Alliance detection, king-maker awareness, and asymmetric rollout policies.
- Features activate correctly after bugfix, but **no reliable competitive advantage**
- Asymmetric rollouts (heuristic self / random opponents): 29% win rate
- 2.4x slower than baseline — computational cost exceeds marginal benefit at low iteration budgets

### Layer 8 — Parallelization
Root-parallel multiprocessing is the clear winner over tree-parallel (GIL-limited).
- **Root 2-worker: 46% win rate**, TrueSkill #1
- **Root 4-worker: 3.1x throughput**, near-linear scaling
- Tree parallelization with virtual loss: **< 10% win rate** (GIL contention)

### Layer 9 — Meta-Optimization
Adaptive rollout depth (shallow in high-branching early game, deep in low-branching late game).
- **Adaptive depth: 36% win rate**, TrueSkill #1, 1.64x faster than baseline
- Adaptive exploration constant: **8% win rate** — harmful (double-exploration with RAVE)
- Combined "full" agent loses to baseline — less is more

---

## Best Configuration

The optimal agent combines findings from Layers 3–9:

```json
{
  "rollout_policy": "random",
  "rollout_cutoff_depth": 5,
  "minimax_backup_alpha": 0.25,
  "state_eval_weights": "calibrated (from regression on 13K states)",
  "rave_enabled": true,
  "rave_k": 1000,
  "num_workers": 2,
  "parallel_strategy": "root",
  "adaptive_rollout_depth_enabled": true
}
```

---

## What Worked vs. What Didn't

| Worked | Didn't Work | Why |
|--------|-------------|-----|
| Calibrated global weights (76% WR) | Phase-dependent weights (0% WR) | Inverted signs at low R², hard transitions |
| Random rollout policy | Heuristic rollout policy (worst) | Heuristic is 10x slower, introduces bias |
| RAVE k=1000 (4x convergence) | Progressive history + RAVE | Redundant exploration signals |
| Root parallelization (46% WR) | Tree parallelization (<10% WR) | Python GIL kills thread-based search |
| Adaptive rollout depth (36% WR) | Adaptive exploration constant (8% WR) | Over-explores on top of RAVE |
| Minimax backup α=0.25 | Minimax without rollouts | Needs stochastic variance to filter |

---

## Methodology

- **Arena format:** 4-player round-robin tournaments, 25 games per experiment, deterministic seeding
- **Statistics:** Win rates, pairwise head-to-head records, TrueSkill ratings, score distributions
- **Data collection:** Checkpoint snapshots every 4 plies with 7 state-evaluator + 34 winprob features
- **Analysis:** Linear regression with bootstrap CIs, Random Forest with MDI, SHAP values, residual analysis by game phase
- **Reproducibility:** All configs, seeds, and run artifacts preserved in `arena_runs/` and `archive/`

---

## Future Directions

1. **TD-UCT Learning** — R² = 0.136 is well below the 0.5 threshold where temporal-difference bootstrapping would incrementally correct evaluation errors during search
2. **Expanded feature set** — `center_proximity` is the #1 RF feature (36.1% importance) but carries zero weight in the current evaluator; integrating top winprob features could close the R² gap
3. **Multi-seed validation** — Current tournaments use single seeds with 25 games; 100+ game multi-seed runs would strengthen statistical confidence
4. **Learned evaluator revisit** — Original GBT model had 26ms inference cost (killed the 200ms budget); distillation or quantization could make this viable

---

*Full experimental reports for each layer are in [`archive/reports/`](archive/reports/). Arena run artifacts (configs, game logs, snapshots) are in [`arena_runs/`](arena_runs/) and [`archive/arena_runs/`](archive/arena_runs/).*
