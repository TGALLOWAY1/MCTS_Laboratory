# Overnight Training Roadmap (30 Nights, Single Machine, 10 PM–8 AM)

Date: 2026-03-30

## 1) Top-Line Recommendation

Use the 30-night window as an **MCTS-first optimization + measurement program**, with RL treated as a **deferred/rehabilitation track** rather than a primary nightly workload. The active branch is built around arena-driven MCTS experiments with reproducible seeds, resumability, and detailed run artifacts, while the RL execution stack is archived and partially broken in this checkout.

Recommended compute allocation across 30 nights:

- **~70% MCTS search tuning + self-play arenas**
- **~20% evaluation/tournaments + rating stability checks**
- **~10% instrumentation, throughput calibration, and reporting**
- **0% overnight PPO training until RL runtime is restored on this branch**

Practical split:
- Nights 1–4: instrumentation/benchmark baselines + reliability hardening.
- Nights 5–20: focused MCTS tuning (time budget, rollout policy/cutoff, parallel strategy, selective ablations).
- Nights 21–26: championship validation (multi-seed, larger sample sizes).
- Nights 27–30: strongest-agent freeze, regression checks, and human-play package.

## 2) What Exists Today

### Working, production-usable systems (active branch)

- **Arena execution harness** with deterministic seed derivation per game and per agent, structured run outputs, and JSONL game logs (`scripts/arena.py`, `analytics/tournament/arena_runner.py`).
- **Resumable runs** through `--resume` path support in arena CLI and append semantics in runner.
- **Per-game telemetry** includes move counts, duration, invalid actions, truncation, and per-agent time/simulation metrics.
- **Summary generation** computes win stats, pairwise outcomes, seat breakdowns, score distributions, score margins, and TrueSkill leaderboard.
- **Snapshot pipeline** can emit fixed-ply datasets (`snapshots.csv/.parquet`) plus feature diagnostics for downstream modeling.
- **Post-audit MCTS correctness baseline** is explicitly versioned (`audit_version = v1_2026-03-28`) and FastMCTS is removed from competitive path.

### Existing analytics/metrics capability

- TrueSkill-style multiplayer ratings implemented with OpenSkill Plackett-Luce model.
- Elo utility exists, but it decomposes multiplayer into pairwise pseudo-matches (useful as secondary signal only).
- Bootstrap/permutation statistical utilities are present for pairwise score-difference significance checks.

### Evidence of real run throughput

Recent arena outputs (post-audit) show representative game durations around **~61–71 sec/game (mean ~66.8 sec)** for 100ms configured MCTS agents in a 4-agent round-robin setup, with per-agent effective simulations around **~42–45 sims/sec** under that configuration.

## 3) Critical Gaps / Risks

1. **RL pipeline on active branch is not overnight-ready.**
   - README states RL training code was archived from active branch.
   - RL docs and scripts still reference `training/*`, `envs/*`, and archived modules not present here.
   - Some scripts still import removed FastMCTS modules.

2. **Benchmark/tooling drift and stale scripts.**
   - Multiple benchmark scripts depend on archived RL modules or removed agents.
   - This creates false confidence risk if you assume those scripts are current.

3. **TrueSkill trust limitations in 4-player free-for-all.**
   - TrueSkill works for multiplayer ranking, but can overstate certainty with small samples and seat effects.
   - Must combine with seat-stratified stats, pairwise deltas, and confidence intervals.

4. **Experiment tracking is partially there but fragmented.**
   - Strong run artifacts exist, but no single experiment registry unifies nightly job metadata, commit hash, machine profile, planned-vs-actual schedule, and cross-run rollups.

5. **Nightly reliability risk without preflight gates.**
   - If a run dies mid-night, resume exists, but no orchestrated watchdog/report step currently guarantees “morning-ready” summaries.

## 4) Throughput Estimate

These estimates are anchored to current arena artifacts and then widened with explicit assumptions.

### Baseline anchor (from existing arena runs)
- Mean game duration: ~66.8 sec/game (25-game run sample).
- Implied throughput: ~53.9 games/hour.
- 10-hour window: ~539 games/night (if configuration and hardware are similar, and no downtime).

### Practical planning ranges (single machine)

- **Fast evaluation lane (100ms agents, fixed configs):**
  - ~35–60 games/hour
  - ~350–600 games/night

- **Heavier tuning lane (more expensive settings, deeper/searchier configs):**
  - ~15–35 games/hour
  - ~150–350 games/night

- **Mixed nightly program (self-play + ablations + eval):**
  - ~220–500 games/night realistic planning band

