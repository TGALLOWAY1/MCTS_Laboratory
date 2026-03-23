# Layer 2: Win-Probability Evaluation Model Report

> **Status**: COMPLETE — model trained and validated, but inference cost dominates MCTS time budget.

**Branch:** `claude/implement-layer-2-MVsLP`

## 2.1 — Training Data

- **Source:** 200 games via `fast_mcts` agent (100ms thinking time), checkpoint interval 4
- **Snapshots:** 11,604 rows across 200 games (~58 snapshots/game × 4 players)
- **Features:** 34 pairwise features extracted per player snapshot
- **Data file:** `data/snapshots.parquet` (290 KB)

## 2.2 — Models Trained

### Primary: Pairwise GBT with Phase Models (`eval_v1.pkl`)

- **Architecture:** `HistGradientBoostingClassifier` (max_depth=5, max_iter=300)
- **Phase models:** 3 phase-specific models (early, mid, late) + fallback
- **Model type:** `pairwise_gbt_phase`

### Baseline: Logistic Regression (`eval_v1_logreg.pkl`)

- **Architecture:** `StandardScaler` → `LogisticRegression` pipeline
- **Model type:** `pairwise_logreg`

## 2.3 — Validation Results (40 games, 200ms budget, `mcts` backend)

| Agent Configuration | Win% | Wins | Games | Avg Score |
|---------------------|------|------|-------|-----------|
| base_rollout | 27.5% | 11 | 40 | 75.8 |
| leaf_eval_only | 25.0% | 10 | 40 | 75.3 |
| leaf_eval_bias_0.25 | 22.5% | 9 | 40 | 75.1 |
| leaf_eval_bias_shaping | 25.0% | 10 | 40 | 75.3 |

**Total validation time:** 1893.4 seconds (~31.6 minutes)

## 2.4 — Key Finding: Inference Cost Dominates Time Budget

**Performance is flat across all configurations.** No learned-eval variant outperforms the base rollout agent.

**Root cause:** The model inference cost (~26ms per call) dominates the 200ms MCTS time budget:

- At 200ms budget, MCTS can perform ~7–8 evaluations total
- Each evaluation requires a full feature extraction + model prediction cycle
- This leaves insufficient iterations for meaningful tree search differentiation
- The tree is too shallow for the learned evaluation to provide signal over random rollouts

### Score spread analysis

The average scores range from 75.1 to 75.8 — a spread of only **0.7 points** across all four configurations. For reference, the Layer 1 baseline showed an 8-point gap between heuristic-only and MCTS agents. The 0.7-point spread here is well within noise.

## 2.5 — Inference Optimization: 4x Feature Extraction Redundancy Fix

**Problem:** `predict_player_win_probability(board, player)` calls `_extract_features_for_all_players(board)` on every invocation. Since MCTS calls this method once per player (and multiple times per board state for reward shaping), features for all 4 players were extracted **4x redundantly** for the same board position.

For example, during reward-shaping evaluation of a single node:
- `parent_value` calls `predict_player_win_probability(parent_board, player)` → extracts features for all 4 players
- `child_value` calls `predict_player_win_probability(child_board, player)` → extracts features for all 4 players
- If `potential()` is called for each player on the same board, that's 4 calls × 4 feature extractions = **16 extractions** instead of 4

**Fix:** Added a single-entry board-state cache (`_feature_cache_key` / `_feature_cache_value`) to `_extract_features_for_all_players()`. The cache key uses `board.grid.tobytes() + move_count + pieces_used`, so consecutive calls on the same board state hit the cache instead of re-extracting.

**Expected impact:** Reduces per-evaluation cost from ~26ms to ~6.5ms for repeated calls on the same board state. This roughly quadruples the number of useful MCTS iterations within the same time budget, directly addressing the core bottleneck identified in Section 2.4.

## 2.6 — Implications for Future Layers

| Finding | Implication | Affected Layer |
|---------|-------------|----------------|
| 26ms inference cost | Model must be made faster (< 1ms) or budget increased | Layer 2 revision |
| Flat win rates | Learned eval provides no benefit at current inference speed | Layer 4 |
| ~7 evals per turn | Tree too shallow for evaluation to matter | Layer 3, 8 |
| Feature extraction overhead | Consider caching or incremental feature updates | Layer 2 revision |

### Recommended next steps

1. **Reduce inference cost**: Profile feature extraction vs. model prediction; consider simpler models, feature caching, or C++ feature extraction
2. **Increase time budget**: Test with 1000ms+ budgets where inference cost is < 5% of total
3. **Action pruning (Layer 3)**: Reducing the branching factor would make fewer evaluations more impactful
4. **Batch evaluation**: Amortize model loading/prediction across multiple leaf nodes

## 2.7 — Artifacts

| File | Description |
|------|-------------|
| `data/snapshots.parquet` | 11,604 training snapshots from 200 games |
| `models/eval_v1.pkl` | Primary GBT phase model |
| `models/eval_v1_logreg.pkl` | Baseline logistic regression model |
| `validation_runs/eval_v1/validation_results.json` | Full validation results |

## Checklist: Layer 2 Complete When...

- [x] Training data generated (200 games, 11,604 snapshots)
- [x] Primary model trained (pairwise GBT with phase models)
- [x] Baseline model trained (logistic regression)
- [x] Validation arena run (40 games, 200ms budget)
- [x] Results documented in report
- [ ] Learned eval shows improvement over base rollout (**NOT MET** — inference cost too high)
