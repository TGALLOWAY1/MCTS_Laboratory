# MCTS Laboratory — TODO

Aggregated from Layers 0–9 PR reports. Last updated: 2026-03-25.

## Status Summary

| Layer | What | Arena Results? |
|-------|------|---------------|
| L0 | Measurement infrastructure (profiler, TrueSkill, tournament runner) | N/A (foundation) |
| L1 | Baseline characterization (571 self-play + 119 heuristic games) | **Invalid** — used `gameplay_fast_mcts` (no real rollout), not full MCTS. Needs re-run. |
| L2 | Learned evaluation model (GBT on 11,604 snapshots) | Done — zero benefit, inference cost (~26ms) eats 200ms budget |
| L3 | Action reduction (progressive widening + progressive history) | **Done** — PW wins 64%, mean score 92.4 vs 76 baseline. PH alone = no benefit. |
| L4 | Simulation strategy (two-ply, cutoff, minimax backups) | **Done** — cutoff_5 + random rollout + alpha=0.25 is best |
| L5 | RAVE & NST history heuristics | **Done** — RAVE k=1000 wins, PH hurts with RAVE, 4x convergence speedup |
| L6 | Evaluation function refinement (feature analysis, calibrated weights) | **Done** — calibrated weights help, phase weights hurt |
| L7 | Opponent modeling (blocking tracker, alliance, king-maker) | **Needs re-do** — zero effect due to implementation bugs, not technique failure |
| L8 | Parallelization (root + tree parallelization) | **None** |
| L9 | Meta-optimization (adaptive C, depth, sufficiency, loss avoidance) | **None** |
| L10 | Throughput calibration, progress reporting, calibrated arena configs | Done — infrastructure only, no competitive results yet |

## Timing Expectations

~~At default 100ms budget (1000 iterations/move), **one game takes ~20-30 minutes**. A 25-game tournament = **8-12 hours**.~~

**Updated (Layer 10 calibration):** Full rollouts (50+ moves) took **2+ hours per game** and have been replaced with `rollout_cutoff_depth` configs. With cutoff depths 0/5/10, games now take **~4-5 minutes each**, and a 25-game tournament completes in **~60-90 minutes**. Per-move verbose progress reporting was also added (every 4 turns) so long-running games show activity within seconds.

Use `--num-games 4` for quick smoke tests. Add `--verbose` for per-game progress output.

---

## Priority 1: Fix Known Evaluation Bugs — DONE

These affect all subsequent experiments — fix before running arena benchmarks.

- [x] **Fix `largest_remaining_piece_size` sign error and weight miscalibrations** (commit `55d397b`, 2026-03-22)
  Default weights in `mcts/state_evaluator.py` corrected per L6 regression analysis.

- [x] **Add `center_proximity` feature to `BlokusStateEvaluator`** (commit `55d397b`, 2026-03-22)
  Added to evaluator. L6 identified this as the #1 Random Forest feature (36.1% importance).

## Completed: Long-Running Game Fixes

- [x] **Replace full rollout configs with cutoff depth sweep** (commit `89245e3`, 2026-03-24)
  Full 50-move rollouts exceeded 2+ hrs/game. Both `arena_config_layer4_cutoff.json` and `arena_config_extended_rollout.json` now use `rollout_cutoff_depth` (0, 5, 10) for 3-20x speedup.

- [x] **Add per-move verbose progress reporting** (commit `b97b984`, 2026-03-24)
  Arena runner now reports every 4 turns with elapsed time, current agent, and move duration. Activated with `--verbose`.

- [x] **Layer 10 throughput calibration** (commit `b97b984`, `00add69`, 2026-03-24)
  Measured actual MCTS iter/sec: depth_0 = 0.32 iter/ms, depth_5 = 0.024, depth_10 = 0.018. All Layer 10 configs calibrated to ~4-5 min/game.

## Priority 2: Run Arena Experiments (Layers 3–9)

All configs exist in `scripts/` and are verified working.

### Layer 3 — Full validation ← **DONE**
- [x] L3 full validation — **DONE** (run `20260325_201856_32cf0875`)
  PW wins 64% (16/25), TrueSkill #1 (mu=47.5). PW+PH wins 32%, TrueSkill #2.
  PH alone = 0% wins, statistically tied with baseline.
  PW beats PH 25-0 pairwise. PW beats PW+PH 17-8.
  **Best L3 settings**: `progressive_widening_enabled: true`, `pw_c: 2.0`, `pw_alpha: 0.5`.
  Progressive history should NOT be used (adds overhead, no benefit).

### Layer 4 — Simulation strategy ← **DONE**
- [x] L4 cutoff depth sweep — **DONE** (run `20260325_164035_0a7ca009`)
  cutoff_5@25iter wins 54%, cutoff_0@1000iter wins 0%. Rollout quality > iteration quantity.
- [x] L4 minimax alpha sweep — **DONE** (run `20260325_164033_3b30eeb2`)
  ZERO effect at cutoff_depth=0. All alphas produce identical scores (std=0.0).
