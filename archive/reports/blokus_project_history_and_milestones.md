## How this report was constructed

This report was reconstructed from four layers of evidence in the repository as of March 23, 2026: the full git history and merge history, surviving documentation and planning notes, the current codebase structure and key implementation files, and checked-in benchmark / report artifacts such as `benchmarks/results/*.json`, `docs/profiler_baseline.md`, `docs/cpu_bottleneck_audit.md`, and `reports/layer1_baseline_report.md`.

Confidence is high on the broad chronology and on the major turning points after February 2026, because those phases are heavily documented in commits, PR merge titles, new subsystems, and generated artifacts. Confidence is moderate on some early RL-era intent and on exact motivations behind unmerged or later-archived code, because the active checkout no longer contains the full RL implementation and some documentation now points at files that were removed on `main`.

The main uncertainty is not whether the project shifted from RL toward MCTS, but exactly when that shift became deliberate rather than emergent. The strongest evidence for intentionality is the March 6, 2026 archival commit `cc106db`, which explicitly moved RL agents to a separate branch and simplified the active repo around MCTS-oriented work.

# 1. Executive Summary

The repository began as an ambitious full-stack Blokus reinforcement learning environment: a rules engine, PettingZoo/Gymnasium wrappers, MaskablePPO training scripts, a React research UI, and baseline agents including heuristic and MCTS search. In its first phase, the central question appears to have been: “Can Blokus be turned into a trainable RL environment with useful observability and evaluation?”

The project’s center of gravity then moved in two steps. First, simulation speed and environment correctness became dominant concerns. The December 2025 engine work on frontier-based move generation, bitboards, equivalence testing, and environment stabilization was still in service of RL, but it effectively made the engine itself the most important asset in the repo. Second, January through March 2026 added league play, self-play infrastructure, reproducible arena runs, telemetry, MCTS diagnostics, win-probability feature extraction, tournament statistics, time-fair tuning harnesses, and browser-side MCTS execution. At that point the repo started behaving much more like a Blokus AI experimentation platform than a conventional RL training project.

The biggest technical turning points were:

- The M6 move-generation optimization work in early December 2025, which made simulation throughput a first-class concern.
- The Stage 2 / Stage 3 self-play and league work in January and February 2026, which shifted focus from “train one policy” to “compare agents and checkpoints in a structured ecosystem.”
- The February 24, 2026 Pyodide/WebWorker migration, which made local MCTS execution and rich UI analysis central to the project’s public-facing identity.
- The March 2, 2026 arena / dataset / learned-evaluator work, which turned MCTS games into reusable research data.
- The March 6, 2026 RL archival commit, which made the MCTS-centered reframing explicit.
- The March 21, 2026 performance re-audit, which corrected earlier assumptions and re-established empirical profiling as the basis for optimization.

The repo’s biggest engineering wins are not only raw speedups. They are the reframings that made repeatable AI experimentation possible: a reusable engine, deterministic arena scheduling, structured game/step logs, MCTS diagnostics, analysis dashboards, dataset generation, and benchmark/tuning harnesses. The strongest unresolved opportunities are also clear: the full MCTS rollout path is still too expensive, current baseline characterization suggests search quality is not yet where it needs to be, and the repo still carries documentation and structural debt from the archived RL phase.

# 2. Project Evolution Narrative

The repository opened on November 30, 2025 as a reinforcement-learning-first Blokus project. The first substantial commit, `d604462`, introduced the game implementation, agents, engine, frontend, and training components in one move. Very quickly after that, the repo acquired a React research frontend and a more explicit RL framing. The M1 documentation in `docs/architecture/M1-Markdown.md` describes a “Blokus RL project” with a research sidebar, training parameter controls, PPO integration, and even a placeholder for MCTS-tree visualization. That placeholder matters: MCTS existed from the beginning, but as a comparative tool inside an RL-centered system, not yet as the repository’s main identity.

The early README revisions reinforce this reading. By commit `caa1cc8`, the repository described itself as a “Reinforcement Learning Environment for Blokus” with PettingZoo/Gymnasium compatibility, a web UI, and baseline agents including MCTS. The training side was not incidental. Commit `3d62e8e` explicitly added RL training dependencies and rewrote `training/trainer.py` around MaskablePPO. The next day’s M2, M3, and M4 work pushed on rules correctness, RL smoke-test stability, and vectorized environment compatibility. The branch names and merge messages from late November and early December 2025 read like a classic RL project cadence: create UI, resolve rules, add pretraining checklist items, parallelize training environments, benchmark VecEnv throughput.

That RL framing did not disappear immediately. In fact, December 4, 2025 strengthened it by making the training substrate more credible. PR `#22` (`05c60fc`) added canonical game results, win detection, dead-agent and no-legal-moves handling, benchmark scripts, and extensive operational documentation. This was foundational RL infrastructure work. But the same date also brought the more consequential M6 engine optimization branch, merged as PR `#20` (`1b78cfe`). That branch is a major inflection point in retrospect. Its explicit goal was to reduce move-generation cost by 5-10x through frontier tracking and bitboard legality checks. The work added `engine/bitboard.py`, overhauled `engine/move_generator.py`, expanded `engine/board.py`, created dedicated benchmarks and equivalence tests, and documented the optimization architecture in depth.

This M6 work was still justified partly through RL throughput, but it changed what the project was actually good at. The codebase now contained a relatively serious simulation engine with correctness scaffolding and measurable performance claims. From that point forward, the engine was no longer just a dependency of the RL pipeline. It was the project’s core technical asset.

