# Overnight Training Roadmap (30 Days, Single Machine, 10 PM–8 AM)

## 1. Top-Line Recommendation

Use the next 30 nights primarily for **MCTS improvement + measurement quality**, with RL limited to scoped feasibility checks.

- **Primary allocation**: ~70% MCTS tuning/self-play/eval, ~20% cross-agent tournaments + analytics, ~10% RL viability probes.
- **Weeks 1–2**: instrumentation and throughput baselining first; avoid full-month jobs before calibrated throughput and stable evaluation gates.
- **Weeks 3–4**: sustained MCTS sweeps and rating-stable tournaments with strict promotion gates.
- **RL**: do not allocate major overnight budget unless an active RL trainer is restored in this branch.

## 2. What Exists Today

### Solid foundations

- Arena harness supports deterministic seeds, seat policies, per-game logs, snapshots, summary artifacts, and resumable runs.
- MCTS stack has layered controls for rollout policy, cutoff depth, RAVE/NST, parallel strategy, and adaptive depth/exploration.
- Summary pipeline already computes win rates, seat bias, pairwise results, score margins, TrueSkill, and per-agent time/simulation efficiency.

### Existing throughput evidence

- Calibration tooling exists for iteration throughput by phase/cutoff depth.
- Historical calibration data shows depth-5 rollout throughput is dramatically phase-sensitive.
- A fresh 1-game throughput run under layer-8 config produced ~165s game duration and per-agent sims/sec telemetry.

### RL state

- Active branch positioning is MCTS-first; RL training was archived.
- RL artifacts/docs remain under `archive/rl`.

## 3. Critical Gaps / Risks

1. **Stale/contradictory scripts/docs around FastMCTS**
   - Arena runner rejects `fast_mcts`, but some scripts/docs still reference it.
2. **Parameter sweep script appears incompatible with current arena API**
   - Calls `run_experiment(..., output_root=...)` and expects `agent_stats` in return payload.
3. **Legacy benchmark scripts reference missing RL modules (`envs`, `training`)**
   - Not executable on current branch without restoration.
4. **`self_improve.py` parses non-existent summary shape (`summary["agents"]`)**
   - Current summary emits `win_stats`, `score_stats`, `trueskill_ratings`, etc.
5. **TrueSkill-only conclusions are risky in 4-player games**
   - Need confidence-aware gates + secondary metrics to avoid noise-driven claims.

## 4. Throughput Estimate

Use these as **planning ranges**, not guarantees.

### Evidence-backed inputs

- Layer-8 style config in repo uses 100ms budget, random rollout, cutoff depth 5, RAVE=1000, and worker sweeps (1/2/4/8).  
- New one-game run (same config family) reports ~164.7s/game and agent sims/sec roughly 22 (1w), 34.6 (2w), 32.9 (4w), 28.8 (8w).
- Calibration data indicates depth-5 iter/ms can range from ~0.002 (early/mid) to ~0.062 (late), so game-phase mix dominates realized throughput.

### Practical planning ranges (single machine, overnight)

- **Fast tournament config (100ms/turn, cutoff 5, root-2w favored)**: ~15–30 games/hour.
- **Heavier eval config (200ms+ or deeper rollouts/ablations)**: ~6–15 games/hour.
- **Nightly volume (10h)**:
  - Fast: ~150–300 games/night
  - Heavy: ~60–150 games/night
- **30-day envelope (if stable from night 4 onward)**:
  - ~4,500 to ~9,000 tournament-grade games total.

## 5. Best 30-Day Plan

### Phase 0 (Nights 1–3): Instrumentation + reliability gate

**Objective:** ensure all nightly jobs are resumable, comparable, and non-stale.

**Nightly jobs:**
- Throughput calibration (`scripts/calibrate_throughput.py`) with fixed seed.
- 1–3 short arena smoke runs on intended "production" config.
- Validation of artifact schema: `run_config.json`, `games.jsonl`, `summary.json`, index row.

**Success criteria:**
- Stable games/hour estimate range for your hardware.
- Confirmed resumability with interrupted-and-resumed run.
- No stale fast_mcts pathways in orchestrated jobs.

### Phase 1 (Nights 4–9): Measurement stabilization

**Objective:** make improvement claims trustworthy before major optimization.

**Nightly jobs:**
- Fixed reference tournament block (unchanged control pool, 80–150 games/night).
- Candidate-vs-reference block (new variants, 60–120 games/night).
- Auto-generate nightly summary markdown + CSV row for trend dashboard.

**Success criteria:**
- TrueSkill sigma trends downward for stable references.
- Seat bias and score margin stats stable across 3+ nights.
- Promotion gate policy finalized (see section 7).

### Phase 2 (Nights 10–20): MCTS optimization core

**Objective:** maximize strength-per-time for your target play setting.

**Nightly jobs:**
- Parameter sweeps/ablations (rollout depth, iterations_per_ms, RAVE k, num_workers).
- Follow-up head-to-head blocks for top 2–3 configs.
- Weekly long tournament (higher n) for promotion validation.

**Success criteria:**
- At least one candidate beats incumbent with confidence thresholds.
- Throughput-adjusted strength improves (not just raw win rate).

### Phase 3 (Nights 21–25): RL viability checkpoint (strictly bounded)

**Objective:** decide if RL is worth ongoing overnight allocation in this branch.

