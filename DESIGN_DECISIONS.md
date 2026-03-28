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

---

## Neural Network: Architecture and Training

### Why a Neural Network?

The GA-evolved heuristic agent uses 10 hand-coded features combined linearly. This has two limitations:

1. **Feature ceiling** — we can only evaluate what we thought to measure. The NN learns its own spatial features directly from the 20×20 board, discovering patterns we'd never hand-code.
2. **No lookahead** — the heuristic evaluates one move at a time. Once trained, the NN's value head can plug into MCTS to replace random rollouts, making MCTS dramatically faster and stronger (the AlphaZero approach).

### Training Data Generation

**Decision:** Generate training data from self-play between our existing agents, not from MCTS games.

**Why:** MCTS games would produce higher-quality data but take ~2.5 minutes per game (250 iterations × random rollouts). Heuristic games take ~0.5s per game — 300x faster. We can generate 5,000 games in ~36 minutes vs ~9 days for MCTS. The NN can learn from imperfect data; self-play RL (phase 2) will improve quality later.

**Agent mix:** Games are played between randomly selected agents from:
- GA-evolved `EnhancedHeuristicAgent` (2× weight in pool — strongest agent, generates best data)
- Default `HeuristicAgent`
- Default `EnhancedHeuristicAgent` (10 features, hand-tuned weights)
- `RandomAgent`

**Why mixed opponents?** Diversity matters more than quality for supervised pre-training. Games between identical agents produce narrow, repetitive data. Mixing strong and weak agents creates varied board positions — the NN sees winning positions, losing positions, and everything in between.

**What we record at every turn:**
- `board_grid` — raw 20×20 int8 array (0=empty, 1-4=player)
- `current_player` — whose turn it is (1-4)
- `pieces_used` — 4×21 boolean mask of which pieces each player has placed
- `move_count` — ply number (for game phase estimation)
- `move_played` — (piece_id, orientation, anchor_row, anchor_col) tuple
- `final_scores` — end-of-game scores for all 4 players (backfilled as labels)

**Dataset produced:** 5,000 games → 337,914 board states, 4.9 MB compressed (.npz format). Average 67.6 states per game.

### Input Representation

**Decision:** Encode the board as a multi-channel 2D image (like AlphaGo) plus a separate scalar vector for non-spatial features.

**Spatial input — 9 channels × 20×20:**

| Channel | What it encodes |
|---------|----------------|
| 0 | Current player's stones (binary) |
| 1-3 | Each opponent's stones (binary, rotated so current player is always channel 0) |
| 4 | Empty cells (binary) |
| 5 | Current player's frontier (diagonal-adjacent, not edge-adjacent) |
| 6-8 | Each opponent's frontier |

**Why rotate player order?** The NN should learn "what should I do?" regardless of whether it's Player 1 or Player 4. Rotating so the current player is always channel 0 makes the NN color-agnostic — it learns one strategy that works from any seat.

**Why include frontiers?** Frontier cells are where a player CAN legally start a new piece. They're the most strategically important cells on the board. Computing them from the raw grid is possible (the NN could learn it from channels 0-4) but expensive — it would need to learn the Blokus adjacency rules from data. Pre-computing frontiers gives the NN this critical information for free.

**Scalar input — 85 features:**
- 4×21 = 84 binary values: which pieces each player has used (rotated, current player first)
- 1 float: game phase (move_count / 100, clamped to [0,1])

**Why not broadcast scalars as constant spatial planes?** That would add 85 channels of redundant 20×20 data. Instead, scalar features merge with spatial features at the fully-connected layer after CNN processing.

### Network Architecture

**Decision:** Small ResNet with two output heads (value + policy).

```
Spatial input (9, 20, 20)
    │
    Conv2d(9→64, 3×3, padding=1) + BatchNorm + ReLU
    │
    [ResBlock(64)] × 4
    │
    Shared features (64, 20, 20)
    │
    ├── Value Head:
    │     GlobalAvgPool → (64,)
    │     Concat scalar input → (149,)
    │     Linear(149→64) + ReLU
    │     Linear(64→1) + Sigmoid
    │     Output: predicted normalized score for current player
    │
    └── Policy Head:
          For each candidate move:
            - Average-pool spatial features at the move's cells → (64,)
            - Concat: piece_id one-hot (21) + orientation one-hot (8) + anchor (2)
            - MLP: Linear(95→64) + ReLU + Linear(64→1)
          Softmax over all candidate moves
          Output: probability distribution over legal moves
```

**~200-300k parameters.** Small enough to train on CPU in under an hour.

**Why ResBlocks?** Residual connections let the network learn "corrections" to the identity — each block adds incremental pattern detection. 4 blocks with 3×3 kernels gives an effective receptive field of ~11×11, covering over half the board from any position.

**Why a move-scoring policy head (not a fixed output vector)?** Blokus has ~500 legal moves per turn drawn from a combinatorial space of 21 pieces × 8 orientations × 400 positions. A fixed output of 67,200 logits is wasteful — most are always illegal. Instead, the policy head scores each legal move individually using the spatial features at that move's location. This handles variable action spaces naturally and generalizes across board positions.

### Training Approach

**Phase 1: Supervised pre-training (imitation learning)**

The NN learns to imitate the agents that generated the data:

- **Value loss** — MSE between predicted and actual normalized final score for the current player. The NN learns "who's winning from this position?"
- **Policy loss** — Cross-entropy over candidate moves. For each state, score the move that was actually played (positive) against K=15 random move tuples (negatives). The NN learns "which move would the agent play here?"
- **Combined loss** — `value_weight × value_loss + policy_weight × policy_loss`

**Why not just value or just policy?**
- Value-only: the NN can evaluate positions but can't suggest moves (useless standalone, only useful in MCTS)
- Policy-only: the NN can suggest moves but can't evaluate positions (useless for MCTS integration)
- Both: works standalone AND plugs into MCTS

**Phase 2: Self-play reinforcement learning (future work)**

Once the supervised NN is decent:
1. NN + MCTS plays games against itself
2. Record positions, MCTS move probabilities, and outcomes
3. Re-train the NN on this higher-quality data
4. Repeat — each cycle produces better data and a better NN

This is the AlphaZero loop. The supervised NN from phase 1 gives a warm start so that self-play games are meaningful from round 1 (instead of random vs random garbage).

### Integration Path

The trained NN can be used in three ways:

1. **Standalone agent** — `NNAgent.select_action()` uses the policy head to pick moves. No search, instant evaluation.
2. **MCTS value estimator** — replace MCTS's random rollouts with the NN value head. Instead of simulating 60 random moves, ask the NN "who's winning?" in one forward pass. This is the high-value target.
3. **SAE feature extraction** — train a sparse autoencoder on the NN's hidden layer activations to discover interpretable features, then feed those features into the GA for optimized linear combination. The NN discovers nonlinear features; the GA finds optimal linear weights; MCTS provides compositional reasoning.

### Key Insight: Separation of Concerns

The full pipeline separates three different kinds of intelligence:

```
NN (nonlinear feature extraction) → Linear weights (GA-evolved) → MCTS (compositional search)
```

- The NN discovers *what to look at* (learned spatial features)
- The GA discovers *how important each feature is* (evolved weights)
- MCTS discovers *how features interact over time* (tree search)

Each component does one job. The features extracted by an SAE on the NN are linear in activation space but represent highly nonlinear functions of the raw board (because the ResNet blocks with ReLUs computed them). Combining these features linearly is sufficient because the search tree handles conditional/compositional reasoning ("corner creation matters more when the opponent will block in 3 moves").
