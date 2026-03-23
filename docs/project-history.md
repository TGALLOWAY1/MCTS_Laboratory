# Condensed Blokus Project History

## Overview

This project started as a Blokus reinforcement learning environment with a rules engine, Gym/PettingZoo-style wrappers, PPO training, a research UI, and baseline agents including MCTS.

Over time, the project's center of gravity shifted away from "train an RL agent" and toward building a fast, inspectable Blokus AI experimentation platform centered on MCTS, simulation performance, benchmarking, and comparative evaluation.

The most important pattern in the repo history is that engine quality and simulation speed became more valuable than the original RL framing. Once move generation, legality checks, profiling, and game throughput became major priorities, the engine evolved into the repo's core asset. Then the addition of league play, analytics, arena tooling, browser-side MCTS, and learned-evaluator infrastructure pushed the project further into being a strategy testbed rather than a pure RL project.

By March 2026, that shift appears deliberate rather than incidental. The clearest evidence is the archival of RL agents to a separate branch and the simplification of the active repo around MCTS-oriented work.

## Key Milestones

| Milestone | Approx. Date | Why It Mattered |
| --- | --- | --- |
| RL-first foundation | Nov 30, 2025 | The initial repo established Blokus as a trainable RL environment with engine, agents, frontend, and training stack. This set the project's original identity. |
| RL infrastructure became credible | Early Dec 2025 | Rules correctness, smoke-test stability, vectorized training support, and canonical results made the RL side more serious, but also exposed how critical engine correctness and throughput were. |
| M6 engine optimization reframed the repo | Dec 4, 2025 | Frontier-based move generation, bitboards, equivalence tests, and dedicated benchmarks made simulation throughput a first-class concern. This was the point where the engine became the real technical centerpiece. |
| Shift from single-agent training to league and self-play evaluation | Jan-Feb 2026 | The self-play pipeline, Elo league, and Stage 3 configs shifted the project from "train one policy" toward "compare agents and checkpoints in an ecosystem." |
| Analytics and tournament tooling made it a testbed | Feb 2026 | Logging, metrics, tournament modules, profiling scripts, and analysis/history pages changed the repo from a training project into an experimentation platform. |
| Browser-side MCTS became a public-facing identity | Feb 24, 2026 | The Pyodide/WebWorker migration made local MCTS playable and inspectable in the browser, strengthening the repo's identity as an interactive search-based AI system rather than a backend RL workflow. |
| Arena, datasets, and learned evaluator pushed it into research tooling | Mar 2, 2026 | Arena runs, win-probability features, dataset generation, and learned evaluator support turned MCTS games into reusable research data and gave the repo a stronger experimentation loop. |
| RL archival made the pivot explicit | Mar 6, 2026 | Moving RL agents off the active branch clarified that the mainline repo was now centered on MCTS and strategy evaluation. |
| Profiling re-audit corrected optimization assumptions | Mar 21, 2026 | The project revisited its own performance assumptions, found that some "optimized" paths were actually slower, and re-established empirical profiling as the basis for future work. |

## The Short Story

The cleanest honest story of the project is:

1. Started as a Blokus RL environment. The initial goal was to make Blokus trainable and observable with PPO-style RL plus a research UI.
2. Engine correctness and simulation speed became the real bottleneck. Performance work around move generation, legality, and board representation turned the engine into the repo's most important asset.
3. The project broadened from training to evaluation. League play, tournament infrastructure, analytics, and benchmarking shifted the focus toward comparing strategies rather than training a single agent.
4. MCTS became the practical center of gravity. Browser-side MCTS, diagnostics, arena tooling, and learned-evaluator work made search the most compelling active direction.
5. The repo is now best understood as an AI testbed for Blokus. It is no longer best described as primarily an RL project. Its strongest identity is a platform for fast simulation, MCTS experimentation, analytics, and comparative strategy evaluation.

## Most Important Technical Decisions

### Prioritize Engine Speed as a Strategic Concern

This was the turning point that made everything else possible. Frontier-based move generation and bitboard-style work were not just optimizations; they were a reframing of the whole project around simulation throughput.

### Shift from "One Trained Policy" to "Reproducible Comparison"

The addition of league play, tournament runners, and analytics infrastructure made the repo useful for comparing approaches, not just developing one.

### Treat Gameplay Data as Research Data

The analytics dashboard, telemetry, arena outputs, and dataset generation gave the repo a reusable experimentation loop.

### Explicitly Archive RL from the Active Branch

This clarified the story and reduced conceptual sprawl. The repo stopped trying to be two different things at once.

### Re-profile Instead of Assuming Old Optimizations Still Held

The March audit is important because it showed the project was willing to invalidate its own assumptions and optimize from measured evidence.

## Performance Story, Condensed

The repo's performance story has two chapters:

First: make legal move generation and environment stepping fast enough to matter. Early work reduced extremely slow agent turns through direct-grid access, cached piece positions, frontier-based generation, and representation changes.

Second: once engine overhead improved, the real bottleneck became MCTS rollout and simulation time, which now dominates total iteration cost. That means the next frontier is not just engine optimization, but improving how search evaluates states.

That is why learned evaluators and search-quality measurement now matter so much.

## Current Identity of the Repo

Today, this project is best described as:

> A Blokus AI experimentation platform centered on fast simulation, MCTS, analytics, benchmarking, and comparative strategy evaluation.

It still has RL roots, and some legacy RL structures or assumptions likely remain, but the strongest current identity is not "Blokus RL project." It is a search- and evaluation-oriented AI testbed.

## Portfolio-Friendly Version

I originally built this project as a Blokus reinforcement learning environment with PPO training, a research UI, and baseline agents. As development progressed, engine correctness and simulation throughput became the real challenge, so I invested heavily in move-generation optimization, legality-path improvements, and benchmarking. That work made the engine strong enough to support a broader experimentation layer. From there, the project evolved toward MCTS, league-style evaluation, analytics dashboards, arena tooling, browser-side search, and learned-evaluator experiments. Today, the repo is best understood as a Blokus AI testbed for comparing strategies, measuring search behavior, and improving fast simulation-driven decision systems.