The next important shift came in January and February 2026, when the project moved from single-run training concerns toward league-style self-play and comparative evaluation. Commit `2139cd8` added a self-play training pipeline and Elo league in `rl/`, `league/`, and `agents/registry.py`. This still lived under an RL label, but conceptually it was already moving toward a broader question: not only “can PPO learn?” but “how should agents, checkpoints, and baselines be organized, compared, and ranked over time?” The later Stage 3 configuration files in `configs/stage3_selfplay*.yaml` make the shift clearer. `configs/v1_rl_vs_mcts.yaml` still frames training as RL versus a stronger MCTS opponent plus randoms. `configs/stage3_selfplay.yaml`, by contrast, defines a checkpoint-only self-play league where the opponent list is ignored and league sampling policy becomes the main design surface.

PR `#27` (`d85c876`) is the strongest evidence of this middle-stage reframing. It merged Stage 3 self-play league work, analytics/logging subsystems, tournament modules, metrics packages, benchmark scripts, engine service scaffolding, and new frontend Analysis/History pages. The shape of the repository changed. The project now contained:

- `analytics/logging/` for per-step telemetry.
- `analytics/metrics/` for domain-specific evaluation features.
- `analytics/aggregate/` and `analytics/tournament/` for cross-game analysis.
- `benchmarks/` scripts for profiling Stage 3 behavior.
- Config suites for portfolio, smoke, RL-vs-MCTS, and checkpoint-league runs.

That is the moment when the repo began acting like an experimentation platform rather than a training script plus UI.

The next pivot was public-facing and architectural: deployment shifted toward making MCTS directly usable and inspectable. PR `#31` (`df5827b`) migrated the Python engine and AI stack into a Pyodide WebWorker. This was not just an implementation detail. It introduced the `browser_python/` mirror of the engine, agents, and MCTS code, wired the frontend to load `blokus_core.zip`, and anchored the deployment story around “human vs 3 MCTS” without backend compute costs. Combined with the deploy-profile work from PR `#28`, this changed the strongest external story of the project. Instead of “I built an RL environment,” the repository could now say, in effect: “I built a portable Blokus AI system where users can play against search agents and inspect their behavior locally in the browser.”

At the same time, analytics and interpretability work accelerated. PR `#32`, PR `#39`, PR `#46`, PR `#47`, and PR `#57` layered on advanced metrics, move-vs-round semantics, telemetry deltas, piece-economy and frontier visualizations, and a substantial analysis dashboard. This UI work was not cosmetic. It represented a real conceptual change: gameplay history and MCTS decisions were becoming data products, not only transient runtime objects.

March 2, 2026 is arguably the repository’s clearest shift into MCTS-centered research tooling. PR `#52` (`2a10ea7`) added `analytics/tournament/arena_runner.py`, `analytics/tournament/arena_stats.py`, `analytics/winprob/features.py`, `analytics/winprob/dataset.py`, `mcts/learned_evaluator.py`, `docs/arena.md`, and `docs/datasets.md`. This bundled together three things that matter a lot:

1. A reproducible arena harness with deterministic seeds and structured outputs.
2. A feature/dataset layer that turned game states into modelable examples.
3. A path to reinject learned evaluation back into MCTS through leaf evaluation, progressive bias, and shaping.

This is exactly the behavior of an AI testbed. The project was no longer centered on training a policy network end to end. It was centered on generating strong game states, measuring behavior, comparing search variants, and optionally learning evaluators that support search.

PR `#54` (`fb65413`) tightened that reframing by focusing on fairness, scheduling, and tuning infrastructure. Equal-time tournaments, multiseed aggregation, validation of runtime bounds, and adaptive bias benchmarking all point in the same direction: this repo was now being used to compare MCTS variants scientifically, not just to demonstrate that MCTS exists.

The decisive strategic pivot happened on March 6, 2026. Commit `cc106db` explicitly archived RL agents to the separate `archive/rl-agents` branch and removed `envs/`, `rl/`, `training/`, many RL tests, and large checkpoint artifacts from the active branch. This was not an incidental cleanup. It was a scope decision. The repository description lagged behind the code after this point, but the codebase itself no longer treated RL as the primary active workflow.

What followed in mid-to-late March was a maturing MCTS research layer. PR `#59` (`114b5b3`) added analysis-mode docs, MCTS diagnostics UI, and invariants tests. PR `#61` and PR `#62` audited and fixed performance bottlenecks. The audit in `docs/cpu_bottleneck_audit.md` is especially telling because it reverses a previous assumption: the default bitboard legality path had become slower than the grid-based path due to Python-level mask rebuilding. The fix in `0974105` did not merely make the engine faster; it demonstrated a more rigorous optimization culture. The repo was now profiling first, then redesigning around measured bottlenecks.

The final March 2026 layer, culminating in PRs `#66`-`#70`, is best understood as formalization. `plan.md` laid out an explicit evaluation-function roadmap. `benchmarks/benchmark_mcts_settings.py` benchmarked time-budget and exploration tradeoffs. `scripts/generate_training_data.py`, `scripts/train_eval_model.py`, and `scripts/validate_eval_model.py` turned learned evaluation into an end-to-end pipeline. `scripts/profile_mcts.py` and `docs/profiler_baseline.md` quantified that rollout simulation dominates standard MCTS runtime. The Layer 1 baseline suite and `reports/layer1_baseline_report.md` began treating MCTS improvement as a staged research program with named diagnostic layers.

