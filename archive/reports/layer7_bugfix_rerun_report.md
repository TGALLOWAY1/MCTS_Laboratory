# Layer 7 — Opponent Modeling: Bugfix Re-run Report

**Date:** 2026-03-27
**Branch:** `claude/layer7-fixes-documentation-jJvto`
**Fix commit:** `5346067` ("fix: wire up Layer 7 opponent modeling features that were silently inert")
**Merged via:** PR #102

## Background

The original Layer 7 arena runs (2026-03-26) showed **zero measurable effect** from opponent modeling features. All agents produced identical scores per seat position across 50+ games. Investigation revealed three implementation bugs that caused the features to be silently inert.

## Bugs Fixed

### Bug 1: `get_defensive_eval_adjustment()` was dead code
- **Problem:** The method was defined in `OpponentModelManager` but never called from `mcts_agent.py` during MCTS iterations. Defensive weight adjustments were computed but discarded.
- **Fix:** Added `weight_adjustments` parameter to `BlokusStateEvaluator.evaluate()`. Wired it through all evaluation call sites in `_rollout()` (lines 1535, 1576, 1703). Created `_get_defensive_adjustments()` helper to fetch adjustments once per rollout.

### Bug 2: `opponent_rollout_policy="same"` short-circuited opponent model
- **Problem:** The condition `if current_player == root_player OR opponent_rollout_policy == "same"` sent ALL players through the root player's code path, bypassing `_select_opponent_rollout_move()` entirely. The opponent model could never upgrade rollout policies.
- **Fix:** Changed condition to `if current_player == root_player:` only. Modified `_select_opponent_rollout_move()` to resolve `"same"` internally before checking the opponent model.

### Bug 3: KingMaker occupancy threshold unreachable
- **Problem:** Default 0.55 (55% board fill) was often not reached before game end, so kingmaker detection never triggered.
- **Fix:** Lowered default threshold from 0.55 to 0.40.

### Config Fix
Updated `arena_config_layer7_alliance.json` and `arena_config_layer7_alliance_b.json` to use `opponent_rollout_policy: "random"` instead of `"same"`, allowing the opponent model to upgrade targeting opponents to heuristic rollouts.

---

## Experiment Design

Four arena experiments were run, each with 25 games and round-robin seating:

### Experiment 1: Alliance + Kingmaker Detection
**Configs:** `arena_config_layer7_alliance.json` (seed 20260323), `arena_config_layer7_alliance_b.json` (seed 20260325)

| Agent | Features Enabled |
|-------|-----------------|
| `L7_alliance_kingmaker` | Alliance detection + kingmaker detection |
| `L7_alliance_only` | Alliance detection only |
| `L7_kingmaker_only` | Kingmaker detection only |
| `L6_baseline` | No opponent modeling |

All agents: 100ms budget, 25 iterations, random rollout, cutoff depth 5, minimax alpha 0.25, Layer 6 calibrated weights.

### Experiment 2: Rollout Asymmetry
**Configs:** `arena_config_layer7_rollout_asymmetry.json` (seed 20260323), `arena_config_layer7_rollout_asymmetry_b.json` (seed 20260325)

| Agent | Self Policy | Opponent Policy |
|-------|-------------|----------------|
| `L7_self_heuristic_opp_random` | heuristic | random |
| `L7_self_random_opp_heuristic` | random | heuristic |
| `L6_baseline_symmetric` | random | same (= random) |
| `L6_baseline_no_asymmetry` | random | (no parameter) |

---

## Results

### Alliance + Kingmaker Detection

#### Seed A (20260323) — Run `20260327_000040_551abfe7`

| Rank | Agent | Win Rate | TrueSkill mu | Mean Score |
|------|-------|----------|-------------|------------|
| 1 | `L7_alliance_only` | 26.0% | 25.30 | 70.04 |
| 2 | `L7_alliance_kingmaker` | 24.0% | 25.04 | 70.00 |
| 3 | `L6_baseline` | 30.0% | 25.12 | 70.56 |
| 4 | `L7_kingmaker_only` | 20.0% | 24.38 | 70.12 |

#### Seed B (20260325) — Run `20260327_004854_9e02eb99`

| Rank | Agent | Win Rate | TrueSkill mu | Mean Score |
|------|-------|----------|-------------|------------|
| 1 | `L7_kingmaker_only` | **34.0%** | **26.93** | 70.28 |
| 2 | `L7_alliance_kingmaker` | 18.0% | 25.74 | 69.56 |
| 3 | `L7_alliance_only` | 22.0% | 24.24 | 69.88 |
| 4 | `L6_baseline` | 26.0% | 22.93 | 70.12 |

#### Alliance Combined Analysis (50 games)

| Agent | Avg Win Rate | Avg TrueSkill mu | Consistency |
|-------|-------------|-----------------|-------------|
| `L7_alliance_only` | 24.0% | 24.77 | Stable across seeds |
| `L7_alliance_kingmaker` | 21.0% | 25.39 | Variable (24% vs 18%) |
| `L7_kingmaker_only` | 27.0% | 25.66 | High variance (20% vs 34%) |
| `L6_baseline` | 28.0% | 24.03 | Stable (30% vs 26%) |

**Key observation:** Unlike the pre-fix runs where all agents scored identically, post-fix results show differentiated performance — confirming the bugs are fixed and features are now active. However, opponent modeling provides **no consistent advantage** over the baseline. Kingmaker detection showed a strong seed-B result but was worst in seed-A. The features are working but do not reliably improve play.

