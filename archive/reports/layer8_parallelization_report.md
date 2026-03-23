# Layer 8: Parallelization for MCTS

> **Status**: IMPLEMENTED — Root parallelization via multiprocessing and tree parallelization with virtual loss via threading. Arena experiment configs ready for throughput and playing strength benchmarks.

**Branch:** `claude/layer-8-parallelization-J1rXQ`

## 8.0 — Motivation

Layers 3-7 dramatically improved per-iteration quality: structured simulations (Layer 4), RAVE bootstrapping (Layer 5), phase-dependent evaluation (Layer 6), and opponent modeling (Layer 7). Each iteration now produces more useful information than the baseline UCT iterations from Layer 1. Layer 8 multiplies these high-quality iterations via parallelization, translating available CPU cores into playing strength.

The MCTS survey (§8.1-8.4) describes three fundamental approaches to parallelism:
1. **Leaf parallelization** — multiple rollouts from the same leaf
2. **Root parallelization** — independent trees merged at decision time
3. **Tree parallelization** — shared tree with virtual loss

This layer implements both root parallelization (the practical choice for Python) and tree parallelization with virtual loss (the canonical algorithm from the literature).

### The Research Question

Does multiplying the iteration budget via parallelism translate to measurably better play in 4-player Blokus? The answer depends on:
- Whether Q-values are still converging at the current iteration budget
- Whether the information diversity from multiple trees outweighs the loss from not sharing information
- Whether Python's multiprocessing overhead negates the throughput gains

## 8.1 — Root Parallelization (Primary Strategy)

### Design

Root parallelization spawns N independent MCTS worker processes, each building its own tree with a different random seed. At decision time, root-level move statistics (visit counts and total rewards) are merged across all workers, and the move with the highest aggregate visit count is selected.

| Component | Implementation |
|-----------|---------------|
| Worker spawning | `concurrent.futures.ProcessPoolExecutor` |
| Config transfer | Serializable dict extracted from MCTSAgent |
| Board transfer | `pickle.dumps(board)` |
| Move keying | `(piece_id, orientation, anchor_row, anchor_col)` tuple |
| Iteration split | `iterations // num_workers` per worker |
| Merge formula | Sum visit counts and total rewards per move |
| Move selection | Highest aggregate visit count |

### Why Root Parallelization for Python

CPython's Global Interpreter Lock (GIL) prevents true CPU parallelism with threading. The GIL serializes bytecode execution, so threading-based tree parallelization cannot achieve real speedup for CPU-bound MCTS iterations. Root parallelization uses separate processes, each with its own GIL, achieving genuine parallelism.

### Worker Design

Workers cannot share the MCTSAgent object directly (it holds non-picklable components like move generators and transposition tables). Instead:

1. `_extract_agent_config()` extracts all constructor parameters as a plain dict
2. Each worker reconstructs its own MCTSAgent with a unique seed
3. Workers run `_run_mcts_with_iterations()` independently
4. Workers return per-child `{move_key: (visits, total_reward)}` statistics

Workers are forced to `num_workers=1` internally to prevent recursive parallelism.

### New Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `num_workers` | `1` | Number of parallel MCTS workers (1 = single-threaded) |
| `virtual_loss` | `1.0` | Virtual loss magnitude for tree parallelization |
| `parallel_strategy` | `"root"` | `"root"` (multiprocessing) or `"tree"` (threading + virtual loss) |

### Implementation Files

- `mcts/parallel.py` — Root parallelization module: config extraction, worker function, result merging
- `mcts/mcts_agent.py` — `select_action` dispatch, new constructor parameters

## 8.2 — Tree Parallelization with Virtual Loss

### Design

Tree parallelization uses a single shared tree with multiple threads running MCTS iterations concurrently. **Virtual loss** prevents threads from selecting the same path: when a thread enters a node during selection, it temporarily inflates the visit count and decreases the reward, making the node less attractive to other threads.

### Virtual Loss Mechanism

On `MCTSNode`:

```python
def apply_virtual_loss(self, magnitude=1.0):
    self.virtual_losses += 1
    self.visits += 1          # inflate visit count
    self.total_reward -= magnitude  # decrease reward

def remove_virtual_loss(self, magnitude=1.0):
    self.virtual_losses -= 1
    self.visits -= 1
    self.total_reward += magnitude
```

The standard UCB formula naturally penalizes nodes with virtual losses because:
- Higher visit count → lower exploration term (√(ln N_parent / N))
- Lower reward → lower exploitation term (Q/N)

### Thread Safety

| Critical section | Protection |
|-----------------|------------|
| Node expansion | `threading.Lock()` per search |
| Backpropagation | Lock-free (minor races tolerable per MCTS literature) |
| Virtual loss | Lock-free (atomic-like increments) |
| Transposition table | Disabled in tree-parallel mode |

### GIL Limitation

Due to CPython's GIL, tree parallelization does not achieve real CPU parallelism. It is included for:
1. **Algorithmic completeness** — documents the canonical approach from the literature
2. **Future-proofing** — ready for free-threaded Python (PEP 703, Python 3.13+)
3. **Comparison baseline** — enables empirical comparison with root parallelization

### Selection with Virtual Loss