Taken together, the repository did not simply drift from RL to MCTS. It first built RL-compatible infrastructure, then discovered that engine speed, simulation quality, reproducibility, and comparative analysis were the real leverage points, and finally simplified the active repo around those leverage points.

# 3. Timeline of Key Milestones

| Milestone | Date / Commit / PR | What Changed | Why It Mattered | What It Enabled Next |
|---|---|---|---|---|
| Initial full-stack RL scaffold | 2025-11-30, `d604462` | Added engine, agents, frontend, and training components in one initial buildout. | Established the original thesis: Blokus as an RL-ready environment with an interactive UI. | Later RL training work, environment wrappers, and baseline-agent comparisons. |
| Research UI and PPO-first framing | 2025-11-30, `3d62e8e`, `caa1cc8`, PR `#3` | Added robust MaskablePPO training script and documented the repo as a Blokus RL environment. M1 docs describe a research sidebar and training controls. | Made RL the project’s explicit identity, not just an aspiration. | VecEnv support, smoke testing, training history, and RL documentation. |
| VecEnv compatibility and training throughput work | 2025-12-01, commits around `ec5de01`, `502e37f`, PRs `#8`, `#12`, `#16` | Stabilized Gymnasium/PettingZoo compatibility, wrapper ordering, vectorized env support, and training speed benchmarks. | Showed that environment engineering and throughput were becoming critical concerns. | Later league/self-play infrastructure and deeper performance thinking. |
| Frontier + bitboard move-generation program (M6) | 2025-12-04, PR `#20`, `1b78cfe` | Added frontier tracking, bitboard legality, equivalence tests, and dedicated move-generation benchmarks. | This was the first major “simulation matters more than model choice” milestone. | Faster gameplay, faster search, and a stronger engine as the repo’s core asset. |
| RL training stabilization and game-result semantics | 2025-12-04, PR `#22`, `05c60fc` | Added canonical `GameResult`, win detection, dead-agent/no-legal-moves handling, benchmark scripts, and extensive operational docs. | Made PPO training and environment logging viable instead of brittle. | Stage 2 and Stage 3 self-play training, MongoDB training history, reproducible evaluations. |
| Self-play league and Elo-oriented training | 2026-01-19, `2139cd8` | Added `rl/` self-play training pipeline, `league/` modules, `agents/registry.py`, and overnight configs. | Shifted the problem from isolated policy training to ecosystem-level training and comparison. | Stage 2 RL-vs-MCTS training and later checkpoint leagues. |
| Stage 3 self-play league + analytics platform | 2026-02-18, PR `#27`, `d85c876` | Added Stage 3 configs, analytics/logging, metrics packages, tournament utilities, benchmark scripts, engine service, and Analysis/History frontend pages. | This is where the repo started looking like a research platform, not just a trainer. | Structured telemetry, benchmark artifacts, richer experiments, and later arena/tuning tooling. |
| Deployable MCTS product via Pyodide | 2026-02-23 to 2026-02-24, PRs `#28` and `#31`, `56347b2`, `df5827b` | Added deploy profile for human-vs-3-MCTS and migrated engine/AI into a Pyodide WebWorker with mirrored `browser_python/` modules. | Reframed the project outwardly as a portable MCTS system with local compute. | Recruiter/demo workflows, analysis-mode UX, and zero-backend-cost gameplay. |
| Arena runner + learned-evaluator foundation | 2026-03-02, PR `#52`, `2a10ea7` | Added reproducible `arena_runner`, summary stats, snapshot datasets, feature extraction, learned evaluator integration, and dataset docs. | Turned MCTS games into benchmarkable runs and ML-ready data. | Fair-time tournaments, learned-eval tuning, and model-validation workflows. |
| Fair-time MCTS tuning and multiseed benchmarking | 2026-03-02, PR `#54`, `fb65413` | Added tuning sets, fairness validation, scheduler fixes, parallel tournament execution, multiseed aggregation, and adaptive-bias benchmarks. | Converted ad hoc experiments into statistically defensible tuning studies. | Adaptive benchmark reports, production/default tuning choices, and stronger comparative methodology. |
| Metrics v2 and move-delta telemetry | 2026-03-05, PR `#57`, `62c4fe6` | Added telemetry engine, metrics config, move-delta charts, strategy-mix analysis, and expanded browser/runtime support. | Deepened interpretability and made game history analytically rich. | MCTS diagnostics UI, richer game explanation, and future model features. |
| Explicit RL archival and active-scope reset | 2026-03-06, `cc106db` | Removed `training/`, `rl/`, `envs/`, and many RL tests from active `main`, moving RL agents to `archive/rl-agents`. | Made the MCTS-first reframing deliberate rather than implied. | Cleaner active codebase, though with lingering doc/config debt. |
| MCTS analysis mode and diagnostics | 2026-03-07, PR `#59`, `114b5b3` | Added MCTS analysis docs, `MctsAnalysisPanel`, diagnostics types, and tests. | Search introspection became a first-class feature rather than debug-only plumbing. | Layered baseline analysis and more targeted MCTS optimization. |
| Empirical performance re-audit and legality-path correction | 2026-03-21, PRs `#61` and `#62`, `19016bd`, `0974105` | Audited CPU hotspots, found bitboard-path regression, then added fast mask shifting, BIT_TABLE lookup, singleton move generator, `Board.copy()` optimization, duplicate suppression, and early-exit `has_legal_moves()`. | Corrected earlier assumptions and re-centered optimization around measurement, not folklore. | Faster simulations, more reliable profiling, and better experimental turnaround. |
| End-to-end eval-model pipeline | 2026-03-22, PRs `#66` and `#67`, `ac401a4`, `4ad4f53` | Added `plan.md`, MCTS settings benchmark, and clean scripts for training-data generation, eval-model training, and validation. | Connected arena data, modeling, and search in a single workflow. | Future learned-evaluation experiments beyond dummy artifacts. |
| Layer 0 / Layer 1 baseline characterization | 2026-03-22, PRs `#68`-`#70`, `f35efee`, `a38b523`, `baeaddf` | Added profiler, TrueSkill/stats utilities, tournament runner, baseline analyses, and the Layer 1 report. | The repo began treating MCTS improvement as a staged research program. | A concrete roadmap for action reduction, rollout replacement, and convergence work. |

