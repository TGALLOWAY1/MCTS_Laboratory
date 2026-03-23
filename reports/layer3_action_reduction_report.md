# Layer 3: Action Reduction Report

> **Status**: IMPLEMENTED — progressive widening and progressive history integrated into MCTS agent. Initial validation promising; full sweep pending.

**Branch:** `claude/implement-layer-3-9kB7P`

## 3.1 — Problem Statement

The Layer 1 baseline characterization identified **high branching factor** as the primary bottleneck: Blokus positions commonly have 200–400+ legal moves. At a 200ms time budget, the MCTS agent spends most iterations expanding new children rather than deepening the tree. This produces a wide, shallow tree with poor value estimates.

**Goal:** Reduce the effective branching factor so MCTS concentrates its limited iteration budget on the most promising moves.

## 3.2 — Techniques Implemented

### Progressive Widening (PW)

Limits the number of children expanded at each node to `C_pw * N^alpha`, where N is the visit count. Instead of immediately expanding all legal moves, children are added gradually as a node accumulates visits.

**Parameters:**
| Parameter | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| `pw_c` | C_pw | 2.0 | Initial children at visit=1 |
| `pw_alpha` | α | 0.5 | Growth exponent (0 = fixed width, 1 = linear) |

**Formula:** `max_children = max(1, floor(C_pw * N^alpha))`

At 100 visits with default params: `floor(2.0 * 100^0.5) = 20 children` — a 10–20x reduction from 200–400 legal moves.

### Progressive History (PH)

Adds a history-based bias term to the UCB formula that favors piece types which have historically led to good outcomes. The action abstraction uses `piece_id` (not full move identity) so knowledge transfers across board positions.

**UCB modification:**
```
UCB = exploitation + C * exploration + W * (history_score / (1 + N_child))
```

**Parameters:**
| Parameter | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| `progressive_history_weight` | W | 1.0 | Bias strength (decays as child visits grow) |

History scores are updated during backpropagation with win/loss outcomes.

### Domain-Specific Move Heuristic

Moves are ordered by a fast heuristic before progressive widening selects which to expand first. This ensures the best moves are tried early.

**Heuristic features (weighted sum, normalised to [0, 1]):**
| Feature | Weight | Rationale |
|---------|--------|-----------|
| Piece size (÷5) | 1.0 | Larger pieces score more; harder to place late |
| Corner generation (÷8) | 2.0 | New frontier cells enable future placements |
| Center proximity | 0.5 | Central territory enables multi-directional expansion |
| Opponent blocking | 1.0 | Blocking opponent diagonal anchors limits their options |

**Implementation:** `mcts/move_heuristic.py`

## 3.3 — Initial Validation (8-game smoke test)

Configuration: 100ms thinking time, `mcts` backend, 8 games per agent.

| Agent | Win% | Avg Score | Notes |
|-------|------|-----------|-------|
| `pw_only` (C=2, α=0.5) | **62.5%** | **95.4** | Progressive widening only |
| `baseline` | 25.0% | 76.2 | No action reduction |

**Score improvement:** +19.2 points average over baseline (95.4 vs 76.2).

### Heuristic Calibration

Agreement rate between heuristic ordering and final MCTS move selection:

| Phase | Agreement Rate |
|-------|---------------|
| Early | 55% |
| Mid | 83% |
| Late | 73% |
| **Overall** | **72.2%** |

The heuristic aligns well with MCTS in mid/late game but is weaker in the opening, where positional nuance matters more. This is expected — early game has the most legal moves and the least immediate tactical signal.

## 3.4 — Architecture

```
MCTSAgent
├── progressive_widening_enabled (bool)
│   ├── pw_c: coefficient
│   └── pw_alpha: exponent
├── progressive_history_enabled (bool)
│   └── progressive_history_weight: UCB bias weight
├── _history_table: Dict[int, [wins, plays]]
│   └── key = piece_id (abstract action)
└── move ordering via rank_moves_by_heuristic()
    └── mcts/move_heuristic.py
```

**Selection phase:** If PW is enabled and node hasn't reached its child limit, expand a new child (heuristic-ordered). Otherwise, select best existing child via UCB (with optional PH bias).

**Backpropagation:** If PH is enabled, update history table with win/loss for each piece played along the path.

## 3.5 — Tuning Sets

Three tuning sets registered in `analytics/tournament/tuning.py`:

| Set Name | Purpose | Configurations |
|----------|---------|----------------|
| `pw_sweep` | Sweep PW parameters | 6 configs: C ∈ {1,2,4}, α ∈ {0.3,0.5} |
| `ph_sweep` | Sweep PH weight | 4 configs: W ∈ {0.5,1.0,2.0,4.0} |
| `action_reduction_ablation` | Ablation study | 4 configs: baseline, PW-only, PH-only, PW+PH |

## 3.6 — Recommended Next Steps

1. **Full validation arena** (40+ games, 200ms budget) with `action_reduction_ablation` tuning set
2. **Parameter sweep** using `pw_sweep` and `ph_sweep` to find optimal C_pw, α, and W
3. **Combined with Layer 2**: Re-test learned evaluation now that tree depth should be greater (action reduction + inference cache fix may make learned eval viable)
4. **Heuristic refinement**: Improve early-game agreement rate — consider board-state-dependent feature weights

## 3.7 — Artifacts

| File | Description |
|------|-------------|
| `mcts/move_heuristic.py` | Domain-specific move heuristic (183 lines) |
| `mcts/mcts_agent.py` | PW + PH integration into MCTS selection/expansion |
| `analytics/tournament/tuning.py` | Three Layer 3 tuning sets |
| `scripts/run_layer3_validation.py` | Full validation + heuristic calibration script |
| `tests/test_layer3_action_reduction.py` | 23 unit tests |

## Checklist: Layer 3 Complete When...

- [x] Progressive widening implemented with configurable C_pw and α
- [x] Progressive history implemented with piece_id abstraction
- [x] Domain-specific move heuristic for move ordering
- [x] Heuristic calibration analysis (agreement rate per phase)
- [x] Unit tests (23 tests passing)
- [x] Tuning sets registered for parameter sweeps
- [x] Initial validation shows improvement over baseline (+19.2 avg score)
- [ ] Full 40-game validation arena (**pending**)
- [ ] Parameter sweep for optimal PW/PH settings (**pending**)
- [ ] Combined Layer 2 + Layer 3 validation (**pending**)