**Nightly jobs:**
- Only if RL trainer is restored: tiny-budget feasibility runs + evaluation vs fixed MCTS baselines.
- Otherwise: continue MCTS + evaluator/feature improvements.

**Success criteria:**
- RL either demonstrates measurable uplift potential or is formally deprioritized.

### Phase 4 (Nights 26–30): strongest-agent hardening + human-play prep

**Objective:** lock a "strong agent" build and validate repeatably.

**Nightly jobs:**
- Frozen-candidate vs full benchmark pool (high sample).
- Regression checks (no invalid actions, no error games, no throughput collapse).
- Build a human-challenge package (config + logs + explanation telemetry).

**Success criteria:**
- Champion passes promotion gates for 3 consecutive nights.
- Ready-to-play human-facing config documented.

## 6. Nightly Job Design

Template for `/loop` orchestration (10h window):

1. **22:00–22:30** — health + calibration
   - quick throughput probe + smoke tournament (small n)
2. **22:30–03:30** — main training/tuning block
   - MCTS sweeps or self-play generation
3. **03:30–06:30** — evaluation block
   - fixed-pool round-robin + contender head-to-head
4. **06:30–07:30** — aggregation/report block
   - compile summary table, confidence intervals, ranking deltas
5. **07:30–08:00** — checkpoint + handoff
   - mark promoted candidate(s), archive run metadata

## 7. Measurement Strategy

### Nightly tracked metrics

- Core: win_rate, win_points, score mean/std, pairwise counts, seat win rates, score margins.
- Rating: TrueSkill mu/sigma/conservative with convergence flag.
- Efficiency: avg_time_ms_per_move, sims/sec, budget utilization.
- Reliability: error_games, invalid_actions, truncation counts.
- Provenance: seed, seat policy, run config payload, audit version, git commit.

### Promotion gate (recommended)

A candidate is "better" only if all pass:

1. **Primary**: conservative TrueSkill improvement vs incumbent in pooled games.
2. **Secondary**: non-overlapping (or minimally overlapping) Wilson CI for win-rate delta in direct matchup.
3. **Robustness**: no worse seat-bias profile and no reliability regressions.
4. **Efficiency-aware**: equal or better strength-per-second at target time budget.

### Cadence

- **Nightly**: incremental update + short confidence report.
- **Weekly**: recompute full ratings from the full retained corpus (not only last night).

## 8. RL Viability Assessment

Current branch is **not RL-ready for production overnight training**.

- Repo/docs indicate RL pipeline was archived and project focus moved to MCTS.
- RL benchmark/training-related scripts in active tree reference missing modules and are not directly runnable as-is.

Recommendation:

- Treat RL as a **research side quest** this month unless you first restore an active RL training stack and reproducible eval path in this branch.
- If restored, prefer **MCTS-guided policy warm-start / imitation** over pure-from-scratch PPO for a 30-day horizon.

## 9. When I Can Play a Strong Agent

Realistic timeline:

- **Earliest meaningful playtest:** around **night 14–18**, after Phase 2 identifies a stable promoted MCTS config.
- **Stronger confidence playtest:** **night 26+** after hardening phase.

Operational definition of "strong":

- Champion beats frozen incumbent and baseline pool across >=300 recent eval games,
- Maintains lower/equal TrueSkill sigma trend,
- Shows no reliability regressions,
- Meets target interaction latency for human play.

Likely champion form in this horizon: **tuned MCTS (root-parallel, cutoff+RAVE optimized)**, not RL-first.

## 10. Implementation Roadmap

1. Fix stale scripts/docs that still use fast_mcts.
2. Repair parameter sweep and self-improve scripts against current summary/run_experiment API.
3. Add a dedicated nightly orchestrator script (idempotent, resumable, phase-aware).
4. Add experiment registry row format (CSV/JSONL) with full provenance.
5. Add nightly auto-report generator (markdown + compact machine-readable summary).
6. Add weekly full recomputation command for ratings and confidence intervals.

## 11. Highest-Priority Code Changes

1. `scripts/self_improve.py`: parse `win_stats` / `score_stats` / `trueskill_ratings` correctly.
2. `scripts/parameter_sweep.py`: align with `run_experiment` signature and summary schema.
3. `scripts/run_tournament.py` + `scripts/run_experiments.sh` + `docs/arena.md`: remove fast_mcts defaults/recommendations.
4. Add `scripts/nightly_loop.py` with:
   - run phases,
   - checkpointing/resume,
   - command-level retries,
   - artifact registry append,
   - promotion gate checks.

## 12. Appendix: Key Files / Scripts / Evidence

- Core arena execution: `scripts/arena.py`, `analytics/tournament/arena_runner.py`, `analytics/tournament/arena_stats.py`.
- Rating: `analytics/tournament/trueskill_rating.py`.
- Throughput: `scripts/calibrate_throughput.py`, `data/throughput_calibration.json`, `arena_runs/20260330_033800_621ad19c/summary.json`.
- MCTS controls: `mcts/mcts_agent.py`, `scripts/arena_config_layer8_throughput.json`.
- RL status/archival context: `README.md`, `docs/project-history.md`, `archive/rl/`.
- Fragility/stale paths: `scripts/self_improve.py`, `scripts/parameter_sweep.py`, `scripts/run_tournament.py`, `scripts/run_experiments.sh`, `scripts/benchmark_env.py`, `docs/arena.md`.