# 4. Major Technical Decisions and Strategic Pivots

## Decision: Start as an RL environment, not just a game engine

- Evidence: early README revisions (`caa1cc8`), `training/trainer.py` work in `3d62e8e`, RL-focused docs such as `docs/training-architecture.md`, `docs/evaluation.md`, and `docs/training-history.md`.
- Benefit gained: forced the project to build action masking, reproducibility, evaluation protocols, logging, and a strong abstraction boundary between the engine and training interfaces.
- Tradeoffs or costs: created a very large scope surface early; much of that surface later became stale or was archived.
- Retrospective: strong move overall. Even though RL is no longer the active center, the RL-first scope forced the repo to build infrastructure that later benefited search experiments.

## Decision: Attack simulation speed as a first-order problem

- Evidence: PR `#20` / `1b78cfe`, `benchmarks/benchmark_move_generation.py`, `docs/engine/move-generation-optimization.md`, `docs/architecture/PERFORMANCE_OPTIMIZATION_RESULTS.md`.
- Benefit gained: transformed the engine from “probably too slow for serious experimentation” into something that could support MCTS, arenas, and richer metrics.
- Tradeoffs or costs: some optimization paths, especially the bitboard legality path, later needed a second audit because the theoretical design drifted into slower Python-heavy implementation.
- Retrospective: absolutely the right move. The later MCTS-first identity would not exist without early engine investment.

## Decision: Shift from single-run training to league / self-play / checkpoint ecosystems

- Evidence: `2139cd8`, `configs/v1_rl_vs_mcts.yaml`, `configs/stage3_selfplay.yaml`, PR `#27` / `d85c876`, `league/`, `analytics/tournament/`.
- Benefit gained: made agent comparison, not just policy training, a first-class concern. That broadened the repo from RL training into comparative AI experimentation.
- Tradeoffs or costs: introduced more orchestration complexity, more persistence/state management, and more legacy modules that are now partly out of sync with active `main`.
- Retrospective: strong move, though only partially completed in the active branch. It was a conceptual bridge from RL project to AI testbed.

## Decision: Treat run artifacts and telemetry as primary outputs

- Evidence: `analytics/logging/`, `analytics/tournament/arena_runner.py`, `docs/datasets.md`, `games.jsonl`, `snapshots.csv/parquet`, metrics and telemetry UIs from PR `#57`.
- Benefit gained: improved interpretability, reproducibility, and offline analysis. This also made it possible to use MCTS games as data for learned evaluators.
- Tradeoffs or costs: increased storage/output complexity and widened the documentation surface; some docs now lag behind the code.
- Retrospective: one of the repo’s strongest moves. It materially changed the repo into a research platform.

## Decision: Make browser-local MCTS a first-class deployment target

- Evidence: PR `#31` / `df5827b`, `browser_python/`, `frontend/src/store/blokusWorker.ts`, deploy docs, root README demo flow.
- Benefit gained: turned the system into a portable, low-cost, interactive demo and analysis tool. This is a big differentiator for the repo’s public story.
- Tradeoffs or costs: duplicated engine and MCTS code under `browser_python/`, increasing maintenance burden and risk of divergence.
- Retrospective: strong move for demonstration value and experimentation ergonomics, with a real long-term maintenance cost.

## Decision: Explicitly archive RL code instead of keeping the active branch hybrid

- Evidence: `cc106db`, root README note about `archive/rl-agents`, deletion of `training/`, `rl/`, and `envs/` from active `main`.
- Benefit gained: clarified the active repo’s purpose and removed a large amount of dead or distracting surface area.
- Tradeoffs or costs: current docs are only partially aligned; some files still reference deleted modules, and some legacy configs remain without active code to support them.
- Retrospective: correct decision. The active branch is more coherent because of it, but the cleanup is incomplete.

## Decision: Re-audit optimization assumptions empirically

- Evidence: `docs/cpu_bottleneck_audit.md`, `docs/profiler_baseline.md`, PR `#62` / `0974105`, `benchmarks/benchmark_mcts_settings.py`.
- Benefit gained: corrected a misleading “bitboard must be faster” assumption and prioritized the real bottlenecks: rollout cost, legality-path implementation details, and game-over checks.
- Tradeoffs or costs: exposed that some previous optimization claims had aged poorly under current code.
- Retrospective: very strong move. This is the kind of mid-project correction that raises engineering credibility rather than lowering it.

## Decision: Formalize MCTS improvement as staged measurement layers

- Evidence: profiler + tournament runner + baseline-analysis stack in PRs `#68`-`#70`, `reports/layer1_baseline_report.md`, `scripts/run_layer1_baseline.py`.
- Benefit gained: created an explicit research roadmap instead of one-off tuning runs. The repo can now justify future work using measured deficits.
- Tradeoffs or costs: more complexity in the analysis layer, and some parts of the workflow are still diagnostic rather than productionized.
- Retrospective: excellent move. It is one of the clearest signs that the repo is now an AI experimentation platform.

