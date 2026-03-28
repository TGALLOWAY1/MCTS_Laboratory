# Neural Network: Architecture and Training

## Supervised Pre-training Results (Stage 1)

After 6 epochs of supervised training on 337k board states (98% policy accuracy):

| Agent | Win Rate | Avg Score |
|-------|----------|-----------|
| **GA Evolved** | **80.0%** | **94.8** |
| NN Standalone (policy head) | 15.0% | 81.2 |
| NN + MCTS (value head guiding search) | 5.0% | 78.8 |
| FastMCTS (heuristic rollouts) | 0.0% | 72.6 |

The NN can't beat its teacher — it was trained to imitate the GA agent, so at best it reproduces GA-level play with imitation noise. NN+MCTS was worse than NN standalone because the value head wasn't calibrated for the fine-grained position comparisons MCTS needs.

**Self-play RL (Stage 2) is needed to surpass the GA agent.**

## Why a Neural Network?

The GA-evolved heuristic agent uses 10 hand-coded features combined linearly. This has two limitations:

1. **Feature ceiling** — we can only evaluate what we thought to measure. The NN learns its own spatial features directly from the 20×20 board, discovering patterns we'd never hand-code.
2. **No lookahead** — the heuristic evaluates one move at a time. Once trained, the NN's value head can plug into MCTS to replace random rollouts, making MCTS dramatically faster and stronger (the AlphaZero approach).

## Training Data Generation

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

## Input Representation

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

## Network Architecture

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

**~317k parameters.** Small enough to train on CPU, though slow (~30 min/epoch).

**Why ResBlocks?** Residual connections let the network learn "corrections" to the identity — each block adds incremental pattern detection. 4 blocks with 3×3 kernels gives an effective receptive field of ~11×11, covering over half the board from any position.

**Why a move-scoring policy head (not a fixed output vector)?** Blokus has ~500 legal moves per turn drawn from a combinatorial space of 21 pieces × 8 orientations × 400 positions. A fixed output of 67,200 logits is wasteful — most are always illegal. Instead, the policy head scores each legal move individually using the spatial features at that move's location. This handles variable action spaces naturally and generalizes across board positions.

## Training Approach

### Phase 1: Supervised pre-training (imitation learning)

The NN learns to imitate the agents that generated the data:

- **Value loss** — MSE between predicted and actual normalized final score for the current player. The NN learns "who's winning from this position?"
- **Policy loss** — Cross-entropy over candidate moves. For each state, score the move that was actually played (positive) against K=15 random move tuples (negatives). The NN learns "which move would the agent play here?"
- **Combined loss** — `value_weight × value_loss + policy_weight × policy_loss`

**Why not just value or just policy?**
- Value-only: the NN can evaluate positions but can't suggest moves (useless standalone, only useful in MCTS)
- Policy-only: the NN can suggest moves but can't evaluate positions (useless for MCTS integration)
- Both: works standalone AND plugs into MCTS

### Phase 2: Self-play league training

Initial self-play (NN vs copies of itself, 10 iterations x 20 games) improved the NN from 5% to 33% win rate against the GA agent — but progress was noisy and slow due to narrow opponent diversity.

**League training** (`scripts/self_play_league.py`) addresses this by maintaining a diverse opponent pool, inspired by our island-model GA and AlphaStar's league system:

| Opponent | Probability | Purpose |
|----------|------------|---------|
| Current NN+MCTS | 30% | Self-play (learn from equal opponent) |
| Past NN versions | 25% | Weaker selves (curriculum learning, prevent forgetting) |
| GA-evolved heuristic | 25% | Strong baseline (learn to beat the champion) |
| Default heuristic | 10% | Weak baseline (easy wins build training signal) |
| Random | 10% | Floor (prevents forgetting basics) |

Each iteration:
1. NN+MCTS plays 40 games against diverse opponents from the pool
2. Board states and outcomes are recorded as training data
3. The NN's value head is retrained on the new data
4. The checkpoint is added to the opponent pool (becomes a "past version")
5. Evaluate against GA agent to track progress

The pool keeps the 5 most interesting past checkpoints: the weakest (earliest) plus the 4 most recent. This ensures the NN faces opponents at all skill levels.

**Self-play results (basic, 10 iterations x 20 games):**

| Iteration | NN Win Rate vs GA |
|-----------|-------------------|
| 1 | 0% |
| 2 | 17% |
| 5 | 17% |
| 10 | 33% |

Improvement from 5% to 33%.

**League training results (8 iterations x 40 games before stopped):**

| Iteration | League Win Rate | vs GA (10 games) |
|-----------|----------------|------------------|
| 1 | 5% | 20% |
| 2 | 22% | 0% |
| 3 | 8% | 10% |
| 4 | 8% | 20% |
| 5 | 22% | 0% |
| 6 | 15% | 10% |
| 7 | 12% | 20% |

**League training performed worse than basic self-play** — peaking at 20% vs GA compared to 33% from basic self-play. The diverse opponent pool diluted the training signal: games against random and weak heuristic opponents (20% of the pool) taught the NN to beat easy targets, which didn't help against the GA agent.

### Why the NN didn't surpass the GA

Three fundamental issues prevented the NN from beating its teacher:

1. **Only the value head was trained during self-play** — the policy head (which moves to explore) was frozen from supervised pre-training. The NN got better at evaluating positions but still explored the same moves it learned by imitation.

2. **Insufficient training data per iteration** — ~640 states from 40 games. The value head overfits to this small dataset in a few epochs and doesn't generalize.

3. **MCTS at 100 iterations is too shallow for Blokus** — even with a better value head, 100 iterations across a branching factor of 80-500 can't discover new strategies. The search tree never gets deep enough to find multi-move tactical sequences.

### What would be needed

To surpass the GA agent, the NN approach would need:

- **Policy gradient RL** (REINFORCE/PPO) instead of value-only training — update the policy head directly from win/loss outcomes, no MCTS overhead
- **GPU training** with thousands of games per iteration (not 20-40)
- **Much deeper MCTS** (1000+ iterations) or smarter search (progressive widening, RAVE)
- Alternatively: **train the NN as a feature extractor only**, then use SAE + GA for the final evaluation (the separation-of-concerns approach)

## Integration Path

The trained NN can be used in three ways:

1. **Standalone agent** — `NNAgent.select_action()` uses the policy head to pick moves. No search, instant evaluation.
2. **MCTS value estimator** — replace MCTS's random rollouts with the NN value head. Instead of simulating 60 random moves, ask the NN "who's winning?" in one forward pass. This is the high-value target.
3. **SAE feature extraction** — train a sparse autoencoder on the NN's hidden layer activations to discover interpretable features, then feed those features into the GA for optimized linear combination. The NN discovers nonlinear features; the GA finds optimal linear weights; MCTS provides compositional reasoning.

## Key Insight: Separation of Concerns

The full pipeline separates three different kinds of intelligence:

```
NN (nonlinear feature extraction) → Linear weights (GA-evolved) → MCTS (compositional search)
```

- The NN discovers *what to look at* (learned spatial features)
- The GA discovers *how important each feature is* (evolved weights)
- MCTS discovers *how features interact over time* (tree search)

Each component does one job. The features extracted by an SAE on the NN are linear in activation space but represent highly nonlinear functions of the raw board (because the ResNet blocks with ReLUs computed them). Combining these features linearly is sufficient because the search tree handles conditional/compositional reasoning ("corner creation matters more when the opponent will block in 3 moves").
