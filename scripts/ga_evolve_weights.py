#!/usr/bin/env python
"""Evolve EnhancedHeuristicAgent weights using an Island-Model Genetic Algorithm.

Uses a ring topology with 7+ islands that evolve independently, with periodic
migration of elite individuals between neighbouring islands to balance
exploration (island isolation) and exploitation (gene flow).

Usage:
    # Smoke test (fast)
    python scripts/ga_evolve_weights.py --population 4 --generations 2 \
        --games-per-eval 2 --islands 3 --seed 42

    # Full run (~10 min)
    python scripts/ga_evolve_weights.py --verbose

    # Custom islands
    python scripts/ga_evolve_weights.py --islands 10 --population 8 --verbose
"""

import argparse
import copy
import json
import logging
import multiprocessing
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from agents.enhanced_heuristic_agent import EnhancedHeuristicAgent
from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from engine.board import Player
from engine.game import BlokusGame

logger = logging.getLogger(__name__)

# ── Weight definitions ──────────────────────────────────────────────────────

WEIGHT_NAMES = [
    # Original 4
    "piece_size", "corner_creation", "edge_avoidance", "center_preference",
    # New 6
    "opponent_blocking", "corners_killed", "opponent_proximity",
    "open_space", "piece_versatility", "blocking_risk",
]
DEFAULT_WEIGHTS = [
    # Original 4
    1.0, 2.0, -1.5, 0.5,
    # New 6
    1.5, -1.0, -0.5, 0.5, -0.3, -0.5,
]
WEIGHT_BOUNDS = (-5.0, 5.0)


# ── Data structures ─────────────────────────────────────────────────────────

@dataclass
class Individual:
    """A candidate solution: a vector of heuristic weights."""
    weights: np.ndarray
    fitness: float = 0.0
    games_played: int = 0

    def weights_dict(self) -> Dict[str, float]:
        return dict(zip(WEIGHT_NAMES, self.weights.tolist()))

    def copy(self) -> "Individual":
        return Individual(weights=self.weights.copy(), fitness=self.fitness,
                          games_played=self.games_played)


@dataclass
class Island:
    """A sub-population that evolves independently."""
    island_id: int
    population: List[Individual] = field(default_factory=list)
    best_fitness_history: List[float] = field(default_factory=list)


@dataclass
class EvolutionResult:
    """Final output of the GA run."""
    best_weights: Dict[str, float]
    best_fitness: float
    generation: int
    islands: int
    history: List[dict]
    config: dict


# ── Game simulation ─────────────────────────────────────────────────────────

def play_game(weights: Dict[str, float], opponents: List, seed: int) -> float:
    """Play one 4-player Blokus game and return the focal agent's score.

    The focal agent (with the given weights) is assigned a random seat position
    to avoid positional bias. Opponents fill the remaining seats.

    Returns the focal agent's final score (higher is better).
    """
    game = BlokusGame(enable_telemetry=False)
    players = list(Player)

    # Assign focal agent to a seat determined by seed
    rng = np.random.RandomState(seed)
    focal_seat = rng.randint(0, 4)

    # Build agents dict
    agents = {}
    opponent_idx = 0
    for i, player in enumerate(players):
        if i == focal_seat:
            agent = EnhancedHeuristicAgent(seed=seed)
            agent.set_weights(weights)
            agents[player] = agent
        else:
            agents[player] = opponents[opponent_idx % len(opponents)]
            opponent_idx += 1

    # Reset all opponent agents with fresh seeds
    for i, player in enumerate(players):
        if i != focal_seat:
            agents[player].set_seed(seed + i + 1)

    focal_player = players[focal_seat]

    # Game loop (pattern from generate_analytics_data.py)
    max_turns = 2500  # safety limit
    turn = 0
    while not game.is_game_over() and turn < max_turns:
        current_player = game.get_current_player()
        legal_moves = game.get_legal_moves(current_player)

        if not legal_moves:
            game.board._update_current_player()
            game._check_game_over()
            turn += 1
            continue

        agent = agents[current_player]
        move = agent.select_action(game.board, current_player, legal_moves)

        if move:
            game.make_move(move, current_player)
        else:
            game.board._update_current_player()
            game._check_game_over()

        turn += 1

    result = game.get_game_result()
    return float(result.scores.get(focal_player.value, 0))