# 5. Performance and Simulation Optimization Story

The performance story has two distinct acts. The first act is “make legal move generation fast enough to matter.” The second act is “once move generation is no longer catastrophic, discover what actually dominates MCTS time.”

## The likely original simulation loop

The historical docs and early performance report strongly suggest the original engine relied on naive board scans, heavy `Position` object creation, repeated legality validation, and full move enumeration in the hot path. `docs/architecture/PERFORMANCE_OPTIMIZATION_RESULTS.md` records an early baseline of roughly 3 seconds per agent move, split into about 1.35 seconds for legal move generation and 1.71 seconds for move application. That is too slow for either meaningful RL throughput or meaningful tree search.

## First optimization wave: local code-path acceleration

The early performance report describes direct-grid access, cached piece positions, inline adjacency checking, and skipping redundant board-history copies. That reduced average move time from about 3 seconds to about 500 milliseconds. This work was important, but it was still largely local optimization inside the existing framing.

## Second optimization wave: architectural reframing of move generation

The much more consequential shift came with the M6 frontier/bitboard work in early December 2025. This was not just “micro-optimize Python.” It changed the search space itself:

- Frontier tracking restricted candidate generation to cells diagonally adjacent to the player’s pieces and not orthogonally adjacent.
- Bitboards represented occupancy and per-player presence as masks, creating the possibility of constant-time overlap and adjacency checks.
- Piece orientations and masks were precomputed.
- Extensive equivalence and invariant tests were added so optimization would not silently corrupt rules.

This is the clearest example of architectural reframing enabling performance. The code stopped asking “how do we make full-board scan faster?” and started asking “how do we represent the game so full-board scan is unnecessary?”

## What mattered most in practice

Three classes of changes stand out as materially important.

### 1. Candidate-space reduction

Frontier-based move generation was the single most important conceptual speedup. It reduced the number of candidate anchors dramatically, especially in mid and late game. This was not a local patch; it changed the shape of move generation.

### 2. Avoiding redundant work

The project repeatedly found and removed “hidden full recomputations”:

- duplicate move emission in frontier generation,
- redundant legality validation in `BlokusGame.make_move()`,
- repeated `list(Player)` allocations,
- defensive frontier copies,
- full move enumeration where only a boolean answer was needed,
- reinstantiating move generators instead of using a shared singleton.

These are smaller individually, but they matter a lot in aggregate because search magnifies repeated inefficiencies.

### 3. Correcting the bitboard implementation

By March 2026, the repo had enough profiling discipline to notice that its “optimized” bitboard legality path had become slower than the grid path. `docs/cpu_bottleneck_audit.md` shows frontier+bitboard taking roughly 2-3x the time of frontier+grid across representative stages before the March fix. The cause was not the bitboard idea itself. It was that `is_placement_legal_bitboard_coords()` rebuilt masks from coordinates in Python loops, defeating the whole point.

PR `#62` (`0974105`) corrected this by:

- using precomputed masks with `shift_mask_fast`,
- adding `BIT_TABLE` lookups,
- defaulting to grid-based legality until the fast path was fixed,
- adding early-exit `has_legal_moves()`,
- optimizing `Board.copy()` with `object.__new__`,
- introducing a shared `LegalMoveGenerator`.

This is a good example of performance work that is both local and architectural. The final patches are small enough to fit inside a few files, but they only make sense because the repo had already invested in the deeper representation changes.

## Where the bottleneck moved

The most interesting performance finding is that move generation stopped being the whole story. `docs/profiler_baseline.md` shows that, for the standard `MCTSAgent`, simulation/rollout time accounts for 99%+ of total iteration time across early and mid-game profiled states. Expansion, selection, backpropagation, and board copying became almost negligible by comparison.

That means the project’s optimization frontier moved:

- Early period: “make legal move generation and environment stepping not awful.”
- Later period: “make MCTS evaluation cheap enough that more than 1-2 iterations per second are possible.”

This shift is why the learned-evaluator work matters so much. The profiler baseline and the March `plan.md` both point to the same conclusion: replacing or truncating full rollouts could be transformative because the engine optimizations have already lowered the rest of the stack.

## Performance work that improved research velocity

Some performance-oriented changes had outsized value because they also accelerated experimentation:

- Deterministic time budgets and iteration caps in the arena harness made experiments comparable.
- Benchmark scripts for move generation, MCTS settings, and profiler baselines made optimization measurable.
- Structured run outputs (`games.jsonl`, `summary.json`, `snapshots.*`) made it easy to compare configurations offline.
- Early-exit legality checks reduced overhead in both gameplay and analytics pipelines.
- Shared move-generator infrastructure reduced setup cost across many experiments.

These changes matter because the repo’s current value is not just “runs faster.” It is “makes it easier to answer search questions quickly and repeatably.”

## What the latest evidence says

The current baseline characterization reveals that performance is still a research problem, not a solved one:

- Peak branching factor is 534 at turn 17, leaving only about 3.7 implied visits per child at a 2000-iteration budget.
- Overall utilization is only 11.0%, suggesting the search spreads thin.
- The simulation quality audit in `reports/layer1_baseline_report.md` reports a negative average delta versus heuristic-only rollouts.
- Q-value identity still changes heavily as the budget increases, indicating weak convergence under current settings.

So the optimization story is not “performance solved.” It is “the repo learned how to measure where performance matters, fixed the obvious engine bottlenecks, and is now ready for deeper search-quality work.”