- [x] L4 two-ply rollout comparison — **DONE** (run `20260325_165028_feca38f3`)
  Random rollout wins (36%, TrueSkill #1) and is 10× faster than two_ply_all.
  Heuristic rollout is the WORST policy (14%). Top-K=10 filtering hurts.
- [x] L4 combined best settings — **DONE** (run `20260325_182815_f28a2209`)
  random_d5+alpha0.25 tied for best (36% wins) at 14× less compute than two_ply_all_d8.
  Minimax backup DOES help with rollouts (beats vanilla random 15:10 pairwise).
  **Best L4 settings**: `rollout_policy: "random"`, `rollout_cutoff_depth: 5`, `minimax_backup_alpha: 0.25`

### Layer 5 — RAVE & history heuristics ← **DONE**
- [x] L5 RAVE k sweep — **DONE** (run `20260325_210306_899d97d0`)
  k=1000 wins (36%, TrueSkill #1). k=100 too aggressive (12%), k=5000 too persistent (24%).
- [x] L5 head-to-head — **DONE** (run `20260325_210306_ed7ec9aa`)
  RAVE-only dominates (44.7% wins, TrueSkill mu=30.03). PH+RAVE hurts (26.7%).
  Progressive history alone helps pairwise but doesn't win games (14%).
- [x] L5 convergence validation — **DONE** (run `20260325_210306_4024cab3`)
  RAVE@50ms (12 iter) beats baseline@200ms (50 iter) 15:6 pairwise.
  4x effective speedup. More iterations without RAVE barely help.
  **Best L5 settings**: `rave_enabled: true`, `rave_k: 1000`, `progressive_history_enabled: false`

### Layer 6 — Calibrated weights vs defaults ← **DONE**
- [x] L6 calibrated vs default weights — **DONE** (run `20260325_021148_78fbdc50`)
  Calibrated eval d0 won 19/25 games (76%), TrueSkill rank #1 (mu=36.02).
  Baseline d0 ranked #2, default eval #3, calibrated d5 (25 iter) last.
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer6_weights.json --verbose
  ```
- [x] L6 phase-dependent evaluation — **DONE** (run `20260325_033805_9b3944b6`)
  Phase weights are HARMFUL: 0 wins in 25 games (mean 69 vs 96 for default).
  RAVE makes it worse (mean 61). Default and calibrated eval closely matched
  (48% vs 52% win rate). Phase weights should NOT be used.
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer6_phase.json --verbose
  ```

### Layer 7 — Opponent modeling ← **DONE**
- [x] L7 rollout asymmetry — **DONE** (50+ games across multiple runs, 2026-03-26)
  ZERO effect. All agents produce identical scores per seat position.
  `opponent_rollout_policy` does not change behavior at 25 iterations + cutoff depth 5.
- [x] L7 alliance detection — **DONE** (50+ games across multiple runs, 2026-03-26)
  ZERO effect. All agents produce identical scores per seat position.
  Alliance detection needs 3+ opponent moves to activate (barely triggers).
  Kingmaker detection needs 55% board occupancy (never triggers in normal games).
  `defensive_weight_shift` is dead code — `get_defensive_eval_adjustment()` is never called.
  **L7 conclusion**: Zero effect observed, but likely due to implementation bugs, not
  technique failure. Needs debugging and re-testing before drawing conclusions.
  **Known implementation issues to fix before re-run:**
  1. `get_defensive_eval_adjustment()` is dead code — defined in `opponent_model.py` but never
     called from `mcts_agent.py` during MCTS iterations. Must be wired into the evaluation path.
  2. Alliance detection threshold too strict — tracks opponents individually and requires 3+
     moves per opponent. Blokus research literature (e.g. Stankiewicz et al.) models all
     opponents as a single combined adversary; current per-opponent tracking is too conservative.
  3. Kingmaker detection requires 55% board occupancy — unreachable in many games, especially
     with cutoff-based rollouts. Threshold should be revisited or made adaptive.
  4. `opponent_rollout_policy` may need higher iteration budgets to produce meaningful
     differentiation — at 25 iterations the tree is too shallow for rollout policy to matter.
  5. Consider treating the 3-opponent coalition as a unified adversary (1-vs-all framing)
     rather than tracking individual opponent blocking rates independently.

### Layer 8 — Parallelization
- [ ] L8 throughput scaling (1/2/4/8 workers)
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer8_throughput.json --verbose
  ```
- [ ] L8 playing strength (root vs tree vs baseline)
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer8_strength.json --verbose
  ```

### Layer 9 — Meta-optimization
- [ ] L9 adaptive mechanisms comparison
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer9_adaptive.json --verbose
  ```

## Priority 3: Integration & Ongoing

- [ ] **Combined best-of-all-layers tournament** — After individual benchmarks, create a config combining winning settings from each layer vs baseline.
- [ ] **Run `self_improve.py` for ongoing tracking**
  ```bash
  python3 scripts/self_improve.py
  ```

## Priority 4: Deferred / Nice-to-Have

- [ ] **Reduce L2 model inference cost** — Currently ~26ms/call makes it useless. The lightweight `BlokusStateEvaluator` (sub-0.5ms) likely supersedes it.
- [ ] **Implement TD-UCT learning** — L6 flagged R² < 0.5 as justification. Larger research effort.
- [ ] **Profile L8 lock contention** — Determine optimal worker count for target hardware.

## Recommended Execution Order

Fix L6 bugs → L6 arena → L4 arena → L3 full validation → L5 → L7 → L8 → L9 → Combined tournament

The L6 weight corrections and L4 simulation strategy directly address the two biggest problems from L1 (poor evaluation + wasted iterations). Benchmark those first before layering on RAVE, opponent modeling, etc.
