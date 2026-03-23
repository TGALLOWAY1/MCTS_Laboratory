# MCTS Laboratory — TODO

Aggregated from Layers 0–9 PR reports. Last updated: 2026-03-23.

## Status Summary

| Layer | What | Arena Results? |
|-------|------|---------------|
| L0 | Measurement infrastructure (profiler, TrueSkill, tournament runner) | N/A (foundation) |
| L1 | Baseline characterization (571 self-play + 119 heuristic games) | **Invalid** — used `gameplay_fast_mcts` (no real rollout), not full MCTS. Needs re-run. |
| L2 | Learned evaluation model (GBT on 11,604 snapshots) | Done — zero benefit, inference cost (~26ms) eats 200ms budget |
| L3 | Action reduction (progressive widening + progressive history) | 8-game smoke test only — +19.2 avg score, needs full validation |
| L4 | Simulation strategy (two-ply, cutoff, minimax backups) | **None** |
| L5 | RAVE & NST history heuristics | **None** |
| L6 | Evaluation function refinement (feature analysis, calibrated weights) | **None** |
| L7 | Opponent modeling (blocking tracker, alliance, king-maker) | **None** |
| L8 | Parallelization (root + tree parallelization) | **None** |
| L9 | Meta-optimization (adaptive C, depth, sufficiency, loss avoidance) | **None** |

## Timing Expectations

At default 100ms budget (1000 iterations/move), **one game takes ~20-30 minutes**. A 25-game tournament = **8-12 hours**. Use `--num-games 4` for quick smoke tests. Add `--verbose` for per-game progress output.

---

## Priority 1: Fix Known Evaluation Bugs

These affect all subsequent experiments — fix before running arena benchmarks.

- [ ] **Fix `largest_remaining_piece_size` sign error and weight miscalibrations**
  Default weights in `mcts/state_evaluator.py` are wrong per L6 regression analysis:
  - `largest_remaining_piece_size`: +0.10 → should be **-0.23** (wrong sign)
  - `squares_placed`: 0.30 → should be **0.03** (overweighted 10x)
  - `opponent_avg_mobility`: -0.10 → should be **-0.30** (underweighted 3x)
  Calibrated weights are in `data/layer6_calibrated_weights.json`.

- [ ] **Add `center_proximity` feature to `BlokusStateEvaluator`**
  L6 identified this as the #1 Random Forest feature (36.1% importance) but it is entirely absent from the evaluator. Requires a code change in `mcts/state_evaluator.py`.

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

### Layer 6 — Calibrated weights vs defaults
- [ ] L6 calibrated vs default weights
  ```bash
  python3 scripts/arena.py --config scripts/arena_config_layer6_weights.json --verbose
  ```
- [ ] L6 phase-dependent evaluation
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