# 6. Codebase Reframings That Clearly Helped

## Reframing: from training project to reusable engine + AI layers

- Old framing: the engine mainly existed to support RL environments and gameplay.
- New framing: the engine is the stable substrate underneath MCTS, analytics, arenas, browser execution, and data generation.
- Why this was better: it made engine correctness and performance reusable across multiple AI approaches instead of tying them to one training loop.
- Downstream benefits: MCTS agents, Pyodide deployment, arena benchmarking, telemetry features, and learned-evaluator pipelines all build on the same engine.

## Reframing: from “evaluate an agent” to “run reproducible tournaments”

- Old framing: evaluate a trained agent against simple baselines, largely through RL-oriented evaluation docs.
- New framing: configure four-seat experiments, deterministic seeds, seat policies, fair-time budgets, and statistical summaries through the arena harness.
- Why this was better: multiplayer Blokus is not well served by simplistic win-rate checks against a single baseline.
- Downstream benefits: fair-time MCTS tuning, multiseed aggregation, seat-bias analysis, TrueSkill integration, and the Layer 1 baseline program.

## Reframing: from transient gameplay to persistent telemetry and datasets

- Old framing: a game produces an outcome and maybe some training metrics.
- New framing: each game produces `games.jsonl`, per-step diagnostics, snapshot datasets, and frontend-inspectable traces.
- Why this was better: it connected gameplay, analysis, benchmarking, and model training into one loop.
- Downstream benefits: move-delta dashboards, MCTS diagnostics panels, pairwise dataset generation, and learned evaluation workflows.

## Reframing: from backend game service to local browser compute

- Old framing: Python backend and frontend talk over API/websocket; compute lives server-side.
- New framing: package Python engine and AI into a browser worker and run MCTS locally through Pyodide.
- Why this was better: lowered deployment cost, increased portability, and made the project easier to demonstrate interactively.
- Downstream benefits: explain-this-move UX, recruiter/demo flows, and an identity closer to “interactive AI lab” than “backend training stack.”

## Reframing: from hybrid RL/MCTS active branch to scoped active branch plus archive branch

- Old framing: keep RL training, env wrappers, league code, MCTS, dashboards, and deployment surfaces all active together.
- New framing: archive RL to `archive/rl-agents`, keep the active branch centered on engine, MCTS, analytics, and gameplay/deploy surfaces.
- Why this was better: reduced conceptual noise and aligned active work with the project’s real momentum.
- Downstream benefits: cleaner active branch, more obvious roadmap around search/benchmarking.
- Remaining cost: documentation and some legacy modules still assume the old hybrid world.

## Reframing: from ad hoc optimization to layered measurement

- Old framing: benchmark individual bottlenecks or tune parameters opportunistically.
- New framing: use profiler baselines, fairness audits, MCTS settings sweeps, and Layer 1 characterization as staged diagnostics.
- Why this was better: gives future work a defensible sequence and keeps improvements evidence-driven.
- Downstream benefits: explicit next steps around action reduction, evaluation replacement, convergence, and tournament design correction.

# 7. Current State of the Repo

Today, the repository is best understood as a combination of three things:

1. an MCTS project,
2. a Blokus AI research sandbox,
3. a benchmarking and analysis platform built on a mature simulation engine.

It is no longer best understood as an active RL training repository, even though RL history remains visible in docs, configs, and some leftover modules.

## What feels mature

- The core game engine in `engine/` looks mature enough to support multiple layers of analysis and gameplay.
- The frontier/move-generation stack has strong correctness scaffolding through dedicated tests.
- The fast gameplay-oriented MCTS path is integrated across gameplay, arena, browser execution, and analysis UI.
- The arena runner and tuning stack are substantial and support deterministic experiments, seed control, seat policies, and structured outputs.
- The frontend analysis layer is unusually rich for a personal/research repo: telemetry panels, move-delta views, MCTS diagnostics, strategy-mix summaries, and replay/history flows are all present.

## What feels experimental

- The full `MCTSAgent` is still heavily rollout-bound and appears to need deeper algorithmic help.
- The learned evaluator pipeline is present end to end, but the active repo does not yet show a stable, validated production model artifact beyond scaffolding and registration.
- The Layer 1 report suggests the current search still has weak utilization and convergence characteristics.
- The interplay between `MCTSAgent`, `FastMCTSAgent`, and gameplay adapters still looks like an active experimentation surface rather than a unified final architecture.

## What looks inconsistent with the current direction

The biggest inconsistency is documentation and legacy structure, not the main code path.

- The root `README.md` still opens as an RL project even though the active code is MCTS-centered.
- `docs/training-architecture.md`, `docs/training-history.md`, `docs/evaluation.md`, and `docs/rl_current_state.md` refer to `training/`, `envs/`, and RL scripts that no longer exist on active `main`.
- `docs/arena.md`, `docs/datasets.md`, and `docs/arena_status.md` still reference deleted `scripts/train_winprob_v1.py` and `scripts/train_winprob_v2.py`, while the current repo has `scripts/train_eval_model.py`.
- `league/league.py` still imports `envs.blokus_v0`, even though `envs/` is absent from active `main`.

These are not cosmetic issues. They show that the repo’s conceptual cleanup happened faster than its documentation cleanup.

## Legacy RL-era structures that still remain

- `config/agents/ppo_*.yaml` still exists.
- Stage 2 / Stage 3 RL/self-play configs still exist in `configs/`.
- Training and RL docs remain in `docs/`.
- Historical logs, checkpoints, and benchmark outputs from RL-era experimentation still appear in checked-in artifacts.
- Some league code still assumes the archived environment stack.