def _eval_worker(args_tuple):
    """Worker function for multiprocessing. Must be top-level for pickling."""
    weights_array, games_per_eval, elite_weights, base_seed = args_tuple
    weights = dict(zip(WEIGHT_NAMES, weights_array.tolist()))

    default_agent = HeuristicAgent(seed=0)
    random_agent = RandomAgent(seed=0)

    if elite_weights is not None:
        elite_agent = EnhancedHeuristicAgent(seed=0)
        elite_agent.set_weights(elite_weights)
    else:
        elite_agent = HeuristicAgent(seed=0)

    opponents = [default_agent, random_agent, elite_agent]

    total_score = 0.0
    for g in range(games_per_eval):
        game_seed = base_seed + g * 1000
        score = play_game(weights, opponents, game_seed)
        total_score += score

    return total_score / games_per_eval


def evaluate_fitness(individual: Individual, games_per_eval: int,
                     elite_weights: Optional[Dict[str, float]],
                     base_seed: int) -> float:
    """Evaluate an individual over multiple games (sequential fallback)."""
    avg = _eval_worker((individual.weights, games_per_eval, elite_weights, base_seed))
    individual.fitness = avg
    individual.games_played += games_per_eval
    return avg


def evaluate_population_parallel(individuals: List[Individual],
                                 games_per_eval: int,
                                 elite_weights: Optional[Dict[str, float]],
                                 base_seeds: List[int],
                                 num_workers: int) -> None:
    """Evaluate all individuals in parallel using multiprocessing."""
    work_items = [
        (ind.weights, games_per_eval, elite_weights, seed)
        for ind, seed in zip(individuals, base_seeds)
    ]

    with multiprocessing.Pool(processes=num_workers) as pool:
        results = pool.map(_eval_worker, work_items)

    for ind, fitness in zip(individuals, results):
        ind.fitness = fitness
        ind.games_played += games_per_eval


# ── GA operators ────────────────────────────────────────────────────────────

def create_individual(rng: np.random.RandomState,
                      from_weights: Optional[np.ndarray] = None) -> Individual:
    """Create a new individual, optionally from specific weights."""
    if from_weights is not None:
        w = np.clip(from_weights, *WEIGHT_BOUNDS)
    else:
        w = rng.uniform(WEIGHT_BOUNDS[0], WEIGHT_BOUNDS[1], size=len(WEIGHT_NAMES))
    return Individual(weights=w)


def tournament_select(population: List[Individual], k: int,
                      rng: np.random.RandomState) -> Individual:
    """Tournament selection: pick k random individuals, return the fittest."""
    contestants = rng.choice(len(population), size=min(k, len(population)),
                             replace=False)
    best = max(contestants, key=lambda i: population[i].fitness)
    return population[best].copy()


def blx_alpha_crossover(parent1: Individual, parent2: Individual,
                        alpha: float, rng: np.random.RandomState) -> Tuple[Individual, Individual]:
    """BLX-alpha crossover for continuous weights.

    For each weight dimension, the child's value is sampled uniformly from
    [min(p1,p2) - alpha*d, max(p1,p2) + alpha*d] where d = |p1 - p2|.
    This allows exploration beyond the parents' range.
    """
    w1, w2 = parent1.weights, parent2.weights
    d = np.abs(w1 - w2)
    lo = np.minimum(w1, w2) - alpha * d
    hi = np.maximum(w1, w2) + alpha * d

    child1_w = rng.uniform(lo, hi)
    child2_w = rng.uniform(lo, hi)

    child1_w = np.clip(child1_w, *WEIGHT_BOUNDS)
    child2_w = np.clip(child2_w, *WEIGHT_BOUNDS)

    return Individual(weights=child1_w), Individual(weights=child2_w)


def mutate(individual: Individual, mutation_rate: float, sigma: float,
           rng: np.random.RandomState) -> Individual:
    """Gaussian mutation with per-weight probability."""
    w = individual.weights.copy()
    for i in range(len(w)):
        if rng.random() < mutation_rate:
            w[i] += rng.normal(0, sigma)
    w = np.clip(w, *WEIGHT_BOUNDS)
    individual.weights = w
    return individual


