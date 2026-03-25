# MCTS Laboratory — TODO

Aggregated from Layers 0–9 PR reports. Last updated: 2026-03-25.

## Status Summary

| Layer | What | Arena Results? |
|-------|------|---------------|
| L0 | Measurement infrastructure (profiler, TrueSkill, tournament runner) | N/A (foundation) |
| L1 | Baseline characterization (571 self-play + 119 heuristic games) | **Invalid** — used `gameplay_fast_mcts` (no real rollout), not full MCTS. Needs re-run. |
| L2 | Learned evaluation model (GBT on 11,604 snapshots) | Done — zero benefit, inference cost (~26ms) eats 200ms budget |
| L3 | Action reduction (progressive widening + progressive history) | 8-game smoke test only — +19.2 avg score, needs full validation |
| L4 | Simulation strategy (two-ply, cutoff, minimax backups) | **None** |
| L5 | RAVE & NST history heuristics | **None** |
| L6 | Evaluation function refinement (feature analysis, calibrated weights) | **Done** — calibrated weights help, phase weights hurt |
| L7 | Opponent modeling (blocking tracker, alliance, king-maker) | **None** |
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

### Layer 3 — Full validation (8-game smoke test is not enough)
- [ ] Run full L3 validation tournament
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer3.json --verbose
  ```

### Layer 4 — Simulation strategy (run in order, findings cascade)
- [ ] L4 two-ply rollout comparison
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer4_two_ply.json --verbose
  ```
- [ ] L4 cutoff depth sweep
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer4_cutoff.json --verbose
  ```
- [ ] L4 minimax alpha sweep
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer4_minimax.json --verbose
  ```
- [ ] L4 combined best settings
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer4_combined.json --verbose
  ```

### Layer 5 — RAVE & history heuristics
- [ ] L5 RAVE k sweep
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer5_rave_k_sweep.json --verbose
  ```
- [ ] L5 head-to-head (baseline vs PH vs RAVE vs PH+RAVE)
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer5_head_to_head.json --verbose
  ```
- [ ] L5 convergence validation (50ms RAVE vs 200ms baseline)
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer5_convergence.json --verbose
  ```

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

### Layer 7 — Opponent modeling
- [ ] L7 rollout asymmetry
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer7_rollout_asymmetry.json --verbose
  ```
- [ ] L7 alliance detection
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer7_alliance.json --verbose
  ```

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
