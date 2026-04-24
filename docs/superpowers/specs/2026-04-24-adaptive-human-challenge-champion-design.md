# Adaptive Human-Challenge Champion Design

Date: 2026-04-24

## Purpose

The next portfolio milestone is not a stronger story page first. It is a playable champion agent that can beat a human player reliably, then gives the story page clean evidence to explain.

The agent should feel responsive on ordinary moves while retaining permission to spend up to 30 seconds on positions that are genuinely critical or uncertain. Strength should come from better search and evaluator quality, not simply from longer fixed compute budgets.

## Current Codebase Context

The repository already has most of the research substrate:

- Arena execution with deterministic seeds, summaries, pairwise matchups, TrueSkill, seat breakdowns, snapshots, and resumable artifacts.
- MCTS layers for progressive widening, RAVE, rollout cutoff depth, minimax backup blending, adaptive rollout depth, sufficiency threshold, and loss avoidance.
- A snapshot-to-pairwise modeling pipeline in `scripts/train_eval_model.py`.
- Learned evaluator integration in `mcts/learned_evaluator.py` and `mcts/mcts_agent.py`.
- Existing champion configs such as `scripts/arena_config_overnight_10hr.json` and `scripts/arena_config_learned_champ.json`.

The main product gap is that browser gameplay does not clearly instantiate the full arena-tested champion stack. The web gameplay factory and game manager currently pass only basic MCTS parameters in some paths, so the public playable agent may be weaker than the research champion.

## Goals

- Ship a first-class "Challenge Champion" profile for human play.
- Cap thinking time at 30 seconds, with most non-critical moves returning much faster.
- Improve strength per second through staged evaluator updates and search tuning.
- Promote candidates only through reproducible arena evidence.
- Produce artifacts the portfolio page can cite: champion config, validation summary, latency profile, and examples of adaptive thinking decisions.

## Non-Goals

- Revive the archived RL training stack.
- Claim human-level dominance from small samples or one-off games.
- Make the learned evaluator mandatory if it does not pass latency gates.
- Rewrite the story page before the champion evidence exists.

## Proposed Architecture

### 1. Frozen Champion Profile

Add a checked-in champion profile that can be used by both arena runs and browser gameplay.

The initial control champion should be based on the strongest validated non-learned stack:

- Progressive widening enabled.
- RAVE enabled with the validated `k=1000` setting.
- Random rollout policy with cutoff depth around the current champion setting.
- Calibrated state evaluator weights.
- Adaptive rollout depth if it continues to validate.
- Sufficiency threshold and loss avoidance only if they survive promotion gates.

This profile should become the source of truth for "Challenge Mode" rather than duplicating partial settings across frontend presets, API defaults, and arena configs.

### 2. Adaptive Budget Controller

Introduce a deterministic controller that assigns each move a budget tier. The controller should produce a structured explanation for logging and UI display.

Suggested tiers:

| Tier | Typical budget | Trigger examples |
| --- | ---: | --- |
| Trivial | 250ms-1s | One legal move, very low branching, stable obvious best move |
| Normal | 2-5s | Ordinary mid-game position, moderate branching and score risk |
| Critical | 10-30s | Close top-move Q values, high visit entropy, late game, agent behind, tactical congestion |

The controller should use signals already available or cheap to compute:

- Legal move count.
- Game phase or board occupancy.
- Score rank and score deficit.
- Top candidate Q margin after a warmup search.
- Root visit entropy.
- Best-move stability across search snapshots.
- Loss-avoidance or catastrophic-node indicators.

The controller should avoid spending the full 30 seconds merely because branching is high. High branching means the move is expensive; it does not always mean extra search is useful.

### 3. Search Quality Improvements

The adaptive clock is a ceiling, not the main strength strategy. Candidate improvements should be tested for strength per second:

- Tune progressive widening constants for human-challenge budgets.
- Compare rollout-only, learned-evaluator, and hybrid leaf-evaluation modes.
- Use sufficiency threshold as an early-stop path when the best move is already separated.
- Prefer root-policy stability over raw iteration count as a stopping signal.
- Keep opponent modeling optional unless it demonstrates a real advantage at challenge budgets.

### 4. Staged Evaluator Flywheel

The 300+ game runs should both validate strength and feed evaluator updates.

Stage 0: Freeze Control Champion

- Select the strongest known non-learned champion as the control.
- Record its exact config and current validation artifacts.

Stage 1: Generate Challenge Data

- Run 300+ games with snapshots enabled.
- Include the control champion, prior baselines, and any challenger variants.
- Capture dense checkpoints across early, mid, and late game phases.

Stage 2: Retrain Evaluator

- Train pairwise win-probability models using the existing snapshot pipeline.
- Preserve game-level train/test splits to avoid leakage.
- Compare phase-aware GBT and simpler models such as logistic regression.

Stage 3: Inference Cost Gate

- Benchmark evaluator latency before arena promotion.
- Reject learned candidates that improve raw win rate but lose strength per second or exceed human-play latency targets.
- Consider hybrid use if full learned evaluation is too expensive.

Stage 4: Arena Promotion

Compare at least:

- Previous frozen champion.
- Rollout-only search candidate.
- Learned-evaluator candidate.
- Hybrid candidate that uses learned evaluation selectively.

Stage 5: Repeat

- Promoted champion games become the next training dataset.
- Each cycle leaves behind a model artifact, arena summary, latency profile, and promotion decision.

### 5. Human Challenge Mode

Browser gameplay should expose a clear Challenge Mode that uses the same champion profile validated in the arena.

Runtime requirements:

- Full champion parameters must flow into the MCTS agent constructor.
- The UI should show when the agent is thinking and why a longer budget was selected.
- Move stats should include budget tier, budget cap, time spent, iterations, and early-stop reason.
- The app should handle long moves without appearing frozen.
- The champion profile should be selectable without requiring the user to manually tune layer knobs.

## Promotion Criteria

A candidate can become the Challenge Champion only if it satisfies all of the following:

- At least 300 validation games in the promotion run or cumulative promotion block.
- Positive pairwise margin against the previous champion.
- Positive or neutral seat-stratified performance; no hidden seat collapse.
- No material increase in invalid moves, timeouts, truncations, or game errors.
- p95 move latency remains under the 30 second cap in human-challenge mode.
- Strength per second is better than or competitive with the previous champion.
- Human-play runtime uses the same config path as the promoted arena profile.

## Evidence Artifacts

Each promotion cycle should produce:

- `challenge_champion_config.json` or equivalent checked-in profile.
- Arena run directory with `summary.json`, `summary.md`, and snapshots where relevant.
- Evaluator model artifact if a learned candidate is involved.
- Latency report with p50, p90, p95, max, and budget-tier distribution.
- Promotion report explaining whether the candidate passed or failed.

## Testing Strategy

- Unit tests for the budget controller: tier selection, cap enforcement, deterministic reasons.
- Integration tests that champion config parameters reach `MCTSAgent`.
- Small smoke arena before long validation runs.
- Model training smoke test from a tiny snapshot fixture.
- Validation test that move stats include budget tier and timing fields.

## Risks

- The learned GBT champion may remain too slow for polished browser play.
- More time may not improve strength if evaluator quality is the bottleneck.
- Human reliability is partly product UX: a strong agent still feels broken if the UI freezes.
- Arena dominance against agents may not perfectly predict human challenge strength, so human-play logs should become part of later evaluation.

## Story Impact

Once this lands, the portfolio story can shift from "here are many experiments" to "here is the champion I built, here is how it decides when to think, here is the validation trail, and here is how the evaluator improved from its own championship games."

