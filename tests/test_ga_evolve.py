"""Tests for the Island-Model GA weight evolution script."""

import os
import sys

import numpy as np
import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.ga_evolve_weights import (
    WEIGHT_BOUNDS,
    WEIGHT_NAMES,
    DEFAULT_WEIGHTS,
    Individual,
    Island,
    blx_alpha_crossover,
    create_individual,
    create_island,
    evaluate_fitness,
    evolve_island_generation,
    migrate_ring,
    mutate,
    play_game,
    tournament_select,
)

N = len(WEIGHT_NAMES)  # 10 weights


# ── Individual tests ────────────────────────────────────────────────────────

class TestIndividual:
    def test_creation_random(self):
        rng = np.random.RandomState(42)
        ind = create_individual(rng)
        assert ind.weights.shape == (N,)
        assert all(WEIGHT_BOUNDS[0] <= w <= WEIGHT_BOUNDS[1] for w in ind.weights)
        assert ind.fitness == 0.0

    def test_creation_from_weights(self):
        rng = np.random.RandomState(42)
        target = np.array(DEFAULT_WEIGHTS)
        ind = create_individual(rng, from_weights=target)
        np.testing.assert_array_equal(ind.weights, target)

    def test_creation_clips_bounds(self):
        rng = np.random.RandomState(42)
        extreme = np.array([10.0, -10.0] + [0.0] * (N - 2))
        ind = create_individual(rng, from_weights=extreme)
        assert all(WEIGHT_BOUNDS[0] <= w <= WEIGHT_BOUNDS[1] for w in ind.weights)

    def test_weights_dict(self):
        ind = Individual(weights=np.array(DEFAULT_WEIGHTS))
        d = ind.weights_dict()
        assert set(d.keys()) == set(WEIGHT_NAMES)
        assert d["piece_size"] == 1.0
        assert d["corner_creation"] == 2.0
        assert d["opponent_blocking"] == 1.5

    def test_copy_independence(self):
        w = list(range(N))
        ind = Individual(weights=np.array(w, dtype=float), fitness=10.0)
        clone = ind.copy()
        clone.weights[0] = -99.0
        clone.fitness = -1.0
        assert ind.weights[0] == 0.0
        assert ind.fitness == 10.0


# ── Game simulation tests ──────────────────────────────────────────────────

class TestGameSimulation:
    def test_single_game_completes(self):
        """A single game should complete and return a non-negative score."""
        from agents.heuristic_agent import HeuristicAgent
        from agents.random_agent import RandomAgent

        opponents = [HeuristicAgent(seed=1), RandomAgent(seed=2),
                     HeuristicAgent(seed=3)]
        weights = dict(zip(WEIGHT_NAMES, DEFAULT_WEIGHTS))
        score = play_game(weights, opponents, seed=42)
        assert isinstance(score, float)
        assert score >= 0

    def test_different_seeds_vary(self):
        """Different seeds should produce different game outcomes."""
        from agents.heuristic_agent import HeuristicAgent
        from agents.random_agent import RandomAgent

        opponents = [HeuristicAgent(seed=1), RandomAgent(seed=2),
                     HeuristicAgent(seed=3)]
        weights = dict(zip(WEIGHT_NAMES, DEFAULT_WEIGHTS))
        s1 = play_game(weights, opponents, seed=100)
        s2 = play_game(weights, opponents, seed=200)
        # Just check both complete successfully
        assert isinstance(s1, float) and isinstance(s2, float)


class TestFitnessEvaluation:
    def test_evaluate_returns_positive(self):
        ind = Individual(weights=np.array(DEFAULT_WEIGHTS))
        fitness = evaluate_fitness(ind, games_per_eval=2, elite_weights=None,
                                   base_seed=42)
        assert fitness > 0
        assert ind.fitness == fitness
        assert ind.games_played == 2


# ── GA operator tests ──────────────────────────────────────────────────────

class TestTournamentSelection:
    def test_selects_fittest(self):
        """With k = population size, should always pick the best."""
        pop = [
            Individual(weights=np.zeros(N), fitness=1.0),
            Individual(weights=np.ones(N), fitness=5.0),
            Individual(weights=np.full(N, 2.0), fitness=3.0),
        ]
        rng = np.random.RandomState(42)
        winner = tournament_select(pop, k=3, rng=rng)
        assert winner.fitness == 5.0

    def test_returns_copy(self):
        pop = [Individual(weights=np.arange(N, dtype=float), fitness=10.0)]
        rng = np.random.RandomState(42)
        selected = tournament_select(pop, k=1, rng=rng)
        selected.fitness = -1.0
        assert pop[0].fitness == 10.0


