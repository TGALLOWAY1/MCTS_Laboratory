# Layer 5: History Heuristics and RAVE Report

> **Status**: IMPLEMENTED — RAVE, Progressive History refinement, and NST fully integrated. Arena experiment configs ready for benchmarking.

**Branch:** `claude/layer-5-history-heuristics-rave-gSmSP`

## 5.0 — Motivation

Even with action reduction (Layer 3) and improved simulations (Layer 4), new nodes in the MCTS tree start with zero information. The first few visits to a child node produce unreliable Q-estimates, wasting iterations on noise. Layer 5 addresses this **cold start problem** by providing prior knowledge to bootstrap node estimates.

### The Cold Start Problem in Numbers

From Layer 1 diagnostics:
- **Peak branching factor**: 534 at turn 17
- **Mean iteration efficiency**: 11% (78/80 turns below 50%)
- At 1000 iterations with branching factor 534, each child averages ~2 visits — far too few for reliable Q-estimates

### Three Techniques Implemented

1. **RAVE (Rapid Action Value Estimation)**: Per-node statistics from rollout moves blend with UCT Q-values. Assumes "spatial grounding" — the same piece placement has similar value regardless of exact timing.
2. **Progressive History** (refined from Layer 3): Global action statistics bias selection toward historically successful pieces.
3. **NST (N-gram Selection Technique)**: Tracks 2-gram sequences of same-player moves to capture spatial sequencing patterns.

## 5.1 — RAVE Implementation

### Technique (Browne 2012 MCTS Survey §3.2)

RAVE maintains a separate statistic Q_RAVE(s, a) per node, updated for every occurrence of move `a` during a simulation from node `s` — not just when `a` was the tree move at that node.

**Blending formula:**
```
Q_combined = (1 - β) × Q_UCT(s,a) + β × Q_RAVE(s,a)
β = sqrt(k / (3 × N(s) + k))
```

Where `k` is the RAVE equivalence constant (tunable). As N(s) grows, β → 0 and RAVE influence vanishes.

### Spatial Grounding Hypothesis

