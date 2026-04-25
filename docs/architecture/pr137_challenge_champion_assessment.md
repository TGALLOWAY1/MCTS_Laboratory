# PR #137 Challenge Champion assessment and next-step plan

## Executive summary

PR #137 successfully introduced a **deployable Challenge Champion profile** and adaptive per-move budget logic for human-play mode, including profile validation and telemetry surfacing (`budgetTier`, `budgetCapMs`, `budgetReasons`). The core implementation is sound and covered by focused tests.

The biggest remaining gap is not model quality code, but **evidence quality**: we still do not have a dedicated arena evaluation track that answers "does this reliably beat human-like opponents?" with statistically defensible confidence.

## What PR #137 clearly delivered

1. A source-of-truth profile loader + validation contract:
   - `config/challenge_champion_config.json`
   - `mcts/champion_profile.py`
2. Adaptive budgeting policy with deterministic tiering from warmup uncertainty and game context:
   - `mcts/adaptive_budget.py`
3. Deploy gameplay integration and API telemetry support:
   - `webapi/gameplay_agent_factory.py`
   - `webapi/deploy_validation.py`
   - `webapi/app.py`
4. Browser parity for challenge mode and UI exposure.
5. Focused tests for profile validity, budget policy behavior, deploy constraints, and gameplay stats.

## Gaps that block a "reliably beats humans" claim

### 1) No dedicated challenge-focused arena config/runs checked in
There are many arena config presets, but none currently target the challenge profile directly. Without this, we cannot track champion strength drift in CI or scheduled experiments.

### 2) Arena does not reproduce full gameplay adapter behavior
Arena `build_agent` can load the challenge profile into `MCTSAgent` parameters, but it does **not** run the deploy adapter's warmup -> budget-tier -> final-search loop from `webapi/gameplay_agent_factory.py`.

This means arena can estimate base-search strength, but it is not a full proxy for the exact human-facing runtime policy.

### 3) No explicit statistical acceptance gates for human-proxy performance
Current tests verify correctness and constraints, not outcome strength thresholds (e.g., minimum first-place rate vs fixed baselines, confidence intervals, or minimum effect size).

### 4) No calibration loop from live challenge telemetry back into profile versioning
Telemetry fields are present, but there is no documented routine for:
- collecting challenge sessions,
- identifying tier over/under-escalation,
- and updating `challenge_champion_config.json` versioned parameters.

## Recommended next steps

## Phase 1 (immediate): establish repeatable evaluation

1. Add a challenge-focused arena config (included in this PR):
   - `scripts/arena_config_challenge_champion_validation.json`
2. Run a baseline evaluation set (suggested):
   - 200 games, round-robin seats, fixed seed block A.
   - 200 games, round-robin seats, fixed seed block B.
3. Record and compare:
   - first-place rate,
   - average placement,
   - TrueSkill deltas,
   - bootstrap CIs from arena summary artifacts.

## Phase 2 (short term): close proxy gap

Implement a dedicated arena adapter mode that uses the same gameplay adapter path as deploy (`_ChallengeChampionGameplayAdapter`) so arena reflects warmup/tier/early-stop behavior exactly.

## Phase 3 (short term): define acceptance policy

Adopt explicit release gates for challenge profile updates, e.g.:
- first-place rate delta vs reference >= target,
- lower CI bound > baseline,
- no regression in move-latency p95 budget compliance.

## Phase 4 (ongoing): human telemetry feedback loop

For every profile version:
1. Collect live telemetry samples (`budgetTier`, `budgetReasons`, result, move index).
2. Diagnose where critical/trivial tiers are over-triggered.
3. Tune thresholds in `AdaptiveBudgetController` and/or config budgets.
4. Re-run arena acceptance suite before promotion.

## Suggested command sequence

```bash
python scripts/arena.py --config scripts/arena_config_challenge_champion_validation.json
python scripts/arena.py --config scripts/arena_config_challenge_champion_validation.json --num-games 200 --seed 20260426
python scripts/arena.py --config scripts/arena_config_challenge_champion_validation.json --num-games 200 --seed 20260427
```

Then inspect generated `arena_runs/<run_id>/summary.md` and `arena_runs/<run_id>/summary.json` for regression tracking.