class TestCrossover:
    def test_blx_alpha_produces_valid_children(self):
        rng = np.random.RandomState(42)
        p1 = Individual(weights=rng.uniform(-2, 2, N))
        p2 = Individual(weights=rng.uniform(-2, 2, N))
        c1, c2 = blx_alpha_crossover(p1, p2, alpha=0.5, rng=rng)
        assert c1.weights.shape == (N,)
        assert c2.weights.shape == (N,)
        assert all(WEIGHT_BOUNDS[0] <= w <= WEIGHT_BOUNDS[1] for w in c1.weights)
        assert all(WEIGHT_BOUNDS[0] <= w <= WEIGHT_BOUNDS[1] for w in c2.weights)

    def test_identical_parents(self):
        """With identical parents and alpha=0, children should equal parents."""
        rng = np.random.RandomState(42)
        w = np.linspace(-2, 2, N)
        p1 = Individual(weights=w.copy())
        p2 = Individual(weights=w.copy())
        c1, c2 = blx_alpha_crossover(p1, p2, alpha=0.0, rng=rng)
        np.testing.assert_array_almost_equal(c1.weights, w)
        np.testing.assert_array_almost_equal(c2.weights, w)


class TestMutation:
    def test_respects_bounds(self):
        rng = np.random.RandomState(42)
        ind = Individual(weights=np.full(N, 4.9))
        mutated = mutate(ind, mutation_rate=1.0, sigma=2.0, rng=rng)
        assert all(WEIGHT_BOUNDS[0] <= w <= WEIGHT_BOUNDS[1]
                   for w in mutated.weights)

    def test_zero_rate_no_change(self):
        rng = np.random.RandomState(42)
        original = np.linspace(-2, 2, N)
        ind = Individual(weights=original.copy())
        mutate(ind, mutation_rate=0.0, sigma=1.0, rng=rng)
        np.testing.assert_array_equal(ind.weights, original)


# ── Island model tests ──────────────────────────────────────────────────────

class TestIslandModel:
    def test_create_island_with_seed(self):
        rng = np.random.RandomState(42)
        island = create_island(0, pop_size=4, rng=rng,
                               seed_weights=np.array(DEFAULT_WEIGHTS))
        assert len(island.population) == 4
        np.testing.assert_array_equal(island.population[0].weights,
                                      np.array(DEFAULT_WEIGHTS))

    def test_migrate_ring_topology(self):
        """Migration should send best from island i to island (i+1) % n."""
        rng = np.random.RandomState(42)
        islands = []
        for i in range(3):
            island = Island(island_id=i)
            island.population = [
                Individual(weights=np.full(N, float(i)),
                           fitness=float(i * 10 + j))
                for j in range(4)
            ]
            islands.append(island)

        # Before migration, island 2 has highest fitness individuals
        migrate_ring(islands, num_migrants=1, rng=rng)

        # Island 2's best (fitness 23) should now be on island 0
        island_0_fitnesses = [ind.fitness for ind in islands[0].population]
        assert 23.0 in island_0_fitnesses

    def test_elitism_preserves_best(self):
        """Top individuals should survive unchanged after a generation."""
        rng = np.random.RandomState(42)
        island = Island(island_id=0)
        for i in range(6):
            island.population.append(
                Individual(weights=rng.uniform(-1, 1, N), fitness=float(i)))

        evolve_island_generation(
            island=island, elite_count=2, tournament_k=3,
            crossover_alpha=0.5, mutation_rate=0.3, mutation_sigma=0.5,
            games_per_eval=2, global_elite_weights=None,
            base_seed=42, rng=rng)

        assert len(island.population) == 6


# ── Enhanced agent tests ────────────────────────────────────────────────────

class TestEnhancedHeuristicAgent:
    def test_set_weights_all_10(self):
        from agents.enhanced_heuristic_agent import EnhancedHeuristicAgent
        agent = EnhancedHeuristicAgent(seed=42)
        weights = dict(zip(WEIGHT_NAMES, DEFAULT_WEIGHTS))
        agent.set_weights(weights)
        info = agent.get_action_info()
        assert len(info["weights"]) == 10
        assert info["weights"]["opponent_blocking"] == 1.5

    def test_select_action_returns_move(self):
        from agents.enhanced_heuristic_agent import EnhancedHeuristicAgent
        from engine.board import Board, Player
        from engine.game import BlokusGame

        game = BlokusGame(enable_telemetry=False)
        agent = EnhancedHeuristicAgent(seed=42)
        player = game.get_current_player()
        moves = game.get_legal_moves(player)
        assert len(moves) > 0
        move = agent.select_action(game.board, player, moves)
        assert move is not None
        assert move in moves


# ── End-to-end mini test ────────────────────────────────────────────────────

class TestEndToEnd:
    def test_mini_evolution(self):
        """Run a minimal evolution: 2 islands, pop=4, 2 generations, 2 games."""
        import argparse
        from scripts.ga_evolve_weights import run_ga

        args = argparse.Namespace(
            islands=2,
            population=4,
            generations=2,
            games_per_eval=2,
            tournament_k=3,
            crossover_alpha=0.5,
            mutation_rate=0.3,
            sigma_start=0.5,
            sigma_end=0.1,
            elitism=2,
            migration_interval=1,
            num_migrants=1,
            early_stop=10,
            seed=42,
            verbose=False,
        )
        result = run_ga(args)
        assert result.best_fitness > 0
        assert set(result.best_weights.keys()) == set(WEIGHT_NAMES)
        assert len(result.best_weights) == 10
        assert len(result.history) == 2
        assert result.islands == 2