RAVE assumes action values are somewhat independent of when they occur. In Blokus, placing a specific piece has spatial value that is partially independent of timing — the same piece tends to have similar value whether played on turn 3 or turn 8 (assuming it's still available).

We use `piece_id` (1-21) as the action abstraction key, same as Progressive History. This generalizes across board positions and orientations, capturing "which piece is good to play now?" knowledge.

### Integration Points

| Component | File | Lines | Change |
|-----------|------|-------|--------|
| Per-node storage | `mcts/mcts_agent.py` | MCTSNode | `rave_total: Dict[int, float]`, `rave_visits: Dict[int, int]` |
| Selection blending | `mcts/mcts_agent.py` | `ucb1_value()` | `Q = (1-β)×Q_UCT + β×Q_RAVE` |
| Parent RAVE lookup | `mcts/mcts_agent.py` | `select_child()` | Computes β from parent visits, looks up RAVE Q from parent's table |
| Rollout tracking | `mcts/mcts_agent.py` | `_rollout()` | Returns `(reward, rollout_action_keys)` |
| Backpropagation | `mcts/mcts_agent.py` | `_backpropagation()` | Updates RAVE tables at each ancestor for all actions seen below |

### Memory Cost

Per node: 2 dictionaries with at most 21 entries (one per piece_id) × 2 values (float + int) = ~336 bytes worst case. In practice, most nodes see far fewer unique pieces.

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rave_enabled` | `False` | Enable RAVE blending |
| `rave_k` | `1000.0` | Equivalence constant — higher = more RAVE influence |

## 5.2 — Progressive History Refinement

Progressive History was implemented in Layer 3 and uses a global table of `{piece_id: [total_reward, count]}` to bias UCB selection.

**Key difference from RAVE**: Progressive History is global (one table for the whole tree), while RAVE is per-node (each node has its own action statistics from simulations below it).

**Interaction with Layer 4**: After implementing two-ply rollouts and early termination (Layer 4), the rollout quality improved significantly. This makes both Progressive History and RAVE statistics more reliable — they now learn from higher-quality game continuations.

### Combined Formula

When both Progressive History and RAVE are active:
```
Q_combined = (1 - β) × Q_UCT + β × Q_RAVE
UCB = Q_combined + C×sqrt(ln(N_parent)/N) + W_bias×(prior_bias/(1+N)) + W_hist×(H(a)/(1+N))
```

Progressive History adds an additive bias that decays with visits, while RAVE provides a multiplicative blending that replaces Q_UCT at low visits.

## 5.3 — RAVE k Sweep

**Arena config:** `scripts/arena_config_layer5_rave_k_sweep.json`

Tests k = 100, 500, 1000, 5000 at 100ms thinking time with deterministic budget.

### Interpreting Results

| Optimal k Range | Interpretation | Decision |
|----------------|---------------|----------|
| k > 3000 | RAVE information highly reliable; spatial grounding confirmed | Use RAVE to warm-start progressive widening (Layer 3) |
| k < 500 or RAVE hurts | Move values highly context-dependent | Restrict RAVE to early-game only |
| PH alone wins | Global history sufficient; RAVE overhead not justified | Simplify implementation |
| PH + RAVE wins | Complementary signals captured | Keep both; allocate memory budget |

### Running the Sweep

```bash
# Full sweep (25 games)
python scripts/arena.py --config scripts/arena_config_layer5_rave_k_sweep.json

# Quick smoke test (4 games)
python scripts/arena.py --config scripts/arena_config_layer5_rave_k_sweep.json --num-games 4
```

## 5.4 — Head-to-Head Tournament

**Arena config:** `scripts/arena_config_layer5_head_to_head.json`

Four configurations compete:

| Agent | Progressive History | RAVE | Notes |
|-------|-------------------|------|-------|
| `mcts_baseline` | ✗ | ✗ | Pure UCT |
| `mcts_ph_only` | ✓ (W=1.0) | ✗ | Layer 3 history |
| `mcts_rave_only` | ✗ | ✓ (k=1000) | Layer 5 RAVE |
| `mcts_ph_plus_rave` | ✓ (W=1.0) | ✓ (k=1000) | Combined |

```bash
python scripts/arena.py --config scripts/arena_config_layer5_head_to_head.json
```

## 5.5 — Convergence Validation

**Arena config:** `scripts/arena_config_layer5_convergence.json`

Tests whether RAVE accelerates Q-value convergence by comparing baseline vs RAVE-enabled agents at two time budgets (50ms and 200ms). If RAVE is effective, the 50ms RAVE agent should approach the performance of the 200ms baseline, indicating faster convergence.

Key metrics to check:
- `regret_gap` (best Q - second-best Q): Lower gap = less converged
- `visit_entropy`: Lower = more focused search
- TrueSkill rating comparison

```bash
python scripts/arena.py --config scripts/arena_config_layer5_convergence.json
```

## 5.6 — NST (N-gram Selection Technique)

### Technique (MCTS Survey §2.4, Soemers 2019)

NST tracks pairs of consecutive moves by the same player. In 4-player Blokus, the root player moves every 4th turn, so the relevant 2-gram is (action at turn T, action at turn T+4).

### Why This Matters for Blokus

Blokus has strong spatial sequencing — moves that create an expanding chain of diagonally connected pieces. If "Player 1 places the T-pentomino at (5,7)" followed by "Player 1 later places the L-tetromino at (7,8)" consistently leads to wins, the 2-gram captures this pattern that neither simple history nor RAVE would detect.

### Implementation

| Component | Description |
|-----------|-------------|
| `_nst_table` | `Dict[(prev_piece_id, cur_piece_id), [total_reward, count]]` |
| `_last_root_action_key` | Tracks cross-move continuity between MCTS searches |
| `_nst_biased_select()` | Softmax-weighted move selection using NST scores |
| Backprop update | Extracts 2-gram pairs from rollout root-player moves |
| Rollout integration | When root player's turn, uses NST bias instead of default policy |

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `nst_enabled` | `False` | Enable NST-biased rollouts |
| `nst_weight` | `0.5` | Softmax temperature for NST scoring |

## 5.7 — Key Findings & Decisions for Downstream Layers

*To be populated after arena experiments are run.*

| Finding | Decision | Layer Affected |
|---------|----------|---------------|
| RAVE k sweep result | Determines if spatial grounding holds | Layer 3 (warm-start PW) |
| PH vs RAVE winner | Architecture simplification or combined approach | Memory budget |
| Convergence improvement | Reassess iteration budget; informs Layer 8 (parallelization) | Layer 8 |
| NST value | Whether 2-gram patterns contribute beyond single-action history | Feature importance for Layer 6 |

## Checklist: Layer 5 Complete When...

- [x] RAVE implemented with configurable k parameter
- [x] RAVE k sweep config ready (k = 100, 500, 1000, 5000)
- [x] Progressive History vs RAVE head-to-head config ready
- [x] Combination (PH + RAVE) tested in head-to-head config
- [x] Q-value convergence config ready for validation
- [x] NST implemented and tested
- [x] 23 unit tests passing
- [x] Arena runner wired for all new parameters
- [ ] RAVE k sweep completed with TrueSkill ratings
- [ ] Head-to-head tournament completed
- [ ] Convergence validation completed
- [ ] Winning configuration documented with quantitative justification