## Technical and conceptual debt

The main debts are:

- documentation drift,
- duplicated Python runtime code under `browser_python/`,
- split MCTS implementations with overlapping but not identical responsibilities,
- partially orphaned legacy league/RL artifacts,
- and a still-unfinished transition from heuristic rollouts to stronger learned or truncated evaluation.

The repository’s strongest identity is therefore:

> a Blokus AI experimentation platform centered on MCTS, fast simulation, analysis tooling, and comparative evaluation, with visible but no longer central RL roots.

# 8. Recommended Canonical Milestone Outline

## Chapter 1: Build a Blokus engine and make it trainable

The project started by turning Blokus into a serious programmable environment: rules-complete engine, baseline agents, training wrappers, and a research UI. The original goal was not just to play Blokus, but to create a space where reinforcement learning could be attempted on a difficult multiplayer board game.

Why it matters: this establishes ambition and technical breadth. The repo was never only a UI demo or only an algorithm experiment.

## Chapter 2: Discover that simulation speed is the real bottleneck

Very early, the project hit the real constraint: legal move generation and environment stepping were too expensive. That led to a serious engine optimization phase around frontier-based move generation, bitboards, caching, and correctness testing.

Why it matters: this is where the project became technically interesting. It stopped being a generic RL scaffold and became an engine/performance problem worth solving in its own right.

## Chapter 3: Move from one agent to an ecosystem of agents

The project then evolved from training a single PPO policy toward organizing self-play leagues, Elo tracking, checkpoint opponents, and richer baseline matchups. Evaluation stopped meaning “beat random” and started meaning “compare strong agents fairly and repeatedly.”

Why it matters: this is the bridge from RL project to AI experimentation platform.

## Chapter 4: Turn MCTS into the project’s public face

Deployment work and the Pyodide/WebWorker migration changed the repo’s outward identity. The engine and AI could now run locally in the browser, making MCTS gameplay, analysis, and explanation the most visible feature of the system.

Why it matters: this is the moment the project became easily demonstrable and clearly differentiated.

## Chapter 5: Instrument everything and treat games as data

The repo added arenas, structured logs, telemetry, per-move diagnostics, advanced metrics, snapshot datasets, and analysis dashboards. Games became reusable data for both human interpretation and downstream modeling.

Why it matters: this is what makes the project feel like a research lab instead of a one-off algorithm demo.

## Chapter 6: Use learned evaluation to support search, not replace it

Rather than doubling down on end-to-end RL as the sole path, the project began using ML in a narrower, more pragmatic role: feature extraction, win-probability models, and learned leaf evaluation for MCTS.

Why it matters: this is the clearest articulation of the repo’s mature identity. ML becomes a tool inside the search stack, not the only objective.

## Chapter 7: Intentionally archive the RL phase and simplify the active repo

The March 6 archival commit moved RL agents and training code to a separate branch, making the active branch explicitly about engine, MCTS, analysis, and benchmarking.

Why it matters: this turns an emergent trend into a deliberate project story.

## Chapter 8: Formalize MCTS improvement as a staged research program

Recent profiling, fairness audits, tuning infrastructure, and baseline characterization reports show the project entering a new phase: structured search research with named layers, measurable deficits, and explicit next-step hypotheses.

Why it matters: this is the strongest honest story to tell publicly today. The repo is no longer “I tried RL on Blokus.” It is “I built a Blokus AI lab centered on search, simulation performance, and comparative evaluation.”

# 9. Key Supporting Evidence Appendix

## Key commits and PRs

| Evidence | Why It Matters |
|---|---|
| `d604462` | Establishes the project as a combined engine/frontend/training repo from the start. |
| `3d62e8e` | Makes MaskablePPO and RL training a concrete active concern, not just an aspiration. |
| PR `#20` / `1b78cfe` | Major engine/move-generation optimization milestone. |
| PR `#22` / `05c60fc` | Stabilizes RL environment semantics and game-result/logging path. |
| `2139cd8` | Introduces self-play training pipeline and Elo league. |
| PR `#27` / `d85c876` | Adds Stage 3 self-play league, analytics, metrics, and history/analysis surfaces. |
| PR `#31` / `df5827b` | Moves engine and AI into Pyodide WebWorker and adds browser-side mirror. |
| PR `#52` / `2a10ea7` | Creates arena runner, dataset features, and learned evaluator integration. |
| PR `#54` / `fb65413` | Adds fair-time tuning tournaments and statistical rigor. |
| `cc106db` | Explicitly archives RL to a separate branch and re-scopes active `main`. |
| PR `#62` / `0974105` | Corrects performance regressions with audited, measured changes. |
| PR `#67` / `4ad4f53` | Adds end-to-end eval-model pipeline. |
| PRs `#68`-`#70` / `f35efee`, `a38b523`, `baeaddf` | Formalize layered baseline measurement and characterization. |

## Current files that best reveal the repo’s present identity

