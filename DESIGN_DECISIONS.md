# Design Decisions — GA Weight Evolution & Neural Network

## Architecture: Island-Model GA with Ring Topology

**Decision:** Use 7 islands connected in a ring rather than a single population.

**Why:** A single population in a 10-dimensional space risks premature convergence — one dominant genotype can quickly take over. The island model partitions individuals across 7 sub-populations that evolve independently. Every N generations, the best individuals from each island migrate clockwise to the next:

```
Island 0 → Island 1 → Island 2 → Island 3 → Island 4 → Island 5 → Island 6 → Island 0
```

This preserves diversity (each island explores different weight regions) while still sharing good genes around the ring over time.

## Agent: EnhancedHeuristicAgent (10 features)

**Decision:** Create a new `EnhancedHeuristicAgent` with 10 weighted features rather than modifying the existing 4-feature `HeuristicAgent`.

**Why:** The original agent has no opponent awareness at all — it only evaluates its own position quality. Adding 6 new features covering opponent interaction, frontier management, and piece economy gives the GA far more material to work with. Keeping it as a separate agent avoids modifying existing code.

### Feature Table

| # | Feature | Default | Evolved (v2) | What it measures |
|---|---------|---------|-------------|-----------------|
| 1 | `piece_size` | 1.0 | **4.19** | Prefer placing larger pieces |
| 2 | `corner_creation` | 2.0 | **0.48** | New safe corners created by this move |
| 3 | `edge_avoidance` | -1.5 | **-2.10** | Squares placed within 2 cells of board edge |
| 4 | `center_preference` | 0.5 | **4.26** | Normalized distance from board center |
| 5 | `opponent_blocking` | 1.5 | **-0.37** | Opponent frontier cells we occupy |
| 6 | `corners_killed` | -1.0 | **+1.71** | Our own frontier cells destroyed by this move |
| 7 | `opponent_proximity` | -0.5 | **-2.00** | Chebyshev distance to nearest opponent pieces |
| 8 | `open_space` | 0.5 | **0.44** | Empty cells within Manhattan distance 2 |
| 9 | `piece_versatility` | -0.3 | **-5.00** | Orientation count × early-game factor |
| 10 | `blocking_risk` | -0.5 | **+1.51** | New corners that are edge-adjacent to opponents |

### Feature Design Rationale

**Original 4 (features 1-4):** Evaluate your own position quality — piece economy, expansion potential, spatial positioning. These match the existing `HeuristicAgent` exactly so results are comparable.

**Opponent awareness (features 5, 7):** `opponent_blocking` directly measures how much a move hurts opponents by occupying their frontier cells. `opponent_proximity` controls aggression — lower values mean playing closer to enemies.

**Frontier management (features 6, 10):** `corners_killed` captures the cost of consuming your own frontier when placing. `blocking_risk` detects corners that are edge-adjacent to opponent pieces.

**Resource management (features 8, 9):** `open_space` measures local breathing room to avoid self-trapping. `piece_versatility` penalizes using high-orientation pieces (like pentomino L with 8 orientations) early when space is abundant.

## Training Runs

### Run 1: Short (10 generations, sequential)

- 7 islands × 4 individuals = 28 total, 4 games/eval
- Migration every 3 gens, 1 migrant, sigma 0.5→0.1
- Seed: 42, Runtime: ~40 min
- **Best fitness: 96.8** — weights barely moved from defaults

### Run 2: Long (200 generations, 8-worker parallel)

- 7 islands × 6 individuals = 42 total, 6 games/eval
- Migration every 5 gens, 2 migrants, sigma **1.0→0.05** (wider exploration)
- Seed: 99, Runtime: ~57 min (early stopped at gen 28)
- **Best fitness: 108.3** — radically different weight profile

**Key change:** Adding `multiprocessing.Pool` for parallel fitness evaluation gave ~16x speedup per generation (8 workers on 10 CPU cores). This made 200 generations feasible.

## Key Findings: The GA Overturned Human Intuition

Three weights **completely flipped sign** from the hand-tuned defaults:

1. **`corners_killed`: -1.0 → +1.71** — We assumed consuming your own frontier was a cost. The GA discovered it's actually *efficient space usage*. Playing into your own frontier means you're consolidating territory, not wasting it.

2. **`blocking_risk`: -0.5 → +1.51** — We assumed corners near opponents were fragile. The GA discovered they're *aggressive outposts*. Expanding toward opponents creates territorial pressure.

3. **`opponent_blocking`: 1.5 → -0.37** — We assumed blocking opponents was valuable. The GA essentially says "don't waste moves blocking — focus on your own expansion."

Other notable shifts:

4. **`piece_size`: 1.0 → 4.19** — Play the biggest pieces you can, as fast as you can.

5. **`center_preference`: 0.5 → 4.26** — Rush the center hard.

6. **`piece_versatility`: -0.3 → -5.0** — Hit the bound. NEVER waste flexible pieces early. Save them for the endgame crunch.

7. **`corner_creation`: 2.0 → 0.48** — Raw corner count barely matters. What matters is *which* corners — the aggressive ones near opponents (blocking_risk = +1.51).