### 30-night totals (realistic range)

- Conservative: ~6,600 games (220/night)
- Mid-case: ~10,500 games (350/night)
- Optimistic: ~15,000 games (500/night)

Use night-1 calibration as the binding factor before finalizing these expectations.

## 5) Best 30-Day Plan

## Phase 0 (Nights 1–4): Instrumentation + Calibration

**Objective:** Establish trustworthy speed/cost baselines and harden overnight reliability.

**Nightly jobs:**
- Run 2–3 calibration tournaments at different MCTS budgets/configs.
- Record games/hour, average turns/game, avg sims/sec, crash/invalid rate.
- Validate resume semantics with intentional interruption/restart once.

**Success criteria:**
- Reproducible throughput envelope established.
- Resume tested and verified.
- Morning summary/report produced automatically.

**Artifacts:**
- `arena_runs/<run_id>/...` outputs, plus a small benchmark rollup table.

**Risks:**
- Discovering stale scripts mid-phase; must lock on known-good runner path (`scripts/arena.py`).

## Phase 1 (Nights 5–12): MCTS Core Sweeps

**Objective:** Find strongest cost-effective MCTS configuration under fixed nightly budget.

**Nightly jobs:**
- Structured sweeps over:
  - thinking_time_ms tiers (e.g., 50/100/150/250),
  - rollout policy/cutoff variants,
  - selected Layer 8/9 toggles likely to matter.
- Use round-robin seat policy and fixed seeds + multi-seed reruns for top candidates.

**Success criteria:**
- 2–3 clearly superior candidates with stable advantage across ≥3 seeds.
- No reliance on pre-audit/invalid baselines.

**Artifacts:**
- Per-night summary + cross-night leaderboard table with confidence bands.

**Risks:**
- Overfitting to one seed/night; mitigate with seed blocks and holdout nights.

## Phase 2 (Nights 13–20): Self-Play Volume + Weekly Championship

**Objective:** Accumulate robust comparisons and stress-test best candidates.

**Nightly jobs:**
- Most compute on best 2–4 agent variants in large round-robin volumes.
- One nightly “reference baseline” included to detect drift.

**Success criteria:**
- Ranking stability (TrueSkill order + pairwise score deltas consistent).
- Seat-stratified performance does not contradict overall ranking.

**Artifacts:**
- Weekly championship summaries and cumulative trend plots.

**Risks:**
- Rating noise from small nightly samples; solved by cumulative weekly rollups.

## Phase 3 (Nights 21–26): Strongest-Agent Validation

**Objective:** Freeze “candidate strongest” and validate against regression suite.

**Nightly jobs:**
- Locked candidate vs prior top agents + baselines.
- Multi-seed tournaments with larger game counts and paired comparisons.

**Success criteria:**
- Candidate beats prior champion with statistically meaningful margins.
- No major regressions in robustness metrics (timeouts, invalid actions, truncation).

**Artifacts:**
- Champion acceptance report.

## Phase 4 (Nights 27–30): Human-Play Readiness

**Objective:** Ship a stable “playable strong agent” build.

**Nightly jobs:**
- Low-risk regression suites and final leaderboard regeneration.
- Generate human-facing profile (strength summary, response-time profile, known weaknesses).

**Success criteria:**
- Agent meets minimum strength threshold (defined below).
- Gameplay interface settings fixed and reproducible.

**Artifacts:**
- “Play against champion” checklist and launch config.

## 6) Nightly Job Design

Use a fixed template suitable for Claude Code `/loop` orchestration.

### Nightly template (10 hours)

1. **Block A – Warmup/health check (20–30 min)**
   - small smoke arena (e.g., 8–12 games)
   - validate writes, summaries, and no immediate failures

2. **Block B – Main training/tuning workload (5.5–6.5 h)**
   - one of: broad sweep OR focused self-play volume
   - produce one or more run directories

3. **Block C – Evaluation championship (2–2.5 h)**
   - fixed “evaluation bracket” vs locked baselines/champion
   - consistent seed pack each night

4. **Block D – Aggregation/report (45–60 min)**
   - compile leaderboard deltas
   - produce nightly markdown summary and machine-readable JSON manifest

5. **Block E – Recovery buffer (30–45 min)**
   - resume unfinished run or execute fallback mini-eval

## 7) Measurement Strategy

Use **multi-metric gates**; never promote by TrueSkill alone.

### Nightly metrics (required)