`_selection_with_virtual_loss()` mirrors the standard `_selection()` but:
- Applies virtual loss at each node traversed during selection
- Returns the selection path so virtual losses can be removed after backpropagation
- Supports all existing selection features (progressive widening, RAVE, history)

## 8.3 — Arena Configurations

### Throughput Scaling (`arena_config_layer8_throughput.json`)

| Agent | Workers | Strategy | Purpose |
|-------|---------|----------|---------|
| `L7_baseline_1w` | 1 | — | Single-threaded baseline |
| `L8_root_2w` | 2 | root | 2x parallelism |
| `L8_root_4w` | 4 | root | 4x parallelism |
| `L8_root_8w` | 8 | root | 8x parallelism |

50 games, round-robin. All agents use the same base config (L7 phase weights, cutoff 8, heuristic rollout). Measures iterations/second and time-per-move at each worker count.

**Expected throughput efficiency:**
```
efficiency(N) = throughput(N) / (N × throughput(1))
```
Typical MCTS root parallelization achieves 0.7-0.9x efficiency due to process spawn overhead and merge cost.

### Playing Strength Scaling (`arena_config_layer8_strength.json`)

| Agent | Workers | Strategy | Purpose |
|-------|---------|----------|---------|
| `L7_baseline_1w` | 1 | — | Single-threaded baseline |
| `L8_root_2w` | 2 | root | Root parallel comparison |
| `L8_root_4w` | 4 | root | Root parallel comparison |
| `L8_tree_2w` | 2 | tree | Tree parallel comparison |

100 games for TrueSkill significance. Higher thinking time (200ms = 2000 iterations) to test whether extra parallel iterations improve play.

### Running the Experiments

```bash
# Throughput scaling (50 games)
python scripts/arena.py --config scripts/arena_config_layer8_throughput.json

# Playing strength (100 games)
python scripts/arena.py --config scripts/arena_config_layer8_strength.json

# Smoke test (4 games)
python scripts/arena.py --config scripts/arena_config_layer8_strength.json --num-games 4
```

## 8.4 — Implementation Summary

### Files Changed

| File | Change |
|------|--------|
| `mcts/mcts_agent.py` | Layer 8 params, virtual loss on MCTSNode, tree-parallel iteration loop, selection with virtual loss |
| `mcts/parallel.py` | **NEW** — Root parallelization: config extraction, worker function, result merging |
| `analytics/tournament/arena_runner.py` | Wire `num_workers`, `virtual_loss`, `parallel_strategy` through `build_agent()` |
| `scripts/arena_config_layer8_throughput.json` | **NEW** — Throughput scaling benchmark |
| `scripts/arena_config_layer8_strength.json` | **NEW** — Playing strength benchmark |
| `tests/test_layer8_parallelization.py` | **NEW** — 25 tests covering virtual loss, params, both strategies |

### New Stats Keys

| Key | Description |
|-----|-------------|
| `parallel_workers` | Number of workers used (0 for single-threaded) |
| `parallel_strategy` | Strategy used ("none", "root", "tree") |
| `parallel_trees_merged` | Number of trees merged (root parallelization) |
| `virtual_loss_applications` | Total virtual loss applications (tree parallelization) |

## 8.5 — Interpreting Results

### What the Curves Should Tell You

- **Throughput efficiency > 0.7x at 4 workers:** Root parallelization is effective. Process overhead is acceptable.
- **Throughput efficiency < 0.5x at 4 workers:** Process spawn/merge overhead dominates. Consider larger iteration budgets to amortize fixed costs.
- **Root 2w beats baseline 1w in TrueSkill:** Extra iterations from parallelism translate to better play. The search was under-budgeted.
- **Root 4w ≈ Root 2w in TrueSkill:** Diminishing returns — Q-values converge before the extra iterations are consumed. Invest extra cores elsewhere.
- **Tree 2w ≈ baseline 1w:** GIL prevents real speedup. Tree parallelization is architecturally correct but not beneficial in CPython.

## Checklist

- [x] Root parallelization implemented with configurable worker count
- [x] Tree parallelization implemented with virtual loss
- [x] Virtual loss with configurable magnitude
- [x] Parameters wired through arena config → build_agent → MCTSAgent
- [x] Throughput scaling arena config (1/2/4/8 workers)
- [x] Playing strength scaling arena config (root vs tree vs baseline)
- [x] 25 unit tests covering both strategies
- [ ] Throughput scaling measured (run arena_config_layer8_throughput.json)
- [ ] Playing strength measured via TrueSkill (run arena_config_layer8_strength.json)
- [ ] Lock contention profiled at high thread counts
- [ ] Optimal worker count determined for target hardware

## Key Decisions

| Finding | Downstream Impact |
|---------|-------------------|
| Root parallelization is the practical strategy for Python | Default `parallel_strategy="root"` |
| Tree parallelization included for completeness | Ready for free-threaded Python 3.13+ |
| Workers forced to num_workers=1 | Prevents recursive parallelism |
| Move keyed by (piece_id, orientation, anchor) | Enables cross-tree merge |
| Virtual loss applied in-place on visits/reward | Standard UCB formulas naturally penalize |
| Transposition table disabled in tree-parallel | Avoids shared mutable state races |