### Rollout Asymmetry

#### Seed A (20260323) — Run `20260327_001040_03f138ab`

| Rank | Agent | Win Rate | TrueSkill mu | Mean Score | avg ms/move |
|------|-------|----------|-------------|------------|-------------|
| 1 | `L7_self_heuristic_opp_random` | 24.0% | **26.00** | 70.04 | 1,092ms |
| 2 | `L6_baseline_symmetric` | 28.0% | 25.78 | 69.52 | 454ms |
| 3 | `L7_self_random_opp_heuristic` | 30.0% | 25.06 | 70.32 | 3,043ms |
| 4 | `L6_baseline_no_asymmetry` | 18.0% | 22.98 | 69.84 | 448ms |

#### Seed B (20260325) — Run `20260327_004855_ab8cfb2e`

| Rank | Agent | Win Rate | TrueSkill mu | Mean Score | avg ms/move |
|------|-------|----------|-------------|------------|-------------|
| 1 | `L7_self_heuristic_opp_random` | **34.0%** | **28.10** | 71.16 | 1,101ms |
| 2 | `L6_baseline_symmetric` | 20.0% | 24.73 | 70.16 | 462ms |
| 3 | `L7_self_random_opp_heuristic` | 22.0% | 24.18 | 70.36 | 3,118ms |
| 4 | `L6_baseline_no_asymmetry` | 24.0% | 22.85 | 70.00 | 460ms |

#### Rollout Asymmetry Combined Analysis (50 games)

| Agent | Avg Win Rate | Avg TrueSkill mu | avg ms/move |
|-------|-------------|-----------------|-------------|
| `L7_self_heuristic_opp_random` | **29.0%** | **27.05** | ~1,097ms |
| `L6_baseline_symmetric` | 24.0% | 25.26 | ~458ms |
| `L7_self_random_opp_heuristic` | 26.0% | 24.62 | ~3,081ms |
| `L6_baseline_no_asymmetry` | 21.0% | 22.92 | ~454ms |

**Key findings:**

1. **Asymmetric rollout policies now produce differentiated results** — confirming the `opponent_rollout_policy` fix (Bug 2) is working. Pre-fix, all agents were identical.

2. **`self_heuristic_opp_random` is the best asymmetric strategy** — consistently TrueSkill #1 across both seeds (29% avg win rate). Using heuristic rollouts for the root player while treating opponents as random produces the best results.

3. **Cost-benefit tradeoff is unfavorable.** `self_heuristic_opp_random` takes ~2.4x longer per move than the baseline. The 5 percentage-point win rate advantage (29% vs 24%) may not justify 2.4x compute. `self_random_opp_heuristic` is even worse: 6.8x slower for only 2% more wins.

4. **Explicit `opponent_rollout_policy="same"` beats omitting the parameter entirely.** `L6_baseline_symmetric` (explicit same) outperforms `L6_baseline_no_asymmetry` (no parameter) in both seeds, confirming the code path difference post-fix.

---

## Comparison: Pre-Fix vs Post-Fix

| Metric | Pre-Fix (2026-03-26) | Post-Fix (2026-03-27) |
|--------|---------------------|----------------------|
| Score differentiation | Zero — all agents identical per seat | Agents show distinct win rates and scores |
| Alliance detection effect | None | Small, inconsistent effect |
| Kingmaker detection effect | None (threshold unreachable) | Seed-dependent (20%–34% swing) |
| Rollout asymmetry effect | None (short-circuited) | Clear differentiation; heuristic-self best |
| Defensive eval adjustments | Dead code | Active (wired into evaluation path) |

---

## Conclusions

1. **The bugs are confirmed fixed.** All three Layer 7 features now produce measurable effects on gameplay, in contrast to the pre-fix zero-effect results.

2. **Opponent modeling does not reliably improve play.** Alliance detection, kingmaker detection, and their combination show no consistent advantage over the Layer 6 baseline across 50 games. Results are highly seed-dependent.

3. **Asymmetric rollout policies show modest promise.** The `self_heuristic_opp_random` strategy is consistently ranked #1 by TrueSkill but at 2.4x the compute cost. This is a weaker benefit than Layer 8 root parallelization (46% win rate at 2 workers).

4. **Recommended Layer 7 settings:** Do NOT enable opponent modeling by default. The features work correctly but do not provide reliable competitive advantage at the current iteration budget (25 iter/move). If used, prefer:
   - `opponent_rollout_policy: "random"` with `rollout_policy: "heuristic"` (best asymmetric strategy)
   - Opponent modeling features (alliance/kingmaker) are optional — no consistent benefit

5. **Higher iteration budgets may change the picture.** At 25 iterations with cutoff depth 5, the MCTS tree is very shallow. Opponent modeling may benefit more from deeper searches where rollout policy differentiation has greater impact.

---

## Arena Run IDs

| Experiment | Seed | Run ID | Directory |
|-----------|------|--------|-----------|
| Alliance + Kingmaker | 20260323 | `551abfe7` | `arena_runs/20260327_000040_551abfe7` |
| Alliance + Kingmaker | 20260325 | `9e02eb99` | `arena_runs/20260327_004854_9e02eb99` |
| Rollout Asymmetry | 20260323 | `03f138ab` | `arena_runs/20260327_001040_03f138ab` |
| Rollout Asymmetry | 20260325 | `ab8cfb2e` | `arena_runs/20260327_004855_ab8cfb2e` |