- Run integrity: completed games, error games, invalid actions, truncations.
- Throughput: games/hour, mean duration, moves/game, move-time p50/p95.
- Strength: win rate points, score mean/std, pairwise matchup counts.
- Ratings: TrueSkill (`mu`, `sigma`, conservative `mu-3sigma`) and Elo (secondary only).
- Seat robustness: win/score by seat.
- Stability: variation across seeds (at least 3-seed checkpoints weekly).

### Weekly metrics (promotion gates)

- Pairwise bootstrap CIs and/or permutation-test p-values for top rival comparisons.
- Minimum sample guidance before “better” claim:
  - **Do not claim improvement under ~200 total games for close variants.**
  - Prefer **300–600 games** for promotion decisions when deltas are small.
- Champion promotion rule (example):
  - better conservative TrueSkill,
  - positive pairwise score delta CI excluding 0,
  - no worse seat-robustness profile,
  - no reliability regressions.

## 8) RL Viability Assessment

Blunt assessment: **RL is currently undercooked on this branch for overnight training.**

Why:
- Active project identity explicitly shifted away from RL; RL training code archived.
- RL docs/scripts reference missing runtime modules (`training`, `envs`) in this checkout.
- Some data-generation scripts still reference removed FastMCTS classes.

What this means for 30 days:
- **Do not allocate core nightly window to PPO training now.**
- If RL remains a goal, run a **parallel rehab track** (daytime or dedicated first week):
  1) restore runnable training entrypoints on active branch,
  2) re-establish checkpoint/resume and evaluation parity with current arena,
  3) validate reward/action correctness for 4-player setting,
  4) only then allocate limited overnight budget (e.g., 1–2 nights/week).

Best near-term RL strategy if revived:
- Start with **MCTS-guided imitation / policy warm-start** using arena snapshots and action targets, then small PPO fine-tuning.
- Pure-from-scratch PPO is unlikely to beat tuned MCTS in 30 nights on one machine.

## 9) When I Can Play a Strong Agent

You can likely schedule a meaningful human challenge around **Day 21–30**, assuming phase gates are met.

Operational definition of “strong” for this month:
- Champion consistently top-1 in weekly championship pools.
- Maintains positive pairwise margins vs previous champion across multi-seed runs.
- Stable under seat variation and no major reliability defects.

Most likely strong candidate in this horizon:
- **Tuned pure MCTS** (with proven Layer 5/8/9 combinations and calibrated time budget), not RL.

Human-play evaluation threshold (practical):
- ≥300 validation games in final championship window,
- clear advantage vs previous stable baseline,
- acceptable interaction latency at selected think budget.

## 10) Implementation Roadmap

1. Standardize a nightly manifest schema (`night_id`, commit, configs, machine profile, run_ids, totals).
2. Add a first-class “nightly orchestrator” script that chains calibration/sweep/eval/report and supports resume.
3. Add promotion gating script that consumes cumulative artifacts and emits PASS/FAIL.
4. Create weekly rollup script for cumulative ratings + confidence intervals + trend plots.
5. Create “champion alias” artifact (latest approved config + metadata) for gameplay/testing.

## 11) Highest-Priority Code Changes

1. **Fix/retire stale scripts pointing to archived modules** (benchmark and RL-linked scripts).
2. **Add a robust nightly runner script** around `scripts/arena.py` with failure recovery and report output.
3. **Introduce experiment registry file** (JSONL/CSV initially; one row per run/night).
4. **Add statistical gate checks** using existing bootstrap/permutation utilities.
5. **Add small hardware/throughput probe command** that runs nightly preflight and logs baseline speed.

## 12) Appendix: Key Files / Scripts / Evidence

Core execution and resumability:
- `scripts/arena.py`
- `analytics/tournament/arena_runner.py`
- `analytics/tournament/arena_stats.py`

Ratings/statistics:
- `analytics/tournament/trueskill_rating.py`
- `analytics/tournament/elo.py`
- `analytics/tournament/statistics.py`

Recent trustworthy run artifacts:
- `arena_runs/20260325_201856_32cf0875/run_config.json`
- `arena_runs/20260325_201856_32cf0875/games.jsonl`
- `arena_runs/20260325_201856_32cf0875/summary.json`

Audit and reliability context:
- `docs/audits/mcts_audit_remediation_summary.md`
- `tests/test_audit_invariants.py`
- `archive/docs/cpu_bottleneck_audit.md`

RL status and drift evidence:
- `README.md`
- `docs/evaluation.md`
- `scripts/benchmark_env.py`
- `benchmarks/bench_selfplay_league.py`
- `scripts/generate_training_data.py`
- `archive/rl/training-docs/rl_current_state.md`