| File / Folder | Signal |
|---|---|
| `engine/` | Mature core simulation engine. |
| `agents/fast_mcts_agent.py` | Gameplay-oriented MCTS implementation optimized for real-time use. |
| `mcts/mcts_agent.py` | Full search implementation with learned-evaluator hooks and diagnostics. |
| `analytics/tournament/arena_runner.py` | Strongest evidence that the repo is now an experimentation harness. |
| `analytics/winprob/features.py` | Shows ML is now framed as evaluator support and analysis, not only end-to-end RL. |
| `scripts/arena_tuning.py` | Encodes equal-time, comparative MCTS experimentation. |
| `scripts/profile_mcts.py` | Encodes explicit search-phase profiling. |
| `scripts/run_layer1_baseline.py` | Encodes staged baseline characterization as a formal workflow. |
| `frontend/src/store/blokusWorker.ts` | Shows browser-local Python execution is a core active path. |
| `browser_python/` | Reveals the Pyodide deployment mirror and its maintenance tradeoff. |

## Documents that capture the shift in intent

| Document | What It Reveals |
|---|---|
| `docs/architecture/M1-Markdown.md` | Early RL-centric framing with MCTS as one tool among many. |
| `docs/rl_current_state.md` | Mature RL pipeline description before archival. |
| `docs/arena.md` | Search/tournament/dataset framing. |
| `docs/profiler_baseline.md` | Current bottleneck is rollout simulation, not generic engine cost. |
| `docs/cpu_bottleneck_audit.md` | Optimization culture became evidence-driven and self-correcting. |
| `docs/adaptive_benchmark_report.md` | The repo now evaluates MCTS variants empirically across budgets. |
| `reports/layer1_baseline_report.md` | Search analysis is now organized as a staged research program. |

## Artifact evidence

| Artifact | Why It Matters |
|---|---|
| `benchmarks/results/stage3_env_scan_20260204_222556.json` | Shows environment stepping dominated inference cost in Stage 3 scans. |
| `benchmarks/results/selfplay_league_bench_20260204_*.json` | Captures throughput deltas across Stage 2 / Stage 3 configurations. |
| `arena_runs/` | Demonstrates that tournament and tuning outputs are treated as durable research artifacts. |
| `baseline_runs/` | Demonstrates the newer “layered measurement” workflow. |

## Evidence of active inconsistencies

| Evidence | Why It Matters |
|---|---|
| `README.md` still opens as an RL project | Documentation has not fully caught up to repo identity. |
| `docs/training-architecture.md` and `docs/evaluation.md` reference removed `training/` and `envs/` code | RL archival was intentional but incomplete from a docs perspective. |
| `docs/arena.md` and `docs/datasets.md` reference deleted `train_winprob_v1/v2` scripts | Search/evaluator docs also need cleanup to match the current pipeline. |
| `league/league.py` imports `envs.blokus_v0` while `envs/` is absent | Some RL/self-play league infrastructure is now legacy in active `main`. |
| Unmerged commit `86b0ec7` rewrites the README around MCTS | Shows the project direction was recognized, but the documentation correction did not land on `main`. |

# 10. Open Questions / Uncertain Interpretations

## Exactly when did the RL-to-MCTS pivot become intentional?

- What is uncertain: whether the project’s shift was deliberate by January/February 2026, or whether it only became explicit with the March 6 archival commit.
- Evidence: Stage 3, arena, and Pyodide work strongly emphasize MCTS before RL was archived; `cc106db` makes the intent explicit.
- Most likely interpretation: the pivot was emergent through February 2026 and became explicit in early March 2026.
- What would clarify it: merged PR descriptions or planning notes from late February discussing scope decisions directly.

## How successful was the RL phase empirically?

- What is uncertain: the repo preserves configs, logs, and some checkpoint artifacts from RL runs, but active `main` no longer contains the runnable RL stack.
- Evidence: `configs/v1_rl_vs_mcts.yaml`, Stage 3 configs, logs under `logs/`, and the archived-branch note in `README.md`.
- Most likely interpretation: RL progressed to meaningful engineering maturity, including checkpoint leagues and multi-env runs, but the active repo no longer treats it as the primary research frontier.
- What would clarify it: reviewing the `archive/rl-agents` branch directly or finding a dedicated retrospective on RL training outcomes.

## Did the early bitboard architecture deliver its intended long-term benefit?

- What is uncertain: the December 2025 docs argue frontier+bitboard is a major speedup, but the March 2026 audit found the then-current bitboard path slower than grid.
- Evidence: `docs/engine/move-generation-optimization.md`, `docs/architecture/PERFORMANCE_OPTIMIZATION_RESULTS.md`, and later `docs/cpu_bottleneck_audit.md`.
- Most likely interpretation: the architectural idea was sound, but the intermediate implementation regressed until the March re-audit and fix.
- What would clarify it: benchmark snapshots from immediately after M6 versus immediately before PR `#62`.

## Is the current full MCTS agent actually stronger than its rollout policy?

- What is uncertain: the Layer 1 report shows a negative average score delta for full MCTS versus heuristic-only games, but that diagnostic is not the same as a clean head-to-head proof of inferiority.
- Evidence: `reports/layer1_baseline_report.md` and `analytics/baseline/simulation_quality.py`.
- Most likely interpretation: the current search budget/evaluation combination is not yet extracting clear value from tree search, especially at high branching-factor turns.
- What would clarify it: controlled same-budget head-to-head experiments between rollout-only and full-search variants under the current post-PR-62 code.

## How much of the current codebase should still count as “active” versus “historical residue”?

- What is uncertain: some legacy files remain in active `main` even though they are not consistent with current runtime surfaces.
- Evidence: stale RL docs, `league/` imports against removed `envs/`, and outdated script references in current docs.
- Most likely interpretation: the active center of the repo is engine + MCTS + analytics + frontend analysis, while some league/RL-era files now function more as historical residue than supported entrypoints.
- What would clarify it: a deliberate cleanup pass that marks supported entrypoints and archives or removes the rest.
