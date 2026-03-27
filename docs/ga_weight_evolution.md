# Genetic Algorithm Weight Evolution

Evolve the `HeuristicAgent`'s four feature weights using an **Island-Model Genetic Algorithm** with ring topology.

## Background

The `HeuristicAgent` scores candidate moves using four weighted features:

| Weight | Default | What it does |
|--------|---------|-------------|
| `piece_size` | 1.0 | Prefer placing larger pieces |
| `corner_creation` | 2.0 | Maximize new corner opportunities |
| `edge_avoidance` | -1.5 | Penalize moves near board edges |
| `center_preference` | 0.5 | Prefer central positions |

These defaults were hand-tuned. The GA systematically searches the weight space.

## Island Model Architecture

Instead of a single population, individuals are partitioned across **7 islands** connected in a **ring topology**:

```
Island 0 → Island 1 → Island 2 → ... → Island 6 → Island 0
```

Each island evolves independently. Every N generations, the best individual from each island **migrates clockwise** to the next island, replacing the worst individual there. This balances:

- **Diversity** — islands explore different weight regions independently
- **Information sharing** — elite genes spread around the ring over time
- **Premature convergence prevention** — isolation slows homogenization

## Quick Start

```bash
# Smoke test (~30s)
python scripts/ga_evolve_weights.py \
    --population 4 --generations 2 --games-per-eval 2 \
    --islands 3 --seed 42

# Full run (~10 min)
python scripts/ga_evolve_weights.py --verbose

# Custom configuration
python scripts/ga_evolve_weights.py \
    --islands 10 --population 8 --generations 50 \
    --games-per-eval 15 --verbose
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
| `--seed` | 42 | Random seed |
| `--output` | `data/ga_evolved_weights.json` | Output path |

## Fitness Evaluation

Each individual plays 10 games as a `HeuristicAgent` with its candidate weights. Opponents are:

1. Default heuristic agent (hand-tuned weights)
2. Random agent (floor baseline)
3. Current global elite (co-evolutionary pressure)

The focal agent's seat rotates across games to cancel positional bias. Fitness = average score.

## Output

Results are saved to `data/ga_evolved_weights.json`:

```json
{
  "best_weights": { "piece_size": ..., "corner_creation": ..., ... },
  "best_fitness": 42.5,
  "generation": 24,
  "islands": 7,
  "default_weights": { ... },
  "config": { ... },
  "history": [ ... ]
}
```

## Validation

After evolution, validate evolved weights against baselines using the arena:

1. Update `scripts/arena_config_ga_evolved.json` with the evolved weights from the output JSON
2. Run: `python scripts/arena.py --config scripts/arena_config_ga_evolved.json --num-games 100`
3. Compare evolved agent's win rate and average score against the default heuristic

## Tests

```bash
pytest tests/test_ga_evolve.py -v
```

## GA Operator Details

- **Selection**: Tournament (k=3) — competitive pressure without excessive greediness
- **Crossover**: BLX-alpha (α=0.5) — can explore outside parent bounds, better than uniform crossover for continuous spaces
- **Mutation**: Gaussian with linear sigma decay (0.5→0.1) — explores broadly early, refines late
- **Elitism**: Top 2 per island survive unchanged — prevents losing the best solution
