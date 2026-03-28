# Genetic Algorithm Weight Evolution

Evolve the `EnhancedHeuristicAgent`'s 10 feature weights using an **Island-Model Genetic Algorithm** with ring topology.

## Background

The `EnhancedHeuristicAgent` scores candidate moves using 10 weighted features:

| Weight | Default | Evolved | What it does |
|--------|---------|---------|-------------|
| `piece_size` | 1.0 | **4.19** | Prefer placing larger pieces |
| `corner_creation` | 2.0 | **0.48** | Maximize new corner opportunities |
| `edge_avoidance` | -1.5 | **-2.10** | Penalize moves near board edges |
| `center_preference` | 0.5 | **4.26** | Prefer central positions |
| `opponent_blocking` | 1.5 | **-0.37** | Occupy opponent frontier cells |
| `corners_killed` | -1.0 | **+1.71** | Own frontier cells consumed by this move |
| `opponent_proximity` | -0.5 | **-2.00** | Distance to nearest opponent pieces |
| `open_space` | 0.5 | **0.44** | Local freedom around placed piece |
| `piece_versatility` | -0.3 | **-5.00** | Penalize using flexible pieces early |
| `blocking_risk` | -0.5 | **+1.51** | New corners near opponent pieces |

Three weights flipped sign from defaults. The GA discovered a counterintuitive aggressive strategy: play big, rush center, create outpost corners near opponents, and save flexible pieces at all costs.

## Results

| Agent | Win Rate | Avg Score |
|-------|----------|-----------|
| **GA-Evolved Enhanced Heuristic** | **60.0%** | **96.6** |
| Default Heuristic (4 features) | 32.5% | 88.1 |
| FastMCTS (500 iterations) | 7.5% | 75.9 |
| Random | 0.0% | 60.5 |

The evolved agent beats MCTS 8-to-1 using zero lookahead.

## Island Model Architecture

Individuals are partitioned across **7 islands** connected in a **ring topology**:

```
Island 0 -> Island 1 -> Island 2 -> ... -> Island 6 -> Island 0
```

Each island evolves independently. Every N generations, the best individuals migrate clockwise to the next island. This balances:

- **Diversity** -- islands explore different weight regions independently
- **Information sharing** -- elite genes spread around the ring over time
- **Premature convergence prevention** -- isolation slows homogenization

## Quick Start

```bash
# Smoke test (~30s)
python scripts/ga_evolve_weights.py \
    --population 4 --generations 2 --games-per-eval 2 \
    --islands 3 --seed 42

# Full run (~1 hour with 8 cores)
python scripts/ga_evolve_weights.py --islands 7 --population 6 \
    --generations 200 --games-per-eval 6 --workers 8 \
    --sigma-start 1.0 --verbose

# Quick arena comparison (2 minutes)
python scripts/quick_arena.py 40
```

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--islands` | 7 | Number of islands in ring |
| `--population` | 6 | Individuals per island |
| `--generations` | 30 | Maximum generations |
| `--games-per-eval` | 10 | Games per fitness evaluation |
| `--migration-interval` | 5 | Migrate every N generations |
| `--num-migrants` | 1 | Migrants per event |
| `--tournament-k` | 3 | Tournament selection size |
| `--crossover-alpha` | 0.5 | BLX-alpha blending parameter |
| `--mutation-rate` | 0.3 | Per-weight mutation probability |
| `--sigma-start` | 0.5 | Initial mutation sigma |
| `--sigma-end` | 0.1 | Final mutation sigma (linear decay) |
| `--elitism` | 2 | Elite survivors per island |
| `--early-stop` | 10 | Stop after N gens with no improvement |
| `--workers` | 0 | Parallel workers (0=auto) |
| `--seed` | 42 | Random seed |
| `--output` | `data/ga_evolved_weights.json` | Output path |

## Fitness Evaluation

Each individual plays games as an `EnhancedHeuristicAgent` with its candidate weights. Opponents are:

1. Default heuristic agent (hand-tuned weights)
2. Random agent (floor baseline)
3. Current global elite (co-evolutionary pressure)

The focal agent's seat rotates across games to cancel positional bias. Fitness = average score.

## Tests

```bash
pytest tests/test_ga_evolve.py -v
```

## GA Operator Details

- **Selection**: Tournament (k=3) -- competitive pressure without excessive greediness
- **Crossover**: BLX-alpha (a=0.5) -- can explore outside parent bounds, better than uniform crossover for continuous spaces
- **Mutation**: Gaussian with linear sigma decay (1.0->0.05 recommended) -- explores broadly early, refines late
- **Elitism**: Top 2 per island survive unchanged -- prevents losing the best solution
- **Parallelism**: multiprocessing.Pool for fitness evaluation (~16x speedup on 10 cores)

See [DESIGN_DECISIONS.md](../DESIGN_DECISIONS.md) for the full story including training run comparisons and why the short run (10 gens) failed but the long run (28 gens) succeeded.