**The emergent strategy:** Play big, rush center, get close to opponents, create aggressive outpost corners near them, and save flexible pieces at all costs. This is fundamentally more aggressive than the hand-tuned defaults.

## Arena Results

### Run 1 Results (v1 weights, 10-gen training, 40 games)

| Agent | Wins | Win Rate | Avg Score |
|-------|------|----------|-----------|
| `heuristic_default` (4 features, hand-tuned) | 15 | 37.5% | 86.7 |
| `enhanced_default` (10 features, hand-tuned) | 13 | 32.5% | 82.6 |
| `enhanced_evolved` (10 features, v1 weights) | 12 | 30.0% | 84.0 |
| `random` | 0 | 0.0% | 59.6 |

**Result: Lost.** 10 generations was insufficient — weights barely diverged from defaults.

### Run 2 Results (v2 weights, 28-gen training, 100 games)

| Agent | Wins | Win Rate | Avg Score |
|-------|------|----------|-----------|
| **`enhanced_evolved`** (10 features, v2 weights) | **68** | **68.0%** | **94.5** |
| `enhanced_default` (10 features, hand-tuned) | 18 | 18.0% | 82.3 |
| `heuristic_default` (4 features, hand-tuned) | 14 | 14.0% | 84.2 |
| `random` | 0 | 0.0% | 60.4 |

**Result: Dominant.** 68% win rate, +10 points avg score over all opponents.

### What Changed Between Runs

The v1 failure and v2 success came down to three factors:

1. **Wider initial exploration** — sigma 1.0 (v2) vs 0.5 (v1). The v1 run was trapped near the default weights. Sigma 1.0 let v2 explore radically different strategies including the sign-flipped weights.

2. **More generations** — 28 effective gens (v2) vs 10 (v1). Even though v2 had 200 available, it converged at 28 — but those extra 18 generations past v1's limit were where the breakthrough happened (gen 16-18).

3. **More reliable fitness** — 6 games/eval (v2) vs 4 (v1). Reduced noise meant the GA could distinguish between genuinely better strategies vs lucky outcomes.

### Run 3 Results: vs FastMCTS (v2 weights, 40 games)

Benchmark against the repo's optimized `FastMCTSAgent` at 500 iterations with 0.5s time limit.

**Important: MCTS variant matters.** The repo has two MCTS implementations:
- `MCTSAgent` (`mcts/mcts_agent.py`) — research/analysis version with transposition tables, progressive widening, etc. Very slow (~4.7 min/game at 250 iterations).
- `FastMCTSAgent` (`agents/fast_mcts_agent.py`) — gameplay-optimized version with no board copying, cached legal moves, minimal allocation. ~3s/game at 500 iterations.

We benchmark against `FastMCTSAgent` as this is what the repo uses for tournaments (`run_tournament.py`).

| Agent | Wins | Win Rate | Avg Score |
|-------|------|----------|-----------|
| **`enhanced_evolved`** (10 features, v2 weights) | **24** | **60.0%** | **96.6** |
| `heuristic_default` (4 features, hand-tuned) | 13 | 32.5% | 88.1 |
| `fast_mcts_500` (FastMCTSAgent, 500 iter) | 3 | 7.5% | 75.9 |
| `random` | 0 | 0.0% | 60.5 |

**Result: The GA-evolved heuristic beat MCTS 8-to-1.**

A zero-lookahead agent with 10 evolved features defeated an agent that searches 500 iterations into the game tree. Three factors explain this:

1. **Blokus's branching factor (~80-500 legal moves) makes shallow search nearly useless.** 500 iterations across hundreds of branches means each branch is visited 1-2 times at most.
2. **Random rollouts are uninformative in Blokus.** Unlike Go, random piece placement produces meaningless games, so MCTS's value estimates are extremely noisy.
3. **The evolved weights encode distilled strategic knowledge** — "play big, rush center, create aggressive outposts, save flexible pieces" — that MCTS must rediscover from scratch every move via random rollouts.

This validates that good features + linear combination can beat tree search when the search quality is poor. Plugging the evolved weights into MCTS as a rollout policy would combine both strengths.

## Technical Note: Arena Performance

The full arena system (`arena.py`) was too slow for our comparison — it ran for 48 minutes on 100 games without completing due to telemetry, board snapshots, and rating overhead. We built `quick_arena.py`, a lightweight game runner with no overhead, which completes 40 heuristic-only games in ~47s or 40 games with FastMCTS in ~112s.

## GA Operators

| Operator | Choice | Why |
|----------|--------|-----|
| Selection | Tournament (k=3) | Competitive pressure without excessive greediness |
| Crossover | BLX-alpha (α=0.5) | Can explore outside parent bounds, better than uniform for continuous spaces |
| Mutation | Gaussian, sigma 1.0→0.05 | Wide initial exploration, fine late-stage refinement |
| Elitism | Top 2 per island | Prevents losing the best solution |
| Migration | Ring, 2 migrants/5 gens | Balances isolation with information sharing |
| Parallelism | multiprocessing.Pool (8 workers) | ~16x speedup per generation |



## Future Work

Neural network training and SAE feature extraction are in progress — see `NN.md` for architecture decisions and training details.