# ── Island Model GA ─────────────────────────────────────────────────────────

def create_island(island_id: int, pop_size: int,
                  rng: np.random.RandomState,
                  seed_weights: Optional[np.ndarray] = None) -> Island:
    """Create an island with an initial population.

    If seed_weights is provided, one individual is seeded with those weights
    (ensuring the default hand-tuned weights enter the gene pool).
    """
    island = Island(island_id=island_id)
    if seed_weights is not None:
        island.population.append(create_individual(rng, from_weights=seed_weights))
        for _ in range(pop_size - 1):
            island.population.append(create_individual(rng))
    else:
        for _ in range(pop_size):
            island.population.append(create_individual(rng))
    return island


def migrate_ring(islands: List[Island], num_migrants: int,
                 rng: np.random.RandomState) -> None:
    """Migrate top individuals clockwise around the ring.

    Each island sends its best `num_migrants` individuals to the next island
    (wrapping around). The migrants replace the worst individuals on the
    receiving island.
    """
    n = len(islands)
    # Collect migrants from each island before modifying any
    migrants = []
    for island in islands:
        sorted_pop = sorted(island.population, key=lambda ind: ind.fitness,
                            reverse=True)
        migrants.append([ind.copy() for ind in sorted_pop[:num_migrants]])

    # Insert migrants into the clockwise neighbour
    for i in range(n):
        target = (i + 1) % n
        target_island = islands[target]
        # Sort target population worst-first
        target_island.population.sort(key=lambda ind: ind.fitness)
        # Replace worst individuals with migrants
        for j, migrant in enumerate(migrants[i]):
            if j < len(target_island.population):
                target_island.population[j] = migrant


def evolve_island_generation(island: Island, elite_count: int,
                             tournament_k: int, crossover_alpha: float,
                             mutation_rate: float, mutation_sigma: float,
                             games_per_eval: int,
                             global_elite_weights: Optional[Dict[str, float]],
                             base_seed: int,
                             rng: np.random.RandomState) -> None:
    """Evolve one island for one generation.

    NOTE: Fitness must already be evaluated on all individuals before calling.
    This function handles selection, crossover, mutation, and elitism only.
    """
    pop_size = len(island.population)

    # Sort by fitness (best first)
    island.population.sort(key=lambda ind: ind.fitness, reverse=True)

    # Track best
    island.best_fitness_history.append(island.population[0].fitness)

    # Elitism: preserve top individuals
    new_pop = [ind.copy() for ind in island.population[:elite_count]]

    # Fill the rest with crossover + mutation
    while len(new_pop) < pop_size:
        p1 = tournament_select(island.population, tournament_k, rng)
        p2 = tournament_select(island.population, tournament_k, rng)
        c1, c2 = blx_alpha_crossover(p1, p2, crossover_alpha, rng)
        c1 = mutate(c1, mutation_rate, mutation_sigma, rng)
        c2 = mutate(c2, mutation_rate, mutation_sigma, rng)
        new_pop.append(c1)
        if len(new_pop) < pop_size:
            new_pop.append(c2)

    island.population = new_pop[:pop_size]


def run_ga(args: argparse.Namespace) -> EvolutionResult:
    """Main GA loop with island model and ring topology."""
    rng = np.random.RandomState(args.seed)

    num_islands = args.islands
    pop_per_island = args.population
    total_pop = num_islands * pop_per_island

    num_workers = getattr(args, 'workers', None) or min(num_islands * pop_per_island, multiprocessing.cpu_count())

    if args.verbose:
        print(f"\n{'='*65}")
        print(f" Island-Model GA — Ring Topology")
        print(f" {num_islands} islands × {pop_per_island} individuals = "
              f"{total_pop} total population")
        print(f" Generations: {args.generations}, Games/eval: {args.games_per_eval}")
        print(f" Migration every {args.migration_interval} generations, "
              f"{args.num_migrants} migrant(s)")
        print(f" Workers: {num_workers}, Seed: {args.seed}")
        print(f"{'='*65}\n")

    # Create islands — seed island 0 with default hand-tuned weights
    islands: List[Island] = []
    for i in range(num_islands):
        seed_w = np.array(DEFAULT_WEIGHTS) if i == 0 else None
        island = create_island(i, pop_per_island, rng, seed_weights=seed_w)
        islands.append(island)

    # Track global state
    global_best_fitness = -float("inf")
    global_best_weights = np.array(DEFAULT_WEIGHTS)
    no_improvement_count = 0
    history = []

    t_start = time.time()

    for gen in range(args.generations):
        gen_start = time.time()

        # Decay mutation sigma: linear from sigma_start to sigma_end
        progress = gen / max(1, args.generations - 1)
        mutation_sigma = args.sigma_start + (args.sigma_end - args.sigma_start) * progress

        # Global elite weights for opponent pool
        elite_weights = dict(zip(WEIGHT_NAMES, global_best_weights.tolist()))

        # Collect ALL individuals across ALL islands for parallel evaluation
        gen_seed = args.seed + gen * 10000
        all_individuals = []
        all_seeds = []
        for island in islands:
            island_seed = gen_seed + island.island_id * 1000
            for ind in island.population:
                all_individuals.append(ind)
                all_seeds.append(island_seed)

        # Parallel fitness evaluation across all islands at once
        if num_workers > 1:
            evaluate_population_parallel(
                all_individuals, args.games_per_eval, elite_weights,
                all_seeds, num_workers)
        else:
            for ind, seed in zip(all_individuals, all_seeds):
                evaluate_fitness(ind, args.games_per_eval, elite_weights, seed)

        # Now run selection/crossover/mutation on each island (fast, no games)
        for island in islands:
            island_seed = gen_seed + island.island_id * 1000
            island_rng = np.random.RandomState(island_seed)
            evolve_island_generation(
                island=island,
                elite_count=args.elitism,
                tournament_k=args.tournament_k,
                crossover_alpha=args.crossover_alpha,
                mutation_rate=args.mutation_rate,
                mutation_sigma=mutation_sigma,
                games_per_eval=args.games_per_eval,
                global_elite_weights=elite_weights,
                base_seed=island_seed,
                rng=island_rng,
            )

        # Migration (ring topology)
        if (gen + 1) % args.migration_interval == 0 and gen < args.generations - 1:
            migrate_ring(islands, args.num_migrants, rng)
            if args.verbose:
                print(f"  [Migration] {args.num_migrants} migrant(s) sent "
                      f"clockwise around ring")

        # Find global best across all islands
        gen_best_fitness = -float("inf")
        gen_best_weights = None
        for island in islands:
            for ind in island.population:
                if ind.fitness > gen_best_fitness:
                    gen_best_fitness = ind.fitness
                    gen_best_weights = ind.weights.copy()

        # Update global best
        improved = gen_best_fitness > global_best_fitness
        if improved:
            global_best_fitness = gen_best_fitness
            global_best_weights = gen_best_weights
            no_improvement_count = 0
        else:
            no_improvement_count += 1

        gen_elapsed = time.time() - gen_start

        # Record history
        gen_record = {
            "generation": gen,
            "best_fitness": float(gen_best_fitness),
            "global_best_fitness": float(global_best_fitness),
            "best_weights": dict(zip(WEIGHT_NAMES, gen_best_weights.tolist())),
            "mutation_sigma": round(mutation_sigma, 4),
            "elapsed_seconds": round(gen_elapsed, 2),
            "island_best": [
                float(island.population[0].fitness) if island.population else 0.0
                for island in islands
            ],
        }
        history.append(gen_record)

        if args.verbose:
            w_str = ", ".join(f"{n}={v:.3f}" for n, v in
                              zip(WEIGHT_NAMES, gen_best_weights))
            marker = " *" if improved else ""
            print(f"  Gen {gen:3d}/{args.generations} | "
                  f"best={gen_best_fitness:7.1f} | "
                  f"global={global_best_fitness:7.1f}{marker} | "
                  f"σ={mutation_sigma:.3f} | "
                  f"{gen_elapsed:.1f}s | {w_str}")

        # Early stopping
        if no_improvement_count >= args.early_stop:
            if args.verbose:
                print(f"\n  Early stopping: no improvement for "
                      f"{args.early_stop} generations.")
            break

    total_elapsed = time.time() - t_start

    best_weights_dict = dict(zip(WEIGHT_NAMES, global_best_weights.tolist()))

    if args.verbose:
        print(f"\n{'='*65}")
        print(f" Evolution complete in {total_elapsed:.1f}s")
        print(f" Best fitness: {global_best_fitness:.1f}")
        print(f" Best weights: {best_weights_dict}")
        print(f"{'='*65}\n")

    config = {
        "islands": num_islands,
        "population_per_island": pop_per_island,
        "total_population": total_pop,
        "generations": args.generations,
        "games_per_eval": args.games_per_eval,
        "tournament_k": args.tournament_k,
        "crossover_alpha": args.crossover_alpha,
        "mutation_rate": args.mutation_rate,
        "sigma_start": args.sigma_start,
        "sigma_end": args.sigma_end,
        "elitism": args.elitism,
        "migration_interval": args.migration_interval,
        "num_migrants": args.num_migrants,
        "early_stop": args.early_stop,
        "weight_bounds": list(WEIGHT_BOUNDS),
        "seed": args.seed,
        "total_elapsed_seconds": round(total_elapsed, 2),
    }

    return EvolutionResult(
        best_weights=best_weights_dict,
        best_fitness=float(global_best_fitness),
        generation=len(history) - 1,
        islands=num_islands,
        history=history,
        config=config,
    )


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Evolve EnhancedHeuristicAgent weights via Island-Model GA (ring topology)")

    # Island model
    parser.add_argument("--islands", type=int, default=7,
                        help="Number of islands in ring topology (default: 7)")
    parser.add_argument("--population", type=int, default=6,
                        help="Population per island (default: 6)")
    parser.add_argument("--migration-interval", type=int, default=5,
                        help="Migrate every N generations (default: 5)")
    parser.add_argument("--num-migrants", type=int, default=1,
                        help="Number of migrants per migration event (default: 1)")

    # GA parameters
    parser.add_argument("--generations", type=int, default=30,
                        help="Maximum generations (default: 30)")
    parser.add_argument("--games-per-eval", type=int, default=10,
                        help="Games per fitness evaluation (default: 10)")
    parser.add_argument("--tournament-k", type=int, default=3,
                        help="Tournament selection size (default: 3)")
    parser.add_argument("--crossover-alpha", type=float, default=0.5,
                        help="BLX-alpha crossover parameter (default: 0.5)")
    parser.add_argument("--mutation-rate", type=float, default=0.3,
                        help="Per-weight mutation probability (default: 0.3)")
    parser.add_argument("--sigma-start", type=float, default=0.5,
                        help="Initial mutation standard deviation (default: 0.5)")
    parser.add_argument("--sigma-end", type=float, default=0.1,
                        help="Final mutation standard deviation (default: 0.1)")
    parser.add_argument("--elitism", type=int, default=2,
                        help="Number of elite individuals preserved (default: 2)")
    parser.add_argument("--early-stop", type=int, default=10,
                        help="Stop after N generations without improvement (default: 10)")

    # General
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--workers", type=int, default=0,
                        help="Parallel workers (0=auto, 1=sequential, default: 0)")
    parser.add_argument("--output", type=str, default="data/ga_evolved_weights.json",
                        help="Output JSON path (default: data/ga_evolved_weights.json)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print progress each generation")

    args = parser.parse_args()

    # Validate
    if args.population < args.elitism + 2:
        parser.error(f"Population ({args.population}) must be >= elitism "
                     f"({args.elitism}) + 2")
    if args.islands < 2:
        parser.error("Need at least 2 islands for ring topology")

    result = run_ga(args)

    # Save output
    output_data = {
        "best_weights": result.best_weights,
        "best_fitness": result.best_fitness,
        "generation": result.generation,
        "islands": result.islands,
        "default_weights": dict(zip(WEIGHT_NAMES, DEFAULT_WEIGHTS)),
        "config": result.config,
        "history": result.history,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Results saved to {args.output}")
    print(f"Best weights: {result.best_weights}")
    print(f"Best fitness: {result.best_fitness:.1f}")


if __name__ == "__main__":
    main()
